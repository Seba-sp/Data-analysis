---
phase: 02-core-package
plan: "04"
subsystem: infra
tags: [storage, email, drive, slack, gcs, python, promotion]

# Dependency graph
requires:
  - phase: 02-01
    provides: core/ package scaffold with __init__.py

provides:
  - StorageClient in core/storage.py — local/GCS backend switching with 'gcs' backend string
  - EmailSender in core/email_sender.py — SMTP email sending with PDF attachment support
  - DriveService in core/drive_service.py — Google Drive upload with shared drive support
  - SlackService in core/slack_service.py — Slack notifications with rich block formatting
  - upload_folder_to_gcs functions in core/upload_folder_to_gcs.py — CLI GCS folder upload utility

affects:
  - 02-02 (AssessmentDownloader uses StorageClient)
  - 02-03 (BaseReportGenerator uses StorageClient)
  - 02-05 (PipelineRunner uses EmailSender, DriveService, SlackService)
  - 03 (all report generators inherit from core services)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "copy-as-is promotion: source files copied verbatim from canonical location, only import paths fixed"
    - "bug fix on promotion: backend string 'gcp' corrected to 'gcs' to match env var documentation"
    - "header comment convention: each promoted file gets # Promoted from <source> — Phase 2"

key-files:
  created:
    - core/storage.py
    - core/email_sender.py
    - core/drive_service.py
    - core/slack_service.py
    - core/upload_folder_to_gcs.py
  modified: []

key-decisions:
  - "diagnosticos/complete_deployment/ used as canonical source for storage, email_sender, drive_service (most feature-complete production copy)"
  - "shared/ used for slack_service and upload_folder_to_gcs (only copy available)"
  - "StorageClient backend check fixed from 'gcp' to 'gcs' to match STORAGE_BACKEND=gcs env var documentation"
  - "shared/ directory deleted after promotion (confirmed untracked dead code — no active report imports from it)"
  - "No bare flat imports found in any source file — no import rewrites needed beyond header comments"

patterns-established:
  - "from core.storage import StorageClient — canonical import pattern for all consumers"
  - "from core.email_sender import EmailSender — canonical import pattern"
  - "from core.drive_service import DriveService — canonical import pattern"
  - "from core.slack_service import SlackService — canonical import pattern"

requirements-completed: [CORE-04]

# Metrics
duration: 3min
completed: 2026-03-01
---

# Phase 2 Plan 04: Promote Service Files to core/ Summary

**Five infrastructure service files promoted from shared/ and diagnosticos/complete_deployment/ to core/, with 'gcp'->'gcs' backend bug fixed and shared/ dead-code directory deleted**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-01T04:07:13Z
- **Completed:** 2026-03-01T04:10:41Z
- **Tasks:** 2
- **Files modified:** 5 created, 0 modified

## Accomplishments

- Promoted 3 service files from `diagnosticos/complete_deployment/` (production canonical source): `storage.py`, `email_sender.py`, `drive_service.py`
- Promoted 2 service files from `shared/`: `slack_service.py`, `upload_folder_to_gcs.py`
- Fixed the `StorageClient` backend string bug: `'gcp'` -> `'gcs'` in both the constructor check and `get_backend_info()`, to match `STORAGE_BACKEND=gcs` env var documentation
- Deleted the `shared/` directory (confirmed dead code — never imported by any active report, each project has its own copy)
- All five files verified clean: importable, syntactically valid, no bare flat imports

## Task Commits

Each task was committed atomically:

1. **Task 1: Promote storage.py, email_sender.py, drive_service.py** - `f3b78d5` (feat)
2. **Task 2: Promote slack_service.py, upload_folder_to_gcs.py; delete shared/** - `61d4b52` (feat)

**Plan metadata:** _(docs commit follows)_

## Files Created/Modified

- `core/storage.py` - StorageClient with local/GCS backend switching; backend string fixed to 'gcs'
- `core/email_sender.py` - EmailSender for SMTP email sending with PDF attachment support
- `core/drive_service.py` - DriveService for Google Drive upload with organized folder structure
- `core/slack_service.py` - SlackService for Slack notifications with rich block formatting
- `core/upload_folder_to_gcs.py` - CLI utility and module functions for GCS folder upload

## Decisions Made

- Used `diagnosticos/complete_deployment/` as canonical source for the first three files (production-tested, most feature-complete)
- Used `shared/` for `slack_service.py` and `upload_folder_to_gcs.py` (only available copies, not in complete_deployment/)
- `shared/` confirmed untracked in git (was never committed) — deleted on disk only; no git operation needed
- No import rewrites needed for any file — none of the source files contained bare flat imports like `from storage import StorageClient`

## Deviations from Plan

None - plan executed exactly as written. The 'gcp'->'gcs' fix was planned and documented in the plan's KNOWN BUG section.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. These files read from env vars at runtime.

## Next Phase Readiness

- All five `core/` service files are in place and importable
- `core/storage.py` — ready for use by AssessmentDownloader (02-02) and BaseReportGenerator (02-03)
- `core/email_sender.py`, `core/drive_service.py`, `core/slack_service.py` — ready for PipelineRunner (02-05)
- `core/upload_folder_to_gcs.py` — available as CLI utility and importable module
- Wave 2 is now complete (02-02, 02-03, 02-04); Wave 3 (02-05 PipelineRunner) is ready to execute

---
*Phase: 02-core-package*
*Completed: 2026-03-01*

## Self-Check: PASSED

- core/storage.py: FOUND
- core/email_sender.py: FOUND
- core/drive_service.py: FOUND
- core/slack_service.py: FOUND
- core/upload_folder_to_gcs.py: FOUND
- 02-04-SUMMARY.md: FOUND
- shared/ deleted: CONFIRMED
- Commit f3b78d5: FOUND
- Commit 61d4b52: FOUND
