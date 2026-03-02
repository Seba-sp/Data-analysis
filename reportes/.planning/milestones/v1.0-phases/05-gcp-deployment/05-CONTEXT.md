# Phase 5: GCP Deployment - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a single Dockerfile that deploys all report types to Cloud Run via a unified webhook service. The webhook receives LearnWorlds events, routes them to the correct registered generator via REGISTRY, and queues students for batch processing. Includes a `/status` health endpoint. Removes `complete_deployment/` subfolders from `diagnosticos/` and `diagnosticos_uim/`. Adding new report types in Phase 6 must require zero changes to this layer.

</domain>

<decisions>
## Implementation Decisions

### Deployment model
- Keep `functions_framework` — it is fully compatible with Cloud Run containers and requires minimal rewrite of existing webhook code
- Container supports two modes driven by `REPORT_TYPE` env var:
  - If `REPORT_TYPE` is set → run `python main.py --report-type $REPORT_TYPE` (batch mode, exits after run)
  - If `REPORT_TYPE` is not set → start webhook server (persistent HTTP service)
- Dockerfile CMD: `functions-framework --source=webhook_service.py --target=webhook_handler --port=8080` for the webhook server mode; an entrypoint script handles the mode switch
- New `webhook_service.py` lives at the **repo root** (not inside any subdirectory) and imports from `core/` and `reports/`
- The `main.py` Cloud Functions naming conflict does NOT apply to Cloud Run + Dockerfile — GCP uses whatever CMD is specified; `main.py` stays as the CLI entry point
- Batch processing in the webhook calls `PipelineRunner.run()` directly — all report execution goes through the same PipelineRunner built in Phase 4

### Firestore queue structure
- Per-report-type hierarchical Firestore paths: `report_types/{report_type}/queue/`, `report_types/{report_type}/state/`, `report_types/{report_type}/counters/{assessment_type}`
- Rationale: With 3–4 concurrent report types and potentially 1000 students completing different assessments simultaneously, complete isolation between types prevents any cross-type data access or processing interference
- `FirestoreService`, `BatchProcessor`, and `TaskService` promoted to `core/` — consistent with Phase 2 pattern (`from core.firestore_service import FirestoreService`)
- `assessment_mapper` promoted to `core/` as a single shared module — maps all assessment IDs to `report_type` REGISTRY keys; one source of truth for the entire webhook routing

### Batch trigger mechanism
- Keep Cloud Tasks delayed-callback pattern — already battle-tested in existing deployments, natively supports "wait N minutes then process all queued students" per report type
- Callback URL shape: `GET /process-batch?report_type=diagnosticos&batch_id={uuid}` — explicit report_type in URL so handler loads the correct Firestore path and invokes the right generator
- `BATCH_INTERVAL_MINUTES` env var, default 15 minutes (already exists in `complete_deployment/main.py`, carry forward)
- Keep early-trigger logic: if queue reaches `MAX_QUEUE_SIZE` students before the window expires, processing fires after 30 seconds instead of waiting the full interval. Configurable via `MAX_QUEUE_SIZE` env var.

### Claude's Discretion
- Dockerfile base image choice and layer ordering
- Entrypoint script implementation for the two-mode switch (REPORT_TYPE set vs. not set)
- Exact `decommission_complete_deployment` sequence: delete `complete_deployment/` after the new Dockerfile passes the test webhook delivery (success criterion #2), before the phase is marked complete
- `/status` endpoint response shape (beyond what the success criterion specifies: queue state + last-run metadata per report type)
- `cleanup_handler` endpoint — keep or drop from the unified webhook

</decisions>

<specifics>
## Specific Ideas

- User concern: with 1000 students completing different assessments simultaneously, the queue must not have cross-type interference — the per-report-type Firestore path structure directly addresses this
- User context: previous GCP deployment required renaming `main.py` → `main_app.py` because Cloud Functions scans for `main.py`. This is a Cloud Functions constraint only — Cloud Run uses Dockerfile CMD, so `main.py` stays as CLI and the webhook lives in `webhook_service.py`
- Batching philosophy: 10 students complete `diagnosticos` in 15 min → 1 PipelineRunner call → 1 batch API call to LearnWorlds. N different assessment types → N separate batch calls, not N×students calls. Cloud Tasks is the right tool for this, not Pub/Sub.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `core/runner.py` (PipelineRunner): webhook batch processor calls `PipelineRunner.run(report_type=...)` — same interface as CLI
- `reports/REGISTRY` + `get_generator()`: webhook routes `assessment_type` → generator via REGISTRY lookup
- `diagnosticos/webhook_service.py` and `diagnosticos_uim/webhook_service.py`: nearly identical — canonical base for unified `webhook_service.py`; both handle HMAC validation, Firestore queuing, Cloud Tasks creation, batch processing, status, cleanup endpoints
- `diagnosticos/complete_deployment/`: contains `firestore_service.py`, `batch_processor.py`, `task_service.py`, `assessment_mapper.py` — source files for promoting to `core/`
- `core/email_sender.py`, `core/storage.py`, `core/drive_service.py`: existing `core/` services pattern to follow for promotion of Firestore/Tasks services

### Established Patterns
- Phase 2 service promotion pattern: take standalone service module → canonicalize → move to `core/` → update imports everywhere
- `from core.X import X` import convention throughout the codebase
- `PipelineRunner` + `REGISTRY` is the canonical execution path; webhook batch processing must go through this, not bypass it
- `data/<report_type>/raw/`, `data/<report_type>/processed/`, `data/<report_type>/analysis/` — data directories already namespaced per report type (prevents file conflicts during concurrent runs)
- `templates/<report_type>/` — templates already namespaced

### Integration Points
- `webhook_service.py` at repo root imports: `from core.firestore_service import FirestoreService`, `from core.task_service import TaskService`, `from core.batch_processor import BatchProcessor`, `from core.assessment_mapper import AssessmentMapper`, `from core.runner import PipelineRunner`, `from reports import get_generator`
- Dockerfile at repo root includes `core/`, `reports/`, `templates/`, `data/`, `main.py`, `webhook_service.py`, `requirements.txt`
- `complete_deployment/` directories to be deleted after test webhook delivery passes (success criterion #2)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 05-gcp-deployment*
*Context gathered: 2026-03-01*
