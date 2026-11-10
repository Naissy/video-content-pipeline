---
name: video-content-pipeline
description: Discover recent videos after confirming any account's positioning and content brief, then route verified selections, public Instagram links, or local media through downloading, faithful subtitles, publishing copy, Jianying drafts, and final-output checks. Use for end-to-end single or batch video production with optional Creator Buddy and Feishu; discovery requires original-post likes strictly greater than 10000.
---

# Video Content Pipeline

Read `project.json` from the project root, or use the path supplied by the user. Never copy account names, taxonomies, credentials, personal paths, dates, record IDs, captions, or style values from examples into reusable code.

Read [references/config-schema.md](references/config-schema.md) when configuring a project. Read [references/workflow.md](references/workflow.md) before running a full batch.

## Route the workflow

0. If the user needs video discovery, read [the bundled rehab-video-scout skill](skills/rehab-video-scout/SKILL.md) in full and [the discovery handoff](references/video-scout.md). Ask the four onboarding questions there, reusing known answers; do not search until the account and content brief are confirmed. Enable `modules.video_scout` for this project. No industry or account is assumed. When the user already supplied explicit links or local files and did not request discovery, preserve the existing direct-intake path.
1. Validate configuration with `scripts/run_pipeline.py --config <path> --dry-run`.
2. Read [the Instagram workflow](references/instagram-workflow.md). For discovery, verify recent candidates against the confirmed brief and exact original-post likes > 10000, then generate a selection manifest using `select_video_candidates.py`. Pass it to `run_instagram_pipeline.py --selection-manifest`; do not strip evidence into a bare URL list. For direct intake, normalize supplied `/reel/`, `/reels/`, `/p/`, or `/tv/` links. Dry-run the batch, then download only when authorized. A request to find videos alone ends at recommendations, without downloads or other writes.
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
- Discovery requires a confirmed account brief and fresh primary-source evidence of exact likes strictly greater than 10000. Never substitute views or relax the threshold to fill a quota. Do not disable scout mode to bypass this gate; direct intake is a separate user-requested workflow.
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
