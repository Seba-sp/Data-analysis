# Project Research Summary

**Project:** Reportes — Unified Python Report Pipeline Framework
**Domain:** Internal report generation pipeline (LearnWorlds API, PDF/docx, GCP Cloud Run, plugin architecture)
**Researched:** 2026-02-28
**Confidence:** HIGH (all four research areas grounded in direct codebase analysis of 5 production projects)

## Executive Summary

This project consolidates five independently-evolved Python report pipeline projects (`diagnosticos`, `diagnosticos_uim`, `assessment-analysis-project`, `ensayos_generales`, `reportes de test de diagnostico`) into a single, plugin-based framework. Each project shares the same pipeline skeleton — LearnWorlds API download, CSV analysis, report generation, email delivery, Google Drive upload — but has independently drifted copies of the same core files. The correct architectural approach is a `core/` package with canonical shared services, a `reports/` plugin directory where each report type owns its own `generator.py`, and a unified `entrypoints/` layer covering both local CLI and GCP Cloud Run webhook modes. The existing codebase already contains all required logic; the primary work is structured consolidation, not new feature development.

The recommended stack is entirely Python 3.11 on existing dependencies: pandas 2.2.x, docxtpl for new report generation (replacing weasyprint for new report types only), Flask 3.x + functions-framework for GCP, and the google-cloud-* suite already in use. The most significant technology decision is migrating new report generators from weasyprint/HTML to docxtpl/Word templates — this reduces Docker image size by ~300MB, makes templates editable by non-developers, and aligns with the stated goal in PROJECT.md. Existing generators remain on weasyprint during the migration period.

The highest risk in this project is the divergence between the five project copies and the `complete_deployment/` subfolders within two of them. There are six distinct copies of `assessment_downloader.py` with incompatible APIs (renamed methods, different signatures, different field handling for the LearnWorlds `userId`/`user_id` inconsistency). Skipping a thorough audit of all diverged files before writing any shared code will cause silent regressions — the kind that produce wrong report output rather than crashes. The mitigation is a mandatory consolidation audit in Phase 1 that produces an explicit merge decision document before any code is written.

---

## Key Findings

### Recommended Stack

The full stack is already in place across the five projects. No new dependencies are required for the consolidated framework — only version alignment and one new library for the docx report format. See `.planning/research/STACK.md` for full detail.

**Core technologies:**
- **Python 3.11** — runtime; LTS until Oct 2027; all GCP base images support it
- **pandas 2.2.x** — CSV/XLSX processing; already pinned in `complete_deployment/`; do not allow 1.x to survive into unified requirements
- **docxtpl 0.17.x + Jinja2 3.1.x** — primary report generator for new report types; Word templates editable by non-developers; requires python-docx 1.x (breaking change from 0.x)
- **weasyprint 66.x** — keep for existing report generators during migration; adds ~300MB to Docker image; do not use for new report types
- **Flask 3.x + functions-framework 3.x** — GCP Cloud Run entry point; already proven in existing webhook_service.py
- **google-cloud-firestore 2.x + google-cloud-tasks 2.x** — batch queue infrastructure; must pin protobuf==4.x to avoid known compatibility break with protobuf 5.x
- **stdlib smtplib + email.message** — email delivery; zero dependencies; sufficient for Gmail SMTP
- **requests 2.31+** — LearnWorlds API client; synchronous, appropriate for this use case

**Critical version constraint:** `google-cloud-firestore==2.*` is incompatible with `protobuf==5.*`. Pin `protobuf==4.*` explicitly.

**Key architectural technology decision:** Adopt docxtpl for all new report generators; keep weasyprint only for existing ones. The transition is incremental — existing `report_generator.py` classes move unchanged into `reports/<type>/generator.py` and continue using weasyprint until explicitly migrated.

### Expected Features

All research is grounded in the 5 existing codebases. See `.planning/research/FEATURES.md` for full prioritization matrix.

**Must have — table stakes (P1, migration is broken without these):**
- Shared `core/` package with single canonical versions of: `assessment_downloader.py`, `assessment_analyzer.py`, `storage.py`, `email_sender.py`, `drive_service.py` — eliminates 5-way drift
- Plugin generator interface: `reports/<type>/generator.py` implementing `BaseReportGenerator.generate_pdf()`
- Per-report data namespacing: `data/<report_type>/raw/`, `data/<report_type>/processed/`, `data/<report_type>/analysis/` — prevents cross-contamination between types
- Unified `main.py` accepting `--report-type <name>` — single entry point for all report types
- Shared `processed_emails.csv` tracking per report type — duplicate email suppression
- Template organization: `templates/<report_type>/` — prevents template name collisions
- All 5 existing report types migrated and producing identical output to current standalone versions

