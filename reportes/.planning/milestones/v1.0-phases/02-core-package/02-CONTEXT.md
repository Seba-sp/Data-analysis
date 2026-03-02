# Phase 2: Core Package - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Build `core/` as the single source of truth for all shared pipeline services (AssessmentDownloader, AssessmentAnalyzer, StorageClient, EmailSender, DriveService, SlackService, upload_folder_to_gcs). Establish the plugin base class (`BaseReportGenerator` ABC), the plugin registry, per-report data namespacing (`data/<report_type>/`), and template organization (`templates/<report_type>/`). All imports become package imports (`from core.X import Y`). The old `shared/` folder is deleted.

Phase 1's MERGE-DECISIONS.md defines exactly which method version is canonical for every diverged function. This phase implements those decisions.

</domain>

<decisions>
## Implementation Decisions

### Plugin Interface
- `BaseReportGenerator` ABC defines a **fixed multi-step lifecycle**: `download()` -> `analyze()` -> `render()`, each overridable by report plugins
- `generate()` (or the final render step) returns a **file path** to the produced report on disk
- **Email sending is NOT part of the generator** — a separate PipelineRunner/entry point handles email delivery after report generation. This enables dry-run mode trivially (skip the email step)
- Plugin registry in `reports/__init__.py` uses **explicit imports** mapping report type name strings to generator classes

### Per-report Config Injection
- Core `AssessmentAnalyzer` **keeps diagnosticos config as default** (per Phase 1 merge decision: diagnosticos is the canonical base for `_get_default_config`). Other report types override by passing their own config dict at construction
- Per-report **assessment ID env vars are loaded in each report module** — each `generator.py` defines its own `load_assessment_list_from_env()` function reading its own env var names (CL_ASSESSMENT_ID, F30M_ASSESSMENT_ID, etc.)
- **Ensayos generales keeps its own analyzer module** — Phase 1 audit confirmed zero method overlap between ensayos_generales' analyzer (`get_unique_identifiers`, `load_conversion_data`, `calculate_assessment_score`, `convert_score`, `analyze_all_assessments`) and the config-based core analyzer. The ensayos_generales analyzer lives in `reports/ensayos_generales/` as a report-specific helper

### Directory & Package Layout
- Data directories (`data/<report_type>/raw/`, `processed/`, `analysis/`) are **auto-created at runtime** when a report runs for the first time — no pre-created dirs or .gitkeep files in the repo
- Question data files live under `data/<report_type>/questions/` (e.g., `data/diagnosticos/questions/preguntas_M1.json`)
- Each report type is a **package directory**: `reports/diagnosticos/__init__.py`, `reports/diagnosticos/generator.py`, `reports/diagnosticos/analyzer_config.py`, etc. Room for report-specific helpers
- `core/__init__.py` does **NOT re-export classes** — all imports are explicit: `from core.assessment_downloader import AssessmentDownloader`

### Shared Service Promotion
- Files are **copied as-is to core/, only fixing import paths** — no refactoring or cleanup during promotion
- **All shared/ files promoted**: storage.py, email_sender.py, drive_service.py, slack_service.py, upload_folder_to_gcs.py
- Core versions are built from the **best copy per Phase 1 merge decisions**, not from the `shared/` folder (which is dead code — no report currently imports from it)
- `shared/` folder is **deleted in Phase 2** — it's dead code; each report project already has its own copies of these files

### Claude's Discretion
- Exact `generate()` return type details (file path string vs Path object)
- `BaseReportGenerator.__init__` signature and what common state it initializes
- How `PipelineRunner` orchestrates the lifecycle steps (Phase 4 concern but base class should anticipate it)
- Registry population approach (explicit dict vs explicit imports in `__init__.py`)
- Whether `upload_folder_to_gcs.py` becomes a class or stays a script-style module in core/
- Internal organization of core/ (single flat directory vs sub-packages)

</decisions>

<specifics>
## Specific Ideas

- User confirmed `shared/` is dead code — files were left there as reference copies. Each report type has its own copy of storage, email, drive services. The "shared" folder was used as a source to copy-paste from when creating new report types, not as a live import target.
- Slack service and upload_folder_to_gcs were kept in shared/ as "might use in the future" utilities — they've never been used by any report pipeline but should be preserved in core/ for future use.
- Each report will have different templates (or multiple templates) and input files — the framework must accommodate this variety.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `shared/storage.py`: `StorageClient` with local/GCS backend switching via `STORAGE_BACKEND` env var — dead code in shared/ but pattern is replicated in each project's own copy
- `shared/email_sender.py`: `EmailSender` with SMTP config — same dead-code pattern
- `shared/drive_service.py`: `DriveService` with Google Drive upload, shared drive support — same pattern
- `shared/slack_service.py`: Slack notification utility — never used by any report, future utility
- `shared/upload_folder_to_gcs.py`: Standalone GCS upload script — never used by any report, future utility

### Established Patterns
- All projects use `os.getenv()` for configuration (no config files)
- `StorageClient` provides local/GCS abstraction — all I/O should go through it
- Assessment analyzer uses config dicts to drive per-assessment-type behavior (category types, thresholds, level names)
- Reports follow: load env -> download data -> analyze -> render -> email pattern (currently implicit, will be formalized)

### Integration Points
- `core/assessment_downloader.py` is consumed by every report's download step
- `core/assessment_analyzer.py` is consumed by 4 of 5 reports (not ensayos_generales)
- `core/storage.py` is consumed by both downloader and analyzer for file I/O
- `core/email_sender.py` will be consumed by the PipelineRunner (Phase 4), not by generators directly
- `reports/base.py` `BaseReportGenerator` ABC is extended by every report's `generator.py`
- `reports/__init__.py` REGISTRY is consumed by the unified `main.py` (Phase 4)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-core-package*
*Context gathered: 2026-02-28*
