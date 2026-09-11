# Workflow

## 1. Validate

Run the unified entry point in dry-run mode. It resolves only enabled modules and reports missing configuration without contacting external services.

## 2. Intake and match

Treat the task system or record list as the source of truth. Match normalized creator names to local filenames while preserving source URL and record ID. A duplicated normalized creator on either side is ambiguous and must not continue.

## 3. Analyze

Extract source captions and visual context, then create localized captions and publishing copy under the configured tone and taxonomy. Use the optional helpers for uncertain timing or audio. Unclear speech requires human review; uncertain classification stays empty.

## 4. Synchronize

Plan field updates and attachments separately. Deduplicate by stable source URL. Re-read the record before writing and verify the same record afterward. Do not create missing rows implicitly.

## 5. Deliver

Each video receives an independent draft with main video, subtitle, and creator-credit tracks. The credit spans the source duration. Validate every subtitle range. Require the configured, separately verified style profile; do not inspect or modify an encrypted source draft.

## 6. Report

For every item report its record, source URL, local media, content result, synchronization state, draft result, skips, failures, and checks that remain manual.

