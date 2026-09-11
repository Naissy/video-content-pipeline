#!/usr/bin/env python3
import argparse
import copy
import json
import os
import sys
from datetime import date
from pathlib import Path

from common import add_execution_flags, load_config, read_json


def expanded(value):
    return Path(value).expanduser().resolve()


def validate_item(item):
    missing = [name for name in ("file", "creator", "duration", "slug", "subtitles") if name not in item]
    if missing:
        return f"missing fields: {', '.join(missing)}"
    path = expanded(item["file"])
    if not path.is_file():
        return f"missing video: {path}"
    duration = float(item["duration"])
    for index, segment in enumerate(item["subtitles"]):
        start, length = float(segment["start"]), float(segment["duration"])
        if start < 0 or length <= 0 or start + length > duration + 0.05 or not str(segment["text"]).strip():
            return f"invalid subtitle segment {index}"
    return None


def main():
    parser = argparse.ArgumentParser(description="Create configurable Jianying drafts; dry-run by default.")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    add_execution_flags(parser)
    args = parser.parse_args()
    config = load_config(args.config, resolve_modules=bool(args.execute))
    if not config["modules"].get("jianying"):
        raise RuntimeError("modules.jianying is disabled")
    items = read_json(args.manifest)
    items = items.get("matched", items.get("videos", []))
    draft = config["draft"]
    plan = []
    for item in items:
        error = validate_item(item)
        name = draft["name_template"].format(account=config["account"]["name"], date=item.get("date", date.today().strftime("%Y%m%d")), slug=item.get("slug", "video"), status=item.get("status", draft["status"]))
        plan.append({"project_name": name, "file": str(expanded(item.get("file", ""))), "ready": error is None, "reason": error})
    dependencies = {"jianying_skill": str(expanded(config["paths"].get("jianying_skill", ""))), "preset_root": str(expanded(config["paths"].get("preset_root", ""))), "style_profile": str(expanded(draft.get("style_reference", {}).get("path", "")))}
    if not args.execute:
        print(json.dumps({"dry_run": True, "dependencies": dependencies, "plan": plan}, ensure_ascii=False, indent=2))
        return
    style = draft.get("style_reference", {})
    if not draft.get("style_verified") or style.get("application_mode") != "verified_profile_reproduction" or not style.get("protected"):
        raise RuntimeError("a protected, verified numeric style profile is required")
    if draft.get("overwrite", False):
        raise RuntimeError("overwrite=true is not allowed")
    if any(not item["ready"] for item in plan):
        raise RuntimeError("blocked videos exist; resolve them before --execute")
    skill_root, preset_root, style_path = map(Path, dependencies.values())
    if not (skill_root / "scripts").is_dir() or not preset_root.is_dir() or not style_path.exists():
        raise RuntimeError("Jianying skill, preset directory, or verified style profile is unavailable")
    os.environ["JY_SKILL_ROOT"] = str(skill_root)
    sys.path.insert(0, str(skill_root / "scripts"))
    from jy_wrapper import JyProject
    import pyJianYingDraft as jy
    from pyJianYingDraft.metadata.effect_meta import EffectMeta

    def load_preset(spec):
        preset_path = preset_root / f"预设文本{spec['preset_number']}.textpreset"
        if not preset_path.is_file():
            raise FileNotFoundError(preset_path)
        data = read_json(preset_path)["style"]
        font_name, resource_id = spec.get("font_name", data.get("font_name")), spec.get("font_resource_id", data.get("font_resource_id"))
        font = None
        if str(font_name).strip().casefold() not in {"system", "系统"}:
            if not font_name or not resource_id:
                raise RuntimeError(f"font metadata missing in {preset_path}")
            font = type("ConfiguredFont", (), {"value": EffectMeta(font_name, False, resource_id, "", "", [])})()
        color = tuple(int(data["color"][i:i + 2], 16) / 255 for i in (1, 3, 5))
        border = None
        if data.get("border_item_checked"):
            value = data["border_color"]
            border = jy.TextBorder(color=tuple(int(value[i:i + 2], 16) / 255 for i in (1, 3, 5)), width=data["border_width"] * 500)
        background = None
        if data.get("frame_item_checked"):
            background = jy.TextBackground(color=data["frame_color"], style=1 if data["frame_style"] == 1 else 2, alpha=data["frame_alpha"], height=data["frame_height"], width=data["frame_width"], horizontal_offset=0.5 + data["frame_horizontal_offset"] / 2, vertical_offset=0.5 + data["frame_vertical_offset"] / 2)
        style_obj = jy.TextStyle(size=float(spec.get("size", data["font_size"] + spec.get("size_offset", 0))), color=color, align=data["alignment"])
        clip = jy.ClipSettings(transform_x=data["transform_x"], transform_y=data["transform_y"], scale_x=data["scale_x"], scale_y=data["scale_y"], rotation=data["rotation"])
        return font, style_obj, border, background, clip

    def add_text(project, text, start, duration, track, preset):
        font, text_style, border, background, clip = preset
        kwargs = {"style": copy.deepcopy(text_style), "border": border, "background": background, "clip_settings": clip}
        if font is not None:
            kwargs["font"] = font
        project.add_text_simple(text, start_time=f"{start:.6f}s", duration=f"{duration:.6f}s", track_name=track, **kwargs)

    subtitle, credit = draft["subtitle"], draft["creator_credit"]
    subtitle_preset, credit_preset = load_preset(subtitle), load_preset(credit)
    results = []
    for item, planned in zip(items, plan):
        project = JyProject(planned["project_name"], width=draft["width"], height=draft["height"], overwrite=False)
        path = expanded(item["file"])
        if project.add_media_safe(str(path), start_time="0s", track_name="MainVideo") is None:
            raise RuntimeError(f"video import failed: {path}")
        for segment in item["subtitles"]:
            add_text(project, segment["text"], float(segment["start"]), float(segment["duration"]), subtitle["track_name"], subtitle_preset)
        add_text(project, "@" + str(item["creator"]).lstrip("@"), 0.0, float(item["duration"]), credit["track_name"], credit_preset)
        results.append({"project_name": planned["project_name"], "subtitle_segments": len(item["subtitles"]), "creator_segments": 1, "save_result": str(project.save())})
    print(json.dumps({"dry_run": False, "created": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

