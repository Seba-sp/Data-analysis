# Phase 3: First Plugin Migration - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Port `diagnosticos` into the plugin structure: create `reports/diagnosticos/generator.py` extending `BaseReportGenerator`, register it in `REGISTRY`, and verify it produces identical output to the current standalone version. Email sending, GCP deployment, and the remaining four report types are out of scope.

</domain>

<decisions>
## Implementation Decisions

### Lifecycle mapping
- `render()` loops internally over students × assessment types, collects all generated PDFs, and returns an output directory `Path` — the base class `render() → Path` contract is satisfied by returning a directory
- `download()` fetches all raw data; `analyze()` produces analysis keyed by assessment type; `render()` iterates over types and students and generates PDFs
- If the internal loop proves unworkable, overriding `generate()` in `DiagnosticosGenerator` is the fallback (option C), but try option A first
- **Two output shapes exist across the pipeline** (captured for future phases):
  - Type 1 (diagnosticos): one PDF per student per assessment type → `render()` returns a directory of N × 4 PDFs
  - Type 2 (other report types): one PDF per student spanning multiple assessment types → `render()` also returns a directory, but N PDFs total
  - Both types work with `render() → Path` (directory); the base class does NOT need to change for Phase 3

### Plugin-private helpers
- `diagnosticos/report_generator.py` → moves to `reports/diagnosticos/report_generator.py` as a private module (imported only by `DiagnosticosGenerator`)
- `diagnosticos/assessment_mapper.py` → **NOT migrated** — this was a GCP webhook routing artifact (maps incoming webhook assessment IDs to report types). It is not needed to generate reports locally. It belongs in the GCP/webhook layer (Phase 5).
- `diagnosticos/batch_processor.py` → **NOT migrated** — GCP batch orchestration, out of scope for Phase 3

### Template and data migration
- Move (not copy): `diagnosticos/templates/*.html` → `templates/diagnosticos/`
- Move (not copy): `diagnosticos/data/questions/*.csv` → `data/diagnosticos/questions/`
- Delete old locations after migration — do not keep duplicate files
- The old `diagnosticos/` directory is not deleted in Phase 3 (it still contains the standalone version for verification)

### Output equivalence verification
- Run both versions (standalone `diagnosticos/main.py` and new `reports/diagnosticos/generator.py`) on the same real input data
- Visually diff one sample student's PDF output side by side
- Byte-for-byte match is not required — weasyprint embeds timestamps; content equivalence is the bar

### Claude's Discretion
- Exact internal structure of `DiagnosticosGenerator.__init__` (which services to instantiate)
- Whether to use `self.templates_dir` and `self.questions_dir` from `BaseReportGenerator` or redefine them
- How to handle the `incremental_mode` flag — Phase 4 (`PipelineRunner`) will own incremental/batch modes; the generator should assume full-run semantics for now

</decisions>

<specifics>
## Specific Ideas

- `assessment_mapper.py` is a GCP artifact — do not let it contaminate the plugin. The generator should read assessment IDs from env vars directly (same as the current standalone).
- The visual diff verification (one sample student's PDF) is the acceptance test for Phase 3. Plan a manual step or a simple comparison script.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `core/assessment_downloader.py`: already used by `diagnosticos/main.py` — generator imports from `core.assessment_downloader`
- `core/assessment_analyzer.py`: same — already the canonical version
- `core/storage.py`, `core/email_sender.py`, `core/drive_service.py`: all in core, imported via `core.*`
- `reports/base.py`: `BaseReportGenerator` ABC provides `self.templates_dir`, `self.questions_dir`, `self.raw_dir`, `self.analysis_dir`, `self.processed_dir`, `self.processed_emails_path` — all pre-wired for `report_type="diagnosticos"`
- `reports/__init__.py`: REGISTRY is empty, ready to receive `"diagnosticos": DiagnosticosGenerator`

### Established Patterns
- Template path convention: `templates/<report_type>/<name>.html` — maps directly to `diagnosticos`'s 4 HTML templates
- Question data convention: `data/<report_type>/questions/<name>.csv` — maps to the 4 question CSVs
- Import convention: all `core.*` imports (no bare `from storage import ...`)

### Integration Points
- `REGISTRY["diagnosticos"] = DiagnosticosGenerator` in `reports/__init__.py` — one line addition
- `diagnosticos/report_generator.py` becomes `reports/diagnosticos/report_generator.py` — imported locally, not from core
- `diagnosticos/main.py` remains in place (standalone) as the reference implementation for output verification

</code_context>

<deferred>
## Deferred Ideas

- `assessment_mapper.py` migration — belongs in Phase 5 (GCP/webhook layer), not Phase 3
- `batch_processor.py` — GCP batch orchestration, Phase 5
- Type 2 report shape (single PDF per student spanning all assessment types) — will affect other generator migrations in Phase 6; base class may need documentation update then
- `incremental_mode` handling — Phase 4 (PipelineRunner) owns this; generator gets full-run semantics only for now

</deferred>

---

**Research recommendation:** Phase 3 is a mechanical porting task — the patterns are established and the source code is in the same repo. Use `/gsd:plan-phase 3 --skip-research` to skip the external research agent and go straight to planning.

*Phase: 03-first-plugin-migration*
*Context gathered: 2026-03-01*
