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


def record_ids_for_url(feishu, source_field, source_url):
    response = run([
        "lark-cli", "base", "+record-list",
        "--base-token", feishu["base_token"], "--table-id", feishu["table_id"],
        "--filter-json", json.dumps({"logic": "and", "conditions": [[source_field, "==", source_url]]}, ensure_ascii=False),
        "--field-id", source_field, "--limit", "3", "--format", "json",
        "--jq", ".data.record_id_list", "--as", feishu.get("identity", "user"),
    ])
    if not isinstance(response, list):
        raise RuntimeError("unexpected record lookup response")
    return response


def extract_record_id(value):
    if isinstance(value, str) and value.startswith("rec"):
        return value
    if isinstance(value, dict):
        for item in value.values():
            found = extract_record_id(item)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = extract_record_id(item)
            if found:
                return found
    return None


def writable_fields(row, field_map):
    candidates = {
        "primary": row.get("recommended_title") or row.get("title"),
        "creator": row.get("creator"),
        "source_url": row.get("source_url"),
        "source_platform": row.get("source_platform", "instagram"),
        "status": row.get("status"),
        "summary": row.get("summary"),
        "body": row.get("body"),
        "tags": row.get("tags"),
        "category": row.get("category"),
        "audience": row.get("audience"),
    }
    return {field_map[key]: value for key, value in candidates.items() if key in field_map and value is not None}


def main():
    parser = argparse.ArgumentParser(description="Safely upload matched videos to existing Feishu records.")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    add_execution_flags(parser)
    args = parser.parse_args()
    config = load_config(args.config, resolve_modules=bool(args.execute))
    if not config["modules"].get("feishu"):
        raise RuntimeError("modules.feishu is disabled")
    manifest = read_json(args.manifest)
    rows = manifest.get("matched", manifest.get("videos", []))
    plan = []
    for row in rows:
        path = Path(row.get("file", "")).expanduser().resolve()
        reason = None
        if not row.get("creator") or not row.get("source_url"):
            reason = "missing creator or source_url"
        elif row.get("record_id") and not row.get("attachment_empty", False):
            reason = "attachment is not empty"
        elif not path.is_file():
            reason = "video file missing"
        action = "update" if row.get("record_id") else "lookup_then_create_or_update"
        plan.append({**row, "file": str(path), "action": action, "ready": reason is None, "reason": reason})
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
        record_id = row.get("record_id")
        action = "updated"
        if not record_id:
            ids = record_ids_for_url(feishu, feishu["fields"]["source_url"], row["source_url"])
            if len(ids) > 1:
                results.append({"source_url": row["source_url"], "status": "blocked", "reason": "multiple records share the source URL"})
                continue
            record_id = ids[0] if ids else None
            action = "updated" if record_id else "created"
        values = writable_fields(row, feishu["fields"])
        command = ["lark-cli", "base", "+record-upsert", "--base-token", feishu["base_token"], "--table-id", feishu["table_id"], "--json", json.dumps(values, ensure_ascii=False), "--as", feishu.get("identity", "user")]
        if record_id:
            command.extend(["--record-id", record_id])
        response = run(command)
        record_id = record_id or extract_record_id(response)
        if not record_id:
            raise RuntimeError(f"record {action} response did not include a record ID")
        path = Path(row["file"])
        response = run(["lark-cli", "base", "+record-upload-attachment", "--base-token", feishu["base_token"], "--table-id", feishu["table_id"], "--record-id", record_id, "--field-id", candidates[0]["id"], "--file", path.name, "--as", feishu.get("identity", "user")], cwd=path.parent)
        results.append({"record_id": record_id, "action": action, "file": path.name, "attachment_response": response})
    print(json.dumps({"dry_run": False, "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
