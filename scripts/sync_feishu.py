#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path

from common import add_execution_flags, load_config, read_json


def run(command, cwd=None):
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description="Safely upload matched videos to existing Feishu records.")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    add_execution_flags(parser)
    args = parser.parse_args()
    config = load_config(args.config, resolve_modules=bool(args.execute))
    if not config["modules"].get("feishu"):
        raise RuntimeError("modules.feishu is disabled")
    rows = read_json(args.manifest).get("matched", [])
    plan = []
    for row in rows:
        path = Path(row.get("file", "")).expanduser().resolve()
        reason = None
        if not row.get("record_id"):
            reason = "missing record_id"
        elif not row.get("creator") or not row.get("source_url"):
            reason = "missing creator or source_url"
        elif not row.get("attachment_empty", False):
            reason = "attachment is not empty"
        elif not path.is_file():
            reason = "video file missing"
        plan.append({**row, "file": str(path), "ready": reason is None, "reason": reason})
    if not args.execute:
        print(json.dumps({"dry_run": True, "plan": plan}, ensure_ascii=False, indent=2))
        return
    if any(not row["ready"] for row in plan):
        raise RuntimeError("blocked rows exist; resolve them before --execute")
    feishu = config["feishu"]
    fields = run(["lark-cli", "base", "+field-list", "--base-token", feishu["base_token"], "--table-id", feishu["table_id"], "--as", feishu.get("identity", "user"), "--limit", "200", "--format", "json"])
    field_name = feishu["fields"]["video"]
    candidates = [field for field in fields["data"]["fields"] if field["name"] == field_name]
    if len(candidates) != 1 or candidates[0]["type"] != "attachment":
        raise RuntimeError(f"attachment field is missing or ambiguous: {field_name}")
    results = []
    for row in plan:
        path = Path(row["file"])
        response = run(["lark-cli", "base", "+record-upload-attachment", "--base-token", feishu["base_token"], "--table-id", feishu["table_id"], "--record-id", row["record_id"], "--field-id", candidates[0]["id"], "--file", path.name, "--as", feishu.get("identity", "user")], cwd=path.parent)
        results.append({"record_id": row["record_id"], "file": path.name, "response": response})
    print(json.dumps({"dry_run": False, "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

