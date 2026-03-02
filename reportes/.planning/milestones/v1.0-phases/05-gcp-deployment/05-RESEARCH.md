# Phase 5: GCP Deployment - Research

**Researched:** 2026-03-01
**Domain:** Google Cloud Run, Docker, functions-framework, Firestore, Cloud Tasks
**Confidence:** HIGH (core stack verified against official docs and existing production code)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Deployment model:**
- Keep `functions_framework` — it is fully compatible with Cloud Run containers and requires minimal rewrite of existing webhook code
- Container supports two modes driven by `REPORT_TYPE` env var:
  - If `REPORT_TYPE` is set → run `python main.py --report-type $REPORT_TYPE` (batch mode, exits after run)
  - If `REPORT_TYPE` is not set → start webhook server (persistent HTTP service)
- Dockerfile CMD: `functions-framework --source=webhook_service.py --target=webhook_handler --port=8080` for the webhook server mode; an entrypoint script handles the mode switch
- New `webhook_service.py` lives at the **repo root** (not inside any subdirectory) and imports from `core/` and `reports/`
- The `main.py` Cloud Functions naming conflict does NOT apply to Cloud Run + Dockerfile — GCP uses whatever CMD is specified; `main.py` stays as the CLI entry point
- Batch processing in the webhook calls `PipelineRunner.run()` directly — all report execution goes through the same PipelineRunner built in Phase 4

**Firestore queue structure:**
- Per-report-type hierarchical Firestore paths: `report_types/{report_type}/queue/`, `report_types/{report_type}/state/`, `report_types/{report_type}/counters/{assessment_type}`
- `FirestoreService`, `BatchProcessor`, and `TaskService` promoted to `core/` — consistent with Phase 2 pattern (`from core.firestore_service import FirestoreService`)
- `assessment_mapper` promoted to `core/` as a single shared module — maps all assessment IDs to `report_type` REGISTRY keys; one source of truth for the entire webhook routing

**Batch trigger mechanism:**
- Keep Cloud Tasks delayed-callback pattern — already battle-tested in existing deployments
- Callback URL shape: `GET /process-batch?report_type=diagnosticos&batch_id={uuid}`
- `BATCH_INTERVAL_MINUTES` env var, default 15 minutes
- Keep early-trigger logic: if queue reaches `MAX_QUEUE_SIZE` students, processing fires after 30 seconds. Configurable via `MAX_QUEUE_SIZE` env var.

