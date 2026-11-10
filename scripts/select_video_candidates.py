#!/usr/bin/env python3
"""Validate agent-collected discovery evidence; never scrape or invent evidence."""

import argparse
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from common import add_execution_flags, load_config, read_json
from run_instagram_pipeline import normalize_instagram_url

MIN_LIKES_EXCLUSIVE = 10000
LOADS = {"none": 0, "low": 1, "medium": 2, "high": 3}


def timestamp(value):
    result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamps must include a timezone")
    return result.astimezone(timezone.utc)


def brief_missing(config):
    account = config.get("account", {})
    discovery = config.get("discovery", {})
    missing = []
    for key in ("positioning", "audience"):
        if not isinstance(account.get(key), str) or not account[key].strip():
            missing.append(f"account.{key}")
    for key in ("topics", "content_types"):
        value = discovery.get(key)
        if not isinstance(value, list) or not value or not all(isinstance(x, str) and x.strip() for x in value):
            missing.append(f"discovery.{key}")
    for key in ("source_platform", "destination_platform"):
        if not isinstance(discovery.get(key), str) or not discovery[key].strip():
            missing.append(f"discovery.{key}")
    if discovery.get("brief_confirmed") is not True:
        missing.append("discovery.brief_confirmed")
    return missing


def validate_settings(config):
    missing = brief_missing(config)
    if missing:
        raise ValueError("ask the user before searching: " + ", ".join(missing))
    settings = config["discovery"]
    if settings["source_platform"] != "instagram":
        raise ValueError("the current download adapter supports Instagram only")
    for key, default in (("lookback_days", 7), ("limit", 5), ("verification_max_age_hours", 24)):
        value = settings.get(key, default)
        if type(value) is not int or value <= 0:
            raise ValueError(f"discovery.{key} must be a positive integer")
    duration = settings.get("max_duration_seconds", 30)
    if type(duration) not in (int, float) or not math.isfinite(duration) or duration <= 0:
        raise ValueError("discovery.max_duration_seconds must be positive and finite")
    if settings.get("max_subtitle_load", "low") not in LOADS:
        raise ValueError("invalid discovery.max_subtitle_load")
    # This is deliberately not a configurable threshold.
    if "min_likes" in settings or "min_likes_exclusive" in settings:
        raise ValueError("remove the configurable likes threshold; likes must be strictly greater than 10000")
    return settings


def brief_fingerprint(config):
    brief = {"account": config["account"], "discovery": config["discovery"]}
    encoded = json.dumps(brief, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def candidate_reasons(item, settings, now):
    reasons = []
    try:
        source = normalize_instagram_url(item.get("source_url", ""))
        evidence = normalize_instagram_url(item.get("likes_source_url", ""))
        if source["shortcode"] != evidence["shortcode"]:
            reasons.append("likes evidence belongs to a different post")
    except ValueError:
        reasons.append("missing or invalid original/evidence URL")
    creator = item.get("creator")
    if not isinstance(creator, str) or not creator.strip().lstrip("@"):
        reasons.append("creator is missing")
    likes = item.get("like_count")
    if type(likes) is not int or likes <= MIN_LIKES_EXCLUSIVE:
        reasons.append("exact original-post likes must be greater than 10000")
    if item.get("likes_evidence_type") not in ("instagram_page", "instagram_metadata"):
        reasons.append("likes need primary Instagram evidence")
    try:
        age = now - timestamp(item["verified_at"])
        if age < timedelta(0) or age > timedelta(hours=settings.get("verification_max_age_hours", 24)):
            reasons.append("likes evidence is stale or future-dated")
    except (KeyError, TypeError, ValueError):
        reasons.append("verification timestamp is missing or invalid")
    try:
        published = timestamp(item["published_at"])
        if published > now or published < now - timedelta(days=settings.get("lookback_days", 7)):
            reasons.append("publication is outside the confirmed recent window")
    except (KeyError, TypeError, ValueError):
        reasons.append("publication timestamp is missing or invalid")
    duration = item.get("duration")
    if type(duration) not in (int, float) or not math.isfinite(duration) or not 0 < duration <= settings.get("max_duration_seconds", 30):
        reasons.append("duration is missing or exceeds the confirmed limit")
    if item.get("duration_evidence") not in ("player", "media_metadata"):
        reasons.append("duration has not been verified against the video")
    if item.get("video_reviewed") is not True or item.get("relevant") is not True:
        reasons.append("actual video review and account relevance are required")
    if not isinstance(item.get("fit_reason"), str) or not item["fit_reason"].strip():
        reasons.append("account-fit explanation is missing")
    load = item.get("subtitle_load")
    if not isinstance(load, str) or load not in LOADS or LOADS[load] > LOADS[settings.get("max_subtitle_load", "low")]:
        reasons.append("subtitle load is unknown or exceeds the confirmed preference")
    return reasons


def select_candidates(config, candidates, now=None, seen_urls=()):
    settings = validate_settings(config)
    now = now or datetime.now(timezone.utc)
    if not isinstance(candidates, list) or not all(isinstance(item, dict) for item in candidates):
        raise ValueError("candidates must be a list of objects")
    seen = {normalize_instagram_url(url)["shortcode"] for url in seen_urls}
    selected, excluded = [], []
    for item in candidates:
        reasons = candidate_reasons(item, settings, now)
        if not reasons:
            base = normalize_instagram_url(item["source_url"])
            if base["shortcode"] in seen:
                reasons.append("duplicate or already used source")
            elif len(selected) >= settings.get("limit", 5):
                reasons.append("confirmed selection count already reached")
            else:
                seen.add(base["shortcode"])
                selected.append({**item, **base, "creator": item["creator"].strip().lstrip("@")})
        if reasons:
            excluded.append({"source_url": item.get("source_url"), "reasons": reasons})
    return {
        "schema_version": 1,
        "account_slug": config["account"]["slug"],
        "brief_fingerprint": brief_fingerprint(config),
        "generated_at": now.isoformat(),
        "min_likes_exclusive": MIN_LIKES_EXCLUSIVE,
        "videos": selected,
        "excluded": excluded,
        "counts": {"reviewed": len(candidates), "selected": len(selected), "excluded": len(excluded)},
    }


def revalidate_selection(config, selection, now=None):
    if not isinstance(selection, dict) or selection.get("schema_version") != 1:
        raise ValueError("unsupported selection manifest")
    if selection.get("account_slug") != config["account"]["slug"]:
        raise ValueError("selection belongs to a different account")
    if selection.get("brief_fingerprint") != brief_fingerprint(config):
        raise ValueError("the account brief has changed; review candidates and reselect")
    result = select_candidates(config, selection.get("videos"), now=now)
    if not result["videos"] or result["excluded"]:
        raise ValueError("selection is empty or no longer passes discovery gates; refresh and reselect")
    return result["videos"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--candidates", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    add_execution_flags(parser)
    args = parser.parse_args()
    config = load_config(args.config, resolve_modules=False)
    if not config["modules"].get("video_scout"):
        raise ValueError("modules.video_scout is disabled")
    payload = read_json(args.candidates)
    result = select_candidates(config, payload["candidates"], seen_urls=payload.get("seen_urls", []))
    if args.execute:
        if args.output is None:
            raise ValueError("--output is required to write a selection manifest")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"dry_run": not args.execute, **result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
