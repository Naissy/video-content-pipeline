#!/usr/bin/env python3
"""Normalize and download public Instagram videos without browser cookies."""

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

from common import add_execution_flags, load_config

CONTENT_TYPES = {"reel", "p", "tv"}
SHORTCODE = re.compile(r"^[A-Za-z0-9_-]+$")
MEDIA_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm"}


def normalize_instagram_url(value):
    raw = str(value).strip()
    parsed = urlsplit(raw)
    host = (parsed.hostname or "").casefold()
    if parsed.scheme != "https" or host not in {"instagram.com", "www.instagram.com", "m.instagram.com"}:
        raise ValueError("only public https Instagram URLs are supported")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2 or parts[0].casefold() not in CONTENT_TYPES or not SHORTCODE.fullmatch(parts[1]):
        raise ValueError("expected an Instagram /reel/, /p/, or /tv/ content URL")
    kind, shortcode = parts[0].casefold(), parts[1]
    return {
        "source_platform": "instagram",
        "content_type": kind,
        "shortcode": shortcode,
        "stable_id": f"instagram:{kind}:{shortcode}",
        "source_url": f"https://www.instagram.com/{kind}/{shortcode}/",
    }


def collect_urls(values, url_file=None):
    raw = list(values or [])
    if url_file:
        raw.extend(
            line.strip() for line in Path(url_file).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
    if not raw:
        raise ValueError("provide at least one --url or --url-file")
    unique, duplicates, seen = [], [], set()
    for value in raw:
        item = normalize_instagram_url(value)
        if item["stable_id"] in seen:
            duplicates.append(item)
        else:
            seen.add(item["stable_id"])
            unique.append(item)
    return unique, duplicates


def find_media(output_root, shortcode):
    candidates = sorted(
        path for path in output_root.glob(f"instagram_{shortcode}.*")
        if path.is_file() and path.suffix.casefold() in MEDIA_SUFFIXES
    )
    return candidates[0] if len(candidates) == 1 else None


def metadata_to_item(base, info, media, reused=False):
    creator = info.get("uploader_id") or info.get("uploader") or info.get("channel")
    duration = info.get("duration")
    if not creator:
        raise RuntimeError("downloaded metadata is missing the creator")
    if duration is None or float(duration) <= 0:
        raise RuntimeError("downloaded metadata is missing a valid duration")
    return {
        **base,
        "creator": str(creator).lstrip("@"),
        "file": str(media.resolve()),
        "duration": float(duration),
        "slug": base["shortcode"],
        "download_status": "reused" if reused else "downloaded",
        "subtitles": [],
        "content_status": "pending_analysis",
    }


def download_one(item, output_root, downloader, timeout):
    existing = find_media(output_root, item["shortcode"])
    info_path = output_root / f"instagram_{item['shortcode']}.info.json"
    if existing and info_path.is_file():
        info = json.loads(info_path.read_text(encoding="utf-8"))
        return metadata_to_item(item, info, existing, reused=True)
    output_template = str(output_root / f"instagram_{item['shortcode']}.%(ext)s")
    command = [
        downloader,
        "--no-playlist",
        "--no-overwrites",
        "--restrict-filenames",
        "--write-info-json",
        "--print-json",
        "--output",
        output_template,
        item["source_url"],
    ]
    result = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
    if result.returncode != 0:
        reason = (result.stderr or result.stdout).strip().splitlines()
        raise RuntimeError(reason[-1] if reason else "yt-dlp failed")
    lines = [line for line in result.stdout.splitlines() if line.strip().startswith("{")]
    if not lines:
        raise RuntimeError("yt-dlp returned no metadata")
    info = json.loads(lines[-1])
    media = find_media(output_root, item["shortcode"])
    if not media:
        raise RuntimeError("download completed but exactly one media file was not found")
    return metadata_to_item(item, info, media)


def main():
    parser = argparse.ArgumentParser(description="Prepare one or more public Instagram videos for content and Jianying delivery.")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--url", action="append", default=[])
    parser.add_argument("--url-file", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--sync-feishu", action="store_true", help="Request optional Feishu upsert after content generation")
    add_execution_flags(parser)
    args = parser.parse_args()

    config = load_config(args.config, resolve_modules=False)
    if not config["modules"].get("instagram_intake"):
        raise RuntimeError("modules.instagram_intake is disabled")
    settings = config["instagram"]
    if not settings.get("public_only", True):
        raise RuntimeError("this skill supports public-only Instagram intake")
    links, duplicates = collect_urls(args.url, args.url_file)
    maximum = int(settings.get("max_urls_per_batch", 20))
    if len(links) > maximum:
        raise RuntimeError(f"batch contains {len(links)} unique URLs; configured maximum is {maximum}")
    if args.sync_feishu and not config["modules"].get("feishu"):
        raise RuntimeError("--sync-feishu requires modules.feishu=true")

    downloader = settings.get("downloader", "yt-dlp")
    output_root = Path(config["paths"].get("download_root", config["paths"]["video_root"])).expanduser().resolve()
    manifest_path = args.manifest or Path(config["paths"]["work_root"]) / "instagram-ingest.json"
    plan = {
        "dry_run": not args.execute,
        "downloader": downloader,
        "downloader_available": shutil.which(downloader) is not None,
        "public_only": True,
        "output_root": str(output_root),
        "manifest": str(manifest_path),
        "links": links,
        "duplicates": duplicates,
        "requested_outputs": {"jianying": True, "feishu": args.sync_feishu},
    }
    if not args.execute:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return
    if not plan["downloader_available"]:
        raise RuntimeError(f"required downloader is unavailable: {downloader}")
    output_root.mkdir(parents=True, exist_ok=True)
    downloaded, failures = [], []
    timeout = int(settings.get("timeout_seconds_per_url", 120))
    for item in links:
        try:
            downloaded.append(download_one(item, output_root, downloader, timeout))
        except Exception as error:
            failures.append({**item, "stage": "download", "reason": str(error)})
    result = {
        "videos": downloaded,
        "duplicates": duplicates,
        "failures": failures,
        "requested_outputs": {"jianying": True, "feishu": args.sync_feishu},
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"dry_run": False, "manifest": str(manifest_path), "downloaded": len(downloaded), "duplicates": len(duplicates), "failures": len(failures)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

