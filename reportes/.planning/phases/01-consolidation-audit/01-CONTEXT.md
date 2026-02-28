# Phase 1: Consolidation Audit - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Catalogue all diverged code across 6 copies (5 project dirs + `diagnosticos/complete_deployment/`) and produce a merge decision document. Nothing is written to `core/` yet — this phase only decides what will go there and how conflicts are resolved. Deliverable is a markdown document, not code.

</domain>

<decisions>
## Implementation Decisions

### Core boundary — what belongs in core/ vs per-report module

Methods that exist in only ONE project and are specific to that report type's domain stay in the report module, NOT in `core/`. Examples:
- `_normalize_commune`, `_compare_emails`, `_process_email_columns` (only in assessment-analysis-project) → stay in `reports/assessment_analysis/`
- `download_users` (only in ensayos_generales) → stays in `reports/ensayos_generales/`
- `save_form_responses_to_csv`, `download_and_process_form` (only in assessment-analysis family) → stay per-report

Methods that exist in 2+ projects go into `core/` — these are the shared infrastructure.

### The ensayos_generales analyzer is architecturally separate

`ensayos_generales/assessment_analyzer.py` is completely different from the config-based family (`get_unique_identifiers`, `load_conversion_data`, `calculate_assessment_score`, `convert_score`). It should NOT be forced into the same `BaseReportGenerator`/`AssessmentAnalyzer` ABC. It lives as `reports/ensayos_generales/analyzer.py` — a report-specific helper, not a `core/` service.

The `BaseReportGenerator` ABC only governs the `generate()` interface — not the analysis approach.

### Claude's Discretion

- How to resolve `cleanup_incremental_files` vs `cleanup_temp_files` naming conflict — pick whichever name is clearest for the canonical core version
- Audit document format — method-by-method comparison table with explicit resolution decision per row
- Where `_download_form_responses_full` goes: `ensayos_generales` has it AND `assessment-analysis-project` has it — if both need it, it could go into `core/`; check body similarity before deciding
- Whether `diagnosticos_uim/complete_deployment` and `diagnosticos/complete_deployment` share enough differences to be audited separately or can be treated as one
- How to handle the `main.py` vs `main_app.py` ambiguity in `diagnosticos_uim/complete_deployment/` — investigate which one Cloud Run actually calls

</decisions>

<code_context>
## Existing Code Insights

### Three families of assessment_downloader.py

| Family | Projects | Key additions vs others |
|--------|----------|------------------------|
| Diagnosticos | diagnosticos/, diagnosticos_uim/, diagnosticos/complete_deployment/ | `cleanup_incremental_files`, `get_only_new_responses`, `get_incremental_json_file_path`, incremental merge flow |
| Ensayos | ensayos_generales/ | Superset of diagnosticos family + `get_temp_csv_file_path`, `get_temp_analysis_file_path`, `get_latest_user_timestamp_from_json`, `_download_form_responses_full`, `save_temp_responses_to_csv`, `cleanup_temp_files`, `save_responses_to_csv(include_usernames)`, `download_users` |
| Assessment-analysis | assessment-analysis-project/, reportes de test de diagnostico/ | Different branch: no incremental JSON, adds `get_users_csv_file_path`, `download_form_responses_incremental`, `save_form_responses_to_csv`, `_normalize_commune`, `_compare_emails`, `_process_email_columns`, `download_and_process_form` |

### Two families of assessment_analyzer.py

| Family | Projects | Structure |
|--------|----------|-----------|
| Config-based | diagnosticos/, diagnosticos_uim/, assessment-analysis-project/, reportes de test de diagnostico/ | Config-driven, category/percentage analysis, `analyze_assessment()` + `analyze_assessment_from_csv()`. Note: diagnosticos has `_analyze_by_category_generic` that diagnosticos_uim doesn't |
| Score-conversion | ensayos_generales/ | Completely different: conversion tables, `calculate_assessment_score`, `convert_score`, `analyze_all_assessments` |

### Env variable naming inconsistency

- `diagnosticos`/`diagnosticos_uim` use `GOOGLE_CLOUD_PROJECT` + assessment-specific IDs
- `shared/env.template` uses `GCP_PROJECT_ID` (different name for same thing)
- `shared/env.template` includes Slack config, SMTP_SERVER, GCP_BUCKET_NAME not present in others

### Integration Points

- `diagnosticos_uim/complete_deployment/` has both `main.py` AND `main_app.py` — entry point is ambiguous
- `diagnosticos/complete_deployment/` only has `main.py` — no ambiguity
- `shared/` already has canonical versions of `drive_service.py`, `email_sender.py`, `storage.py` — these don't need diff audit, just promotion to `core/`

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for the merge decision document structure.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-consolidation-audit*
*Context gathered: 2026-02-28*
