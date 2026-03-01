---
phase: 02-core-package
plan: "05"
subsystem: infra
tags: [imports, migration, python, refactor, google-cloud]

# Dependency graph
requires:
  - phase: 02-02
    provides: core/assessment_downloader.py — canonical AssessmentDownloader
  - phase: 02-03
    provides: core/assessment_analyzer.py — canonical AssessmentAnalyzer
  - phase: 02-04
    provides: core/storage.py, core/email_sender.py, core/drive_service.py, core/slack_service.py

provides:
  - All bare flat imports replaced with from core.X import Y across 30 .py files
  - GOOGLE_CLOUD_PROJECT env var renamed to GCP_PROJECT_ID in task_service.py files
  - Zero bare imports in diagnosticos/, diagnosticos_uim/, ensayos_generales/, assessment-analysis-project/, reportes de test de diagnostico/

affects:
  - 03 (report generators can now import from core without conflict)
  - Phase 5 (deployment references GCP_PROJECT_ID not GOOGLE_CLOUD_PROJECT)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "systematic grep-and-replace: bare flat imports migrated to from core.X import Y"
    - "GCP_PROJECT_ID canonical env var: replaces GOOGLE_CLOUD_PROJECT in all .py files"
    - "complete_deployment/ subdirs also updated: same import migration applied"

key-files:
  created: []
  modified:
    - diagnosticos/assessment_downloader.py
    - diagnosticos/main.py
    - diagnosticos/report_generator.py
    - diagnosticos/send_emails.py
    - diagnosticos/task_service.py
    - diagnosticos/complete_deployment/assessment_downloader.py
    - diagnosticos/complete_deployment/main_app.py
    - diagnosticos/complete_deployment/report_generator.py
    - diagnosticos/complete_deployment/task_service.py
    - diagnosticos_uim/assessment_downloader.py
    - diagnosticos_uim/main.py
    - diagnosticos_uim/main_app.py
    - diagnosticos_uim/report_generator.py
    - diagnosticos_uim/send_emails.py
    - diagnosticos_uim/task_service.py
    - diagnosticos_uim/complete_deployment/assessment_downloader.py
    - diagnosticos_uim/complete_deployment/main_app.py
    - diagnosticos_uim/complete_deployment/report_generator.py
    - diagnosticos_uim/complete_deployment/task_service.py
    - ensayos_generales/assessment_analyzer.py
    - ensayos_generales/assessment_downloader.py
    - ensayos_generales/main.py
    - ensayos_generales/report_generator.py
    - ensayos_generales/send_emails.py
    - assessment-analysis-project/assessment_downloader.py
    - assessment-analysis-project/report_generator.py
    - assessment-analysis-project/send_pdf_reports.py
    - reportes de test de diagnostico/assessment_downloader.py
    - reportes de test de diagnostico/report_generator.py
    - reportes de test de diagnostico/send_pdf_reports.py

key-decisions:
  - "task_service.py files included in GCP_PROJECT_ID rename even though not in original file list — they were in GOOGLE_CLOUD_PROJECT grep results and are .py files in scope"
  - "complete_deployment/ subdirs updated alongside parent directories — same import migration, consistent package structure"
  - "from report_generator import ReportGenerator left as bare import in main.py/main_app.py files — report_generator is not a core/ module (it stays per-project), so no replacement needed"

patterns-established:
  - "from core.storage import StorageClient — all project directories use this"
  - "from core.email_sender import EmailSender — all project directories use this"
  - "from core.drive_service import DriveService — all project directories use this"
  - "from core.assessment_downloader import AssessmentDownloader — all project directories use this"
  - "from core.assessment_analyzer import AssessmentAnalyzer — all project directories use this"
  - "GCP_PROJECT_ID — canonical env var name for GCP project ID across all .py files"

requirements-completed: [CORE-05]

# Metrics
duration: 8min
completed: 2026-03-01
---

# Phase 2 Plan 05: Migrate Bare Imports to core.* Package Imports Summary

