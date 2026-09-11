#!/usr/bin/env python3
import json
import os
import re
from pathlib import Path

ENV_REF = re.compile(r"^\$\{([A-Z][A-Z0-9_]*)\}$")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def resolve_env(value):
    if isinstance(value, dict):
        return {key: resolve_env(item) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve_env(item) for item in value]
    if isinstance(value, str):
        match = ENV_REF.fullmatch(value)
        if match:
            name = match.group(1)
            if name not in os.environ:
                raise RuntimeError(f"missing environment variable: {name}")
            return os.environ[name]
    return value


def load_config(path, resolve_modules=True):
    config = read_json(path)
    required = ("version", "account", "modules", "taxonomy", "paths")
    missing = [name for name in required if name not in config]
    if missing:
        raise ValueError(f"missing configuration blocks: {', '.join(missing)}")
    modules = config["modules"]
    if modules.get("feishu"):
        if "feishu" not in config:
            raise ValueError("feishu configuration is required when modules.feishu is enabled")
        if resolve_modules:
            config["feishu"] = resolve_env(config["feishu"])
    if modules.get("jianying"):
        if "draft" not in config:
            raise ValueError("draft configuration is required when modules.jianying is enabled")
        if resolve_modules:
            config["draft"] = resolve_env(config["draft"])
            for key in ("jianying_skill", "preset_root"):
                config["paths"][key] = resolve_env(config["paths"][key])
    return config


def add_execution_flags(parser):
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Show the plan without external writes")
    mode.add_argument("--execute", action="store_true", help="Perform the explicitly requested write")

