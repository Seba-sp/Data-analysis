---
phase: 06-remaining-migrations
plan: 02
subsystem: reporting
tags: [weasyprint, pandas, plugin-migration, ensayos_generales, html-templates]

# Dependency graph
requires:
  - phase: 03-first-plugin-migration
    provides: BaseReportGenerator ABC with namespaced data/templates dirs
  - phase: 02-core-package
    provides: core.storage.StorageClient, base path conventions
provides:
  - EnsayosGeneralesGenerator plugin extending BaseReportGenerator
  - reports/ensayos_generales/ package with generator.py and report_generator.py
  - templates/ensayos_generales/ with Portada.html, Ensayo2.html, resultados_ensayos.html
affects:
  - 06-04 (REGISTRY registration of EnsayosGeneralesGenerator)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Manual-prep download() pattern: fail fast with FileNotFoundError when pre-placed CSV absent"
    - "1 PDF per student render() — all assessment types combined in single output"

key-files:
  created:
    - reports/ensayos_generales/__init__.py
    - reports/ensayos_generales/generator.py
    - reports/ensayos_generales/report_generator.py
    - templates/ensayos_generales/Portada.html
    - templates/ensayos_generales/Ensayo2.html
    - templates/ensayos_generales/resultados_ensayos.html
  modified: []

key-decisions:
  - "ensayos_generales download() is manual-prep pattern: reads analysis.csv from data/ensayos_generales/analysis/, fails fast with FileNotFoundError if absent"
  - "render() produces 1 PDF per student (not 1 per assessment type) — key distinction from diagnosticos"
  - "No REGISTRY registration in this plan — deferred to Plan 06-04"

patterns-established:
  - "Manual-prep plugin: download() checks file exists, raises FileNotFoundError with descriptive path message"
  - "Single-PDF render: iterate rows, call generate_report(username), write resultados_{username}.pdf"

requirements-completed: [MIG-03, PLUG-02]

# Metrics
duration: 2min
completed: 2026-03-01
---

# Phase 06 Plan 02: EnsayosGenerales Plugin Migration Summary

**EnsayosGeneralesGenerator plugin wrapping standalone report_generator with manual-prep download() fail-fast and 1-PDF-per-student render(), using namespaced data/ensayos_generales/* paths**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-01T23:10:28Z
- **Completed:** 2026-03-01T23:12:59Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Copied three HTML templates verbatim from legacy ensayos_generales/templates/ to canonical templates/ensayos_generales/
- Created reports/ensayos_generales/ Python package with updated report_generator.py (all flat paths replaced with namespaced data/ensayos_generales/* and templates/ensayos_generales paths)
- Created EnsayosGeneralesGenerator with manual-prep download() (FileNotFoundError fail-fast), pass-through analyze(), and 1-PDF-per-student render()

## Task Commits

Each task was committed atomically:

1. **Task 1: Copy HTML templates to canonical location** - `e4f9dc3` (feat)
2. **Task 2: Copy and update report_generator.py; create generator.py plugin** - `0cea13a` (feat)

## Files Created/Modified
- `templates/ensayos_generales/Portada.html` - Main student results HTML template (verbatim copy)
- `templates/ensayos_generales/Ensayo2.html` - Secondary assessment template (verbatim copy)
- `templates/ensayos_generales/resultados_ensayos.html` - Results summary template (verbatim copy)
- `reports/ensayos_generales/__init__.py` - Empty package marker
- `reports/ensayos_generales/report_generator.py` - Standalone ReportGenerator copied and updated with namespaced paths
- `reports/ensayos_generales/generator.py` - EnsayosGeneralesGenerator extending BaseReportGenerator

## Decisions Made
- Manual-prep download() pattern: analysis.csv must be manually placed at data/ensayos_generales/analysis/analysis.csv before running; FileNotFoundError raised immediately if absent (no warn-and-continue)
- render() iterates rows and produces one resultados_{username}.pdf per student (not one per assessment type)
- REGISTRY registration deferred to Plan 06-04 as specified

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- EnsayosGeneralesGenerator importable from reports.ensayos_generales.generator
- Ready for REGISTRY registration in Plan 06-04
- To use the plugin: place analysis.csv at data/ensayos_generales/analysis/analysis.csv before running

---
*Phase: 06-remaining-migrations*
*Completed: 2026-03-01*
