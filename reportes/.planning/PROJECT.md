# Unified Report Pipeline

## What This Is

A unified Python framework that consolidates 6 independently-evolved LearnWorlds report pipelines into a single plugin-based codebase. It downloads data from the LearnWorlds API, processes CSV/XLSX input files, and generates PDF reports emailed to recipients. New report types are added by creating one plugin module under `reports/` — all infrastructure is inherited automatically.

**Shipped v1.0** — 4 report types live (`diagnosticos`, `diagnosticos_uim`, `ensayos_generales`, `test_diagnostico`), single Cloud Run container, unified `main.py` CLI.

## Core Value

Adding a new report type requires only a new `reports/<type>/generator.py` module and templates — all infrastructure (API download, data processing, email delivery, GCP webhook deployment) is reused automatically via `BaseReportGenerator`.

## Requirements

### Validated

- ✓ Consolidate core pipeline files (assessment_downloader, assessment_analyzer, storage, drive_service, email_sender) into `core/` — v1.0
- ✓ Pluggable report generator system — each report type is a `BaseReportGenerator` subclass in `reports/` — v1.0
- ✓ Templates organized per report type under `templates/<report_type>/` — v1.0
- ✓ Unified `main.py` entry point accepting `--report-type` argument — v1.0
- ✓ GCP Cloud Run deployment from a single `Dockerfile` for all report types — v1.0
- ✓ LearnWorlds webhook receiver routing events to the correct generator via REGISTRY — v1.0
- ✓ All 4 report types migrated: diagnosticos, diagnosticos_uim, ensayos_generales, test_diagnostico — v1.0

### Active

(No active requirements — start `/gsd:new-milestone` to define next milestone scope)

### Out of Scope

- Rewriting existing logic — consolidation only, not rewrite
- Config-file-driven reports — new reports use a new Python module
- Non-Python implementations
- Other data sources beyond LearnWorlds API + CSV/XLSX
- `assessment-analysis-project/` migration — separate standalone, kept as-is

## Context

- **v1.0 shipped:** All 4 report types in unified plugin architecture
- **Codebase:** ~20,300 Python LOC, `core/` + `reports/` + `templates/` + `data/` layout
- **GCP:** Single Cloud Run container, webhook service handles all report types
- **Remaining standalone:** `assessment-analysis-project/` — not migrated, kept separate
- **Known issues:** None
- **Tech debt:** CORE-01 traceability table showed "Pending" despite being complete — was a sync gap, corrected at v1.0 close

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| New report type = new Python module (not config file) | Allows custom logic per report; config-driven too rigid for varied formats | ✓ Good — 4 plugins ship cleanly |
| Start from existing `shared/` folder as `core/` foundation | Already has the right files; extend rather than start from scratch | ✓ Good — minimal rework |
| Decimal phase numbering for urgent insertions | Clear insertion semantics without renumbering | ✓ Good — not needed in v1.0 but convention established |
| Parallel Wave 1 execution for plugin migrations (06-01–03) | Independent plugins have no shared state | ✓ Good — saved ~10min wall time |
| Keep `assessment-analysis-project/` as standalone | Different architecture (webhook-driven, not batch); not in scope | — Pending (revisit in v1.1) |

## Constraints

- **Tech stack:** Python — existing codebase, no language change
- **GCP compatibility:** Cloud Run deployment must continue to work
- **Backwards compatibility:** Existing reports must generate correctly after migration

---
*Last updated: 2026-03-01 after v1.0 milestone*
