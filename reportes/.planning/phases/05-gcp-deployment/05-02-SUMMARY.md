---
phase: 05-gcp-deployment
plan: 02
subsystem: infra
tags: [webhook, cloud-run, functions-framework, assessment-mapper, firestore, cloud-tasks, gcp]

requires:
  - phase: 05-gcp-deployment
    plan: 01
    provides: core/firestore_service.py, core/task_service.py, core/batch_processor.py, core/assessment_mapper.py

provides:
  - webhook_service.py — Unified HTTP entry point for all Cloud Run webhook events

affects:
  - Dockerfile / cloudbuild.yaml (05-03) — will set FUNCTION_TARGET=webhook_handler
  - All LearnWorlds webhook routing — replaces diagnosticos/webhook_service.py and diagnosticos_uim/webhook_service.py

tech-stack:
  added: []
  patterns:
    - "Single @functions_framework.http entry point dispatching all routes (POST /, GET /process-batch, GET /status, POST /cleanup)"
    - "REGISTRY-driven status and cleanup — no hard-coded report type lists"
    - "Lazy module-level service init via _initialize_services() — avoids import-time GCP client errors"
    - "report_type flows through every layer: webhook -> FirestoreService(report_type) -> BatchProcessor.process_batch(report_type, batch_id)"

key-files:
  created:
    - webhook_service.py
  modified: []

key-decisions:
  - "Single @functions_framework.http decorator on webhook_handler only — status_handler and cleanup_handler are plain functions dispatched internally (the old diagnosticos/webhook_service.py had multiple @functions_framework.http decorators which is incorrect)"
  - "BATCH_INTERVAL_MINUTES env var drives delay_seconds (default 15 min) instead of hard-coded constant — preserved from existing webhook_service.py"
  - "student_data dict includes report_type and assessment_type fields — makes the queued record self-describing for BatchProcessor"
  - "cleanup_handler calls TaskService().purge_queue() once (queue is shared) after iterating per-type Firestore cleanup"

metrics:
  duration: 3min
  started: "2026-03-01T18:19:24Z"
  completed: "2026-03-01T18:22:51Z"
  tasks: 2
  files_created: 1
  files_modified: 0
---

# Phase 5 Plan 2: Unified webhook_service.py Summary

**Single 449-line functions-framework HTTP handler dispatching all webhook routes to REGISTRY-registered report types via core/ services**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-01T18:19:24Z
- **Completed:** 2026-03-01T18:22:51Z
- **Tasks:** 2
- **Files created:** 1

## Accomplishments

- `webhook_service.py` created at repo root — replaces per-report-type `diagnosticos/webhook_service.py` and `diagnosticos_uim/webhook_service.py` with a single dispatcher
- `webhook_handler` (single `@functions_framework.http` entry point) dispatches: POST / to `handle_webhook`, GET /process-batch to `process_batch`, GET /status to `status_handler`, POST /cleanup to `cleanup_handler`
- `handle_webhook` uses `AssessmentMapper.get_route()` to obtain `(report_type, assessment_type)` from the webhook payload URL, then scopes all Firestore and TaskService calls to that `report_type`
- `status_handler` iterates `REGISTRY` keys to build per-type `{queue_count, batch_active, batch_state}` status — zero hard-coded type lists
- `cleanup_handler` iterates `REGISTRY` keys for per-type Firestore cleanup then purges the shared Cloud Tasks queue once

## Task Commits

Each task was committed atomically:

1. **Task 1+2: Write webhook_service.py (dispatch core + status/cleanup handlers)** — `bd93e2a` (feat)

Note: Tasks 1 and 2 were implemented in a single write since both target the same file and Task 2 is purely additive to what Task 1 defines. The file was written complete and the structural verification confirmed all handlers before committing.

## Files Created/Modified

- `webhook_service.py` (449 lines) — Unified webhook service at repo root; all imports from `core/` and `reports/` only; single `@functions_framework.http` decorated entry point; REGISTRY-driven status and cleanup

## Decisions Made

- **Single decorated entry point only.** The original `diagnosticos/webhook_service.py` applied `@functions_framework.http` to `status_handler` and `cleanup_handler` separately — that pattern is incorrect for a single-function Cloud Run deployment. Only `webhook_handler` carries the decorator; the others are plain functions dispatched internally.
- **`student_data` includes `report_type` field.** The queued Firestore document is self-describing: `report_type` and `assessment_type` are stored alongside student contact data so BatchProcessor does not need to infer context from collection path alone.
- **`BATCH_INTERVAL_MINUTES` drives all delay calculations.** The delay_seconds variable is computed from `BATCH_INTERVAL_MINUTES * 60` (env var, default 15) rather than hard-coding 900 seconds, keeping the existing operational configuration surface.

## Deviations from Plan

None — plan executed exactly as written.

The only implementation note: Tasks 1 and 2 were written as a single file rather than in two sequential edits, since Task 2 is purely additive (adding `status_handler` and `cleanup_handler` to what Task 1 defines). All plan requirements for both tasks are satisfied in the final file.

## Issues Encountered

- `functions_framework` is not installed in the local dev environment — same situation as `google-cloud-*` packages in Plan 05-01. Verification was performed via AST parsing and pattern matching rather than live import. The package will be present in the Cloud Run container image.

## User Setup Required

None — no additional configuration required beyond what was documented in `.env.example` during Plan 05-01. The `LEARNWORLDS_WEBHOOK_SECRET`, `MAX_QUEUE_SIZE`, `MEMORY_SIZE_MB`, `BATCH_INTERVAL_MINUTES`, and `PROCESS_BATCH_URL` env vars are already covered.

## Next Phase Readiness

- `webhook_service.py` is the last application-level file; the deployment container layer (Dockerfile, `cloudbuild.yaml`) is next (Plan 05-03)
- The Cloud Run deployment must set `FUNCTION_TARGET=webhook_handler` as the functions-framework entry point

---
*Phase: 05-gcp-deployment*
*Completed: 2026-03-01*
