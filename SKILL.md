---
name: video-content-pipeline
description: Turn one or more public Instagram video links or local media into configurable short-video content and Jianying drafts, with optional Creator Buddy research and optional Feishu synchronization. Use for repeatable single or batch video production; do not use to bypass platform access controls or edit unrelated local videos.
---

# Video Content Pipeline

Read `project.json` from the project root, or use the path supplied by the user. Never copy account names, taxonomies, credentials, personal paths, dates, record IDs, captions, or style values from examples into reusable code.

Read [references/config-schema.md](references/config-schema.md) when configuring a project. Read [references/workflow.md](references/workflow.md) before running a full batch.

## Route the workflow

1. Validate configuration with `scripts/run_pipeline.py --config <path> --dry-run`.
2. When the user supplies Instagram links, read [the Instagram workflow](references/instagram-workflow.md). Normalize and dry-run all links with `scripts/run_instagram_pipeline.py`; after the batch confirmation, execute the download. Accept public `/reel/`, `/p/`, and `/tv/` links only.
3. For local-only input, match records to files with `scripts/match_videos.py`. Continue only for unique one-to-one matches.
4. Transcribe each downloaded video, create faithful Chinese subtitles, and use the analysis helpers only when needed. Keep uncertain speech in human review instead of guessing.
5. When `modules.xiaohongshu_research` is enabled, read [the Xiaohongshu content workflow](references/xiaohongshu-content.md) and invoke `$creator-buddy` before writing publishing copy. Creator Buddy supplies read-only market evidence and reusable patterns; it does not write the final post.
6. Generate the final content manifest from the source video, `account.tone`, `taxonomy`, and any verified research context. It must contain creator, canonical source URL, stable Instagram ID, duration, slug, and timed subtitles before draft delivery.
7. Generate one Jianying draft per ready video. Draft generation is the default output for Instagram intake, but still requires the batch dry-run and explicit `--execute` confirmation. Skip only the failing item; do not abort unrelated ready items.
8. If the user selects Feishu synchronization, call `sync_feishu.py` after content generation. Match exactly by canonical source URL: zero matches creates a record, one updates it, and multiple matches block that item. Upload the attachment only after a unique record ID exists.
9. Report every downloaded, reused, duplicated, blocked, failed, drafted, synchronized, and unverified item.

## Safety invariants

- Expand secrets only from environment-variable references such as `${FEISHU_BASE_TOKEN}`. Never print resolved secrets.
- Do not create missing Feishu records unless the user explicitly asks.
- Before an attachment upload, require a record ID, creator, stable source URL, existing local file, and empty attachment field.
- Never overwrite an existing draft. Missing fonts, presets, verified style profiles, applications, or dependencies are blocking errors.
- An encrypted or manually adjusted draft may prove provenance, but must not be parsed, copied, edited, or published. Reproduce only a separately verified numeric profile.
- Keep `--dry-run` as the default. External writes and formal draft generation require `--execute` immediately before the action.
- Creator Buddy is a read-only research dependency. If it or its Xiaohongshu backend is unavailable, mark research as unavailable and clearly label any content-only fallback; never invent trend or engagement data.
- Do not read browser cookies, accept cookie files, automate login, or bypass Instagram access controls. If a public link cannot be downloaded, fail that item with the downloader's concise reason.
- Normalize Instagram links to a canonical URL and deduplicate by content type plus shortcode before any network call. Never overwrite an existing download.

## Tools

- `run_pipeline.py`: validate configuration and show the enabled execution plan.
- `run_instagram_pipeline.py`: normalize, deduplicate, and download public Instagram videos into an intake manifest.
- `match_videos.py`: create a stable match manifest.
- `sync_feishu.py`: plan or execute attachment uploads to existing records.
- `create_jianying_drafts.py`: validate and create configured drafts.
- `detect_caption_changes.py`: refine planned overlay boundaries locally.
- `detect_major_transitions.py`: find visual cuts near configured times.
- `make_boundary_sheets.py`: create configured frame-review sheets.
- `refine_whisper_segments.py`: re-transcribe configured ambiguous audio regions with local whisper.cpp.
