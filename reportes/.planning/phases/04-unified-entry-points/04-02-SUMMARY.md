---
phase: 04-unified-entry-points
plan: "02"
subsystem: infra
tags: [cli, argparse, entry-point, pipeline, PipelineRunner, REGISTRY]

# Dependency graph
requires:
  - phase: 04-01
    provides: PipelineRunner (core/runner.py) with dry_run, test_email, PipelineResult
  - phase: 03-first-plugin-migration
    provides: DiagnosticosGenerator registered in reports/REGISTRY
provides:
  - "main.py at repo root: single CLI entry point routing --report-type to PipelineRunner"
  - "Early report-type validation via get_generator() before PipelineRunner construction"
  - "Structured exit: code 0 on success=True, code 1 on success=False or crash"
affects:
  - 05-cloud-run-packaging
  - 06-second-plugin-migration

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CLI entry: argparse with required --report-type, optional --dry-run/--test-email"
    - "Early validation: get_generator() called before PipelineRunner to surface descriptive KeyError"
    - "All output via logging module — zero bare print() calls (Cloud Run compatible)"

key-files:
  created:
    - main.py
  modified: []

key-decisions:
  - "Early get_generator() call in main.py validates report type BEFORE PipelineRunner construction — ensures descriptive 'Available types' error is always reachable"
  - "No shebang line in main.py — Windows compatibility"
  - "All exit paths use sys.exit(0) or sys.exit(1) with a logged summary — never silent"

patterns-established:
  - "Single CLI entry point: python main.py --report-type <type> [--dry-run] [--test-email addr]"
  - "Unknown type: logged error with available REGISTRY.keys(), exits 1"
  - "Pipeline crash: logged with full traceback via logger.exception, exits 1"

requirements-completed: [ENTRY-01]

# Metrics
duration: 5min
completed: "2026-03-01"
---

# Phase 4 Plan 02: Unified Entry Point Summary

**argparse CLI in main.py routes --report-type to PipelineRunner via REGISTRY, with early type validation, structured PipelineResult logging, and zero bare print() calls**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-01T14:42:00Z
- **Completed:** 2026-03-01T14:47:00Z
- **Tasks:** 2 (1 auto + 1 human-verify checkpoint, approved)
- **Files modified:** 1 (main.py created)

## Accomplishments
- main.py created at repo root — single command runs any registered report type end-to-end
- Early report-type validation via get_generator() surfaces descriptive error listing available types before pipeline starts
- All three control flags wired: --report-type (required), --dry-run, --test-email
- User confirmed `python main.py --report-type diagnosticos --dry-run` executes correctly
- Exit code contract: 0 = success, 1 = failure or crash — Cloud Run compatible

## Task Commits

Each task was committed atomically:

1. **Task 1: Create main.py CLI entry point** - `bf22145` (feat)
2. **Task 2: Human verify — unified entry point end-to-end** - checkpoint approved by user (no separate commit)

**Plan metadata:** _(docs commit created after summary)_

## Files Created/Modified
- `main.py` — CLI entry point: argparse, early get_generator() validation, PipelineRunner instantiation, structured result logging, sys.exit codes

## Decisions Made
- Early get_generator() validation before PipelineRunner construction — ensures the descriptive "Available types: [...]" error message is always reachable. Without it, KeyError surfaces inside runner.run() with no context.
- No shebang line — Windows dev environment compatibility.
- No bare print() calls — all output via logging so Cloud Run captures structured logs.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The fix commit `d231a4d` (add early get_generator() validation) was already part of Task 1 in the prior session; no new issues arose.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 4 complete: PipelineRunner (core/runner.py) + main.py CLI entry point fully wired
- Phase 5 (Cloud Run packaging) can proceed — main.py is the CMD target for the Dockerfile
- Blocker noted in STATE.md remains: verify exact deployment commands before planning Phase 5 (no existing Dockerfile or cloudbuild.yaml in repo)

---
*Phase: 04-unified-entry-points*
*Completed: 2026-03-01*
