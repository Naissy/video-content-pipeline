# Xiaohongshu research and content workflow

Use this workflow only when `modules.xiaohongshu_research` is enabled. Creator Buddy is an optional read-only research dependency; the pipeline remains responsible for final content generation and validation.

## 1. Derive the research query

For every matched video, derive one primary Chinese keyword and up to two supporting keywords from the verified transcript, visible context, and configured taxonomy. Do not infer a sensitive diagnosis, identity, or factual claim from entertainment footage.

## 2. Invoke Creator Buddy

Invoke `$creator-buddy` with:

- platform: `xiaohongshu`;
- object: the primary and supporting keywords;
- task: recent popular-note search, engagement signals, title-pattern analysis, audience pain points, and reusable content structures;
- limits: `xiaohongshu.lookback_days` and `xiaohongshu.search_limit` from the project configuration.

Creator Buddy should prefer its `xhs-hotnotes` route for keyword heat and use `global-content-search` only when note, creator, or comment detail is needed. It must report the route/backend used and must not fabricate unavailable Xiaohongshu data.

## 3. Save research context

Store a batch-local `research_context` alongside the content manifest:

```json
{
  "research_status": "verified",
  "platform": "xiaohongshu",
  "backend": "creator-buddy/xhs-hotnotes",
  "queries": ["primary keyword", "supporting keyword"],
  "observed_at": "YYYY-MM-DD",
  "sources": [{"title": "example", "url": "https://example.com"}],
  "keywords": ["keyword"],
  "title_patterns": ["audience + tension + payoff"],
  "audience_pain_points": ["pain point"],
  "reusable_structures": ["hook -> situation -> emotional payoff"],
  "avoid_copying": ["source wording or unsupported claim"]
}
```

Keep source URLs so a reviewer can distinguish observed evidence from generated recommendations. Do not copy full source posts into the manifest.

## 4. Generate the final package

Generate the final title, body, and tags from the source video first, then use research only to improve discoverability and framing:

- Produce `xiaohongshu.title_count` distinct title candidates and select one recommended title.
- Preserve the video's actual premise; do not attach an unrelated trending keyword.
- Write an original body in `account.tone`, with a clear first-line hook and no invented experience or outcome.
- Produce up to `xiaohongshu.tag_count` tags, combining topic, audience, scenario, and account taxonomy. Do not repeat near-identical tags.
- Record which research keywords or patterns influenced the result.

## 5. Failure and review

If Creator Buddy, its route, or the Xiaohongshu backend is unavailable, set `research_status` to `unavailable`, report the reason, and label output as `content_only_fallback`. Never claim that fallback copy is trend-validated.

When `human_review_before_sync` is true, do not write the selected title, body, or tags to Feishu until the user approves them.

