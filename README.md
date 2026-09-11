# video-content-pipeline

A reusable Codex Skill for short-video intake, matching, analysis, optional Feishu synchronization, and optional Jianying draft delivery.

## Quick start

1. Copy `templates/project.template.json` to a working directory as `project.json`.
2. Enable only the modules you use and replace placeholders with local paths or environment-variable references.
3. Run `python3 scripts/run_pipeline.py --config project.json --dry-run`.
4. Follow `references/workflow.md` for matching and optional delivery.

All external writes and formal Jianying draft generation require `--execute`. Real credentials, media, models, presets, drafts, and batch outputs are intentionally excluded.

## Requirements

The core configuration and matching tools use Python 3.9+ and the standard library. Visual analysis helpers additionally require OpenCV and NumPy. Whisper refinement requires `whisper-cli`; Jianying delivery requires a separately installed compatible Jianying Skill and local presets. Feishu delivery requires an authenticated `lark-cli`.