### Claude's Discretion
- Dockerfile base image choice and layer ordering
- Entrypoint script implementation for the two-mode switch (REPORT_TYPE set vs. not set)
- Exact `decommission_complete_deployment` sequence: delete `complete_deployment/` after the new Dockerfile passes the test webhook delivery (success criterion #2), before the phase is marked complete
- `/status` endpoint response shape (beyond what the success criterion specifies: queue state + last-run metadata per report type)
- `cleanup_handler` endpoint — keep or drop from the unified webhook

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ENTRY-02 | Unified GCP webhook service routes incoming LearnWorlds webhook events to the correct report type based on assessment ID mapping | Webhook routing via core AssessmentMapper → REGISTRY key lookup; process-batch callback carries report_type param |
| GCP-01 | Single `Dockerfile` covers all report types — the active generator is selected via `REPORT_TYPE` environment variable, eliminating the `complete_deployment/` subfolder duplication pattern | functions-framework + entrypoint.sh mode-switch pattern; weasyprint system deps in Dockerfile |
| GCP-02 | `GET /status` health endpoint is available in all GCP-deployed report type configurations, returning queue state and last-run metadata | Per-report-type Firestore paths enable per-type status; status_handler iterates REGISTRY keys |
</phase_requirements>

---

## Summary

Phase 5 converts the project from duplicate Cloud Functions-based deployments (one per report type, with `complete_deployment/` subdirectories) to a single unified Dockerfile that runs on Cloud Run. The key insight is that Cloud Run — unlike Cloud Functions — uses whatever CMD the Dockerfile specifies, eliminating the `main.py` naming conflict that forced earlier renaming. The same container image is used for both the persistent webhook server mode (no `REPORT_TYPE` env var) and batch CLI mode (`REPORT_TYPE` set, container exits after run).

The existing `diagnosticos/webhook_service.py` and `diagnosticos/complete_deployment/` files are the canonical sources for all promoted `core/` modules. The existing `diagnosticos/webhook_service.py` is nearly identical to `diagnosticos_uim/webhook_service.py` — the primary difference is the assessment type set in `AssessmentMapper`. The new unified `webhook_service.py` at repo root must merge these into a single dispatcher that uses the shared `core/assessment_mapper.py` and routes to any REGISTRY-registered generator. The new Firestore path structure (`report_types/{report_type}/...`) provides complete isolation between concurrent report types.

The main technical work is: (1) promote `firestore_service.py`, `task_service.py`, `batch_processor.py`, and `assessment_mapper.py` to `core/` with unified namespacing; (2) write the new root `webhook_service.py` that dispatches to any REGISTRY type; (3) write the Dockerfile and `entrypoint.sh` mode switch; (4) add `/status` endpoint; (5) verify via test webhook delivery; (6) delete `complete_deployment/` directories.

**Primary recommendation:** Base the new `core/` services on `diagnosticos/complete_deployment/firestore_service.py` (uses the modern `FieldFilter` API — the most up-to-date copy), update Firestore paths to the per-report-type hierarchy, and use the `google.cloud.tasks_v2.Task` dataclass pattern with `OidcToken` for Cloud Tasks authentication.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| functions-framework | 3.* (already in requirements.txt) | Wraps Python function as HTTP handler for Cloud Run | Official Google library; compatible with Cloud Run container mode |
| flask | 2.* (already in requirements.txt) | HTTP request/response handling inside functions-framework | functions-framework uses Flask internally |
| google-cloud-firestore | 2.* (already in requirements.txt) | Firestore queue, state, counters | Already in production use |
| google-cloud-tasks | 2.* (already in requirements.txt) | Delayed batch callbacks | Already in production use; battle-tested |
| python-dotenv | 0.* (already in requirements.txt) | Load .env for local dev | Already used |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| google-auth | 2.* | Service account credentials for OIDC task auth | Required if Cloud Run service is not allow-unauthenticated |
| protobuf | 4.* (already in requirements.txt) | `timestamp_pb2.Timestamp` for Cloud Tasks schedule_time | Used in existing task_service.py |

### Dockerfile System Packages (for WeasyPrint)

WeasyPrint requires native libraries that cannot be pip-installed. On Debian 11+ / Ubuntu 20.04+ slim:

```
libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0
```

These are required by `weasyprint==66.0` (already in requirements.txt). The existing deployments work, so these packages are the correct set.

**No additional Python package changes needed** — the root `requirements.txt` already covers all dependencies for Phase 5.

---

## Architecture Patterns

### Recommended Project Structure After Phase 5

```
reportes/
├── Dockerfile              # NEW — single image for all report types
├── entrypoint.sh           # NEW — mode switch: webhook server vs. batch CLI
├── webhook_service.py      # NEW — unified webhook at repo root
├── main.py                 # EXISTING — CLI entry point (unchanged)
├── requirements.txt        # EXISTING — no changes needed
├── core/
│   ├── __init__.py
│   ├── assessment_downloader.py
│   ├── assessment_analyzer.py
│   ├── email_sender.py
│   ├── storage.py
│   ├── drive_service.py
│   ├── runner.py
│   ├── firestore_service.py   # PROMOTED from diagnosticos/complete_deployment/
│   ├── task_service.py        # PROMOTED from diagnosticos/
│   ├── batch_processor.py     # PROMOTED from diagnosticos/ (rewritten to use PipelineRunner)
│   └── assessment_mapper.py   # PROMOTED — unified, covers all report types
├── reports/
│   ├── __init__.py            # REGISTRY — diagnosticos registered
│   ├── base.py
│   └── diagnosticos/
│       └── generator.py
├── templates/
│   └── diagnosticos/
└── data/                   # gitignored
```

### Pattern 1: Two-Mode Entrypoint Script

**What:** A shell entrypoint that checks `REPORT_TYPE` and switches between batch-CLI and webhook-server modes.
**When to use:** Single container image must serve two purposes — persistent HTTP service and one-shot batch job.

```bash
#!/bin/bash
# entrypoint.sh
set -e

if [ -n "$REPORT_TYPE" ]; then
    # Batch mode: run pipeline and exit
    exec python main.py --report-type "$REPORT_TYPE"
else
    # Webhook mode: start functions-framework HTTP server
    exec functions-framework --source=webhook_service.py --target=webhook_handler --port=8080
fi
```

The Dockerfile should use this as its ENTRYPOINT/CMD with exec form to ensure signal propagation.

### Pattern 2: Unified Firestore Service with Per-Report-Type Paths

**What:** FirestoreService parameterized by `report_type`, uses `report_types/{report_type}/queue/`, `report_types/{report_type}/state/`, `report_types/{report_type}/counters/{assessment_type}`.
**When to use:** Multiple report types share the same Firestore database. Namespacing prevents cross-type data access.

**Canonical source:** `diagnosticos/complete_deployment/firestore_service.py` — this is the most up-to-date version. It uses `FieldFilter` (the modern non-deprecated API):

```python
# Source: diagnosticos/complete_deployment/firestore_service.py
from google.cloud.firestore_v1 import FieldFilter

# Modern query pattern (not deprecated .where('field', '==', value))
student_docs = (
    self.db.collection(self.queue_collection)
    .where(filter=FieldFilter('status', '==', 'queued'))
    .stream()
)
```

When promoting to `core/`, `__init__` must accept `report_type` and set:
```python
self.queue_collection = f"report_types/{report_type}/queue"
self.state_collection = f"report_types/{report_type}/state"
self.counters_collection = f"report_types/{report_type}/counters"
```

### Pattern 3: Unified Webhook Handler with report_type Routing

**What:** The root `webhook_service.py` adds a second mapping layer: assessment_id → assessment_type (existing) → REGISTRY report_type key (new). The `AssessmentMapper` in `core/` maps across ALL report types.
**When to use:** Single webhook endpoint must route events for multiple report type families.

```python
# webhook_service.py (root)
from core.firestore_service import FirestoreService
from core.task_service import TaskService
from core.assessment_mapper import AssessmentMapper
from core.runner import PipelineRunner
from reports import get_generator

# AssessmentMapper returns (report_type, assessment_type) tuple
# report_type → "diagnosticos" (REGISTRY key)
# assessment_type → "M1", "CL", etc. (per-generator internal type)
```

The Cloud Tasks callback URL shape carries `report_type`:
```
GET /process-batch?report_type=diagnosticos&batch_id={uuid}
```

The handler loads the correct `FirestoreService(report_type)` and calls `PipelineRunner.run(report_type=report_type)`.

### Pattern 4: Batch Processor Calling PipelineRunner (replaces subprocess)

**What:** The promoted `core/batch_processor.py` calls `PipelineRunner.run()` directly — NOT `subprocess.run(['python', 'main.py', ...])`.
**When to use:** Always. The existing `diagnosticos/batch_processor.py` uses subprocess which is fragile in containers. PipelineRunner is the canonical path.

```python
# core/batch_processor.py
from core.runner import PipelineRunner

def process_report_type(self, report_type: str) -> bool:
    runner = PipelineRunner(report_type=report_type)
    result = runner.run()
    return result["success"]
```

### Pattern 5: Cloud Tasks HTTP Target with OIDC (for authenticated Cloud Run)

**What:** When the Cloud Run service is NOT `--allow-unauthenticated`, Cloud Tasks must include an OIDC token.
**When to use:** Production deployment where the process-batch endpoint should not be publicly callable.

```python
# Source: https://docs.cloud.google.com/tasks/docs/creating-http-target-tasks
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2
import datetime

task = tasks_v2.Task(
    http_request=tasks_v2.HttpRequest(
        http_method=tasks_v2.HttpMethod.GET,
        url=f"{self.process_url}?report_type={report_type}&batch_id={batch_id}",
        oidc_token=tasks_v2.OidcToken(
            service_account_email=self.service_account_email,
            audience=self.process_url,
        ),
    ),
    schedule_time=self._make_schedule_time(delay_seconds),
)

def _make_schedule_time(self, delay_seconds: int):
    ts = timestamp_pb2.Timestamp()
    ts.FromDatetime(
        datetime.datetime.now(tz=datetime.timezone.utc)
        + datetime.timedelta(seconds=delay_seconds)
    )
    return ts
```

**Important:** The existing `task_service.py` sets `schedule_time` on the inner `http_request` dict, which is wrong — `schedule_time` is a top-level field on `Task`, not on `HttpRequest`. This is a bug in the existing code that will silently fail to schedule the delay correctly. Fix it when promoting to `core/`.

### Pattern 6: Unified AssessmentMapper

**What:** `core/assessment_mapper.py` combines assessment IDs from ALL report types. Returns a `(report_type, assessment_type)` tuple.
**When to use:** Single `AssessmentMapper` instance serves all incoming webhooks.

The two existing mappers differ only in assessment type sets:
- `diagnosticos/assessment_mapper.py` maps: `M1_ASSESSMENT_ID → "M1"`, `CL_ASSESSMENT_ID → "CL"`, `CIEN_ASSESSMENT_ID → "CIEN"`, `HYST_ASSESSMENT_ID → "HYST"`
- `diagnosticos_uim/assessment_mapper.py` maps: `M1_ASSESSMENT_ID → "M1"`, `F30M_ASSESSMENT_ID → "F30M"`, `B30M_ASSESSMENT_ID → "B30M"`, `Q30M_ASSESSMENT_ID → "Q30M"`, `HYST_ASSESSMENT_ID → "HYST"`

The unified mapper must also know WHICH report_type each assessment_type belongs to (for Firestore path routing). This can be done by each registered report type contributing its assessment ID mappings at startup:

```python
# Each generator declares its assessment mapping
# core/assessment_mapper.py uses REGISTRY to gather all mappings
# Returns: {"<hex_id>": {"report_type": "diagnosticos", "assessment_type": "M1"}}
```

### Dockerfile Pattern (Locked Decisions + Claude's Discretion)

```dockerfile
FROM python:3.11-slim

# System packages required by WeasyPrint
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy dependency manifest first (layer cache optimization)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY core/ ./core/
COPY reports/ ./reports/
COPY templates/ ./templates/
COPY main.py .
COPY webhook_service.py .
COPY entrypoint.sh .

RUN chmod +x entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
```

**Base image rationale:** `python:3.11-slim` matches the existing production stack (requirements.txt targets Python 3.9+ based on Union type hints in core/; Cloud Run supports 3.11). `slim` is recommended in official GCP docs for security and image size; `alpine` has wheel compatibility issues with pandas/numpy.

**Layer order:** requirements.txt before code — rebuilds only reinstall pip packages when code changes but deps do not.

**data/ directory:** Do NOT copy `data/` into the image — it is gitignored and should not be baked into the container. The Dockerfile omits it; Cloud Run's `STORAGE_BACKEND=gcs` causes the generator to use GCS instead of local filesystem.

### Anti-Patterns to Avoid

- **Subprocess calling main.py from batch_processor:** Fragile in containers, no shared process state. Use `PipelineRunner.run()` directly.
- **Flat Firestore collection paths (no report_type namespace):** Causes cross-contamination between concurrent report types. Always use `report_types/{report_type}/queue/...`.
- **Importing from `diagnosticos/` or `diagnosticos_uim/` subdirectories:** After Phase 5, all imports must come from `core/`. The subdirectory services are deleted with `complete_deployment/`.
- **Copying .env into Docker image:** Cloud Run injects env vars at deploy time via `--set-env-vars` or Secret Manager. Never COPY .env.
- **schedule_time on HttpRequest instead of Task:** The existing `task_service.py` has this bug. `schedule_time` is a field on `Task`, not `HttpRequest`.
- **allow-unauthenticated on the /process-batch endpoint in production:** Should be authenticated. Cloud Tasks handles OIDC token injection.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP handler for Cloud Run | Custom Flask app startup code | `functions-framework` | Already in stack; handles port binding, graceful shutdown, request routing |
| Firestore atomic counters | Manual read-modify-write | `@firestore.transactional` | Already implemented in existing code; handles race conditions correctly |
| Scheduled task delay | `time.sleep()` in a thread | Cloud Tasks `schedule_time` | Tasks survive container restarts; sleep does not |
| Assessment type routing | Manual if/elif chains | `AssessmentMapper` + `REGISTRY` dict lookup | O(1) lookup, easily extended |
| Report pipeline invocation in batch | `subprocess.run(['python', 'main.py', ...])` | `PipelineRunner.run(report_type=...)` | In-process, no shell overhead, structured result |

**Key insight:** All the hard infrastructure (queue management, batch scheduling, HMAC validation, report dispatch) already exists and is tested in production. Phase 5 is primarily a promotion/consolidation task, not a build-from-scratch task.

---

## Common Pitfalls

### Pitfall 1: schedule_time Placement in Cloud Tasks

**What goes wrong:** Task is created but never executes at the scheduled time; it fires immediately or fails silently.
**Why it happens:** The existing `diagnosticos/task_service.py` places `schedule_time` inside the `http_request` dict structure. The correct location is as a top-level field on the `Task` object, not on `HttpRequest`.
**How to avoid:** When promoting `task_service.py` to `core/`, use the `tasks_v2.Task()` dataclass pattern with `schedule_time` at the top level. Use `timestamp_pb2.Timestamp()` with `FromDatetime()` and a UTC-aware datetime.
**Warning signs:** Tasks process students immediately regardless of `BATCH_INTERVAL_MINUTES` setting.

### Pitfall 2: Firestore `.where()` Deprecation Warning

**What goes wrong:** Deprecation warning spam in Cloud Run logs; future version will be an error.
**Why it happens:** `diagnosticos/firestore_service.py` uses `.where('status', '==', 'queued')` (old positional API). `diagnosticos/complete_deployment/firestore_service.py` already has the fix.
**How to avoid:** Use the `complete_deployment/` version as the canonical source when promoting to `core/`. Use `FieldFilter` from `google.cloud.firestore_v1`:
```python
from google.cloud.firestore_v1 import FieldFilter
.where(filter=FieldFilter('status', '==', 'queued'))
```
**Warning signs:** Log messages containing "The `where` method is deprecated."

### Pitfall 3: WeasyPrint Missing System Libraries

**What goes wrong:** `ImportError` or `OSError` when WeasyPrint tries to load Pango/cairo at container startup.
**Why it happens:** `python:3.11-slim` does not include native graphics libraries. WeasyPrint cannot be loaded without them.
**How to avoid:** Add `apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0` to the Dockerfile before `pip install`. Test with `docker build` locally before deploying.
**Warning signs:** Success criterion #1 (`docker run -e REPORT_TYPE=diagnosticos ...`) fails with ImportError at startup.

### Pitfall 4: Entrypoint Environment Variable Not Exported

**What goes wrong:** `entrypoint.sh` checks `$REPORT_TYPE` but it evaluates as empty even when set.
**Why it happens:** In Docker exec form (`ENTRYPOINT ["/app/entrypoint.sh"]`), the shell running the script may not have the env var if the script does not use `#!/bin/bash`. CMD vs ENTRYPOINT interaction matters.
**How to avoid:** Always start `entrypoint.sh` with `#!/bin/bash` and use `set -e`. Use exec form ENTRYPOINT (`["/bin/bash", "/app/entrypoint.sh"]`) or chmod+x the script and use `ENTRYPOINT ["/app/entrypoint.sh"]`.
**Warning signs:** Container always starts webhook server even when `REPORT_TYPE` is set.

### Pitfall 5: Firestore Cross-Type Data Contamination

**What goes wrong:** Students completing `diagnosticos_uim` assessments appear in the `diagnosticos` queue.
**Why it happens:** Old flat Firestore paths (`queue/`, `state/`, `counters/`) are shared across all report types in the same GCP project.
**How to avoid:** The new `FirestoreService(report_type)` constructor must set `self.queue_collection = f"report_types/{report_type}/queue"` — not just `"queue"`. Verify with a test webhook delivery before deleting `complete_deployment/`.
**Warning signs:** Success criterion #2 fails because the wrong generator processes the queued student.

### Pitfall 6: PROCESS_BATCH_URL Missing report_type Parameter

**What goes wrong:** Cloud Tasks callback fires but the webhook handler can't route it to the correct FirestoreService path.
**Why it happens:** The old `task_service.py` creates tasks with `url=f"{self.process_url}?batch_id={batch_id}"` — no `report_type` parameter.
**How to avoid:** `TaskService.create_delayed_task(report_type, delay_seconds, batch_id)` must include `report_type` in the callback URL: `f"{self.process_url}?report_type={report_type}&batch_id={batch_id}"`.
**Warning signs:** Process-batch handler logs "no report_type in request args" or fails to find queued students.

### Pitfall 7: data/ Directory Missing at Container Startup

**What goes wrong:** `BaseReportGenerator.__init__` fails to create `data/<report_type>/` subdirectories because the parent path has permissions issues or the volume is read-only.
**Why it happens:** The `data/` directory is gitignored and excluded from Docker image. Cloud Run's container filesystem is writable for the container lifetime, but it's ephemeral — data written does not persist between invocations.
**How to avoid:** This is expected behavior. `STORAGE_BACKEND=gcs` must be set in Cloud Run env vars so the generator writes outputs to GCS rather than local `data/`. The `BaseReportGenerator.__init__` auto-creates subdirs at runtime, which works fine for the duration of a single invocation.
**Warning signs:** First webhook delivery works, second one fails because previous batch data was not cleaned up.

### Pitfall 8: decommission_complete_deployment/ Too Early

**What goes wrong:** The `complete_deployment/` directories are deleted before the unified Dockerfile is verified working, creating a rollback situation.
**Why it happens:** Rushing to clean up before validation is complete.
**How to avoid:** Per the locked decision, delete `complete_deployment/` directories ONLY after success criterion #2 (test webhook delivery passes). Make deleting the directories the LAST step in the final wave.
**Warning signs:** Not applicable — this is a sequencing discipline issue, not a code bug.

---

## Code Examples

Verified patterns from official sources and existing codebase:

### Dockerfile with WeasyPrint Dependencies

```dockerfile
# Source: Official WeasyPrint docs + GCP Cloud Run optimization guide
FROM python:3.11-slim

# WeasyPrint requires native Pango/HarfBuzz libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core/ ./core/
COPY reports/ ./reports/
COPY templates/ ./templates/
COPY main.py webhook_service.py entrypoint.sh ./
RUN chmod +x entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
```

### entrypoint.sh Mode Switch

```bash
#!/bin/bash
# Source: Pattern from Docker best practices + GCP env var docs
set -e

if [ -n "$REPORT_TYPE" ]; then
    echo "Batch mode: report_type=$REPORT_TYPE"
    exec python main.py --report-type "$REPORT_TYPE"
else
    echo "Webhook server mode"
    exec functions-framework \
        --source=webhook_service.py \
        --target=webhook_handler \
        --port=8080
fi
```

### FirestoreService with Namespaced Paths and FieldFilter

```python
# Source: diagnosticos/complete_deployment/firestore_service.py (canonical)
# Updated to use report_type namespacing per CONTEXT.md decision
from google.cloud import firestore
from google.cloud.firestore_v1 import FieldFilter

class FirestoreService:
    def __init__(self, report_type: str):
        self.db = firestore.Client()
        self.report_type = report_type
        self.queue_collection = f"report_types/{report_type}/queue"
        self.state_collection = f"report_types/{report_type}/state"
        self.counters_collection = f"report_types/{report_type}/counters"

    def get_queued_students(self):
        return list(
            doc.to_dict() | {"id": doc.id}
            for doc in self.db.collection(self.queue_collection)
            .where(filter=FieldFilter("status", "==", "queued"))
            .stream()
        )
```

### Cloud Tasks schedule_time (Correct Pattern)

```python
# Source: https://docs.cloud.google.com/tasks/docs/creating-http-target-tasks
# Fixes bug in existing task_service.py (schedule_time is on Task, not HttpRequest)
import datetime
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

def _make_schedule_timestamp(delay_seconds: int):
    ts = timestamp_pb2.Timestamp()
    ts.FromDatetime(
        datetime.datetime.now(tz=datetime.timezone.utc)
        + datetime.timedelta(seconds=delay_seconds)
    )
    return ts

task = tasks_v2.Task(
    http_request=tasks_v2.HttpRequest(
        http_method=tasks_v2.HttpMethod.GET,
        url=f"{process_url}?report_type={report_type}&batch_id={batch_id}",
        # Add oidc_token if Cloud Run is not allow-unauthenticated
    ),
    schedule_time=_make_schedule_timestamp(delay_seconds),  # TOP-LEVEL field
)
```

### /status Endpoint Pattern (Per-Type)

```python
# webhook_service.py root
@functions_framework.http
def status_handler(request: Request):
    from reports import REGISTRY
    status_by_type = {}
    for report_type in REGISTRY:
        fs = FirestoreService(report_type)
        state = fs.get_batch_state()
        queue_count = fs.get_queue_count()
        status_by_type[report_type] = {
            "queue_count": queue_count,
            "batch_active": fs.is_batch_active(),
            "batch_state": state,
        }
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "report_types": status_by_type,
    }), 200
```

### webhook_handler Routing (Unified)

```python
# The main webhook_handler function dispatches based on assessment_id → report_type
@functions_framework.http
def webhook_handler(request: Request):
    if request.method == "POST":
        return handle_webhook(request)
    elif request.method == "GET":
        path = request.path
        if path == "/process-batch" or request.args.get("batch_id"):
            return process_batch(request)
        elif path == "/status":
            return status_handler(request)
    return jsonify({"error": "Method not allowed"}), 405

def handle_webhook(request: Request):
    # HMAC validation (unchanged from existing code)
    # assessment_mapper.get_route(assessment_id) → (report_type, assessment_type)
    # FirestoreService(report_type).queue_student(student_data)
    # TaskService(report_type).create_delayed_task(report_type, delay, batch_id)
    ...

def process_batch(request: Request):
    report_type = request.args.get("report_type")
    batch_id = request.args.get("batch_id")
    # BatchProcessor(report_type).process_batch(batch_id)
    # → calls PipelineRunner(report_type=report_type).run()
    ...
```

### gcloud Deploy Commands (for reference)

```bash
# Build and push to Artifact Registry
gcloud builds submit --tag gcr.io/$GCP_PROJECT_ID/unified-pipeline .

# Deploy as webhook server (no REPORT_TYPE → webhook mode)
gcloud run deploy unified-webhook \
    --image gcr.io/$GCP_PROJECT_ID/unified-pipeline \
    --platform managed \
    --region us-central1 \
    --memory 1Gi \
    --timeout 540 \
    --set-env-vars "GCP_PROJECT_ID=$GCP_PROJECT_ID,TASK_QUEUE_ID=batch-processing-queue,BATCH_INTERVAL_MINUTES=15,STORAGE_BACKEND=gcs" \
    --set-secrets "LEARNWORLDS_WEBHOOK_SECRET=learnworlds-webhook-secret:latest" \
    --allow-unauthenticated

# Batch invocation (REPORT_TYPE set → batch mode, exits)
gcloud run jobs create diagnosticos-batch \
    --image gcr.io/$GCP_PROJECT_ID/unified-pipeline \
    --set-env-vars "REPORT_TYPE=diagnosticos,STORAGE_BACKEND=gcs"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Cloud Functions with flat-directory source | Cloud Run with Dockerfile + package imports | GCP deprecated gen1 Cloud Functions for complex deps | Full `core/` package imports work; no renaming hacks |
| `gcloud functions deploy --entry-point` | `ENTRYPOINT` in Dockerfile + `gcloud run deploy --image` | Cloud Run GA | No naming constraints on source files |
| Flat Firestore collections (`queue/`, `state/`) | Namespaced paths (`report_types/{type}/queue/`) | Phase 5 design decision | Complete cross-type isolation |
| `subprocess.run(['python', 'main.py', ...])` in BatchProcessor | `PipelineRunner.run(report_type=...)` | Phase 4 introduced PipelineRunner | In-process, structured result, no shell |
| `where('field', '==', value)` positional Firestore API | `where(filter=FieldFilter(...))` | google-cloud-firestore 2.x | Eliminates deprecation warnings in Cloud Run logs |

**Deprecated/outdated:**
- Old `tasks_v2` dict-based task creation: The newer `tasks_v2.Task()` dataclass pattern is cleaner and catches type errors at Python level.
- `from protobuf import timestamp_pb2` (in existing `task_service.py`): Should be `from google.protobuf import timestamp_pb2` — the bare `protobuf` package import may fail in newer protobuf versions.

---

## Open Questions

1. **OIDC Authentication for process-batch endpoint**
   - What we know: The existing deployments use `--allow-unauthenticated` for the webhook handler (so LearnWorlds can POST to it). The `/process-batch` endpoint is invoked only by Cloud Tasks.
   - What's unclear: Whether the current production setup has the process-batch URL publicly accessible or authenticated via OIDC token. The CONTEXT.md is silent on this.
   - Recommendation: For the initial unified Dockerfile, use `--allow-unauthenticated` for simplicity (matching existing behavior). Note that this means the process-batch endpoint is publicly callable — acceptable for the internal tool context described in REQUIREMENTS.md.

2. **Cloud Run service per report type vs. single unified service**
   - What we know: CONTEXT.md says "single Dockerfile" and GCP-01 says "REPORT_TYPE env var selects generator". The webhook server mode is one persistent Cloud Run service.
   - What's unclear: Whether the batch-mode invocations are via Cloud Run Jobs (one-shot) or via the same webhook service calling PipelineRunner in-process.
   - Recommendation: Batch processing happens IN-PROCESS within the webhook service (Cloud Tasks callback → `/process-batch?report_type=...` → BatchProcessor → PipelineRunner.run()). Cloud Run Jobs is a separate feature not required here. This matches the CONTEXT.md pattern exactly.

3. **AssessmentMapper unification: env var naming collision**
   - What we know: Both `diagnosticos` and `diagnosticos_uim` define `M1_ASSESSMENT_ID` and `HYST_ASSESSMENT_ID` but map them to the SAME assessment types. This is likely the same physical assessment used in both report types.
   - What's unclear: Should the unified mapper treat `M1` from diagnosticos and `M1` from diagnosticos_uim as the same entry, or should they be distinguished by report_type prefix?
   - Recommendation: Map the same hex assessment ID to a single `(report_type, assessment_type)` tuple. If the same hex ID could route to two different report types (which would be a product decision), that edge case does not exist today based on the different ID sets.

---

## Sources

### Primary (HIGH confidence)
- `diagnosticos/complete_deployment/firestore_service.py` — canonical Firestore service with FieldFilter API; direct code inspection
- `diagnosticos/webhook_service.py` and `diagnosticos_uim/webhook_service.py` — canonical webhook sources; direct code inspection
- `diagnosticos/task_service.py` — existing TaskService; bug identified in schedule_time placement
- `requirements.txt` (root) — confirmed all needed packages already present
- https://docs.cloud.google.com/tasks/docs/creating-http-target-tasks — Cloud Tasks HTTP target task pattern with OIDC
- https://doc.courtbouillon.org/weasyprint/stable/first_steps.html — WeasyPrint system package requirements (Debian 11+)
- https://docs.cloud.google.com/run/docs/tips/python — Cloud Run Python optimization: PYTHONUNBUFFERED, slim images

### Secondary (MEDIUM confidence)
- https://github.com/GoogleCloudPlatform/functions-framework-python/blob/main/examples/cloud_run_http/Dockerfile — functions-framework Dockerfile pattern (official example, older Python base)
- https://docs.cloud.google.com/run/docs/triggering/using-tasks — Cloud Tasks + Cloud Run IAM (OIDC roles/run.invoker pattern)

### Tertiary (LOW confidence)
- Web search: entrypoint.sh mode-switch pattern — common Docker pattern, not GCP-specific; verified against Docker documentation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — entire stack already in production requirements.txt; no new packages needed
- Architecture: HIGH — existing code directly inspected; patterns verified against official docs
- Pitfalls: HIGH (schedule_time bug) / MEDIUM (entrypoint env var) — schedule_time bug found in direct code inspection; entrypoint pitfall from Docker docs

**Research date:** 2026-03-01
**Valid until:** 2026-04-01 (GCP APIs stable; WeasyPrint deps stable)
