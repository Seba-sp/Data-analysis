# Phase 11: Examen de Eje Plugin - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement and register `examen_de_eje` end-to-end report generation. Plugin reads
`M30M2-EXAMEN DE EJE 1-DATA.xlsx` (and equivalent group variants), computes per-unit
PDU% from student responses, assigns a state/recommendation bracket per unit, and
renders a 2-page PDF body (+ cover) via the existing template infrastructure.

</domain>

<decisions>
## Implementation Decisions

### PDU% thresholds (LOCKED by user)
- PDU% < 50%  → Estado: **Riesgo**    → Recomendación: **RR**
- 50% ≤ PDU% < 80% → Estado: **En desarrollo** → Recomendación: **RD**
- PDU% ≥ 80%  → Estado: **Sólido**   → Recomendación: **RS**

### Data source
- Question bank columns required: `pregunta`, `alternativa`, `unidad` (no `leccion` column needed — examen_de_eje analysis is unit-level only, not lesson-level).
- ids.xlsx rows matching pattern `GROUP-EXAMEN DE EJE N-DATA` are used to resolve assessment IDs.
- Bank files follow naming convention `GROUP-EXAMEN DE EJE N-DATA.xlsx` under `inputs/`.

### Analysis output
- Per student: a list of `(unit_name, pdu_percent, estado, recomendacion)` tuples ordered by bank row order.
- No lesson-level breakdown needed (unlike test_de_eje).
- No hour estimate needed.

### Template / rendering
- body.html updated (2026-03-08) to match PDF template with emojis and correct Spanish orthography.
- Page 1: narrative — intro, interpretation table (Estado/Interpretación/Recomendación), roadmap steps.
- Page 2: dynamic unit status table (`data-table-anchor="unit_status_rows"`) + static Guía de Recomendaciones Personalizadas (RS/RD/RR sections).
- The Guía de Recomendaciones section is static in the template — no dynamic injection needed there.
- Unit table injection replaces `tbody[data-table-anchor="unit_status_rows"]` with generated `<tr>` rows.
- Cover is composed as page 1 using existing `templates/examen_de_eje/cover.html`.

### Email template
- Follows same pattern as `reports/test_de_eje/email_template.py`.
- Subject: "Tu reporte Examen de Eje" (or similar — Claude's discretion).
- Body: brief congratulation noting the attached report.

### Generator structure
- Class `ExamenDeEjeGenerator(BaseReportGenerator)` in `reports/examen_de_eje/generator.py`.
- Implements `download → analyze → render` through `BaseReportGenerator` (same pattern as `TestDeEjeGenerator`).
- REPORT_TYPE = `"examen_de_eje"`.
- Register in REGISTRY.

### Claude's Discretion
- Exact regex pattern for EXAMEN DE EJE name normalization (model after `_TDE_NAME_RE` in test_de_eje).
- Filename pattern for output PDFs (follow existing convention).
- Whether `unit_priority_summary` anchor is populated or left empty.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `reports/test_de_eje/generator.py`: Full reference implementation — copy structure, adapt for examen_de_eje analysis logic (remove lesson-level tracking, add estado/recomendacion assignment).
- `reports/template_contracts.load_body_template(report_type)`: Loads body.html for a given report type.
- `reports/template_renderer.render_with_placeholders(...)`: Fills `data-placeholder` attributes.
- `core/assessment_downloader.AssessmentDownloader`: Handles LearnWorlds API download.

### Established Patterns
- Name normalization: `_normalize_text()` + `unicodedata.normalize("NFKD", ...)`.
- ids.xlsx loading: `load_workbook` + column index detection (header or positional).
- PDF composition: `_compose_cover_plus_body_html(cover_html, body_html)` + `weasyprint.HTML.write_pdf()`.
- Output dir: `data/examen_de_eje/output/`.

### Integration Points
- Register `ExamenDeEjeGenerator` in `core/webhook_service.py` or equivalent REGISTRY.
- `inputs/ids.xlsx` must have rows with assessment names matching `GROUP-EXAMEN DE EJE N-DATA`.
- Template anchor `unit_status_rows` in `templates/examen_de_eje/body.html` is the injection point for dynamic rows.

</code_context>

<specifics>
## Specific Ideas

- PDU% thresholds are explicit and locked: <50% Riesgo/RR, 50–80% Desarrollo/RD, ≥80% Sólido/RS.
- HTML body template has been updated to match the PDF template (emojis, correct Spanish orthography, full content including Guía de Recomendaciones Personalizadas).
- The Guía section (RS/RD/RR step-by-step instructions) is static content already in the template — generator does not need to render it dynamically.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 11-examen-de-eje-plugin*
*Context gathered: 2026-03-08*
