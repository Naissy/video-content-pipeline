#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from common import add_execution_flags, load_config


def main():
    parser = argparse.ArgumentParser(description="Validate and route a configured video workflow.")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    add_execution_flags(parser)
    args = parser.parse_args()

    config = load_config(args.config, resolve_modules=bool(args.execute))
    modules = config["modules"]
    stages = ["validate"]
    scout_brief_missing = []
    if modules.get("video_scout"):
        from select_video_candidates import brief_missing, validate_settings
        scout_brief_missing = brief_missing(config)
        if not scout_brief_missing:
            validate_settings(config)
        stages.extend(["account_brief", "recent_trend_research", "verified_video_selection"])
    if modules.get("instagram_intake"):
        if "instagram" not in config:
            raise ValueError("instagram configuration is required when modules.instagram_intake is enabled")
        stages.append("instagram_public_download")
    if modules.get("local_intake"):
        stages.append("local_intake_and_match")
    if modules.get("xiaohongshu_research"):
        if "xiaohongshu" not in config:
            raise ValueError("xiaohongshu configuration is required when modules.xiaohongshu_research is enabled")
        stages.append("xiaohongshu_creator_buddy_research")
    if modules.get("content_analysis"):
        stages.append("content_analysis")
    if modules.get("feishu"):
        stages.append("optional_feishu_sync")
    if modules.get("jianying"):
        stages.append("optional_jianying_delivery")
    result = {
        "dry_run": not args.execute,
        "account": config["account"]["name"],
        "enabled_modules": [name for name, enabled in modules.items() if enabled],
        "stages": stages,
        "scout_brief_missing": scout_brief_missing,
        "scout_search_ready": bool(modules.get("video_scout")) and not scout_brief_missing,
        "manifest": str(args.manifest.resolve()) if args.manifest else None,
        "note": "This router validates and plans; execute mutating stages with their dedicated scripts.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
