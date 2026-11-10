---
name: video-content-pipeline
description: Discover evidence-backed recent breakout videos after confirming any account's brief, with an optional minimum-likes filter, then route selections or user-supplied media through downloading, faithful subtitles, publishing copy, Jianying drafts, and final-output checks. Use for single or batch video production with optional Creator Buddy and Feishu; keep potential candidates separate.
---

# Video Content Pipeline

Read `project.json` from the project root, or use the path supplied by the user. Never copy account names, taxonomies, credentials, personal paths, dates, record IDs, captions, or style values from examples into reusable code.

Read [references/config-schema.md](references/config-schema.md) when configuring a project. Read [references/workflow.md](references/workflow.md) before running a full batch.

## Route the workflow

0. If the user needs video discovery, read [the bundled rehab-video-scout skill](skills/rehab-video-scout/SKILL.md) in full and [the discovery handoff](references/video-scout.md). Ask the four onboarding questions there, reusing known answers; do not search until the account and content brief are confirmed. Enable `modules.video_scout` for this project. No industry or account is assumed. When the user already supplied explicit links or local files and did not request discovery, preserve the existing direct-intake path.
1. Validate configuration with `scripts/run_pipeline.py --config <path> --dry-run`.
2. Read [the Instagram workflow](references/instagram-workflow.md). For discovery, verify recent candidates against the brief, reliable heat evidence, and any user-enabled minimum-likes filter. Generate a selection manifest using `select_video_candidates.py` and pass it to `run_instagram_pipeline.py --selection-manifest`; preserve evidence. Default to proven recent breakouts; enabled potential candidates remain separate and are not automatically downloaded. For explicitly user-supplied links use `--direct-input` with normalized `/reel/`, `/reels/`, `/p/`, or `/tv/` URLs, regardless of discovery settings. Dry-run the batch, then execute when authorized; do not re-ask for an already authorized scope. A request to find videos alone ends at recommendations.
3. For local-only input, match records to files with `scripts/match_videos.py`. Continue only for unique one-to-one matches.
4. Transcribe each downloaded video, create faithful Chinese subtitles, and use the analysis helpers only when needed. Keep uncertain speech in human review instead of guessing.
5. When `modules.xiaohongshu_research` is enabled, read [the Xiaohongshu content workflow](references/xiaohongshu-content.md) and invoke `$creator-buddy` before writing publishing copy. Creator Buddy supplies read-only market evidence and reusable patterns; it does not write the final post.
6. Generate the final content manifest from the source video, `account.tone`, `taxonomy`, and any verified research context. It must contain creator, canonical source URL, stable Instagram ID, duration, slug, and timed subtitles before draft delivery.
7. Generate one Jianying draft per ready video. Draft generation is the default output for Instagram intake, but still requires the batch dry-run and explicit `--execute` confirmation. Skip only the failing item; do not abort unrelated ready items.
8. If the user selects Feishu synchronization, call `sync_feishu.py` after content generation. It uploads attachments to uniquely matched existing records; it does not create rows or implement content-field updates. Missing or duplicated matches block that item. Separate field updates or row creation require an available connector and appropriate user authority.
9. When final videos are requested, use the configured editor/export capability and check the actual exported file for picture, sound, complete and aligned subtitles, attribution safe margins, and configured endcard. Read the delivery checklist in [the workflow](references/workflow.md). The repository generates drafts, not rendered MP4s; if export is unavailable, report that boundary rather than calling a draft publish-ready.
10. Report every selected, rejected, downloaded, reused, duplicated, blocked, failed, drafted, synchronized, exported, and verified item. Retain selection evidence through every manifest.

## Safety invariants

- Expand secrets only from environment-variable references such as `${FEISHU_BASE_TOKEN}`. Never print resolved secrets.
- Do not create missing Feishu records unless the user explicitly asks.
- Before an attachment upload, require a record ID, creator, stable source URL, existing local file, and empty attachment field.
- Never overwrite an existing draft. Missing fonts, presets, verified style profiles, applications, or dependencies are blocking errors.
- An encrypted or manually adjusted draft may prove provenance, but must not be parsed, copied, edited, or published. Reproduce only a separately verified numeric profile.
- Keep `--dry-run` as the default. External writes and formal draft generation require `--execute` immediately before the action.
- Creator Buddy is a read-only research dependency. If it or its Xiaohongshu backend is unavailable, mark research as unavailable and clearly label any content-only fallback; never invent trend or engagement data.
- Do not read browser cookies, accept cookie files, automate login, or bypass Instagram access controls. If a public link cannot be downloaded, fail that item with the downloader's concise reason.
- Normalize Instagram links and deduplicate by shortcode across `/p/`, `/reel/`, and `/reels/` before downloads. Never overwrite an existing download.
- Discovery requires a confirmed brief, recent publication and fresh primary-source heat evidence plus a sourced assessment. Minimum likes are optional (`discovery.min_likes_exclusive=null` by default). When enabled, the exact original-post count must exceed that number; views cannot substitute. Never relax enabled filters to fill a quota or mislabel agent-discovered items as user-provided input. Direct intake is a separate, explicitly user-requested workflow.
- High likes do not establish factual accuracy, reuse permission, or likely future virality. Keep provenance and attribution, flag rights questions, and do not publish without authorization.

## Tools

- `run_pipeline.py`: validate configuration and show the enabled execution plan.
- `select_video_candidates.py`: validate collected discovery evidence and write a deduplicated selection manifest; it does not search the web or authenticate supplied evidence.
- `run_instagram_pipeline.py`: normalize, deduplicate, and download public Instagram videos into an intake manifest.
- `match_videos.py`: create a stable match manifest.
- `sync_feishu.py`: plan or execute attachment uploads to existing records.
- `create_jianying_drafts.py`: validate and create configured drafts.
- `detect_caption_changes.py`: refine planned overlay boundaries locally.
- `detect_major_transitions.py`: find visual cuts near configured times.
- `make_boundary_sheets.py`: create configured frame-review sheets.
- `refine_whisper_segments.py`: re-transcribe configured ambiguous audio regions with local whisper.cpp.
