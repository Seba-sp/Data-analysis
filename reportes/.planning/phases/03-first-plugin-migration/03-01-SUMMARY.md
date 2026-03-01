---
phase: 03-first-plugin-migration
plan: 01
subsystem: reporting
tags: [python-package, weasyprint, html-templates, csv, file-migration]

# Dependency graph
requires:
  - phase: 02-core-package
    provides: core/ package with StorageClient, BaseReportGenerator in reports/base.py

provides:
  - reports/diagnosticos/ Python package (importable via `import reports.diagnosticos`)
  - reports/diagnosticos/report_generator.py with canonical path references
  - templates/diagnosticos/ with 4 HTML templates (M1, CL, HYST, CIEN)
  - data/diagnosticos/questions/ with 4 question CSVs (M1, CL, HYST, CIEN)

affects: [03-02-diagnosticos-generator, 04-pipeline-runner, 05-gcp-deployment]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-report-type asset directories: templates/<report_type>/ and data/<report_type>/questions/"
    - "Plugin package at reports/<report_type>/__init__.py (empty) + report_generator.py (private)"

key-files:
  created:
    - reports/diagnosticos/__init__.py
    - reports/diagnosticos/report_generator.py
    - templates/diagnosticos/M1.html
    - templates/diagnosticos/CL.html
    - templates/diagnosticos/HYST.html
    - templates/diagnosticos/CIEN.html
    - data/diagnosticos/questions/M1.csv (gitignored by design)
    - data/diagnosticos/questions/CL.csv (gitignored by design)
    - data/diagnosticos/questions/HYST.csv (gitignored by design)
    - data/diagnosticos/questions/CIEN.csv (gitignored by design)
  modified: []

key-decisions:
  - "data/diagnosticos/questions/*.csv files are gitignored by parent .gitignore (data/ and *.csv exclusions) — this is by design, data files are not version-controlled"
  - "diagnosticos/report_generator.py is NOT deleted — kept as standalone reference for output-equivalence verification in Plan 03-02"

patterns-established:
  - "Plugin package pattern: reports/<report_type>/__init__.py (empty marker) + report_generator.py (private PDF renderer)"
  - "Asset location pattern: templates/<report_type>/ for HTML templates, data/<report_type>/questions/ for question CSVs"

requirements-completed: [MIG-01]

# Metrics
duration: 3min
completed: 2026-03-01
---

# Phase 3 Plan 01: Package Scaffold and Asset Migration Summary

**reports/diagnosticos/ Python package scaffolded with updated canonical path references; 4 HTML templates and 4 question CSVs moved from diagnosticos/ to per-report-type locations**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-01T13:27:42Z
- **Completed:** 2026-03-01T13:30:48Z
- **Tasks:** 2
- **Files modified:** 6 (tracked by git; 4 CSV files gitignored)

## Accomplishments

- Created `reports/diagnosticos/` Python package — importable as `import reports.diagnosticos`
- Copied and updated `report_generator.py` with three canonical path references: `templates/diagnosticos`, `data/diagnosticos/questions`, `data/diagnosticos/analysis`
- Moved 4 HTML templates from `diagnosticos/templates/` to `templates/diagnosticos/` (old locations now empty)
- Moved 4 question CSVs from `diagnosticos/data/questions/` to `data/diagnosticos/questions/` (old locations now empty)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create reports/diagnosticos/ package and update report_generator.py paths** - `cdef815` (feat)
2. **Task 2: Move templates and question CSVs to canonical per-report-type locations** - `a519db1` (feat)

## Files Created/Modified

- `reports/diagnosticos/__init__.py` - Empty Python package marker
- `reports/diagnosticos/report_generator.py` - Copy of diagnosticos/report_generator.py with three updated path references (templates_dir, questions_dir, analysis_dir)
- `templates/diagnosticos/M1.html` - M1 assessment HTML template (moved from diagnosticos/templates/)
- `templates/diagnosticos/CL.html` - CL assessment HTML template (moved from diagnosticos/templates/)
- `templates/diagnosticos/HYST.html` - HYST assessment HTML template (moved from diagnosticos/templates/)
- `templates/diagnosticos/CIEN.html` - CIEN assessment HTML template (moved from diagnosticos/templates/)
- `data/diagnosticos/questions/M1.csv` - M1 question bank (moved; gitignored by design)
- `data/diagnosticos/questions/CL.csv` - CL question bank (moved; gitignored by design)
- `data/diagnosticos/questions/HYST.csv` - HYST question bank (moved; gitignored by design)
- `data/diagnosticos/questions/CIEN.csv` - CIEN question bank (moved; gitignored by design)

## Decisions Made

- Question CSV files are gitignored: the parent `.gitignore` at `Data-analysis/.gitignore` excludes `data/` and `*.csv` patterns. This is intentional — data files are not version-controlled. The files exist on disk in the correct locations and are functionally ready for use.
- The standalone `diagnosticos/report_generator.py` was NOT deleted as required by the plan — it remains for output-equivalence verification in Plan 03-02.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The `data/diagnosticos/questions/*.csv` files are excluded from git by the parent-level `.gitignore` (`data/` directory exclusion). This was recognized as intentional design, not a bug. Files were moved correctly on disk and are functionally available. No git force-add was needed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `reports/diagnosticos/` package is ready to receive `DiagnosticosGenerator` class in Plan 03-02
- All templates and question data are in canonical locations matching `BaseReportGenerator` path conventions
- `diagnosticos/main.py` and `diagnosticos/report_generator.py` remain available as reference implementations for output-equivalence testing

---
*Phase: 03-first-plugin-migration*
*Completed: 2026-03-01*