**Should have — add after v1 migration is confirmed (P2):**
- Single `Dockerfile` covering all report types via `REPORT_TYPE` env var — eliminates `complete_deployment/` duplicates
- Dry-run mode (`--dry-run`) in unified entry point
- Test mode (`--test-email`) standardized across all types via shared email_sender
- Structured result schema `{success, records_processed, emails_sent, errors[]}` across all operations
- Health/status endpoint for all GCP-deployed report types (currently only diagnosticos has it)

**Defer to v2+:**
- Plugin autodiscovery (auto-detection of modules in `reports/`) — only valuable when N > 8 types
- Slack error notification wired into shared error handler
- Config-file-driven report definitions (YAML/JSON) — do not build; custom Python logic per type cannot be expressed in config without a Turing-complete DSL

### Architecture Approach

The architecture follows two classical patterns: Template Method for the pipeline orchestrator (`PipelineRunner.run()` defines the fixed download → process → analyze → generate → deliver sequence) and Strategy for the report generators (each type implements `BaseReportGenerator`, the `REGISTRY` dict in `reports/__init__.py` maps strings to classes). GCP-specific infrastructure (Firestore, Cloud Tasks, batch_processor) is isolated in `entrypoints/gcp/` and never imported by local CLI code. See `.planning/research/ARCHITECTURE.md` for full structure, component diagrams, and code sketches.

**Major components:**
1. **`core/`** — single source of truth for shared pipeline services; promoted from `shared/` with `assessment_downloader.py` and `assessment_analyzer.py` merged from 5 diverged copies
2. **`reports/<type>/generator.py`** — plugin per report type; subclass of `BaseReportGenerator`; owns its templates and assessment type list; the only file that changes when a new report is added
3. **`entrypoints/pipeline_runner.py`** — shared orchestrator called by both local CLI and GCP webhook; neither entry point re-implements pipeline steps
4. **`entrypoints/webhook_service.py`** — GCP Cloud Run handler; validates HMAC signature, queues students in Firestore, triggers Cloud Tasks batch; uses lazy service initialization to survive cold start
5. **`entrypoints/gcp/`** — Firestore queue, Cloud Tasks scheduling, batch processor; never imported outside GCP entry point
6. **`data/<type>/`** — runtime data namespaced per report type; only `questions/` subdirectory is committed; raw/processed/analysis are gitignored

**Key internal boundary rule:** `core/` never imports from `reports/` or `entrypoints/`. `entrypoints/` never imports a specific generator class directly — always through `get_generator(report_type)`. GCP modules are never imported by local CLI code.

### Critical Pitfalls

All 6 pitfalls below are grounded in directly observed code evidence, not assumptions. See `.planning/research/PITFALLS.md` for full detail, recovery strategies, and the pitfall-to-phase mapping.

1. **Wrong canonical version chosen during merge** — `assessment_downloader.py` exists in 6 locations with renamed methods, different signatures, and different LearnWorlds `userId`/`user_id` field handling. Silently picks wrong behavior. Prevention: mandatory line-by-line diff of all copies before writing any `core/` code; produce a merge decision document as Phase 1 deliverable.

2. **`complete_deployment/` treated as packaging artifact, not a separate code copy** — `diagnosticos/complete_deployment/` has pandas 2.2.2 and weasyprint 66.0 while its parent folder pins pandas 1.x and weasyprint 56.x. Hotfixes have been applied in `complete_deployment/` without backporting. The Cloud Run production environment is running `complete_deployment/` versions. Prevention: audit `complete_deployment/` as a fourth project during Phase 1, not as a footnote.

3. **Dependency version conflicts in unified requirements.txt** — pandas spans 1.x and 2.2.2 across projects; weasyprint spans 56.x and 66.x; these have breaking behavioral changes (DataFrame copy semantics, HTML rendering). Prevention: resolve versions top-down (highest wins); run all pipelines against target versions before committing to unified `requirements.txt`.

4. **Bare imports break when files move to `core/`** — all existing files use `from storage import StorageClient` (bare imports). After reorganization, these silently find stale per-project copies or raise ImportError. Prevention: establish `core/` with proper `__init__.py` from the start; migrate imports project-by-project with pipeline verification after each.

