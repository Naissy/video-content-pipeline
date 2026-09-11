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
        "manifest": str(args.manifest.resolve()) if args.manifest else None,
        "note": "This router validates and plans; execute mutating stages with their dedicated scripts.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
