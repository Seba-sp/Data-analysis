---
phase: 05-gcp-deployment
plan: 04
subsystem: infra
tags: [cloud-run, gcp, docker, webhook, firestore, cloud-tasks]

# Dependency graph
requires:
  - phase: 05-03
    provides: Dockerfile and entrypoint.sh — unified container for batch and webhook modes

provides:
  - Cloud Run service "unified-webhook" running at https://unified-webhook-822197731833.us-central1.run.app
  - End-to-end verified: LearnWorlds webhook POST -> HMAC validation -> Firestore queue -> Cloud Tasks batch
  - /status endpoint reporting per-type queue state (queue_count, batch_active)
  - complete_deployment/ legacy directories removed; unified Dockerfile is sole deployment artifact

affects:
  - Phase 6 (future) — any new report type can now be deployed by adding a plugin and rebuilding the container

# Tech tracking
tech-stack:
  added: [Cloud Run, Google Container Registry, gcloud CLI, Cloud Tasks, Firestore]
  patterns:
    - Unified container serves both webhook (REPORT_TYPE unset) and batch (REPORT_TYPE set) modes
    - PROCESS_BATCH_URL env var self-references the running service URL for Cloud Tasks callbacks
    - Decommission-after-verify locked sequence: complete_deployment/ deleted only after successful test webhook

key-files:
  created: []
  modified:
    - ".gitattributes (added via Task 1 for LF enforcement)"

key-decisions:
  - "Service URL is https://unified-webhook-822197731833.us-central1.run.app (regional URL, not hash-based)"
  - "PROCESS_BATCH_URL set to $SERVICE_URL/process-batch after first deploy — chicken-and-egg resolved by two-step deploy"
  - "complete_deployment/ directories decommissioned only after Task 2 checkpoint human approval (locked sequence per CONTEXT.md)"
  - "8 tracked Python files deleted across diagnosticos/complete_deployment/ and diagnosticos_uim/complete_deployment/"

patterns-established:
  - "Cloud Run two-step deploy: initial deploy without PROCESS_BATCH_URL, then update once URL is known"
  - "Test webhook uses actual M1 assessment ID (688a4a322f0c9ee2f10bcde6) against live Firestore to prove routing"

requirements-completed: [GCP-01, GCP-02, ENTRY-02]

# Metrics
duration: 30min (multi-session: Task 1 deploy + human verification + Task 3 cleanup)
completed: 2026-03-01
---

# Phase 5 Plan 4: GCP Deployment + Decommission Summary

**Unified container deployed to Cloud Run, end-to-end webhook delivery verified with live Firestore queuing, and complete_deployment/ legacy directories removed**

## Performance

- **Duration:** ~30 min (split across Task 1 session + checkpoint + Task 3 session)
- **Started:** 2026-03-01
- **Completed:** 2026-03-01
- **Tasks:** 3 (1 auto, 1 checkpoint:human-verify, 1 auto)
- **Files modified:** 9 (8 deleted from complete_deployment/ + .gitattributes added)

## Accomplishments

- Built and pushed unified-pipeline Docker image to Google Container Registry, deployed to Cloud Run as "unified-webhook" with 1Gi memory, 540s timeout, HMAC secret from Secret Manager
- End-to-end verified: POST to https://unified-webhook-822197731833.us-central1.run.app with M1 assessment ID 688a4a322f0c9ee2f10bcde6 returned `{"assessment_type":"M1","report_type":"diagnosticos","status":"success","user_email":"test@m30m.cl"}`, Firestore queue_count=1, batch_active=true
- Decommissioned 8 legacy Python files across diagnosticos/complete_deployment/ and diagnosticos_uim/complete_deployment/, completing Phase 5 success criterion #4

## Task Commits

Each task was committed atomically:

1. **Task 1: Build, push, and deploy to Cloud Run** - `45759ba` (fix)
2. **Task 2: Human verify — test webhook delivery end-to-end** - checkpoint (approved, no commit)
3. **Task 3: Decommission complete_deployment/ directories** - `dfa6ea6` (chore)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `diagnosticos/complete_deployment/` — DELETED (assessment_downloader.py, main_app.py, report_generator.py, task_service.py)
- `diagnosticos_uim/complete_deployment/` — DELETED (assessment_downloader.py, main_app.py, report_generator.py, task_service.py)
- `.gitattributes` — Added by Task 1 for LF line-ending enforcement

## Decisions Made

- Service URL stabilized as `https://unified-webhook-822197731833.us-central1.run.app` (regional URL format, not hash-based `ph6szgzyra-uc.a.run.app` format) — new revision on redeploy
- Two-step deploy pattern: initial deploy without PROCESS_BATCH_URL, retrieve URL, then update env var — no chicken-and-egg issue
- Decommission sequence was locked (complete_deployment/ deleted ONLY after Task 2 human checkpoint approved) per CONTEXT.md design decision

## Deviations from Plan

None — plan executed exactly as written. The service URL changed format between the plan's example URL and the actual deployed URL (from hash-based to numeric project ID format), which is normal Cloud Run behavior on redeployment — not a deviation.

## Issues Encountered

- Old service URL in plan interfaces (`unified-webhook-ph6szgzyra-uc.a.run.app`) was a previous revision; new deployment produced `unified-webhook-822197731833.us-central1.run.app`. No code references to the old URL were found in the codebase — scan confirmed clean.

## User Setup Required

None - Cloud Run service is deployed and running. Environment variables and secrets are configured on the service.

## Next Phase Readiness

- Phase 5 is fully complete: all 4 success criteria met
  1. Container builds and deploys without error — verified
  2. Test webhook delivery routed correctly to diagnosticos — verified
  3. GET /status returns queue state per report type — verified
  4. complete_deployment/ directories removed — verified
- Adding a new report type requires: new `reports/<type>/generator.py` module + docx template + REGISTRY entry — no infrastructure changes
- Service URL for future webhook configuration: `https://unified-webhook-822197731833.us-central1.run.app`

---
*Phase: 05-gcp-deployment*
*Completed: 2026-03-01*

## Self-Check: PASSED

- FOUND: .planning/phases/05-gcp-deployment/05-04-SUMMARY.md
- FOUND: commit 45759ba (Task 1 — build and deploy)
- FOUND: commit dfa6ea6 (Task 3 — decommission)
- FOUND: diagnosticos/complete_deployment/ DELETED
- FOUND: diagnosticos_uim/complete_deployment/ DELETED