5. **Cloud Run flat-directory assumption broken by package structure** — existing `complete_deployment/` works because everything is flat. The unified framework uses `core/` as a subdirectory. Cloud Run deploys successfully but fails at first request with ImportError. Prevention: write a `Dockerfile` for the unified framework before decommissioning `complete_deployment/`; test `docker build && docker run` locally before deploying.

6. **Hardcoded assessment type lists in multiple places** — `diagnosticos` has `["M1", "CL", "CIEN", "HYST"]`; `ensayos_generales` has a longer list; both also appear in `assessment_analyzer.py` within the same project (repeated). Prevention: assessment types are owned by each report plugin (`BaseReportGenerator.assessment_types`); no hardcoded lists anywhere else.

---

## Implications for Roadmap

The architecture research defines a clear 7-phase build order with hard dependencies between phases. The roadmap should follow this sequence closely — the phases are not arbitrary; each creates the foundation the next requires.

### Phase 1: Consolidation Audit

**Rationale:** You cannot write shared code without first knowing exactly what each version of each shared file does. This phase is the most important risk-mitigation step in the entire project. Skipping or rushing it directly causes Pitfalls 1, 2, and 3.
**Delivers:** Merge decision document listing every diverged method with explicit resolution; complete file inventory across all 6 locations (5 project roots + `complete_deployment/`); resolved unified `requirements.txt` that installs cleanly; documented `.env.example` consolidating all environment variables.
**Addresses features:** Per-report data namespacing design decisions; environment-based configuration consolidation.
**Avoids:** Wrong canonical version (Pitfall 1), `complete_deployment/` missed (Pitfall 2), dependency version conflicts (Pitfall 3).
**Research flag:** No phase-level research needed — this is a code audit, not a design phase.

### Phase 2: Core Package Creation

**Rationale:** All downstream components (`reports/`, `entrypoints/`) import from `core/`. Core must exist and be stable before any plugin or entry point can be built. This phase is the largest single chunk of work — merging 5 diverged copies of `assessment_downloader.py` and `assessment_analyzer.py` is non-trivial.
**Delivers:** `core/` package with canonical single versions of all shared services; `reports/base.py` with `BaseReportGenerator` ABC; `reports/__init__.py` with empty REGISTRY; all bare imports updated to `from core.X import Y`; assessment types owned by plugins, not hardcoded.
**Uses:** Python 3.11, pandas 2.2.x, requests 2.31+, stdlib smtplib, google-cloud-storage 2.x, google-api-python-client 2.x.
**Avoids:** Bare import breakage (Pitfall 4), hardcoded assessment type lists (Pitfall 6), PII cleanup on error paths (Security mistake from PITFALLS.md).
**Research flag:** No phase-level research needed — patterns are well-established and directly observed in existing code.

### Phase 3: First Plugin Migration (diagnosticos)

**Rationale:** Prove the plugin pattern end-to-end before migrating other report types. Diagnosticos is the most complex (4 assessment types, multi-template HTML, webhook integration) — if the pattern works here, it works everywhere. Do not migrate all 5 types simultaneously; validate the interface first.
**Delivers:** `reports/diagnosticos/generator.py` (ported from `diagnosticos/report_generator.py`); `reports/diagnosticos/assessment_mapper.py`; `templates/diagnosticos/*.html`; `data/diagnosticos/questions/*.csv`; REGISTRY entry; full pipeline verified end-to-end producing identical output to pre-migration version.
**Implements:** `BaseReportGenerator` Strategy pattern; `get_template_path()` and `get_data_path()` convention; `generate_pdf()` contract.
**Avoids:** Breaking the existing diagnosticos behavior — this is a migration, not a rewrite.
**Research flag:** No phase-level research needed — direct port from existing working code.

### Phase 4: Unified Entry Points (Local CLI + Pipeline Runner)

**Rationale:** Once `core/` and one validated plugin exist, the shared orchestrator can be built and the unified `main.py` can route to it. Local CLI comes before GCP webhook because it is simpler (no Firestore, no Cloud Tasks) and provides a fast feedback loop for testing all subsequent plugin migrations.
**Delivers:** `entrypoints/pipeline_runner.py`; `entrypoints/main.py` with `--report-type` argument; dry-run mode; test mode (`--test-email`); structured result schema; all tested locally.
**Uses:** Flask 3.x not yet needed (local mode only); all `core/` services.
**Avoids:** Re-implementing pipeline steps in entry points (Template Method pattern enforced).
**Research flag:** No phase-level research needed — directly ports logic from existing `main.py` files.

