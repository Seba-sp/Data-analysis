# Unified Report Pipeline

## What This Is

A unified Python framework that consolidates 6-10 duplicated LearnWorlds report projects into a single codebase. It downloads data from the LearnWorlds API, processes CSV/XLSX input files, and generates docx reports that are emailed to recipients. New report types are added by creating a new generator module and template — without copying the entire project again.

## Core Value

Adding a new report type should require only a new `report_generator` module and a docx template — all infrastructure (API download, data processing, email delivery, GCP webhook deployment) is reused automatically.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Consolidate core pipeline files (assessment_downloader, assessment_analyzer, storage, drive_service, email_sender) into a single shared `core/` package — single source of truth, no more per-project drift
- [ ] Pluggable report generator system — each report type is a separate Python module in a `reports/` directory, with a consistent interface
- [ ] Templates organized per report type inside a shared `templates/` directory
- [ ] Unified `main.py` entry point that accepts a report type as argument and runs the full pipeline
- [ ] GCP Cloud Run deployment that works for any report type from a single codebase — no more `complete_deployment/` duplicate subfolder
- [ ] LearnWorlds webhook receiver that routes events to the correct report generator
- [ ] Migrate existing 5 projects (assessment-analysis-project, diagnosticos, diagnosticos_uim, ensayos_generales, reportes de test de diagnostico) into the new structure

### Out of Scope

- Rewriting existing logic — goal is to reorganize and consolidate, not rewrite
- Config-file-driven reports — new reports use a new Python module (explicit over implicit)
- Non-Python implementations
- Other data sources beyond LearnWorlds API + CSV/XLSX

## Context

- **Existing projects:** assessment-analysis-project, diagnosticos, diagnosticos_uim, ensayos_generales, reportes de test de diagnostico
- **Partial consolidation already exists:** a `shared/` folder has `drive_service.py`, `email_sender.py`, `storage.py`, `slack_service.py` — but projects don't consistently use it
- **Cloud projects** (diagnosticos, diagnosticos_uim): use GCP Cloud Run with LearnWorlds webhook trigger; some use Firestore for task queuing; each currently has a `complete_deployment/` subfolder that duplicates the parent with GCP-specific tweaks
- **Local projects**: run manually via `main.py`, no webhook infrastructure
- **Drift problem**: standard files (assessment_downloader, assessment_analyzer, etc.) have accumulated different functions across projects — no single "latest" version exists
- **scripts/** and **shared/** folders already present at the `reportes/` root — natural foundation to build from

## Constraints

- **Tech stack:** Python — existing codebase, no language change
- **GCP compatibility:** Cloud Run deployment must continue to work
- **Backwards compatibility:** Existing reports must still generate correctly after migration

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|------------|
| New report type = new Python module (not config file) | Allows custom logic per report; config-driven is too rigid for varied report formats | — Pending |
| Start from existing `shared/` folder as core foundation | Already has the right files; extend rather than start from scratch | — Pending |

---
*Last updated: 2026-02-28 after initialization*
