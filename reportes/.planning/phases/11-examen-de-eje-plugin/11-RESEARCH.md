# Phase 11: Examen de Eje Plugin - Research

**Researched:** 2026-03-08
**Domain:** Python report plugin (analysis + rendering) — examen_de_eje report type
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**PDU% thresholds:**
- PDU% < 50%         → Estado: Riesgo        → Recomendacion: RR
- 50% <= PDU% < 80%  → Estado: En desarrollo → Recomendacion: RD
- PDU% >= 80%        → Estado: Solido        → Recomendacion: RS

**Data source:**
- Question bank columns required: `pregunta`, `alternativa`, `unidad` (no `leccion` — unit-level only)
- ids.xlsx rows matching pattern `GROUP-EXAMEN DE EJE N-DATA` resolve assessment IDs
- Bank files follow `GROUP-EXAMEN DE EJE N-DATA.xlsx` under `inputs/`

**Analysis output:**
- Per student: a list of `(unit_name, pdu_percent, estado, recomendacion)` tuples ordered by bank row order
- No lesson-level breakdown needed
- No hour estimate needed

**Template / rendering:**
- Page 1: narrative (intro, interpretation table, roadmap steps) — from `templates/examen_de_eje/body.html`
- Page 2: dynamic unit status table (`data-table-anchor="unit_status_rows"`) + static Guia de Recomendaciones
- Guia de Recomendaciones section is static in the template — no dynamic injection needed there
- Unit table injection replaces `tbody[data-table-anchor="unit_status_rows"]` with generated `<tr>` rows
- Cover is composed as page 1 using `templates/examen_de_eje/cover.html`

