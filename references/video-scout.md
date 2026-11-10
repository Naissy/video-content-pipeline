# Discovery → production handoff

Read the bundled skills/rehab-video-scout/SKILL.md before discovery. Its legacy name does not imply a rehab account.

## Confirm the brief

Ask about positioning/audience, content formats/references/exclusions, platforms/language, and count/recency/duration/subtitle load. Also ask whether to set a minimum likes filter and whether potential candidates are wanted. Reuse existing answers. Only set discovery.brief_confirmed=true after confirmation.

Default suggestions: recent 7 days, 5 videos, 30 seconds, low subtitle load. selection_mode is proven; min_likes_exclusive is null (off). An integer enables exact original-post likes strictly greater than the value, not greater-or-equal. No global 10,000 requirement. Use include_potential only on request. Account settings stay in the ignored business project, not this repository.

The current evidence/downloader adapter is Instagram. Other source platforms require an adapter or user-provided local files.

## Evidence and assessment

Disabling minimum likes does not disable evidence checks. At least one current, primary-source, exact post metric (likes or video views) is required. Hidden likes may be replaced as an assessment input by verified views when the filter is off; views never satisfy an enabled likes threshold. Third-party snippets, follower counts, comment likes, invented counts and stale observations do not pass.

Default production recommendations must be recent proven breakouts. The agent must actually watch the source video and explain its relevance and popularity relative to a sensible content/age context. A large counter alone does not prove virality. No evidence means unverified, not potential. Popularity does not establish factual accuracy or reuse rights.

Assessment bases:
- recent_high_volume: explain the observed volume in a sourced recent/category context.
- relative_outperformance: compare similar content, preferably from the same creator, at comparable post ages. Record the sample and uncertainty; do not mix pinned old hits into a recent baseline.
- observed_growth: at least two same-post/same-metric observations with increasing timestamps and counts. Increasing slightly is not automatically a breakout; the agent must justify magnitude and period.

The validator checks recorded fields, not the authenticity of observations or the validity of qualitative judgments. It never replaces browsing/review. Keep comparison notes factual and cite the posts actually reviewed.

## Candidate JSON

The following is fictional schema data, not a verified recommendation. Use current observed dates/counts and actual source/comparison URLs; never copy the example to manufacture evidence.

~~~json
{
  "seen_urls": [],
  "candidates": [{
    "source_url": "https://www.instagram.com/reel/EXAMPLE_A/",
    "creator": "example_creator",
    "published_at": "2026-01-09T08:00:00+00:00",
    "duration": 24,
    "duration_evidence": "player",
    "subtitle_load": "low",
    "video_reviewed": true,
    "relevant": true,
    "fit_reason": "Matches the confirmed beginner cooking audience",
    "trend_status": "proven",
    "trend_basis": "relative_outperformance",
    "trend_reason": "Explain observed outperformance using real comparison data",
    "comparison": {
      "context": "Record the comparable posts, counts, ages, baseline and uncertainty",
      "source_urls": ["https://www.instagram.com/reel/EXAMPLE_COMPARISON/"]
    },
    "heat_evidence": [{
      "metric": "views",
      "value": 250000,
      "source_url": "https://www.instagram.com/reel/EXAMPLE_A/",
      "evidence_type": "instagram_page",
      "verified_at": "2026-01-10T12:00:00+00:00"
    }]
  }]
}
~~~

Evidence type is instagram_page or instagram_metadata; metric is likes or views; value is a positive exact integer; timestamps include timezones. For an enabled likes filter include a qualifying likes observation in heat_evidence. Any supplied invalid observation blocks the candidate.

For observed_growth add growth_observations with at least two objects in the same format as heat_evidence, from different times; they must be fresh, increasing and refer to the same metric/post. The source must have been published within the confirmed window. Duration evidence is player or media_metadata; subtitle load is none/low/medium/high.

trend_status may be potential only when enabled. It is emitted separately, never silently promoted to proven.

## Validate and select

~~~bash
python3 /path/to/video-content-pipeline/scripts/run_pipeline.py --config project.json --dry-run
python3 /path/to/video-content-pipeline/scripts/select_video_candidates.py \
  --config project.json --candidates work/candidates.json --dry-run
python3 /path/to/video-content-pipeline/scripts/select_video_candidates.py \
  --config project.json --candidates work/candidates.json \
  --output work/selection.json --execute
~~~

Output schema_version is 2: account_slug, brief_fingerprint, generated_at, optional min_likes_exclusive, proven videos, separate potential, excluded with reasons, and counts. The requested total includes both accepted groups, with proven items prioritized. Cross-form shortcode deduplication includes seen_urls; no overwrite of an existing selection file.

A fingerprint detects changes to the account or discovery settings, not forged evidence. Version 1 manifests require refreshed observations/assessments and regeneration; do not silently fill missing fields.

Deliver a short trend explanation and recommendations with creator, full URL, date, duration, subtitle burden, observed metric, assessment basis, fit and verification time. Separate proven/potential/unverified. A request to find videos ends here.

## Handoff

For an authorized production batch, refresh evidence and run:

~~~bash
python3 /path/to/video-content-pipeline/scripts/run_instagram_pipeline.py \
  --config project.json --selection-manifest work/selection.json \
  --manifest work/instagram-ingest.json --dry-run
~~~

Then use --execute for the same authorized scope, without repeatedly requesting permission already given. Revalidation checks the account/brief, current evidence, window, content review and enabled filters. Only proven videos are downloaded; potential stays in the selection report.

For explicitly user-supplied URLs, even when discovery is enabled:

~~~bash
python3 /path/to/video-content-pipeline/scripts/run_instagram_pipeline.py \
  --config project.json --direct-input --url https://www.instagram.com/reel/EXAMPLE_A/ \
  --manifest work/instagram-ingest.json --dry-run
~~~

Do not mix direct input with a selection manifest. Direct input is appropriate for supplied URLs or potential items the user specifically chose, not a workaround for agent-discovered items failing validation.

Retain selection_evidence while enriching intake videos into the content manifest: actual media identity/duration/audio checks, original captions and timings, faithful translations, separate publishing copy, taxonomy and review states. Use workflow.md and optional xiaohongshu-content.md for downstream steps.

## Final output

Existing transcription, editor, font and optional Feishu dependencies still apply. Draft generation is not MP4 export. Use available editor export capabilities, then verify the actual file for picture, sound, aligned and complete subtitles, attribution safe margins and configured ending. Report draft_created/exported/verified separately, plus per-item success/skip/failure reasons. No publication without authorization.
