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
    minimum = settings.get("min_likes_exclusive")
    if minimum is not None and (type(minimum) is not int or minimum < 0):
        raise ValueError("discovery.min_likes_exclusive must be null or a nonnegative integer")
    if "min_likes" in settings:
        raise ValueError("use min_likes_exclusive to make the boundary explicit")
    if settings.get("selection_mode", "proven") not in ("proven", "include_potential"):
        raise ValueError("selection_mode must be proven or include_potential")
    return settings


def brief_fingerprint(config):
    brief = {"account": config["account"], "discovery": config["discovery"]}
    encoded = json.dumps(brief, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def evidence_reasons(evidence, source_url, settings, now):
    reasons = []
    if not isinstance(evidence, dict):
        return ["heat evidence must be an object"]
    try:
        source = normalize_instagram_url(source_url)
        observed = normalize_instagram_url(evidence.get("source_url", ""))
        if source["shortcode"] != observed["shortcode"]:
            reasons.append("heat evidence belongs to a different post")
    except ValueError:
        reasons.append("missing or invalid original/evidence URL")
    if evidence.get("metric") not in ("likes", "views"):
        reasons.append("heat metric must be post likes or video views")
    if type(evidence.get("value")) is not int or evidence["value"] <= 0:
        reasons.append("heat evidence needs a positive exact integer count")
    if evidence.get("evidence_type") not in ("instagram_page", "instagram_metadata"):
        reasons.append("heat needs primary Instagram evidence")
    try:
        age = now - timestamp(evidence["verified_at"])
        if age < timedelta(0) or age > timedelta(hours=settings.get("verification_max_age_hours", 24)):
            reasons.append("heat evidence is stale or future-dated")
    except (KeyError, TypeError, ValueError):
        reasons.append("verification timestamp is missing or invalid")
    return reasons


def candidate_reasons(item, settings, now):
    reasons = []
    creator = item.get("creator")
    if not isinstance(creator, str) or not creator.strip().lstrip("@"):
        reasons.append("creator is missing")
    evidence = item.get("heat_evidence")
    if not isinstance(evidence, list) or not evidence:
        reasons.append("verified heat evidence is required even without a likes filter")
        evidence = []
    for observation in evidence:
        reasons.extend(evidence_reasons(observation, item.get("source_url", ""), settings, now))
    minimum = settings.get("min_likes_exclusive")
    if minimum is not None and not any(
        isinstance(observation, dict) and observation.get("metric") == "likes"
        and type(observation.get("value")) is int and observation["value"] > minimum
        for observation in evidence
    ):
        reasons.append(f"exact original-post likes must be greater than {minimum}")
    status = item.get("trend_status")
    if status not in ("proven", "potential"):
        reasons.append("trend status is unknown or unverified")
    elif status == "potential" and settings.get("selection_mode", "proven") != "include_potential":
        reasons.append("potential candidates are not enabled")
    if not isinstance(item.get("trend_reason"), str) or not item["trend_reason"].strip():
        reasons.append("explain the recent-breakout assessment, not just a counter")
    basis = item.get("trend_basis")
    if basis not in ("recent_high_volume", "relative_outperformance", "observed_growth"):
        reasons.append("a supported heat assessment basis is required")
    if basis in ("recent_high_volume", "relative_outperformance"):
        comparison = item.get("comparison")
        if not isinstance(comparison, dict) or not isinstance(comparison.get("context"), str) or not comparison["context"].strip():
            reasons.append("a sourced comparison context is required")
        else:
            urls = comparison.get("source_urls")
            if not isinstance(urls, list) or not urls:
                reasons.append("comparison source URLs are required")
            else:
                try:
                    for url in urls:
                        normalize_instagram_url(url)
                except ValueError:
                    reasons.append("comparison source URLs must identify Instagram posts")
    if basis == "observed_growth":
        observations = item.get("growth_observations")
        if not isinstance(observations, list) or len(observations) < 2:
            reasons.append("growth requires at least two timed observations")
        else:
            growth_errors = []
            for observation in observations:
                growth_errors.extend(evidence_reasons(observation, item.get("source_url", ""), settings, now))
            reasons.extend(growth_errors)
            if not growth_errors:
                ordered = sorted(observations, key=lambda observation: timestamp(observation["verified_at"]))
                if len({observation["metric"] for observation in ordered}) != 1 or any(
                    timestamp(right["verified_at"]) <= timestamp(left["verified_at"]) or right["value"] <= left["value"]
                    for left, right in zip(ordered, ordered[1:])
                ):
                    reasons.append("growth observations need the same metric and increasing times/counts")
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
    selected, potential, excluded = [], [], []
    for item in sorted(candidates, key=lambda item: item.get("trend_status") == "potential"):
        reasons = candidate_reasons(item, settings, now)
        if not reasons:
            base = normalize_instagram_url(item["source_url"])
            if base["shortcode"] in seen:
                reasons.append("duplicate or already used source")
            elif len(selected) + len(potential) >= settings.get("limit", 5):
                reasons.append("confirmed selection count already reached")
            else:
                seen.add(base["shortcode"])
                destination = potential if item["trend_status"] == "potential" else selected
                destination.append({**item, **base, "creator": item["creator"].strip().lstrip("@")})
        if reasons:
            excluded.append({"source_url": item.get("source_url"), "reasons": reasons})
    return {
        "schema_version": 2,
        "account_slug": config["account"]["slug"],
        "brief_fingerprint": brief_fingerprint(config),
        "generated_at": now.isoformat(),
        "min_likes_exclusive": settings.get("min_likes_exclusive"),
        "videos": selected,
        "potential": potential,
        "excluded": excluded,
        "counts": {"reviewed": len(candidates), "selected": len(selected), "potential": len(potential), "excluded": len(excluded)},
    }


def revalidate_selection(config, selection, now=None):
    if not isinstance(selection, dict) or selection.get("schema_version") != 2:
        raise ValueError("unsupported selection manifest; refresh evidence and regenerate schema version 2")
    if selection.get("account_slug") != config["account"]["slug"]:
        raise ValueError("selection belongs to a different account")
    if selection.get("brief_fingerprint") != brief_fingerprint(config):
        raise ValueError("the account brief has changed; review candidates and reselect")
    if any(item.get("trend_status") != "proven" for item in selection.get("videos", []) if isinstance(item, dict)):
        raise ValueError("potential items cannot enter automatic production; the user must choose direct intake")
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
