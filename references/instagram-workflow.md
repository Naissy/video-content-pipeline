# Public Instagram link workflow

Use this workflow when the user provides one or more Instagram post, Reel, or IGTV links.

## Intake contract

- Accept explicitly user-supplied links as repeated `--url` values or a UTF-8 `--url-file`, with `--direct-input` when scout is enabled. Agent-discovered recommendations require `--selection-manifest`; do not mix input modes or use direct input to misrepresent an unverified recommendation.
- Accept only public HTTPS `instagram.com/reel/<shortcode>`, `/reels/<shortcode>`, `/p/<shortcode>`, and `/tv/<shortcode>` URLs.
- Remove tracking query parameters, canonicalize `/reels/` to `/reel/`, and deduplicate by shortcode across URL forms before download. Existing `stable_id` formatting is retained for compatibility; use shortcode for cross-form identity.
- A schema-2 selection manifest is revalidated for the same account/brief, proven assessment, primary heat evidence, recency, freshness, any enabled likes filter, duration, relevance, and subtitle preference. Default likes filter is disabled. Potential items are not downloaded automatically. Stale/invalid selections stop before download. The validator checks recorded fields, not the live website or truth of an assessment; refresh original observations before handoff. Retain `selection_evidence` through analysis. Old schema-1 selections require refreshed evidence and regeneration.
- Use `yt-dlp` without cookies, browser profiles, usernames, or passwords. Do not install it automatically.
- Reuse an existing uniquely named media file only when its matching `.info.json` metadata exists. Never overwrite media.
- Cap a batch with `instagram.max_urls_per_batch`; larger input requires the user to split it.

## Agent sequence

1. Run `run_instagram_pipeline.py` in dry-run mode and show valid, duplicate, and rejected links plus dependency status.
2. After the user confirms the batch, run it with `--execute`. Use `--sync-feishu` only when the user selected Feishu and its module is enabled.
3. For every downloaded item, verify creator and duration. Extract/transcribe its audio and create faithful timed Chinese subtitles. If transcription is unclear, block only that item for human review.
4. If configured, invoke Creator Buddy and build the Xiaohongshu content package. Add the timed subtitles, recommended title, body, tags, taxonomy choices, and review status to the video's manifest item.
5. Dry-run `create_jianying_drafts.py`, then execute it for ready items after the batch confirmation. One failed item must not cause unrelated ready items to be silently discarded.
6. If requested, dry-run and execute `sync_feishu.py` for uniquely matched existing records. Missing/duplicate rows block that item; this attachment script does not create rows or update publishing-copy fields. Other Feishu actions need a separate available connector and explicit authority where applicable.
7. For finished media, follow the export and QC checklist in [workflow.md](workflow.md); distinguish a draft from an exported, verified video.

## Result states

Report `downloaded`, `reused`, `duplicate`, `download_failed`, `analysis_blocked`, `draft_created`, `draft_failed`, `feishu_created`, `feishu_updated`, and `feishu_blocked` per URL. Do not describe a missing draft or Feishu write as successful.