### Phase 5: GCP Entry Point + Cloud Run Deployment

**Rationale:** GCP webhook mode reuses the same `PipelineRunner` but adds Firestore queue, Cloud Tasks scheduling, and HMAC validation. Must come after Phase 4 because the pipeline runner must exist first. This phase also replaces `complete_deployment/` with a single `Dockerfile`.
**Delivers:** `entrypoints/webhook_service.py`; `entrypoints/gcp/` (firestore_service, task_service, batch_processor); single `Dockerfile`; single `requirements.txt`; Cloud Run deployment verified with test webhook; `complete_deployment/` subfolders decommissioned.
**Uses:** Flask 3.x, functions-framework 3.x, google-cloud-firestore 2.x, google-cloud-tasks 2.x, protobuf 4.x.
**Avoids:** Cloud Run flat-directory assumption (Pitfall 5) — Dockerfile must be verified with `docker build && docker run` locally before deploying; webhook URL change must be reflected in LearnWorlds dashboard configuration.
**Research flag:** Consider a quick research-phase for the Dockerfile + Cloud Run deployment pattern with a package-based project structure — this differs from the current `gcloud functions deploy --source .` approach.

### Phase 6: Remaining Report Type Migrations

**Rationale:** With the pattern proven in Phase 3 and the entry points working in Phases 4 and 5, the remaining 4 report types can be migrated in any order. Each migration follows the same pattern: port `report_generator.py` → `reports/<type>/generator.py`, organize templates and data, add to REGISTRY, verify output matches pre-migration.
**Delivers:** `reports/diagnosticos_uim/generator.py`; `reports/ensayos_generales/generator.py`; `reports/assessment_analysis/generator.py`; all 5 report types in REGISTRY; `shared/` directory removed.
**Avoids:** Assuming all types are identical — `ensayos_generales` has no assessment_mapper and no Firestore dependency; `assessment_analysis` has no email delivery step. Verify each type's specific dependencies are handled without importing unused GCP libraries.
**Research flag:** No phase-level research needed — direct port for each type.

### Phase 7: New docx Report Generator (First docxtpl Report)

**Rationale:** After all existing types are migrated, the framework is ready for the first new report type using the docxtpl/Word template approach. This is the first time the new stack (docxtpl, not weasyprint) is used in production. Proves the migration path for existing generators if they ever transition from weasyprint.
**Delivers:** First new report type using `docxtpl`; Word template (`.docx`) replacing HTML template; Docker image without weasyprint system dependencies (if the new type is the only deployment); documented process for adding future report types.
**Uses:** docxtpl 0.17.x, python-docx 1.1.x, Jinja2 3.1.x.
**Avoids:** Mixed docxtpl/python-docx version conflict — docxtpl 0.17 requires python-docx 1.x; do not mix with python-docx 0.8.x.
**Research flag:** If the new report type involves complex table layouts or conditional sections in Word templates, a research-phase on docxtpl advanced templating is recommended.

### Phase Ordering Rationale

- **Audit before code** (Phase 1 before everything): Every other phase depends on knowing which version of each diverged file is authoritative. This is the most common failure mode in consolidation projects — starting to code before the audit is complete creates technical debt immediately.
- **Core before plugins** (Phase 2 before Phase 3): Plugins import from core. Building plugins before core means building on a moving target.
- **One plugin before many** (Phase 3 before Phase 6): Validates the interface design before it is replicated 4 more times. If the `BaseReportGenerator` ABC needs adjustment, it is far cheaper to discover this after migrating one type than all five.
- **Local before GCP** (Phase 4 before Phase 5): Eliminates GCP-specific variables when debugging pipeline correctness. If the pipeline produces wrong output, you want to rule out Firestore/Cloud Tasks before adding those variables.
- **Migration before new features** (Phases 1-6 before Phase 7): The primary value is eliminating drift and duplication. New report types are the payoff after the framework is stable.

### Research Flags

**Phases needing deeper research during planning:**
- **Phase 5 (GCP Entry Point):** The transition from `gcloud functions deploy --source .` (flat directory) to a Docker-based deployment with a `core/` package is a meaningful operational change. Verify the exact Cloud Run deployment commands, environment variable injection for `REPORT_TYPE`, and how `functions_framework` discovers the Flask app in the new project structure before writing the Dockerfile.

