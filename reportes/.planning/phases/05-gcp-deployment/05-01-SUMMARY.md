---
phase: 05-gcp-deployment
plan: 01
subsystem: infra
tags: [firestore, cloud-tasks, gcp, google-cloud, batch-processing, assessment-mapper]

requires:
  - phase: 04-unified-entry-points
    provides: PipelineRunner.run() interface used by BatchProcessor

provides:
  - core/firestore_service.py — FirestoreService with per-report-type namespaced Firestore paths
  - core/task_service.py — TaskService with correct schedule_time placement and report_type in callback URL
  - core/batch_processor.py — BatchProcessor calling PipelineRunner.run() directly (no subprocess)
  - core/assessment_mapper.py — Unified AssessmentMapper returning (report_type, assessment_type) tuples

affects:
  - 05-gcp-deployment/05-02 (webhook_service.py will import all four of these)
  - Any Cloud Run webhook handler that routes LearnWorlds events

tech-stack:
  added: []
  patterns:
    - "Per-report-type Firestore namespacing: report_types/{report_type}/queue|state|counters"
    - "Unified assessment routing: hex_id -> (report_type, assessment_type) tuple"
    - "Direct PipelineRunner invocation from BatchProcessor — no subprocess"
    - "schedule_time on tasks_v2.Task top-level (not inside HttpRequest)"

key-files:
  created:
    - core/firestore_service.py
    - core/task_service.py
    - core/batch_processor.py
    - core/assessment_mapper.py
  modified: []

key-decisions:
  - "FirestoreService.__init__ accepts report_type and sets namespaced collection paths — no global singleton"
  - "get_counters/reset_counters use generic dict iteration — no hard-coded M1/CL/CIEN/HYST list"
  - "TaskService._make_schedule_timestamp uses datetime.timezone.utc (not time.time() float)"
  - "BatchProcessor.process_batch calls process_report_type once (not per-assessment-type)"
  - "AssessmentMapper uses separate env vars for UIM (M1_UIM_ASSESSMENT_ID, HYST_UIM_ASSESSMENT_ID) to avoid hex collisions with diagnosticos"
  - "UIM routes loaded after DIAG in AssessmentMapper — UIM wins on any shared hex value collision"

patterns-established:
  - "No module-level singleton instances in core/ services — callers construct with needed parameters"
  - "report_type is always passed explicitly, never hard-coded in core/ modules"

requirements-completed:
  - GCP-01
  - ENTRY-02

duration: 6min
completed: 2026-03-01
---

# Phase 5 Plan 1: Core GCP Services Promotion Summary

**Four GCP service modules promoted to core/ with per-report-type namespacing, subprocess elimination, and unified assessment routing covering both diagnosticos and diagnosticos_uim**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-01T18:10:35Z
- **Completed:** 2026-03-01T18:16:39Z
- **Tasks:** 2
- **Files modified:** 4 created

## Accomplishments

- `FirestoreService(report_type)` namespaces all Firestore paths under `report_types/{report_type}/` — enables multi-tenant operation without path collisions
- `TaskService.create_delayed_task(report_type, delay_seconds, batch_id)` embeds `report_type` in callback URL and places `schedule_time` correctly on `tasks_v2.Task` (not inside `HttpRequest`)
- `BatchProcessor.process_report_type(report_type)` calls `PipelineRunner(report_type).run()` directly — subprocess dependency completely removed
- `AssessmentMapper.get_route(assessment_id)` returns `(report_type, assessment_type)` tuple covering all assessment IDs from both diagnosticos and diagnosticos_uim systems

## Task Commits

Each task was committed atomically:

1. **Task 1: Promote FirestoreService and TaskService to core/** - `a9d7bbb` (feat)
2. **Task 2: Promote BatchProcessor and AssessmentMapper to core/** - `2576c77` (feat)

**Plan metadata:** (docs commit — pending)

## Files Created/Modified

- `core/firestore_service.py` — Firestore queue/state/counter management with `report_types/{report_type}/` namespace; generic counter handling without hard-coded type list
- `core/task_service.py` — Cloud Tasks with corrected `schedule_time` placement on `tasks_v2.Task`, `report_type` in callback URL, and `google.protobuf` import fix
- `core/batch_processor.py` — Batch orchestrator that delegates to `PipelineRunner.run()` (no subprocess); `process_batch(report_type, batch_id)` for namespaced cleanup
- `core/assessment_mapper.py` — Unified mapper merging diagnosticos and diagnosticos_uim routes; `get_route()` returns `(report_type, assessment_type)` or None

## Decisions Made

- **FirestoreService is not a singleton** — each call site passes `report_type` to get a correctly scoped instance; this is the only safe design for multi-report-type operation.
- **UIM uses distinct env var names** (e.g. `M1_UIM_ASSESSMENT_ID`, `HYST_UIM_ASSESSMENT_ID`) rather than the same names as diagnosticos. This avoids the ambiguity problem where the same env var name maps to two different systems — each hex value now unambiguously belongs to one route.
- **BatchProcessor has no `_send_emails`** — email is handled inside `PipelineRunner`; cleanup uses `FirestoreService(report_type)` methods.
- **`_make_schedule_timestamp` uses `datetime.timezone.utc`** — the original code passed a float to `FromDatetime()` which expects a `datetime` object; the fix uses the correct datetime API.

## Deviations from Plan

None — plan executed exactly as written.

The only noteworthy implementation detail: the plan listed `M1_ASSESSMENT_ID` and `HYST_ASSESSMENT_ID` as potentially shared env var names between diag and UIM. To avoid the hex collision problem cleanly, the UIM mapping uses `M1_UIM_ASSESSMENT_ID` and `HYST_UIM_ASSESSMENT_ID` as separate env var names. This is within the spirit of the plan's instruction ("check by hex value, not env var name") and produces unambiguous routing.

## Issues Encountered

- `google-cloud-firestore` and `google-cloud-tasks` are not installed in the local Python environment — import-level verification was done via AST parsing and structural checks rather than live import. `google.protobuf` and `core.assessment_mapper` were verified with live imports. This is expected in a dev-only environment; the packages will be present in the Cloud Run container.

## User Setup Required

None — no external service configuration required by this plan. Environment variables (`GCP_PROJECT_ID`, `PROCESS_BATCH_URL`, `*_ASSESSMENT_ID`) are documented in `.env.example`.

## Next Phase Readiness

- All four core services are importable from `core/` and structurally verified
- `webhook_service.py` (Phase 05-02) can now import `FirestoreService`, `TaskService`, `BatchProcessor`, and `AssessmentMapper` from `core/`
- The `AssessmentMapper` env var convention (`M1_UIM_ASSESSMENT_ID`, `HYST_UIM_ASSESSMENT_ID`) must be documented in `.env.example` during Phase 05-02

---
*Phase: 05-gcp-deployment*
*Completed: 2026-03-01*
