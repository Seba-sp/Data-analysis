# Roadmap: Unified Report Pipeline

## Overview

Six independently-evolved copies of the same pipeline codebase are consolidated into a single Python framework. The work proceeds in strict dependency order: audit all diverged files before writing any shared code, build a stable `core/` package, validate the plugin interface with one report type, build the entry points, deploy to GCP, migrate the remaining four report types, and prove the new docxtpl path. Each phase delivers a coherent, verifiable capability. The result is a codebase where adding a new report type means creating one module and one template — nothing else.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Consolidation Audit** - Diff all 6 diverged file copies and produce a merge decision document before writing any shared code
- [x] **Phase 2: Core Package** - Build `core/` with canonical single versions of all shared services, per-report data namespacing, and the plugin base class (completed 2026-03-01)
- [x] **Phase 3: First Plugin Migration** - Port `diagnosticos` into the plugin structure and verify it produces identical output to the standalone version (completed 2026-03-01)
- [x] **Phase 4: Unified Entry Points** - Build the local CLI (`main.py`), `PipelineRunner`, dry-run mode, test-email mode, and structured result schema (completed 2026-03-01)
- [ ] **Phase 5: GCP Deployment** - Build the unified webhook service, single `Dockerfile`, health endpoint, and decommission `complete_deployment/`
- [ ] **Phase 6: Remaining Migrations** - Migrate the four remaining report types and complete the plugin registry

## Phase Details

### Phase 1: Consolidation Audit
**Goal**: Developer has a documented merge decision for every diverged method before any canonical code is written
**Depends on**: Nothing (first phase)
**Requirements**: CORE-01
**Success Criteria** (what must be TRUE):
  1. A merge decision document exists listing every method that differs across all 6 copies of `assessment_downloader.py` and `assessment_analyzer.py`, with an explicit resolution for each
  2. The `complete_deployment/` subfolders are treated as independent audited copies (not footnotes), and their version differences from parent directories are documented
  3. A unified `requirements.txt` candidate exists with all version conflicts resolved (pandas, weasyprint, protobuf) and the resolution rationale documented
  4. All environment variables across all 5 projects are catalogued in a `.env.example` consolidation document
  5. The actual Cloud Run entry point for `diagnosticos_uim` (`main.py` vs `main_app.py`) is identified and documented
**Plans**: 1 plan

Plans:
- [x] 01-01-PLAN.md — Run body diffs on diverged methods and write MERGE-DECISIONS.md with all method resolutions, requirements.txt candidate, and env var catalogue

### Phase 2: Core Package
**Goal**: A stable `core/` package exists as the single source of truth for all shared pipeline services, with per-report data namespacing and a plugin base class ready for the first generator
**Depends on**: Phase 1
**Requirements**: CORE-02, CORE-03, CORE-04, CORE-05, PLUG-01, PLUG-03, ORG-01, ORG-02, ORG-03
**Success Criteria** (what must be TRUE):
  1. `from core.assessment_downloader import AssessmentDownloader` works and the module contains exactly one reconciled version of every method (no duplicates from different project copies)
  2. `from core.assessment_analyzer import AssessmentAnalyzer` works with identical reconciliation
  3. `from core.storage import StorageClient`, `from core.email_sender import EmailSender`, and `from core.drive_service import DriveService` all work from the canonical `core/` package
  4. No file in the unified codebase uses a bare flat import (`from storage import ...`) — all imports use `from core.X import Y`
  5. `reports/base.py` contains `BaseReportGenerator` ABC with the `generate()` interface; `reports/__init__.py` contains an empty `REGISTRY` dict; `data/<report_type>/raw/`, `data/<report_type>/processed/`, and `data/<report_type>/analysis/` directory conventions are established and documented; all templates live under `templates/<report_type>/`
**Plans**: 5 plans

Plans:
- [x] 02-01-PLAN.md — Scaffold core/__init__.py, reports/__init__.py, reports/base.py (BaseReportGenerator ABC), empty REGISTRY, requirements.txt, .env.example
- [x] 02-02-PLAN.md — Assemble core/assessment_downloader.py by merging all 6 copies per MERGE-DECISIONS.md
- [x] 02-03-PLAN.md — Assemble core/assessment_analyzer.py (diagnosticos as canonical base for all methods)
- [x] 02-04-PLAN.md — Promote storage.py, email_sender.py, drive_service.py, slack_service.py, upload_folder_to_gcs.py to core/; delete shared/
- [x] 02-05-PLAN.md — Migrate all bare flat imports to package imports across all project subdirectories