**Email template:**
- Follows same pattern as `reports/test_de_eje/email_template.py`
- Subject: "Tu reporte Examen de Eje" (or similar — Claude's discretion)
- Body: brief congratulation noting the attached report

**Generator structure:**
- Class `ExamenDeEjeGenerator(BaseReportGenerator)` in `reports/examen_de_eje/generator.py`
- Implements `download -> analyze -> render` through `BaseReportGenerator`
- REPORT_TYPE = `"examen_de_eje"`
- Register in REGISTRY

### Claude's Discretion

- Exact regex pattern for EXAMEN DE EJE name normalization (model after `_TDE_NAME_RE`)
- Filename pattern for output PDFs (follow existing convention)
- Whether `unit_priority_summary` anchor is populated or left empty

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PLUG-02 | A dedicated `examen_de_eje` plugin exists and is registered in `reports.REGISTRY` | Full pattern documented from PLUG-01 (test_de_eje); one `__init__.py` entry required |
| DATA-02 | `M30M2-EXAMEN DE EJE 1-DATA.xlsx` structure is consumed as question bank/metadata to compute examen de eje outputs | Bank confirmed: 3 columns (`pregunta`, `alternativa`, `unidad`), 25 rows, 3 units |
</phase_requirements>

---

## Summary

Phase 11 is a straightforward plugin implementation using a fully established pattern. The `test_de_eje` plugin (Phase 9) is the direct reference: copy structure, adapt analysis logic (remove lesson tracking, remove hours estimation, add estado/recomendacion bracket assignment), and use `insert_dynamic_tables` via the existing `unit_status_rows` tbody anchor instead of the bespoke `_build_unit_sections` approach used by test_de_eje.

The infrastructure for examen_de_eje is already complete. The `templates/examen_de_eje/body.html` is updated and confirmed correct. The `templates/examen_de_eje/table_anchors.json` defines the `unit_status_rows` anchor with required columns `[unidad, estado, recomendacion]`. The placeholder schema in `templates/contracts/new_report_placeholders.yaml` already declares the `examen_de_eje` key. The `AssessmentMapper` already knows how to parse EXAMEN DE EJE names. The `ids.xlsx` EXAMEN DE EJE rows will route to `report_type="examen_de_eje"` automatically once the generator is registered.

The key difference from test_de_eje is the simpler analysis: no lesson tracking, no hours, just PDU% per unit → estado/recomendacion bracket. The render step uses `insert_dynamic_tables` (from `template_renderer.py`) rather than a bespoke HTML string builder, since the anchor is a `<tbody>` tag that the framework already handles via `_render_table_rows`.

**Primary recommendation:** Implement `ExamenDeEjeGenerator` as a thin adaptation of `TestDeEjeGenerator`, removing lesson/hour logic and replacing unit section generation with a single call to `insert_dynamic_tables(report_type, body_html, {"unit_status_rows": rows})`.

---

## Standard Stack

### Core (all already present in the project)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `openpyxl` | installed | Load `ids.xlsx` and question bank XLSX | Same as test_de_eje |
| `pandas` | installed | Read bank `.xlsx`, iterate student rows | Same as test_de_eje |
| `weasyprint` | installed | Render HTML to PDF bytes | Same as all report generators |
| `unicodedata` | stdlib | NFKD normalization of text values | Established in `_normalize_text()` |
| `re` | stdlib | Regex for name parsing and safe filenames | Established pattern |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `importlib` | stdlib | Email template resolution in `PipelineRunner` | Already handled by runner — plugin only needs `email_template.py` |

**Installation:** No new dependencies required.

---

## Architecture Patterns

### Recommended Project Structure

New files to create:

```
reports/examen_de_eje/
├── __init__.py           # empty module marker
├── generator.py          # ExamenDeEjeGenerator class
└── email_template.py     # SUBJECT + BODY constants
```

Template files already exist:
```
templates/examen_de_eje/
├── body.html             # confirmed updated and correct
├── cover.html            # confirmed present
└── table_anchors.json    # confirmed correct (unit_status_rows anchor)
```

Contract schema already updated:
```
templates/contracts/
└── new_report_placeholders.yaml  # examen_de_eje key already present
```

Registry integration:
```
reports/__init__.py       # add one import + REGISTRY entry
```

### Pattern 1: IDs Mapping Load (adaptation of _TDE_NAME_RE)

The test_de_eje generator uses `_TDE_NAME_RE = re.compile(r"^([A-Z0-9]+)-TEST DE EJE\s+(\d+)-DATA$")`.

For examen_de_eje, the equivalent regex is:

```python
# Source: reports/test_de_eje/generator.py (adapted)
_EDE_NAME_RE = re.compile(r"^([A-Z0-9]+)-EXAMEN DE EJE\s+(\d+)-DATA$")
```

The mapping load method follows the same `ids.xlsx` loading flow: `load_workbook` → detect headers → iterate rows → normalize name → match regex → build `bank_path` from `inputs/GROUP-EXAMEN DE EJE N-DATA.xlsx`.

Bank file existence check uses: `BANKS_DIR / f"{assessment_type}-EXAMEN DE EJE {assessment_number}-DATA.xlsx"`.

### Pattern 2: Analysis — Unit-Level PDU% with Estado/Recomendacion

The analysis is simpler than test_de_eje. No `LessonStats` dataclass needed. The output is ordered per bank row order (use an `ordered_unit_names` list built as bank rows are iterated).

```python
# Dataclasses needed (source: adapted from reports/test_de_eje/generator.py)

@dataclass
class UnitStats:
    name: str
    total: int = 0
    correct: int = 0

    @property
    def percent(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.correct / self.total) * 100.0


@dataclass
class ExamenPlan:
    assessment_type: str
    student_id: str
    email: str
    assessment_name: str = ""
    units: dict[str, UnitStats] = field(default_factory=dict)
    unit_order: list[str] = field(default_factory=list)  # preserves bank row order
```

PDU% threshold logic (LOCKED):

```python
# Source: CONTEXT.md decisions (locked)
def _assign_estado_recomendacion(pdu_percent: float) -> tuple[str, str]:
    if pdu_percent >= 80.0:
        return "Solido", "RS"
    if pdu_percent >= 50.0:
        return "En desarrollo", "RD"
    return "Riesgo", "RR"
```

Required columns check (DATA-02):

```python
required_cols = {"pregunta", "alternativa", "unidad"}
# No "leccion" — confirmed by actual bank file inspection
```

### Pattern 3: Dynamic Table Injection via insert_dynamic_tables

The examen_de_eje template uses a `<tbody data-table-anchor="unit_status_rows">` tag. The `insert_dynamic_tables` function in `template_renderer.py` detects `tag_name == "tbody"` and calls `_render_table_rows` (not `_render_full_table`), so it inserts `<tr>` rows only, preserving the existing `<thead>` above it.

```python
# Source: reports/template_renderer.py (insert_dynamic_tables, lines 141-183)
from reports.template_renderer import insert_dynamic_tables, render_with_placeholders

# In render():
rows = [
    {"unidad": unit.name, "estado": estado, "recomendacion": rec}
    for unit, (estado, rec) in zip(ordered_units, estados)
]
body_html = insert_dynamic_tables(
    report_type=REPORT_TYPE,
    body_html=rendered_body,
    table_payloads={"unit_status_rows": rows},
)
```

Contract validation is automatic: `insert_dynamic_tables` validates that anchor exists in `table_anchors.json` and that each row has `["unidad", "estado", "recomendacion"]`.

### Pattern 4: PDF Filename Convention

The `PipelineRunner._extract_email_from_pdf` expects the pattern `informe_{email}_{atype}.pdf`:
- `stem.split("_")` → `parts[0] == "informe"`, `parts[1:-1]` == email segments, `parts[-1]` == atype

However, test_de_eje's `render()` uses a DIFFERENT filename pattern: `{assessment_label}__{email}.pdf` (e.g., `M30M-TEST DE EJE 1__student@example.com.pdf`). This means the runner's `_extract_email_from_pdf` returns `None` for test_de_eje filenames, and the runner logs a warning then skips Drive upload — email is sent directly to the student address extracted from Firestore (not from the PDF name).

**Decision:** Follow the SAME filename pattern as test_de_eje: `{assessment_label}__{email}.pdf`. This is the established convention in render(), even though it does not match the runner's `informe_` pattern. The batch processor (not PipelineRunner) is the actual email dispatch path for webhook-triggered reports.

### Pattern 5: REGISTRY Registration

```python
# Source: reports/__init__.py (current state)
from reports.examen_de_eje.generator import ExamenDeEjeGenerator

REGISTRY: Dict[str, Type[BaseReportGenerator]] = {
    # ... existing entries ...
    "examen_de_eje": ExamenDeEjeGenerator,
}
```

### Pattern 6: Email Template (importlib plugin)

```python
# Source: reports/test_de_eje/email_template.py (pattern)
# File: reports/examen_de_eje/email_template.py

SUBJECT = "Tu reporte Examen de Eje"

BODY = """Hola,

Has completado tu Examen de Eje correctamente. En el informe adjunto encontraras tu resultado con el estado y recomendacion para cada unidad.

Cualquier consulta, estamos aqui para ayudarte.

Un abrazo a la distancia
"""
```

The runner resolves this at send time via `importlib.import_module("reports.examen_de_eje.email_template")`.

### Pattern 7: Cover Composition

Identical to test_de_eje. The `_compose_cover_plus_body_html` helper merges `<style>` blocks and `<body>` inner content with a `page-break-after: always` separator. Copy or reuse this function verbatim.

### Anti-Patterns to Avoid

- **Do not build lesson-level tracking:** examen_de_eje analysis is unit-level only — no `LessonStats` equivalent.
- **Do not build a bespoke unit section builder:** test_de_eje has `_build_unit_sections` / `_replace_unit_sections` for multi-page dynamic pagination. examen_de_eje has a single fixed `<tbody>` anchor; use `insert_dynamic_tables` instead.
- **Do not add placeholder values for static text in body.html:** The placeholder schema already has `examen_de_eje` computed/static entries. Injecting values for static placeholders that body.html already has as hardcoded text (e.g., `rs_heading`, `rd_heading`) is NOT needed — those `data-placeholder` attrs in body.html are metadata only and `render_with_placeholders` will raise `ValueError` for unknown inputs. Only supply the schema-declared placeholders.
- **Do not estimate hours:** No hours model needed — remove entirely from analysis output.
- **Do not add `leccion` to required_cols:** The actual bank file has only 3 columns. Requiring `leccion` would break DATA-02.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Table row injection | Custom regex replacement | `insert_dynamic_tables(report_type, body_html, {"unit_status_rows": rows})` | Already handles `<tbody>` anchor detection, column validation, HTML escaping |
| Cover + body merge | Custom HTML merger | `_compose_cover_plus_body_html(cover_html, body_html)` (copy from test_de_eje) | Handles style extraction and page-break composition |
| Placeholder substitution | String `.replace()` | `render_with_placeholders(report_type, body_html, computed, static)` | Validates against schema, handles both brace and data-attr patterns |
| ids.xlsx loading | Custom file reader | `load_workbook` + header detection pattern (verbatim from test_de_eje) | Already handles headed/headerless layouts with empty-row skipping |
| Name normalization | Custom unicode strip | `_normalize_text(value)` via NFKD + combining-char removal (copy verbatim) | Handles accents, non-breaking spaces, irregular whitespace |
| Email template resolution | Hard-coded strings in runner | `email_template.py` module in plugin dir | PipelineRunner resolves via importlib — dropping the file is the entire extension point |

**Key insight:** Every shared infrastructure piece was deliberately designed for this extension scenario. The "add a new report type" value proposition means Phase 11 primarily assembles existing parts with new analysis logic.

---

## Common Pitfalls

### Pitfall 1: Placeholder Schema Mismatch

**What goes wrong:** `render_with_placeholders` raises `ValueError: Unknown placeholders` or `Missing placeholder values`.
**Why it happens:** The `new_report_placeholders.yaml` schema for `examen_de_eje` lists specific computed/static keys. The body.html also uses `data-placeholder` attributes for narrative sections (e.g., `page_portada`, `page_resultados`, `report_title`, etc.) that must be supplied.
**How to avoid:** Inspect all `data-placeholder` attrs in body.html and supply them as `static_values` with empty strings for purely structural markers. The schema shows:
- computed: `student_name`, `course_name`, `generated_at`, `period_label`
- static: `page_portada`, `report_name`, `cover_page_label`, `report_title`, `what_it_measures_heading`, `what_it_measures_body`, `important_heading`, `important_body`, `states_heading`, `state_solido_text`, `state_desarrollo_text`, `state_riesgo_text`, `how_to_use_heading`, `how_to_use_line_1`, `how_to_use_line_2`, `how_to_use_line_3`, `page_resultados`, `table_section_heading`, `priority_guidance`, `closing_message`

**Warning signs:** Check which of these attrs are actually in the body.html. The body.html uses its OWN attrs (e.g., `intro_body`, `what_to_know_heading`, `roadmap_heading`) that are NOT in the schema. The `render_with_placeholders` call will fail if you pass keys that aren't in the schema. Only pass keys that ARE declared in the schema AND appear in the body.html.

**Critical finding:** The body.html `data-placeholder` attrs do NOT perfectly match the schema-declared keys. Many attrs in body.html (like `intro_body`, `roadmap_steps`, `rs_heading`) are NOT in the schema and NOT computed — they are hardcoded text in the template. `render_with_placeholders` will skip them (they'll stay as the original template text). Only supply values for schema-declared keys that actually appear as `data-placeholder` in body.html.

**Resolution approach:** Run `discover_placeholders_in_html(body_html)` and cross-check against `load_report_placeholder_schema("examen_de_eje")` to find the intersection — only that intersection needs values.

### Pitfall 2: MappingRow Dataclass Missing `assessment_name`

**What goes wrong:** Pre-existing test failures in `test_test_de_eje_phase9_data_contract.py` show `MappingRow.__init__() missing 1 required positional argument: 'assessment_name'`. The `MappingRow` dataclass in `test_de_eje/generator.py` now has `assessment_name` as a required field but old test fixtures don't pass it.
**Why it happens:** The dataclass was updated but tests were not. This is a pre-existing failure (5 tests fail) that Phase 11 should NOT introduce in the new generator.
**How to avoid:** When creating `MappingRow` for examen_de_eje (or an equivalent `ExamenMappingRow`), always include `assessment_name`. If reusing the same dataclass, ensure all test fixtures pass it.

### Pitfall 3: Bank Unit Order Not Preserved

**What goes wrong:** Unit status rows appear in wrong order in the PDF.
**Why it happens:** Python dicts preserve insertion order (3.7+), but iterating `bank_df.iterrows()` and checking `if unit_name not in plan.units` preserves the first-seen order. If the same student is processed from multiple bank files (not the case here — one bank per assessment), order could break.
**How to avoid:** Maintain an explicit `unit_order: list[str]` field in the plan dataclass, appending `unit_name` only when first seen.

### Pitfall 4: Template Body.html Has `data-placeholder` on Structural `<section>` Nodes

**What goes wrong:** `render_with_placeholders` sees `data-placeholder="page_portada"` on a `<section>` tag. The renderer's `_replace_data_placeholder_elements` function checks `if "<" in inner and ">" in inner` and skips structural nodes — so the section's content is preserved. But if you try to supply a non-empty value for `page_portada` in `static_values`, the renderer will silently not replace it (the section contains child HTML so the guard fires).
**How to avoid:** Supply `page_portada: ""` and `page_resultados: ""` in static_values. They won't be replaced but must be present to pass the schema validation.

### Pitfall 5: Webhook Route Depends on `examen_de_eje` Being in REGISTRY

**What goes wrong:** Webhook receives an examen_de_eje event, `AssessmentMapper.get_route()` returns `("examen_de_eje", "M2")`, Firestore queues it, but `PipelineRunner` calls `get_generator("examen_de_eje")` and raises `KeyError`.
**Why it happens:** REGISTRY entry missing.
**How to avoid:** Registration in `reports/__init__.py` is the single integration point. The test `assert "examen_de_eje" in REGISTRY` covers this.

---

## Code Examples

Verified patterns from the existing codebase:

### PDU% Threshold Assignment

```python
# Derived from CONTEXT.md locked thresholds
def _assign_estado_recomendacion(pdu_percent: float) -> tuple[str, str]:
    """Return (estado, recomendacion) for a given PDU percentage."""
    if pdu_percent >= 80.0:
        return "Solido", "RS"
    if pdu_percent >= 50.0:
        return "En desarrollo", "RD"
    return "Riesgo", "RR"
```

### Dynamic Table Injection (the correct approach for examen_de_eje)

```python
# Source: reports/template_renderer.py insert_dynamic_tables (lines 141-183)
from reports.template_renderer import insert_dynamic_tables

unit_rows = []
for unit_name in plan.unit_order:
    unit = plan.units[unit_name]
    estado, rec = _assign_estado_recomendacion(unit.percent)
    unit_rows.append({"unidad": unit_name, "estado": estado, "recomendacion": rec})

body_html = insert_dynamic_tables(
    report_type="examen_de_eje",
    body_html=rendered_body,
    table_payloads={"unit_status_rows": unit_rows},
)
```

### Name Regex for EXAMEN DE EJE

```python
# Modeled after _TDE_NAME_RE in reports/test_de_eje/generator.py
_EDE_NAME_RE = re.compile(r"^([A-Z0-9]+)-EXAMEN DE EJE\s+(\d+)-DATA$")
```

### Bank Name Construction

```python
# Pattern consistent with test_de_eje bank_name construction
bank_name = f"{assessment_type}-EXAMEN DE EJE {assessment_number}-DATA.xlsx"
bank_path = BANKS_DIR / bank_name
```

### PDF Filename

```python
# Source: reports/test_de_eje/generator.py render() (line 507-510)
# Same double-underscore separator convention:
assessment_label = _strip_data_suffix(plan.assessment_name or plan.assessment_type)
pdf_path = output_dir / (
    f"{_safe_filename_component(assessment_label)}__"
    f"{_safe_filename_component(email)}.pdf"
)
```

### Cover + Body Composition

```python
# Source: reports/test_de_eje/generator.py _compose_cover_plus_body_html() (lines 286-306)
# Copy verbatim — change title from "Test de eje" to "Examen de Eje"
def _compose_cover_plus_body_html(cover_html: str, body_html: str) -> str:
    cover_styles = _extract_head_styles(cover_html)
    body_styles = _extract_head_styles(body_html)
    cover_body = _extract_body_inner(cover_html)
    body_inner = _extract_body_inner(body_html)
    return (
        "<!DOCTYPE html><html lang=\"es\"><head>"
        "<meta charset=\"utf-8\" /><title>Examen de Eje</title>"
        f"<style>{cover_styles}\n{body_styles}</style></head><body>"
        f"{cover_body}"
        "<div style=\"page-break-after: always;\"></div>"
        f"{body_inner}</body></html>"
    )
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Bespoke unit section builder (like test_de_eje) | Use `insert_dynamic_tables` with `unit_status_rows` anchor | Phase 8 (template anchor contracts) | Simpler render code; contract-validated |
| Email subject/body hardcoded in runner | Plugin-dir `email_template.py` resolved via importlib | Phase 10 plan 04 | Dropping `email_template.py` in plugin dir is the entire extension point |
| MappingRow without assessment_name | MappingRow now requires `assessment_name` field | Phase 9 (current generator.py) | All test fixtures must include `assessment_name` |

---

## Key Findings About Existing Infrastructure

### templates/examen_de_eje/body.html (confirmed)
- 2 pages: page 1 narrative, page 2 unit table + static guide
- `data-table-anchor="unit_status_rows"` is a `<tbody>` tag → `_render_table_rows` path in `insert_dynamic_tables`
- `data-table-anchor="unit_priority_summary"` is an empty `<div>` → Claude's discretion whether to populate
- Static guide sections (RS/RD/RR) are hardcoded HTML — no dynamic injection needed

### templates/examen_de_eje/table_anchors.json (confirmed)
- Three anchors defined: `unit_status_recommendations`, `unit_status_rows`, `unit_priority_summary`
- `unit_status_rows` required_columns: `["unidad", "estado", "recomendacion"]`
- `unit_priority_summary` required_columns: `["prioridad", "unidades"]`

### templates/contracts/new_report_placeholders.yaml (confirmed)
- `examen_de_eje` key already present with 4 computed + 20 static placeholders
- Many of the static placeholder names do NOT appear as `data-placeholder` attrs in body.html — they are schema-declared but unused in the template. The validator allows "unused schema placeholders" (only unknown ones fail).

### inputs/M30M2-EXAMEN DE EJE 1-DATA.xlsx (confirmed via direct inspection)
- 3 columns: `pregunta`, `alternativa`, `unidad`
- 25 rows (questions)
- 3 units: `Matematica financiera` (7 Qs), `Logaritmos` (8 Qs), `Numeros reales` (10 Qs)
- No `leccion` column — confirmed correct for unit-level analysis

### reports/__init__.py (current REGISTRY)
- Current entries: `diagnosticos`, `diagnosticos_uim`, `ensayos_generales`, `test_diagnostico`, `test_de_eje`
- `examen_de_eje` not yet registered

### Pre-existing test failures (important context)
- 5 tests in `tests/test_test_de_eje_phase9_data_contract.py` fail due to `MappingRow` missing `assessment_name`
- These are PRE-EXISTING failures from Phase 9 — Phase 11 should NOT fix or worsen them
- New examen_de_eje tests must pass `assessment_name` to any equivalent mapping row dataclass

---

## Open Questions

1. **`unit_priority_summary` anchor population**
   - What we know: The anchor exists in `table_anchors.json` with required_columns `["prioridad", "unidades"]`; the body.html has an empty `<div data-table-anchor="unit_priority_summary"></div>`
   - What's unclear: Whether the planner wants this populated (grouping units by estado) or left empty
   - Recommendation: Leave empty (don't call `insert_dynamic_tables` for this anchor). The body.html renders fine with the empty div. The CONTEXT.md notes this as Claude's discretion.

2. **Placeholder schema vs body.html mismatch resolution**
   - What we know: The schema has 24 placeholder keys for `examen_de_eje` but body.html uses different attribute names for its narrative sections (e.g., `intro_body`, `roadmap_steps`, `rs_heading`)
   - What's unclear: Which schema-declared keys actually appear as `data-placeholder` in body.html (needs `discover_placeholders_in_html` to enumerate)
   - Recommendation: In Wave 0 or the first plan task, run `discover_placeholders_in_html(load_body_template("examen_de_eje"))` and intersect with schema. Supply only the intersection. Structural placeholders (`page_portada`, `page_resultados`) should use `""` as value.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (confirmed installed, version ~7.4.4 from pycache markers) |
| Config file | none — runs from project root with `python -m pytest` |
| Quick run command | `python -m pytest tests/ -k "examen_de_eje" --tb=short -q` |
| Full suite command | `python -m pytest tests/ --tb=short -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PLUG-02 | `"examen_de_eje"` key in REGISTRY with correct class name | unit | `python -m pytest tests/ -k "registry_contains_examen_de_eje" -x` | Wave 0 |
| DATA-02 | Bank with `[pregunta, alternativa, unidad]` columns accepted; missing column raises with name | unit | `python -m pytest tests/ -k "examen_de_eje and (data_contract or missing_col)" -x` | Wave 0 |
| PLUG-02 | `_load_examen_de_eje_mapping` accepts valid `GROUP-EXAMEN DE EJE N-DATA` rows | unit | `python -m pytest tests/ -k "examen_de_eje and mapping" -x` | Wave 0 |
| PLUG-02 | PDU% thresholds assign correct estado/recomendacion at boundaries | unit | `python -m pytest tests/ -k "examen_de_eje and threshold" -x` | Wave 0 |
| PLUG-02 | `analyze()` returns per-unit list in bank row order | unit | `python -m pytest tests/ -k "examen_de_eje and analyze" -x` | Wave 0 |
| PLUG-02 | `render()` calls `insert_dynamic_tables` and writes PDF with correct filename | unit | `python -m pytest tests/ -k "examen_de_eje and render" -x` | Wave 0 |
| PLUG-02 | Webhook route for examen_de_eje assessment queues exactly one student intent | integration | `python -m pytest tests/webhook/ -k "examen_de_eje" -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/ -k "examen_de_eje" --tb=short -q`
- **Per wave merge:** `python -m pytest tests/ --tb=short -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_examen_de_eje_phase11_logic.py` — PDU% threshold unit tests + analyze unit order
- [ ] `tests/test_examen_de_eje_phase11_data_contract.py` — REGISTRY, bank column validation, mapping load
- [ ] `tests/test_examen_de_eje_phase11_render_contract.py` — render() output path + PDF filename + dynamic table injection
- [ ] `tests/webhook/test_webhook_phase11_examen_de_eje_integration.py` — webhook route → queue path for examen_de_eje

*(Test infrastructure (pytest, conftest.py) already in place — no framework install needed)*

---

## Sources

### Primary (HIGH confidence)

- Direct code inspection: `reports/test_de_eje/generator.py` — full reference implementation pattern
- Direct code inspection: `reports/template_renderer.py` — `insert_dynamic_tables`, `render_with_placeholders`
- Direct code inspection: `reports/template_contracts.py` — `load_body_template`, schema validation
- Direct code inspection: `templates/examen_de_eje/body.html` — confirmed 2-page layout, anchor locations
- Direct code inspection: `templates/examen_de_eje/table_anchors.json` — confirmed anchor contracts
- Direct code inspection: `templates/contracts/new_report_placeholders.yaml` — confirmed examen_de_eje schema exists
- Direct data inspection: `inputs/M30M2-EXAMEN DE EJE 1-DATA.xlsx` — 3 cols, 25 rows, 3 units confirmed
- Direct code inspection: `reports/__init__.py` — current REGISTRY state
- Direct code inspection: `core/assessment_mapper.py` — `_TYPE_TO_REPORT` already maps EXAMEN DE EJE → examen_de_eje
- Direct code inspection: `core/runner.py` — email template importlib resolution pattern
- Direct test inspection: `tests/test_test_de_eje_phase9_*.py` — test structure and patterns to replicate

### Secondary (MEDIUM confidence)

- pytest version inferred from `__pycache__` filenames (cpython-312-pytest-7.4.4)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies confirmed present and used in test_de_eje
- Architecture: HIGH — every integration point confirmed by direct code inspection
- Pitfalls: HIGH — placeholder mismatch confirmed by schema vs body.html diff; MappingRow issue confirmed by running tests
- Data contract: HIGH — confirmed by direct pandas inspection of actual bank file

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (stable codebase — no fast-moving dependencies)
