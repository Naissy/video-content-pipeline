# Public Instagram link workflow

Use this workflow when the user provides one or more Instagram post, Reel, or IGTV links.

## Intake contract

- Accept links as repeated `--url` values or a UTF-8 `--url-file` with one link per line.
- Accept only public HTTPS `instagram.com/reel/<shortcode>`, `/p/<shortcode>`, and `/tv/<shortcode>` URLs.
- Remove tracking query parameters, canonicalize the URL, and deduplicate by content type plus shortcode before download.
- Use `yt-dlp` without cookies, browser profiles, usernames, or passwords. Do not install it automatically.
- Reuse an existing uniquely named media file only when its matching `.info.json` metadata exists. Never overwrite media.
- Cap a batch with `instagram.max_urls_per_batch`; larger input requires the user to split it.

## Agent sequence

1. Run `run_instagram_pipeline.py` in dry-run mode and show valid, duplicate, and rejected links plus dependency status.
2. After the user confirms the batch, run it with `--execute`. Use `--sync-feishu` only when the user selected Feishu and its module is enabled.
3. For every downloaded item, verify creator and duration. Extract/transcribe its audio and create faithful timed Chinese subtitles. If transcription is unclear, block only that item for human review.
4. If configured, invoke Creator Buddy and build the Xiaohongshu content package. Add the timed subtitles, recommended title, body, tags, taxonomy choices, and review status to the video's manifest item.
5. Dry-run `create_jianying_drafts.py`, then execute it for ready items after the batch confirmation. One failed item must not cause unrelated ready items to be silently discarded.
6. If requested, dry-run and execute `sync_feishu.py` after content generation. Exact canonical source URL is the business key: create on zero matches, update on one, block on multiple.

## Result states

Report `downloaded`, `reused`, `duplicate`, `download_failed`, `analysis_blocked`, `draft_created`, `draft_failed`, `feishu_created`, `feishu_updated`, and `feishu_blocked` per URL. Do not describe a missing draft or Feishu write as successful.
