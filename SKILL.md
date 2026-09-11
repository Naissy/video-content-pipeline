---
name: video-content-pipeline
description: Run a configurable short-video workflow across accounts and content types, including safe local matching, content-analysis helpers, optional Feishu synchronization, and optional Jianying draft delivery. Use for repeatable batch video production; do not use for ordinary one-off video edits.
---

# Video Content Pipeline

Read `project.json` from the project root, or use the path supplied by the user. Never copy account names, taxonomies, credentials, personal paths, dates, record IDs, captions, or style values from examples into reusable code.

Read [references/config-schema.md](references/config-schema.md) when configuring a project. Read [references/workflow.md](references/workflow.md) before running a full batch.

## Route the workflow

1. Validate configuration with `scripts/run_pipeline.py --config <path> --dry-run`.
2. If `modules.feishu` is enabled, obtain only the target records and required fields. Otherwise use a local JSON record list.
3. Match records to files with `scripts/match_videos.py`. Continue only for unique one-to-one matches.
4. Use the analysis helpers only when needed: caption-boundary detection, transition detection, contact sheets, or local Whisper refinement. Their boundaries and prompts must come from input JSON, never from embedded examples.
5. Generate captions and publishing copy according to `account.tone` and `taxonomy`. Keep uncertain classifications empty and route unclear transcripts to human review.
6. Treat Feishu upload and Jianying delivery as independent optional steps. Both default to dry-run and require explicit `--execute`.
7. Report every matched, unmatched, ambiguous, skipped, failed, executed, and unverified item.

## Safety invariants

- Expand secrets only from environment-variable references such as `${FEISHU_BASE_TOKEN}`. Never print resolved secrets.
- Do not create missing Feishu records unless the user explicitly asks.
- Before an attachment upload, require a record ID, creator, stable source URL, existing local file, and empty attachment field.
- Never overwrite an existing draft. Missing fonts, presets, verified style profiles, applications, or dependencies are blocking errors.
- An encrypted or manually adjusted draft may prove provenance, but must not be parsed, copied, edited, or published. Reproduce only a separately verified numeric profile.
- Keep `--dry-run` as the default. External writes and formal draft generation require `--execute` immediately before the action.

## Tools

- `run_pipeline.py`: validate configuration and show the enabled execution plan.
- `match_videos.py`: create a stable match manifest.
- `sync_feishu.py`: plan or execute attachment uploads to existing records.
- `create_jianying_drafts.py`: validate and create configured drafts.
- `detect_caption_changes.py`: refine planned overlay boundaries locally.
- `detect_major_transitions.py`: find visual cuts near configured times.
- `make_boundary_sheets.py`: create configured frame-review sheets.
- `refine_whisper_segments.py`: re-transcribe configured ambiguous audio regions with local whisper.cpp.

