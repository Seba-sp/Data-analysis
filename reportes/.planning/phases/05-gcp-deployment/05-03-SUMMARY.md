---
phase: 05-gcp-deployment
plan: 03
subsystem: infra
tags: [docker, cloud-run, weasyprint, functions-framework, entrypoint, gcp]

requires:
  - phase: 05-gcp-deployment
    plan: 02
    provides: webhook_service.py — unified HTTP entry point (functions-framework target)
  - phase: 04-unified-entry-points
    plan: 02
    provides: main.py — CLI entry point for batch mode

provides:
  - Dockerfile — single container image (python:3.11-slim) for all report types
  - entrypoint.sh — mode switch: REPORT_TYPE set → batch CLI; unset → webhook server port 8080
  - .dockerignore — excludes data/, .env, legacy subdirs, __pycache__ from build context

affects:
  - Plan 05-04 — GCP deployment uses this image; `docker build -t unified-pipeline .` is the first step

tech-stack:
  added: []
  patterns:
    - "Single Dockerfile supports two execution modes via REPORT_TYPE env var (batch vs webhook)"
    - "Layer-cached pip install: COPY requirements.txt before COPY application code — only reinstalls pip deps when requirements.txt changes"
    - "ENTRYPOINT exec array form ['/app/entrypoint.sh'] — correct signal propagation to PID 1"
    - "entrypoint.sh uses exec python / exec functions-framework — replaces shell process with target process"
    - ".dockerignore mirrors Dockerfile exclusions for build-context efficiency"

key-files:
  created:
    - Dockerfile
    - entrypoint.sh
    - .dockerignore
  modified: []

key-decisions:
  - "python:3.11-slim base image — avoids alpine wheel compatibility issues with pandas/numpy while keeping image small"
  - "No CMD instruction — entrypoint.sh handles both modes; a CMD would conflict with the mode-switch logic"
  - "ENTRYPOINT uses exec form array notation — ensures signals (SIGTERM) propagate to the Python process, not blocked by shell"
  - ".dockerignore added as good practice — build context excludes data/, .env, legacy subdirs even though Dockerfile uses selective COPY"

requirements-completed: [GCP-01]

duration: 2min
completed: 2026-03-01
---

# Phase 5 Plan 3: Dockerfile and entrypoint.sh Summary

**python:3.11-slim container with WeasyPrint native libs and a REPORT_TYPE-driven entrypoint that switches between batch CLI and functions-framework webhook server**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-01T18:25:07Z
- **Completed:** 2026-03-01T18:26:48Z
- **Tasks:** 2
- **Files created:** 3

## Accomplishments

- `Dockerfile` at repo root: `python:3.11-slim` base, installs `libpango-1.0-0`, `libpangoft2-1.0-0`, `libharfbuzz-subset0` for WeasyPrint; layer-ordered pip install before code COPY; ENTRYPOINT `["/app/entrypoint.sh"]`
- `entrypoint.sh` at repo root: `set -e` bash script that branches on `$REPORT_TYPE` — batch mode uses `exec python main.py --report-type "$REPORT_TYPE"`; webhook mode uses `exec functions-framework --source=webhook_service.py --target=webhook_handler --port=8080`
- `.dockerignore` excludes `data/`, `.env`, `__pycache__`, legacy subdirectories (`diagnosticos/`, `diagnosticos_uim/`, etc.), and planning/tooling dirs from the Docker build context
- 12/12 structural checks verified: base image, all 3 WeasyPrint deps, PYTHONUNBUFFERED, requirements-first layer order, all COPY targets, chmod, ENTRYPOINT array form, data/ and .env not copied

## Task Commits

Each task was committed atomically:

1. **Task 1: Write Dockerfile and entrypoint.sh** — `6b5daa4` (feat)
2. **Task 2: Local docker build verification + .dockerignore** — `6494363` (chore)

## Files Created/Modified

- `Dockerfile` (27 lines) — Single container image; python:3.11-slim; WeasyPrint native libs; layer-cached pip install; COPY core/, reports/, templates/, main.py, webhook_service.py, entrypoint.sh; ENTRYPOINT ["/app/entrypoint.sh"]
- `entrypoint.sh` (15 lines) — Bash mode switch; REPORT_TYPE set → exec python main.py batch; unset → exec functions-framework webhook server port 8080
- `.dockerignore` (29 lines) — Excludes data/, .env/.env.*, __pycache__, legacy subdirs, tests, planning, .git from build context

## Decisions Made

- **python:3.11-slim chosen over alpine.** Alpine's musl libc causes wheel incompatibilities with pandas/numpy (pre-built PyPI wheels target glibc). Slim Debian gives small image size without the musl problem.
- **No CMD instruction.** The ENTRYPOINT script handles both execution modes. Adding CMD would create a conflict where the default CMD might bypass the mode switch logic.
- **exec form in entrypoint.sh.** Using `exec` replaces the bash shell process with the target process (Python or functions-framework), ensuring PID 1 receives SIGTERM signals from Cloud Run — critical for graceful shutdown.
- **.dockerignore added via plan discretion.** Dockerfile uses explicit COPY (not `COPY . .`), so .dockerignore is not strictly required — but it reduces build context size and prevents accidental context leakage if someone adds `COPY . .` later.

## Deviations from Plan

None — plan executed exactly as written.

The only operational note: Docker CLI 23.0.5 is installed but the Docker daemon was not running. Manual structural verification (12 checks via Python parsing) confirmed Dockerfile correctness. Live `docker build` will be executed during Plan 05-04 GCP deployment.

## Issues Encountered

- Docker daemon not running — covered by the plan's fallback: "If docker is not installed locally, document this in the task output and note that success criterion #1 will be verified during Plan 05-04." Manual syntax verification confirmed all structural requirements are met.

## User Setup Required

None — no external service configuration required. Environment variables for Cloud Run deployment are documented in `.env.example` from Plan 05-01.

## Next Phase Readiness

- `Dockerfile` and `entrypoint.sh` are ready for `gcloud run deploy` or Cloud Build
- Plan 05-04 must start with `docker build -t unified-pipeline .` (daemon must be running) to confirm zero ImportErrors before deploying to GCP
- The `complete_deployment/` legacy subdirectories (`diagnosticos/complete_deployment/`, `diagnosticos_uim/complete_deployment/`) are slated for deletion after test webhook delivery passes in Plan 05-04

---
*Phase: 05-gcp-deployment*
*Completed: 2026-03-01*
