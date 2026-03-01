# Requirements: Unified Report Pipeline

**Defined:** 2026-02-28
**Core Value:** Adding a new report type requires only a new `report_generator` module and a docx template — all infrastructure is reused automatically.

## v1 Requirements

Requirements for the initial unified framework. Each maps to roadmap phases.

### Core Package

- [x] **CORE-01**: Developer can run a diff audit that documents all diverged functions across 6 copies of `assessment_downloader.py` and `assessment_analyzer.py`, producing a merge decision document before any canonical version is written
- [x] **CORE-02**: Unified `core/assessment_downloader.py` exists as a single canonical version that reconciles all diverged methods from 6 project copies (including `complete_deployment/` subfolder versions)
- [x] **CORE-03**: Unified `core/assessment_analyzer.py` exists as a single canonical version that reconciles all diverged methods across all project copies
- [x] **CORE-04**: `core/` package includes canonical `storage.py`, `email_sender.py`, `drive_service.py` promoted from existing `shared/` folder
- [x] **CORE-05**: All project files use package imports (`from core.storage import StorageClient`) — no bare flat-directory imports remain in the unified codebase

### Plugin System

- [x] **PLUG-01**: `BaseReportGenerator` abstract base class exists in `reports/base.py` with consistent interface: `generate(analysis_data) -> bytes` (or file path)
- [x] **PLUG-02**: Each existing report type has a `reports/<report_type>/generator.py` module that extends `BaseReportGenerator`
- [x] **PLUG-03**: Explicit plugin registry (dict or equivalent) maps report type name strings to generator classes, enabling lookup by name without dynamic discovery

### Data & Template Organization

- [x] **ORG-01**: All templates are organized under `templates/<report_type>/` — no template files scattered inside report-type module directories or project root
- [x] **ORG-02**: All runtime data is namespaced per report type under `data/<report_type>/analysis/`, `data/<report_type>/processed/`, `data/<report_type>/raw/` — prevents file collisions when multiple report types run from the same codebase
- [x] **ORG-03**: Duplicate email suppression uses per-report-type tracking at `data/<report_type>/processed_emails.csv` — a student who received report type A is not blocked from receiving report type B

### Entry Points

- [x] **ENTRY-01**: Unified `main.py` CLI entry point accepts `--report-type <name>` flag and routes execution to the correct generator via the plugin registry
- [x] **ENTRY-02**: Unified GCP webhook service routes incoming LearnWorlds webhook events to the correct report type based on assessment ID mapping
- [x] **ENTRY-03**: `--dry-run` flag in unified entry point runs the full pipeline (download, analyze, generate) without sending emails or uploading to Drive
- [x] **ENTRY-04**: `--test-email <address>` flag standardized across all report types via shared `email_sender` — redirects all outgoing email to one address during development

### Migration

- [x] **MIG-01**: `diagnosticos` report type runs via the unified framework and produces output identical to the current standalone version
- [x] **MIG-02**: `diagnosticos_uim` report type runs via the unified framework and produces output identical to the current standalone version
- [x] **MIG-03**: `ensayos_generales` report type runs via the unified framework and produces output identical to the current standalone version
- [x] **MIG-04**: `assessment-analysis-project` report type runs via the unified framework and produces output identical to the current standalone version
- [x] **MIG-05**: `reportes de test de diagnostico` report type runs via the unified framework and produces output identical to the current standalone version

### GCP Deployment

- [x] **GCP-01**: Single `Dockerfile` covers all report types — the active generator is selected via `REPORT_TYPE` environment variable, eliminating the `complete_deployment/` subfolder duplication pattern
- [x] **GCP-02**: `GET /status` health endpoint is available in all GCP-deployed report type configurations, returning queue state and last-run metadata

### Developer Experience

- [x] **DX-01**: All pipeline operations return a structured result dict `{success, records_processed, emails_sent, errors[]}` — consistent across all report types and entry points

## v2 Requirements

Deferred to future release.

### GCP Deployment

- **GCP-V2-01**: Single `cloudbuild.yaml` for unified GCP deployment pipeline — automates build/push/deploy in one command

### Observability

- **OBS-V2-01**: `slack_service` integrated into the shared core error handler — pipeline failures post to Slack automatically

### Plugin Discovery

- **PLUG-V2-01**: Automatic plugin autodiscovery scans `reports/` directory for generator modules — only valuable when report type count exceeds ~10

## Out of Scope

Explicitly excluded to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Config-file-driven report definition (YAML/JSON DSL) | Every existing report type has custom Python logic; a config DSL would need to become Turing-complete. Explicit module is simpler and equally fast to write |
| Database-backed email tracking (replacing CSV) | CSV works at this scale (hundreds of students). Database adds a service dependency with no benefit |
| Web UI / dashboard for report status | Internal tool used by one developer. GCP Cloud Logging + `/status` endpoint covers operational visibility needs |
| Multi-tenancy | Single organization (M30M). Pre-building multi-tenancy is YAGNI |
| Retry queue with exponential backoff (Celery/Redis) | Failed emails are logged; operator re-runs with `--force`. Operational failure mode is already manageable |
| Per-student immediate webhook trigger (non-batch) | Batch model (15-minute window) prevents API rate limiting; changing this requires a fundamentally different architecture |
| Rewriting existing report logic | Goal is reorganize and consolidate, not rewrite — existing rendering logic is preserved |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CORE-01 | Phase 1 | Pending |
| CORE-02 | Phase 2 | Complete |
| CORE-03 | Phase 2 | Complete |
| CORE-04 | Phase 2 | Complete |
| CORE-05 | Phase 2 | Complete |
| PLUG-01 | Phase 2 | Complete |
| PLUG-02 | Phase 6 | Complete |
| PLUG-03 | Phase 2 | Complete |
| ORG-01 | Phase 2 | Complete |
| ORG-02 | Phase 2 | Complete |
| ORG-03 | Phase 2 | Complete |
| ENTRY-01 | Phase 4 | Complete |
| ENTRY-02 | Phase 5 | Complete |
| ENTRY-03 | Phase 4 | Complete |
| ENTRY-04 | Phase 4 | Complete |
| MIG-01 | Phase 3 | Complete |
| MIG-02 | Phase 6 | Complete |
| MIG-03 | Phase 6 | Complete |
| MIG-04 | Phase 6 | Complete |
| MIG-05 | Phase 6 | Complete |
| GCP-01 | Phase 5 | Complete |
| GCP-02 | Phase 5 | Complete |
| DX-01 | Phase 4 | Complete |

**Coverage:**
- v1 requirements: 23 total
- Mapped to phases: 23
- Unmapped: 0

---
*Requirements defined: 2026-02-28*
*Last updated: 2026-03-01 after Plan 04-01 — ENTRY-03, ENTRY-04, DX-01 marked complete*
