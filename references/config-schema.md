# Configuration schema

`project.json` is the only project-specific entry point. `version`, `account`, `modules`, `taxonomy`, and `paths` are required. `feishu` and `draft` are required only when their modules are enabled.

## Modules

- `local_intake`: match local media to records.
- `feishu`: allow Feishu reads and explicitly authorized writes.
- `content_analysis`: enable transcript, visual-analysis, and publishing-copy work.
- `jianying`: allow explicitly authorized draft generation.

Disabled modules must not require their credentials, applications, presets, or paths.

## Secrets and paths

Any string exactly matching `${NAME}` is resolved from environment variable `NAME` when—and only when—the owning module is enabled. Missing required variables stop that module. Never store resolved configuration in the repository.

## Match manifest

The matcher writes `matched`, `unmatched_records`, `unmatched_files`, and `ambiguous`. Each matched item contains `record_id`, `creator`, `source_url`, `attachment_empty`, and an absolute `file` path. Draft delivery additionally requires `duration`, `slug`, and `subtitles`, whose segments contain `start`, `duration`, and `text` in seconds.

## Analysis inputs

Transition boundaries are JSON objects with `name` and `approximate_time`. Review windows contain `name`, `start`, `end`, and `step`. Whisper regions contain `name`, `start`, `end`, and optional `prompt`. These files are batch inputs and should normally live under an ignored work directory.

