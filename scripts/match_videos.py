#!/usr/bin/env python3
import argparse
import json
import re
import unicodedata
from pathlib import Path

from common import add_execution_flags, load_config, read_json

VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}


def plain_creator(value):
    text = "" if value is None else str(value).strip()
    match = re.match(r"^\[([^]]+)]\([^)]+\)", text)
    return (match.group(1) if match else text).strip().lstrip("@")


def match_key(value):
    text = unicodedata.normalize("NFKC", plain_creator(value)).casefold()
    return re.sub(r"[\s._-]+", "", text)


def build_manifest(records, video_dir, fields):
    files = sorted(
        p.resolve() for p in Path(video_dir).iterdir()
        if p.is_file() and p.suffix.casefold() in VIDEO_EXTENSIONS
    )
    files_by_key = {}
    for path in files:
        files_by_key.setdefault(match_key(path.stem), []).append(path)
    normalized = []
    records_by_key = {}
    for row in records:
        values = row.get("fields", row)
        creator = plain_creator(values.get(fields["creator"]))
        item = {
            "record_id": row.get("record_id", row.get("id")),
            "creator": creator,
            "source_url": values.get(fields["source_url"]),
            "attachment_empty": not bool(values.get(fields["video"])),
        }
        normalized.append(item)
        records_by_key.setdefault(match_key(creator), []).append(item)
    matched, unmatched, ambiguous, used = [], [], [], set()
    for item in normalized:
        candidates = files_by_key.get(match_key(item["creator"]), [])
        duplicate_records = records_by_key.get(match_key(item["creator"]), [])
        if not item["record_id"] or not item["creator"] or not item["source_url"]:
            unmatched.append({**item, "reason": "missing stable record fields"})
        elif len(candidates) == 1 and len(duplicate_records) == 1:
            used.add(candidates[0])
            matched.append({**item, "file": str(candidates[0])})
        elif len(candidates) > 1 or len(duplicate_records) > 1:
            ambiguous.append({**item, "files": [str(path) for path in candidates], "record_count": len(duplicate_records)})
        else:
            unmatched.append({**item, "reason": "local video not found"})
    return {
        "matched": matched,
        "unmatched_records": unmatched,
        "unmatched_files": [str(path) for path in files if path not in used],
        "ambiguous": ambiguous,
    }


def main():
    parser = argparse.ArgumentParser(description="Match records to local videos without guessing.")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--records", required=True, type=Path)
    parser.add_argument("--video-dir", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    add_execution_flags(parser)
    args = parser.parse_args()
    config = load_config(args.config, resolve_modules=False)
    fields = config.get("feishu", {}).get("fields", {"creator": "creator", "source_url": "source_url", "video": "video"})
    records = read_json(args.records)
    if isinstance(records, dict):
        records = records.get("records", records.get("data"))
    if not isinstance(records, list):
        raise ValueError("records input must resolve to a JSON array")
    video_dir = args.video_dir or Path(config["paths"]["video_root"])
    result = build_manifest(records, video_dir, fields)
    summary = {key: len(value) for key, value in result.items()}
    if not args.execute:
        print(json.dumps({"dry_run": True, "summary": summary, "manifest": result}, ensure_ascii=False, indent=2))
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"dry_run": False, "output": str(args.output), "summary": summary}, ensure_ascii=False))


if __name__ == "__main__":
    main()

