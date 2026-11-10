# Workflow

## 0. Discover when requested

Read the bundled scout instructions and [video-scout.md](video-scout.md). Ask about positioning/audience, topics/formats/exclusions, platforms/language, and count/recency/duration/subtitle burden. Reuse known answers, but obtain the missing brief before searching. Review recent source evidence and actual videos; select only exact original-post likes > 10000. Generate the evidence-bearing selection manifest and feed it directly to Instagram intake. Insufficient qualified results means fewer results, not a lower threshold. Direct user-supplied media can skip discovery in a separate direct-intake project.

## 1. Validate

Run the unified entry point in dry-run mode. It resolves only enabled modules and reports missing configuration without contacting external services.

## 2. Intake and match

Treat the task system or record list as the source of truth. Match normalized creator names to local filenames while preserving source URL and record ID. A duplicated normalized creator on either side is ambiguous and must not continue.

## 3. Analyze

Extract source captions and visual context, then create faithful translations and separate publishing copy under the configured tone and taxonomy. Match source caption appearance/disappearance, not estimated sentence timings; keep role labels and spoken dialogue separate. Do not add invented dialogue or emoji to subtitles. Use optional helpers for uncertain timing or audio. Unclear speech requires human review; uncertain classification stays empty. Preserve `selection_evidence` when enriching intake items.

## 4. Synchronize

Plan field updates and attachments separately. Deduplicate by stable source URL. Re-read the record before writing and verify the same record afterward. Do not create missing rows implicitly.

## 5. Deliver

Each video receives an independent draft with main video, subtitle, and creator-credit tracks. The credit spans the source duration. Validate every subtitle range. Require the configured, separately verified style profile; do not inspect or modify an encrypted source draft.

If the user requested finished media, export using an available, configured editor capability. No MP4 renderer is bundled here. After export, verify the actual file, not only the timeline: full duration/picture, audible audio when expected, all caption groups and their boundaries (including the ending), independent text layers, font/size and no occlusion, attribution within safe margins for the destination aspect ratio, and any configured endcard. Rewatch ambiguous passages. Missing audio or uncertain text is a blocking quality issue, not a successful final delivery.

Track `draft_created`, `exported`, and `verified` separately. Mark `verified` only after the exported file passed both technical and audiovisual review. Keep output paths and the check results in the business project's batch report; never publish automatically. Rights/permission to reuse and factual review are separate from popularity.

## 6. Report

For every item report its selection decision/evidence, record, source URL, local media, content result, synchronization state, draft and export paths, final QC state, skips/failures and reasons, and checks that remain manual. Do not mark later stages complete merely because an earlier stage passed.

