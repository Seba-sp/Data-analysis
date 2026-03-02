---
phase: 02-core-package
plan: 02
subsystem: api
tags: [python, learnworlds, downloader, merge, core, pandas]

# Dependency graph
requires:
  - phase: 01-consolidation-audit
    provides: MERGE-DECISIONS.md with canonical resolution for all 36+ AssessmentDownloader methods
  - phase: 02-core-package
    plan: 01
    provides: core/__init__.py package marker, core/storage.py StorageClient
provides:
  - core/assessment_downloader.py AssessmentDownloader class (36+ methods, import-clean)
affects:
  - 02-03-core-analyzer (imports via from core.assessment_downloader import AssessmentDownloader)
  - 02-04-core-services (same import pattern)
  - 03-report-plugins (all report generators use AssessmentDownloader for download step)
  - 04-pipeline-runner (orchestrates AssessmentDownloader in pipeline lifecycle)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Package import: from core.assessment_downloader import AssessmentDownloader (replaces from storage import)"
    - "Dual userId/user_id API handling: r.get('userId') or r.get('user_id') in filter_responses"
    - "No respondida substitution: empty/NaN answers replaced with No respondida in save_responses_to_csv and add_answer_columns_to_csv"
    - "Temp CSV pattern: incremental mode writes temp CSV via save_temp_responses_to_csv (not in-memory)"

key-files:
  created:
    - core/assessment_downloader.py
  modified: []

key-decisions:
  - "save_form_responses_to_csv kept from aa despite domain-specific mcma logic — per MERGE-DECISIONS.md Section 8 override rule (form infrastructure always promoted to core/)"
  - "filter_responses uses Union type hint (not | syntax) for Python 3.9 compatibility"
  - "pd.isna() check wrapped in isinstance(float) guard to avoid pandas warning on non-float types"

patterns-established:
  - "38 methods (exceeds 36 minimum) — all MERGE-DECISIONS.md Section 2 entries with Destination=core/ included"
  - "No bare module imports: from core.storage import StorageClient (not from storage import)"

requirements-completed: [CORE-02]

# Metrics
duration: 7min
completed: 2026-03-01
---

# Phase 02 Plan 02: Core Downloader Summary

**Canonical AssessmentDownloader merged from 6 diverged copies — 38 methods, import-clean (from core.storage), no bare imports, cleanup_temp_files canonical name, GCP_PROJECT_ID env var**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-01T04:08:16Z
- **Completed:** 2026-03-01T04:15:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Assembled `core/assessment_downloader.py` from 4 source files (diagnosticos/, ensayos_generales/, assessment-analysis-project/, diagnosticos_uim/) following all MERGE-DECISIONS.md Section 2 resolution decisions
- 38 methods total (exceeds required 36): all IDENTICAL methods verbatim from diag, all DIVERGES methods resolved per canonical base, all ABSENT methods added from their respective source
- `from core.storage import StorageClient` import replacing all bare `from storage import` occurrences
- `cleanup_temp_files` as canonical name (eg body — superset deleting incremental JSON + temp CSV + temp analysis)
- `filter_responses` uses `r.get('userId') or r.get('user_id')` dual API variant handling from diag
- `save_responses_to_csv` with `include_usernames` param and "No respondida" substitution from eg
- `_download_and_process_common` uses eg base: writes temp CSV in incremental mode (not in-memory)
- All user/form infrastructure methods promoted from eg and aa per core boundary override rules

## Task Commits

Each task was committed atomically:

1. **Task 1: Read all four source files and assemble core/assessment_downloader.py** - `98e44c5` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `core/assessment_downloader.py` — Canonical merged AssessmentDownloader; 38 methods; from core.storage import; cleanup_temp_files; no GOOGLE_CLOUD_PROJECT; 1569 lines

## Decisions Made
- `save_form_responses_to_csv` kept from aa including the `_normalize_commune` call and `_process_email_columns` call — these were referenced inside the method body in aa. However, on inspection, `save_form_responses_to_csv` in the canonical core version does NOT call `_normalize_commune` or `_process_email_columns` (those are domain-specific per MERGE-DECISIONS.md). The commune normalization and email processing lines were removed from `save_form_responses_to_csv` in core/ — only the core form CSV saving logic is included.
- Used `Union[List[Dict[str, Any]], pd.DataFrame]` type hints instead of `|` union syntax for broader Python version compatibility
- `pd.isna()` check wrapped with `isinstance(answer_val, float)` guard to avoid type errors on non-float values

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed domain-specific method calls from save_form_responses_to_csv**
- **Found during:** Task 1 (assembling save_form_responses_to_csv from aa source)
- **Issue:** aa's `save_form_responses_to_csv` calls `self._normalize_commune()` and `self._process_email_columns()` — both explicitly excluded from core/ per MERGE-DECISIONS.md Section 8 (domain-specific, stay in reports/assessment_analysis/). Including these calls in core/ would create a broken reference (methods not defined in core/).
- **Fix:** Removed the `_normalize_commune` and `_process_email_columns` calls from the core/ version of `save_form_responses_to_csv`. Retained the mcma multi-choice question handling and test preparation sum column logic (infrastructure, not domain-specific).
- **Files modified:** core/assessment_downloader.py
- **Verification:** All 38 methods parse cleanly; import test passes; no NameError on missing methods
- **Committed in:** `98e44c5` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug — broken reference prevention)
**Impact on plan:** Fix was required for correctness — the aa source had domain-specific method calls that cannot exist in core/. No scope creep.

## Issues Encountered
- Source files were very large (60-80KB each) requiring section-by-section reading. No functional issues.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `from core.assessment_downloader import AssessmentDownloader` imports cleanly from repo root
- 38 methods verified (all MERGE-DECISIONS.md Section 2 core/ destinations covered)
- Plans 02-03 (core analyzer) and 02-04 (core services) can proceed independently
- No blockers

---
*Phase: 02-core-package*
*Completed: 2026-03-01*
