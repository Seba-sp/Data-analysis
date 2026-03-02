---
phase: 06-remaining-migrations
plan: 01
subsystem: plugin-migration
tags: [python, weasyprint, pdf, assessment, plugin, baseReportGenerator]

# Dependency graph
requires:
  - phase: 03-first-plugin-migration
    provides: DiagnosticosGenerator gold-standard plugin pattern and BaseReportGenerator lifecycle
  - phase: 05-gcp-deployment
    provides: UIM env var naming convention (*_UIM_ASSESSMENT_ID) established in AssessmentMapper
provides:
  - DiagnosticosUIMGenerator plugin at reports/diagnosticos_uim/generator.py
  - Namespaced report_generator.py at reports/diagnosticos_uim/report_generator.py
  - UIM HTML template at templates/diagnosticos_uim/Portada.html
  - UIM question banks at data/diagnosticos_uim/questions/ (gitignored, on disk)
affects: [06-04-registry-validation, any plan adding diagnosticos_uim to REGISTRY]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - API-download plugin pattern applied to diagnosticos_uim (mirrors DiagnosticosGenerator exactly)
    - Namespaced path update pattern (copy standalone report_generator.py, update 5 hardcoded flat paths)

key-files:
  created:
    - reports/diagnosticos_uim/__init__.py
    - reports/diagnosticos_uim/generator.py
    - reports/diagnosticos_uim/report_generator.py
    - templates/diagnosticos_uim/Portada.html
  modified: []

key-decisions:
  - "data/diagnosticos_uim/questions/ files (CSVs + xlsx) are gitignored by parent .gitignore — intentional, data files not version-controlled (same as diagnosticos)"
  - "render() returns self.data_dir / 'output' (not self.analysis_dir.parent / 'output') — more explicit and matches namespacing intent"

patterns-established:
  - "UIM plugin mirrors DiagnosticosGenerator exactly with ASSESSMENT_TYPES and env var names as only differences"
  - "Namespaced path update: copy standalone report_generator.py and change templates/, data/questions/, data/processed/, data/analysis/, data/questions/lecciones.xlsx to include diagnosticos_uim/ prefix"

requirements-completed: [MIG-02, PLUG-02]

# Metrics
duration: 3min
completed: 2026-03-01
---

# Phase 06 Plan 01: DiagnosticosUIM Plugin Migration Summary

**DiagnosticosUIMGenerator plugin wrapping standalone UIM report generator into BaseReportGenerator lifecycle with namespaced paths and *_UIM_ASSESSMENT_ID env vars**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-01T19:10:25Z
- **Completed:** 2026-03-01T19:13:19Z
- **Tasks:** 2
- **Files modified:** 4 (1 template committed; 3 Python files committed; 6 data files on disk)

## Accomplishments
- Copied UIM Portada.html template to templates/diagnosticos_uim/ canonical location
- Copied 5 CSV question banks + lecciones.xlsx to data/diagnosticos_uim/questions/ (on disk)
- Created reports/diagnosticos_uim/ package with __init__.py, report_generator.py (namespaced paths), generator.py (DiagnosticosUIMGenerator)
- DiagnosticosUIMGenerator importable from reports.diagnosticos_uim.generator; ASSESSMENT_TYPES = ["M1", "F30M", "B30M", "Q30M", "HYST"]; all _assessment_ids use *_UIM_ASSESSMENT_ID naming

## Task Commits

Each task was committed atomically:

1. **Task 1: Copy templates and question banks to canonical locations** - `fff836c` (chore)
2. **Task 2: Copy and update report_generator.py; create generator.py plugin** - `8781c5e` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `templates/diagnosticos_uim/Portada.html` - UIM HTML report template (committed)
- `data/diagnosticos_uim/questions/M1.csv` - Question bank for M1 (on disk, gitignored)
- `data/diagnosticos_uim/questions/F30M.csv` - Question bank for F30M (on disk, gitignored)
- `data/diagnosticos_uim/questions/B30M.csv` - Question bank for B30M (on disk, gitignored)
- `data/diagnosticos_uim/questions/Q30M.csv` - Question bank for Q30M (on disk, gitignored)
- `data/diagnosticos_uim/questions/HYST.csv` - Question bank for HYST (on disk, gitignored)
- `data/diagnosticos_uim/questions/lecciones.xlsx` - Lecture name lookup (on disk, gitignored)
- `reports/diagnosticos_uim/__init__.py` - Empty package marker
- `reports/diagnosticos_uim/report_generator.py` - UIM ReportGenerator with 5 paths updated to namespaced locations
- `reports/diagnosticos_uim/generator.py` - DiagnosticosUIMGenerator extending BaseReportGenerator

## Decisions Made
- data/diagnosticos_uim/questions/ files are gitignored by parent .gitignore — same as diagnosticos question banks, intentional design
- render() uses self.data_dir / "output" directly (not self.analysis_dir.parent / "output" as in DiagnosticosGenerator) — both resolve identically but the direct form is clearer

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- data/ directory is gitignored by parent .gitignore — question bank CSVs and lecciones.xlsx exist on disk but cannot be committed. This matches the established pattern from Phase 3 (diagnosticos question banks have the same behavior). Template file (Portada.html) was committed successfully to templates/diagnosticos_uim/.

## User Setup Required
None - no external service configuration required. Environment variables M1_UIM_ASSESSMENT_ID, F30M_UIM_ASSESSMENT_ID, B30M_UIM_ASSESSMENT_ID, Q30M_UIM_ASSESSMENT_ID, HYST_UIM_ASSESSMENT_ID must be set before running (established in Phase 5).

## Next Phase Readiness
- DiagnosticosUIMGenerator is ready for REGISTRY registration in Plan 06-04
- Plugin is NOT yet registered in reports/__init__.py REGISTRY — that happens in Plan 06-04 per plan instructions
- Plans 06-02 and 06-03 (ensayos_generales and test_diagnostico plugins) can proceed independently

---
*Phase: 06-remaining-migrations*
*Completed: 2026-03-01*