### Phase 3: First Plugin Migration
**Goal**: The `diagnosticos` report type runs via the unified framework and produces output identical to its current standalone version, proving the plugin interface end-to-end
**Depends on**: Phase 2
**Requirements**: MIG-01
**Success Criteria** (what must be TRUE):
  1. `reports/diagnosticos/generator.py` exists, extends `BaseReportGenerator`, and is registered in `REGISTRY` under the key `"diagnosticos"`
  2. Running the pipeline for report type `diagnosticos` with the same input data produces a report file byte-for-byte (or content-equivalent) to the output of the pre-migration standalone version
  3. The `diagnosticos` generator's assessment type list (`["M1", "CL", "CIEN", "HYST"]`) lives in `generator.py` only — it does not appear anywhere in `core/`
  4. All `diagnosticos`-specific templates and question data files are organized under `templates/diagnosticos/` and `data/diagnosticos/questions/` respectively
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md — Scaffold reports/diagnosticos/ package and move templates + question CSVs to canonical per-report-type locations
- [x] 03-02-PLAN.md — Implement DiagnosticosGenerator, register in REGISTRY, verify output equivalence against standalone version

### Phase 4: Unified Entry Points
**Goal**: A single `main.py` routes to any registered report type, runs the full pipeline through `PipelineRunner`, and supports dry-run and test-email modes with a structured result on every exit
**Depends on**: Phase 3
**Requirements**: ENTRY-01, ENTRY-03, ENTRY-04, DX-01
**Success Criteria** (what must be TRUE):
  1. `python main.py --report-type diagnosticos` runs the full pipeline end-to-end using only `core/` services and the registered generator — no legacy standalone `main.py` is invoked
  2. `python main.py --report-type diagnosticos --dry-run` completes download, analysis, and generation steps without sending any email or uploading anything to Drive
  3. `python main.py --report-type diagnosticos --test-email developer@example.com` redirects all outgoing email to the specified address instead of student addresses
  4. Every pipeline exit (success or failure, local or GCP) returns a dict matching `{success: bool, records_processed: int, emails_sent: int, errors: list}` — no pipeline path returns `None` or an unstructured value
**Plans**: 2 plans

Plans:
- [x] 04-01-PLAN.md — Implement PipelineRunner in core/runner.py with email loop, Drive upload, dry-run/test-email controls, and structured PipelineResult
- [ ] 04-02-PLAN.md — Create main.py CLI entry point wiring --report-type, --dry-run, --test-email to PipelineRunner

### Phase 5: GCP Deployment
**Goal**: A single Dockerfile deploys all report types to Cloud Run; the webhook service routes events to the correct generator; health endpoint is available; `complete_deployment/` subfolders are removed
**Depends on**: Phase 4
**Requirements**: ENTRY-02, GCP-01, GCP-02
**Success Criteria** (what must be TRUE):
  1. `docker build -t unified-pipeline . && docker run -e REPORT_TYPE=diagnosticos unified-pipeline` succeeds locally with the unified `core/` package structure — no ImportError at startup or on first request
  2. A LearnWorlds webhook event for a `diagnosticos` assessment ID is received, validated (HMAC), queued in Firestore, and processed by the `diagnosticos` generator — verified via a test webhook delivery
  3. `GET /status` returns a JSON response with queue state and last-run metadata for every Cloud Run-deployed report type configuration
  4. The `complete_deployment/` subfolder inside `diagnosticos/` and `diagnosticos_uim/` no longer exists — all Cloud Run deployments use the unified Dockerfile
**Plans**: 4 plans

Plans:
- [ ] 05-01-PLAN.md � Promote FirestoreService, TaskService, BatchProcessor, AssessmentMapper to core/
- [ ] 05-02-PLAN.md � Write unified webhook_service.py at repo root with all route handlers
- [ ] 05-03-PLAN.md � Write Dockerfile and entrypoint.sh for two-mode Cloud Run container
- [ ] 05-04-PLAN.md � Deploy to Cloud Run, verify test webhook delivery, decommission complete_deployment/

### Phase 6: Remaining Migrations
**Goal**: All five existing report types run via the unified framework with verified identical output, the plugin registry is complete, and the old `shared/` directory is removed
**Depends on**: Phase 5
**Requirements**: MIG-02, MIG-03, MIG-04, MIG-05, PLUG-02
**Success Criteria** (what must be TRUE):
  1. `reports/diagnosticos_uim/generator.py`, `reports/ensayos_generales/generator.py`, `reports/assessment_analysis/generator.py`, and `reports/test_diagnostico/generator.py` all exist, extend `BaseReportGenerator`, and are registered in `REGISTRY`
  2. Running each of the four migrated report types with their respective input data produces output identical to the current standalone versions
  3. The `shared/` directory at the `reportes/` root no longer exists — its contents have been fully superseded by `core/`
  4. The REGISTRY in `reports/__init__.py` maps all 5 report type name strings to their generator classes, and `get_generator("diagnosticos_uim")` (and equivalents) returns the correct class without error
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Consolidation Audit | 1/1 | Complete | 2026-02-28 |
| 2. Core Package | 5/5 | Complete   | 2026-03-01 |
| 3. First Plugin Migration | 2/2 | Complete   | 2026-03-01 |
| 4. Unified Entry Points | 1/2 | Complete    | 2026-03-01 |
| 5. GCP Deployment | 0/TBD | Not started | - |
| 6. Remaining Migrations | 0/TBD | Not started | - |