**30 .py files across 5 project directories migrated from bare flat imports to `from core.X import Y` package imports; `GOOGLE_CLOUD_PROJECT` renamed to `GCP_PROJECT_ID` in all task_service.py files**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-01T04:16:23Z
- **Completed:** 2026-03-01T04:24:00Z
- **Tasks:** 1 of 2 complete (checkpoint pending human verification)
- **Files modified:** 30

## Accomplishments

- Migrated all `from storage import`, `from email_sender import`, `from drive_service import`, `from assessment_downloader import`, `from assessment_analyzer import` bare imports to `from core.X import Y` across all project directories
- Renamed `GOOGLE_CLOUD_PROJECT` to `GCP_PROJECT_ID` in all 4 `task_service.py` files (diagnosticos/, diagnosticos/complete_deployment/, diagnosticos_uim/, diagnosticos_uim/complete_deployment/)
- Verification grep returns zero matches — no bare imports remain in any of the 5 project directories

## Task Commits

Each task was committed atomically:

1. **Task 1: Find all bare imports and execute systematic replacement** - `e54fa56` (feat)

**Task 2 (checkpoint):** Awaiting human verification of smoke tests before marking complete.

## Files Created/Modified

30 .py files modified across 5 directories:
- `diagnosticos/` — 5 files (assessment_downloader, main, report_generator, send_emails, task_service)
- `diagnosticos/complete_deployment/` — 4 files (assessment_downloader, main_app, report_generator, task_service)
- `diagnosticos_uim/` — 5 files (assessment_downloader, main, main_app, report_generator, send_emails, task_service)
- `diagnosticos_uim/complete_deployment/` — 4 files (assessment_downloader, main_app, report_generator, task_service)
- `ensayos_generales/` — 5 files (assessment_analyzer, assessment_downloader, main, report_generator, send_emails)
- `assessment-analysis-project/` — 3 files (assessment_downloader, report_generator, send_pdf_reports)
- `reportes de test de diagnostico/` — 3 files (assessment_downloader, report_generator, send_pdf_reports)

## Decisions Made

- `task_service.py` files were included in the `GCP_PROJECT_ID` rename scope even though they weren't in the plan's `files_modified` frontmatter — the grep scan found them and they are .py files within the stated directories
- `from report_generator import ReportGenerator` was intentionally left as a bare import in `main.py`/`main_app.py` files — `report_generator` is a per-project file, not a `core/` module
- `complete_deployment/` subdirs received the same treatment as parent directories for consistency

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Updated task_service.py files not listed in plan frontmatter**
- **Found during:** Task 1 (GOOGLE_CLOUD_PROJECT grep discovery)
- **Issue:** The grep for `GOOGLE_CLOUD_PROJECT` found 4 task_service.py files (2 in diagnosticos/, 2 in diagnosticos_uim/) that were not in the plan's `files_modified` list. The must_haves truth states "GOOGLE_CLOUD_PROJECT env var name does not appear in any file in diagnosticos/ or diagnosticos_uim/"
- **Fix:** Renamed GOOGLE_CLOUD_PROJECT to GCP_PROJECT_ID in all 4 task_service.py files
- **Files modified:** diagnosticos/task_service.py, diagnosticos/complete_deployment/task_service.py, diagnosticos_uim/task_service.py, diagnosticos_uim/complete_deployment/task_service.py
- **Verification:** grep returns zero matches for GOOGLE_CLOUD_PROJECT in .py files
- **Committed in:** e54fa56 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 - missing critical)
**Impact on plan:** Required to meet the must_haves truth. No scope creep.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. Import paths are code changes only.

## Next Phase Readiness

- All project directories now use `from core.X import Y` package imports
- Phase 2 is fully complete pending human verification of smoke tests (Task 2 checkpoint)
- Phase 3 (report generators) can import from core/ without any conflict with legacy flat imports

---
*Phase: 02-core-package*
*Completed: 2026-03-01*

## Self-Check: PASSED

- Task 1 commit e54fa56: FOUND
- diagnosticos/assessment_downloader.py uses from core.storage: VERIFIED (grep returns 0 bare imports)
- GOOGLE_CLOUD_PROJECT absent from .py files in diagnosticos/ and diagnosticos_uim/: VERIFIED
- 02-05-SUMMARY.md: CREATED
