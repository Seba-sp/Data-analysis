# Unified Report Pipeline

## What This Is

A unified Python framework that consolidates 6 independently-evolved LearnWorlds report pipelines into a single plugin-based codebase. It downloads data from the LearnWorlds API, processes CSV/XLSX input files, and generates PDF reports emailed to recipients. New report types are added by creating one plugin module under `reports/` and reusing the existing infrastructure.

**Current milestone:** v1.1 expands routing and report coverage with dynamic assessment IDs from GCS and three new report plugins.

## Core Value

Adding a new report type requires only a new `reports/<type>/generator.py` module and templates, while shared infrastructure (API download, data processing, email delivery, GCP webhook deployment) remains reusable.

## Current Milestone: v1.1 Dynamic Assessment Routing + 3 New Report Types

**Goal:** Deliver three new report pipelines (`test_de_eje`, `examen_de_eje`, `ensayo`) with dynamic LearnWorlds assessment ID routing from a GCS-hosted `ids.xlsx`.

**Target features:**
- Dynamic assessment ID routing from `ids.xlsx` with local-first development loading and GCS production source
- Separate plugins for `test_de_eje`, `examen_de_eje`, and `ensayo`
- DOCX-based templates converted to HTML (layout preserved) plus per-type cover image converted to HTML and inserted as page 1
- Use XLSX inputs as question banks/metadata to compute scores and generate report tables
- Webhook-triggered single-assessment report generation and single email per completed assessment
- Final milestone phase deploys all three new plugins to GCP and validates production webhook flow

## Requirements

### Validated

- [x] Consolidate core pipeline files (assessment_downloader, assessment_analyzer, storage, drive_service, email_sender) into `core/` - v1.0
- [x] Pluggable report generator system - each report type is a `BaseReportGenerator` subclass in `reports/` - v1.0
- [x] Templates organized per report type under `templates/<report_type>/` - v1.0
- [x] Unified `main.py` entry point accepting `--report-type` argument - v1.0
- [x] GCP Cloud Run deployment from a single `Dockerfile` for all report types - v1.0
- [x] LearnWorlds webhook receiver routing events to the correct generator via REGISTRY - v1.0
- [x] All 4 report types migrated: diagnosticos, diagnosticos_uim, ensayos_generales, test_diagnostico - v1.0

### Active

- [ ] v1.1 dynamic routing from GCS `ids.xlsx` with pattern-based parsing for new assessments
- [ ] v1.1 three new plugins: `test_de_eje`, `examen_de_eje`, `ensayo`
- [ ] v1.1 report rendering from DOCX-derived HTML templates + per-type HTML covers

### Out of Scope

- Rewriting existing report logic for already-shipped plugins unless required for integration compatibility
- Multi-assessment aggregation in one email (v1.1 sends one report per completed assessment)
- Replacing GCP/Cloud Run architecture
- Non-Python implementations

## Context

- v1.0 shipped all existing 4 report types in unified plugin architecture
- New v1.1 inputs are provided under `inputs/` (DOCX templates, XLSX question banks, cover images, `ids.xlsx`)
- New assessment names follow pattern `[GROUP]-[TYPE N]-DATA`, with TYPE in {TEST DE EJE, EXAMEN DE EJE, ENSAYO}
- Group prefixes for v1.1 are constrained to known values (`M1`, `M2`, `H30M`, `Q30M`, `F30M`, `B30M`, `CL`)
- Parsing must tolerate lowercase and accent variants (for example `EXAMEN`/`EXAMEN` with accent variants)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Keep one-plugin-per-report-type for v1.1 | Existing architecture is plugin-centric and isolates template/business rules cleanly | - Pending |
| Move new assessment ID source to GCS `ids.xlsx` | Supports N assessments per group/type without environment-variable churn | - Pending |
| Preserve DOCX layout as closely as possible in HTML templates | Business requirement for report look-and-feel continuity | - Pending |
| Enforce one assessment -> one report email | Matches expected user trigger behavior and avoids batching ambiguity | - Pending |

## Constraints

- **Tech stack:** Python - keep current runtime and architecture
- **Deployment:** Cloud Run + GCP services must remain compatible
- **Data source:** New assessment ID mapping file lives in GCS bucket
- **Compatibility:** Existing report types must continue working while v1.1 features are added

---
*Last updated: 2026-03-06 after v1.1 milestone start*