**Phases with well-established patterns (skip additional research):**
- **Phase 1 (Audit):** Code diffing and merge decision documentation — no research needed, this is manual inspection work.
- **Phase 2 (Core Package):** Python package structure with `__init__.py` and ABC pattern — standard, well-documented.
- **Phase 3 (First Plugin):** Porting existing working code — no research needed.
- **Phase 4 (Local CLI):** argparse + pipeline orchestration — standard Python patterns.
- **Phase 6 (Remaining Migrations):** Same pattern as Phase 3, repeated.
- **Phase 7 (docxtpl):** Well-documented library; research-phase only if complex Word table layouts are required.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | Core libraries (pandas, requests, smtplib, google-cloud-*) are HIGH confidence — used in production today. docxtpl and python-docx 1.x versions sourced from training knowledge (cutoff Aug 2025); verify with `pip index versions` before pinning. weasyprint version compatibility with templates must be tested — rendering differences between 56.x and 66.x are real. |
| Features | HIGH | Based on direct analysis of all 5 production codebases. The feature set is not speculative — it is observed existing behavior plus the clearly stated goal in PROJECT.md of eliminating duplication. |
| Architecture | HIGH | Plugin pattern, ABC interface, and REGISTRY approach are directly derived from reading the existing code. The proposed structure is an evolution, not an invention. All component boundaries are validated against how the existing code actually communicates. |
| Pitfalls | HIGH | All 6 critical pitfalls are grounded in directly observed code evidence (method name differences diffed line-by-line, version pins compared, import patterns inspected). These are not theoretical risks. |

**Overall confidence:** HIGH

### Gaps to Address

- **docxtpl version compatibility:** Training knowledge places docxtpl at 0.17.x and python-docx at 1.1.x. Verify with `pip index versions docxtpl` and `pip index versions python-docx` before writing the Phase 7 report generator. The incompatibility between docxtpl 0.17 and python-docx 0.8.x is a known breaking change — do not mix.
- **Exact Cloud Run deployment commands:** The current deployment mechanism for `diagnosticos` and `diagnosticos_uim` Cloud Run services is not fully documented in the codebase (no `Dockerfile`, no `cloudbuild.yaml` found). Before Phase 5, identify the exact `gcloud run deploy` or `gcloud functions deploy` command used in production so the migration can preserve the deployment semantics.
- **`diagnosticos_uim/complete_deployment/main_app.py` ambiguity:** It is unclear whether `main.py` or `main_app.py` is the actual deployed entry point for diagnosticos_uim Cloud Run. This must be resolved in Phase 1 before migrating the GCP entry point.
- **weasyprint template rendering compatibility:** Templates currently rendering under weasyprint 56.x must be verified against weasyprint 66.x before the unified requirements.txt locks in 66.0. This is a required Phase 1 deliverable if existing report generators are to keep using weasyprint.

---

## Sources

### Primary (HIGH confidence — direct codebase analysis)
- `diagnosticos/assessment_downloader.py` vs `ensayos_generales/assessment_downloader.py` — method rename and signature divergence
- `diagnosticos/complete_deployment/requirements.txt` vs `diagnosticos/requirements.txt` — three-way version conflict evidence
- `diagnosticos/webhook_service.py` — GCP webhook architecture, HMAC validation, Firestore queue pattern
- `diagnosticos/main.py` (871 lines) — pipeline orchestration, incremental mode, CLI flags
- `diagnosticos/report_generator.py` — multi-template plugin pattern (M1/CL/CIEN/HYST)
- `ensayos_generales/report_generator.py` — simpler single-template plugin pattern
- `shared/` directory — drive_service.py, email_sender.py, storage.py, slack_service.py (confirmed shared but inconsistently used)
- `diagnosticos/firestore_service.py`, `task_service.py`, `batch_processor.py` — GCP queue infrastructure
- All 5 project file trees — confirmed 5+ copies of `assessment_downloader.py`, `storage.py`
- `PROJECT.md` — authoritative project spec: docx target format, pluggable generators, no rewrite of logic

### Secondary (MEDIUM confidence — training knowledge, August 2025 cutoff)
- docxtpl 0.17.x / python-docx 1.1.x version ranges
- Flask 3.x / functions-framework 3.x compatibility
- python-dotenv 1.x stable API
- google-cloud-firestore 2.x / protobuf 4.x compatibility constraint

---
*Research completed: 2026-02-28*
*Ready for roadmap: yes*
