# Phase 6: Remaining Migrations - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Migrate four remaining standalone report types into the plugin registry. Each becomes a `BaseReportGenerator` subclass registered in `REGISTRY`. `shared/` is already gone (removed in Phase 2). The phase is complete when all five report types (including diagnosticos from Phase 3) run through the unified framework and REGISTRY maps all five keys.

</domain>

<decisions>
## Implementation Decisions

### Plugin count
- Three plugins total for this phase: `diagnosticos_uim`, `ensayos_generales`, `test_diagnostico`
- `assessment_analysis` and `test_diagnostico` are identical codebases — only `test_diagnostico` becomes a plugin; the `assessment-analysis-project/` directory is not migrated
- REGISTRY will map: `diagnosticos`, `diagnosticos_uim`, `ensayos_generales`, `test_diagnostico` (4 total; diagnosticos already done in Phase 3)

### Excel / manual-prep generators (ensayos_generales, test_diagnostico)
- Both rely on a manually prepared input file dropped on disk before the run — no LearnWorlds API call in `download()`
- `download()` reads the file from a known path and returns its contents; if the file is missing, **fail fast with a clear, descriptive error** (do not warn-and-continue)
- For `test_diagnostico`: input is `analisis de datos.xlsx` (segment + external data, manually prepared and tweaked)
- For `ensayos_generales`: input is a single combined `analysis.csv` covering all assessment types for all students

### Output shape (1 PDF vs N PDFs)
- `diagnosticos` and `diagnosticos_uim`: **N PDFs per student** — one per assessment type
- `ensayos_generales` and `test_diagnostico`: **1 PDF per student** — all assessment types combined in one report
- This difference lives entirely in `render()` — the base class lifecycle is the same for all

### diagnosticos_uim specifics
- Assessment types: `["M1", "F30M", "B30M", "Q30M", "HYST"]` — different from diagnosticos
- Follows the same automated API-download pattern as diagnosticos (no manual prep)
- Has its own `report_generator.py` and templates — keep them under `reports/diagnosticos_uim/`

### Verification
- Sign-off method: **visual spot-check on sample PDFs** — run each plugin with real input data, open a few output PDFs, confirm layout and content match the standalone version
- No byte-for-byte comparison required; content equivalence is sufficient

### Claude's Discretion
- Exact path for the expected input files (e.g., `data/ensayos_generales/analysis.csv` vs `data/ensayos_generales/input/analysis.csv`)
- Whether to copy templates to `templates/<report_type>/` or reference them in-place from the legacy directories
- Error message wording for missing-file failures

</decisions>

<specifics>
## Specific Ideas

- The "1 PDF per student joining N assessment types" pattern in ensayos_generales is distinct from diagnosticos — planner should not assume the diagnosticos render() pattern applies here
- test_diagnostico's Excel data requires manual human preparation before the plugin can run — the plugin should document this precondition clearly (e.g., in a docstring or README note)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `reports/diagnosticos/generator.py`: Reference implementation for the full API-download plugin lifecycle (download → analyze → render with per-type CSVs)
- `reports/base.py` (`BaseReportGenerator`): ABC with `download()`, `analyze()`, `render()`, and `generate()` orchestrator — already in place
- `reports/__init__.py` (`REGISTRY`): Already scaffolded with diagnosticos registered; new generators add one line each
- `core/assessment_downloader.py`, `core/assessment_analyzer.py`: Used directly by diagnosticos_uim (same pattern as diagnosticos)

### Established Patterns
- Per-report namespaced data dirs (`data/<report_type>/raw/`, `processed/`, `analysis/`, `questions/`) — set by `BaseReportGenerator.__init__`
- Templates under `templates/<report_type>/` — BaseReportGenerator sets `self.templates_dir`
- diagnosticos_uim already uses `from core.*` imports (updated in Phase 2) — no import migration needed

### Integration Points
- `reports/__init__.py` REGISTRY: each new generator adds `REGISTRY["key"] = GeneratorClass`
- `main.py` CLI and `PipelineRunner` already route by REGISTRY key — no changes needed once generators are registered
- Webhook service routes by `REPORT_TYPE` env var — new types work automatically once in REGISTRY

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-remaining-migrations*
*Context gathered: 2026-03-01*
