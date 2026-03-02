---
phase: 06-remaining-migrations
plan: 03
subsystem: plugin-migration
tags: [weasyprint, pandas, pdf-generator, test-diagnostico, plugin]

# Dependency graph
requires:
  - phase: 02-core-package
    provides: BaseReportGenerator base class and package structure
  - phase: 03-first-plugin-migration
    provides: Plugin pattern (generator.py extending BaseReportGenerator)
provides:
  - reports/test_diagnostico/ Python package with TestDiagnosticoGenerator
  - PDF generation for study plans for both Egresado and Cuarto medio students
  - templates/test_diagnostico/ with HTML template and Segmentos.xlsx
affects:
  - 06-04 (registry registration will import TestDiagnosticoGenerator)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Manual-prep Excel plugin pattern: download() fails fast with FileNotFoundError when data file missing (no API download)
    - Package-relative imports: all intra-package imports use reports.test_diagnostico.* prefix

key-files:
  created:
    - reports/test_diagnostico/__init__.py
    - reports/test_diagnostico/generator.py
    - reports/test_diagnostico/pdf_generator.py
    - reports/test_diagnostico/data_loader.py
    - reports/test_diagnostico/checklist_generator.py
    - reports/test_diagnostico/schedule_generator.py
    - reports/test_diagnostico/html_formatter.py
    - reports/test_diagnostico/utils.py
    - templates/test_diagnostico/plantilla_plan_de_estudio.html
    - templates/test_diagnostico/Segmentos.xlsx
  modified: []

key-decisions:
  - "Segmentos.xlsx force-added to git (-f) — gitignore has *.xlsx rule but this is a static config template asset, not a data file"
  - "TestDiagnosticoGenerator.analyze() is a pass-through (returns download_result unchanged) — data is pre-analyzed in the Excel workbook"
  - "render() returns data/test_diagnostico/output/ directory path (not a single file) — PDFGenerator writes multiple PDFs internally"

patterns-established:
  - "Manual-prep plugin pattern: download() raises FileNotFoundError with human-readable instructions when input file is missing"
  - "Explicit template paths passed to PDFGenerator constructor — overrides flat-directory defaults from standalone code"

requirements-completed: [MIG-04, MIG-05, PLUG-02]

# Metrics
duration: 8min
completed: 2026-03-01
---

# Phase 06 Plan 03: test_diagnostico Plugin Migration Summary

**TestDiagnosticoGenerator plugin with weasyprint PDF generation, 8-module package, and package-relative imports migrated from standalone flat-directory codebase**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-01T23:10:47Z
- **Completed:** 2026-03-01T23:18:48Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Migrated 6 support modules from standalone "reportes de test de diagnostico/" directory to reports/test_diagnostico/ package with all imports updated to package-relative form
- Created TestDiagnosticoGenerator extending BaseReportGenerator with fail-fast download() and explicit-path render()
- Copied HTML template and Segmentos.xlsx to canonical templates/test_diagnostico/ location

## Task Commits

Each task was committed atomically:

1. **Task 1: Copy templates to canonical location** - `c3b5df6` (feat)
2. **Task 2: Copy support modules with updated imports; create generator.py plugin** - `88be7a5` (feat)

**Plan metadata:** (to be added in final commit)

## Files Created/Modified
- `reports/test_diagnostico/__init__.py` - Package marker (empty)
- `reports/test_diagnostico/generator.py` - TestDiagnosticoGenerator: manual-prep plugin, download() fails fast, render() uses PDFGenerator with explicit template paths
- `reports/test_diagnostico/pdf_generator.py` - PDFGenerator orchestrator with all imports updated to reports.test_diagnostico.*
- `reports/test_diagnostico/data_loader.py` - Excel workbook loading/caching; imports from reports.test_diagnostico.utils
- `reports/test_diagnostico/checklist_generator.py` - HTML checklist table generation; imports from reports.test_diagnostico.{data_loader,utils}
- `reports/test_diagnostico/schedule_generator.py` - Weekly schedule table rendering; imports from reports.test_diagnostico.{data_loader,utils}
- `reports/test_diagnostico/html_formatter.py` - HTML template loading and placeholder population; imports from reports.test_diagnostico.utils
- `reports/test_diagnostico/utils.py` - Utility functions (no intra-package imports needed)
- `templates/test_diagnostico/plantilla_plan_de_estudio.html` - HTML study plan template
- `templates/test_diagnostico/Segmentos.xlsx` - Segments configuration Excel file (force-added to git)

## Decisions Made
- **Segmentos.xlsx force-added to git:** The `.gitignore` has a `*.xlsx` rule, but `Segmentos.xlsx` is a static configuration template asset (not data/output). Used `git add -f` to override. This is the correct approach — the file is required for the plugin to function and belongs in version control alongside the HTML template.
- **analyze() as pass-through:** Unlike API-download plugins, test_diagnostico data is pre-analyzed in the Excel workbook. `analyze()` simply returns the path from `download()` unchanged. No analysis code is needed.
- **render() returns directory:** PDFGenerator writes multiple PDFs to hard-coded output paths internally. The render() method returns `data/test_diagnostico/output/` as the output directory path rather than a single file path.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Force-added Segmentos.xlsx to git**
- **Found during:** Task 1 (Copy templates to canonical location)
- **Issue:** Git refused to stage Segmentos.xlsx due to `*.xlsx` rule in .gitignore; the file is a required static asset, not a data file
- **Fix:** Used `git add -f templates/test_diagnostico/Segmentos.xlsx` to bypass .gitignore rule; commit proceeded normally
- **Files modified:** templates/test_diagnostico/Segmentos.xlsx (staged)
- **Verification:** Both template files confirmed present via Python pathlib check
- **Committed in:** c3b5df6 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical — git staging)
**Impact on plan:** Required for template to be version-controlled. No scope creep.

## Issues Encountered
None beyond the gitignore deviation above.

## User Setup Required
None — no external service configuration required. Input data (`analisis de datos.xlsx`) must be manually placed at `data/test_diagnostico/analysis/` before running the plugin. The plugin's `download()` method will raise a descriptive `FileNotFoundError` if the file is missing.

## Next Phase Readiness
- TestDiagnosticoGenerator is importable and functionally complete
- Plan 06-04 can register it in the REGISTRY (one import + one dict entry)
- No blockers

---
*Phase: 06-remaining-migrations*
*Completed: 2026-03-01*
