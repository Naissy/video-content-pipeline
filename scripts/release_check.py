#!/usr/bin/env python3
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".json", ".py", ".yaml", ".yml", ".txt"}
FORBIDDEN = [
    re.compile("".join(parts), flags)
    for parts, flags in [
        (("NXufbqFe", "PaRdN1sa", "Km5cHXB0nNb"), 0),
        (("tbl5lRQP", "ldmXWD8q"), 0),
        (("adhd", "脑子", "加载中"), 0),
        (("/Users/", "Syrenia"), 0),
        ((r"kristina", r"\.7979"), re.I),
    ]
]


def main():
    errors = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.stat().st_size > 5 * 1024 * 1024:
            errors.append(f"file exceeds 5 MiB: {path.relative_to(ROOT)}")
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in {"SKILL.md", ".gitignore"}:
            text = path.read_text(encoding="utf-8")
            for pattern in FORBIDDEN:
                if pattern.search(text):
                    errors.append(f"forbidden project-specific value in {path.relative_to(ROOT)}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        raise SystemExit(1)
    print("release check passed")


if __name__ == "__main__":
    main()
