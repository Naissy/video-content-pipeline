# Configuration schema

`project.json` is the only project-specific entry point. `version`, `account`, `modules`, `taxonomy`, and `paths` are required. `feishu` and `draft` are required only when their modules are enabled.

## Modules

- `video_scout`: enable onboarding-first discovery of evidence-backed recent breakouts. Defaults to false for existing direct-intake projects.
- `instagram_intake`: public Instagram download adapter.
- `xiaohongshu_research`: optional Creator Buddy target-platform research.
- `local_intake`: match local media to records.
- `feishu`: allow Feishu reads and explicitly authorized writes.
- `content_analysis`: enable transcript, visual-analysis, and publishing-copy work.
- `jianying`: allow explicitly authorized draft generation.

Disabled modules must not require their credentials, applications, presets, or paths.

## Account and discovery brief

All projects retain `account.name`, `slug`, and `tone`. Discovery additionally requires nonempty `account.positioning` and `account.audience`, without assuming an industry. `discovery.brief_confirmed` must be true only after the user has answered or accepted the brief. Reuse confirmed answers for the same account; reconfirm when materially changed.

`discovery.topics` and `content_types` are nonempty string arrays. `source_platform` and `destination_platform` are required strings; the current executable source adapter supports `instagram` only. `content_language`, `target_region`, `excluded_topics`, and `reference_urls` retain the user's context for agent research and review, not mechanical topic classification.

Defaults to propose and confirm: `lookback_days=7`, `limit=5`, `max_duration_seconds=30`, `max_subtitle_load="low"`, and `verification_max_age_hours=24`. The three count/time settings must be positive integers; duration must be positive and finite; subtitle load is `none`, `low`, `medium`, or `high`.

`min_likes_exclusive=null` disables the optional likes filter; a nonnegative integer enables the strict `>` boundary (e.g. 10000 excludes exactly 10000). Disabling this filter does not disable evidence requirements. `selection_mode="proven"` is the default; `include_potential` additionally allows separately labeled potential candidates within the requested total count. Only proven items enter automatic production. Use `--direct-input` for explicitly user-supplied URLs, without changing the discovery configuration.

Selection manifests now use schema version 2 and include primary `heat_evidence`, an assessment basis/reason, and a `potential` list separate from production `videos`. Version 1 manifests must be regenerated after reviewing evidence; do not silently upgrade or infer missing heat assessments.

The template leaves positioning and content direction empty and `brief_confirmed=false`. It is intentionally not search-ready. Existing configurations without discovery remain valid when `video_scout` is off. See [video-scout.md](video-scout.md) for the evidence and selection handoff contract.

## Secrets and paths

Any string exactly matching `${NAME}` is resolved from environment variable `NAME` when—and only when—the owning module is enabled. Missing required variables stop that module. Never store resolved configuration in the repository.

## Match manifest

The matcher writes `matched`, `unmatched_records`, `unmatched_files`, and `ambiguous`. Each matched item contains `record_id`, `creator`, `source_url`, `attachment_empty`, and an absolute `file` path. Draft delivery additionally requires `duration`, `slug`, and `subtitles`, whose segments contain `start`, `duration`, and `text` in seconds.

## Analysis inputs

Transition boundaries are JSON objects with `name` and `approximate_time`. Review windows contain `name`, `start`, `end`, and `step`. Whisper regions contain `name`, `start`, `end`, and optional `prompt`. These files are batch inputs and should normally live under an ignored work directory.

