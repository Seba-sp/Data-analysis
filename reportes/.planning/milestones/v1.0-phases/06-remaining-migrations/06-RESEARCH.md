# Phase 6: Remaining Migrations - Research

**Researched:** 2026-03-01
**Domain:** Python plugin migration — wrapping three existing standalone report generators into BaseReportGenerator subclasses and registering them in REGISTRY
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Plugin count**
- Three plugins total for this phase: `diagnosticos_uim`, `ensayos_generales`, `test_diagnostico`
- `assessment_analysis` and `test_diagnostico` are identical codebases — only `test_diagnostico` becomes a plugin; the `assessment-analysis-project/` directory is not migrated
- REGISTRY will map: `diagnosticos`, `diagnosticos_uim`, `ensayos_generales`, `test_diagnostico` (4 total; diagnosticos already done in Phase 3)

**Excel / manual-prep generators (ensayos_generales, test_diagnostico)**
- Both rely on a manually prepared input file dropped on disk before the run — no LearnWorlds API call in `download()`
- `download()` reads the file from a known path and returns its contents; if the file is missing, **fail fast with a clear, descriptive error** (do not warn-and-continue)
- For `test_diagnostico`: input is `analisis de datos.xlsx` (segment + external data, manually prepared and tweaked)
- For `ensayos_generales`: input is a single combined `analysis.csv` covering all assessment types for all students

**Output shape (1 PDF vs N PDFs)**
- `diagnosticos` and `diagnosticos_uim`: **N PDFs per student** — one per assessment type
- `ensayos_generales` and `test_diagnostico`: **1 PDF per student** — all assessment types combined in one report
- This difference lives entirely in `render()` — the base class lifecycle is the same for all

**diagnosticos_uim specifics**
- Assessment types: `["M1", "F30M", "B30M", "Q30M", "HYST"]` — different from diagnosticos
- Follows the same automated API-download pattern as diagnosticos (no manual prep)
- Has its own `report_generator.py` and templates — keep them under `reports/diagnosticos_uim/`

**Verification**
- Sign-off method: **visual spot-check on sample PDFs** — run each plugin with real input data, open a few output PDFs, confirm layout and content match the standalone version
- No byte-for-byte comparison required; content equivalence is sufficient

### Claude's Discretion
- Exact path for the expected input files (e.g., `data/ensayos_generales/analysis.csv` vs `data/ensayos_generales/input/analysis.csv`)
- Whether to copy templates to `templates/<report_type>/` or reference them in-place from the legacy directories
- Error message wording for missing-file failures

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MIG-02 | `diagnosticos_uim` report type runs via the unified framework and produces output identical to the current standalone version | DiagnosticosUIMGenerator extends BaseReportGenerator; same API-download pattern as DiagnosticosGenerator; assessment types are ["M1", "F30M", "B30M", "Q30M", "HYST"]; UIM env vars use M1_UIM_ASSESSMENT_ID pattern (established in Phase 5) |
| MIG-03 | `ensayos_generales` report type runs via the unified framework and produces output identical to the current standalone version | EnsayosGeneralesGenerator extends BaseReportGenerator; download() reads `analysis.csv` from disk and fails fast if missing; render() produces 1 PDF per student combining all assessment types |
| MIG-04 | `assessment-analysis-project` report type runs via the unified framework — **OVERRIDDEN by user decision** | This requirement is satisfied by MIG-05 (test_diagnostico). assessment-analysis-project directory is NOT migrated. |
| MIG-05 | `reportes de test de diagnostico` report type runs via the unified framework and produces output identical to the current standalone version | TestDiagnosticoGenerator extends BaseReportGenerator; download() reads `analisis de datos.xlsx` from disk and fails fast if missing; render() produces 1 PDF per student using segment schedule logic |
| PLUG-02 | Each existing report type has a `reports/<report_type>/generator.py` module that extends `BaseReportGenerator` | Three new generator modules created; all registered in REGISTRY; REGISTRY maps all 4 keys including diagnosticos from Phase 3 |
</phase_requirements>

---

## Summary

Phase 6 is a mechanical porting exercise — three existing standalone report generators are wrapped into `BaseReportGenerator` subclasses and registered in `REGISTRY`. The framework infrastructure (base class, REGISTRY, namespaced data dirs, templates dirs) was completed in Phases 2-3 and is fully verified. No new libraries are needed; no new architecture decisions are required.

The key insight from reading the source code is that the three new plugins divide into two distinct patterns: the **API-download pattern** (diagnosticos_uim, mirrors diagnosticos exactly) and the **manual-prep pattern** (ensayos_generales and test_diagnostico, read a file from disk). Within manual-prep, there are two sub-patterns: ensayos_generales uses a flat CSV and produces one PDF per student by running a single `ReportGenerator.generate_report()` call, while test_diagnostico uses an Excel workbook with multiple sheets and produces one PDF per student using a more complex `PDFGenerator` with segment logic and checklist/schedule generators.

The diagnosticos plugin in `reports/diagnosticos/generator.py` is the gold-standard reference implementation for all three. The planner should treat it as the template and adapt it for each report type's specific data shape and render behavior. Template migration (copying from legacy dirs to `templates/<report_type>/`) is a required sub-task for each plugin that has HTML templates.

**Primary recommendation:** Create each plugin in a single plan: copy templates, create `reports/<report_type>/generator.py` extending `BaseReportGenerator`, add one line to `reports/__init__.py`, run spot-check. Three plans (one per plugin) plus a fourth for REGISTRY validation and verification.

---

## Standard Stack

All libraries are already installed — this phase adds zero new dependencies.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python ABC (`abc`) | stdlib | `BaseReportGenerator` abstract interface | Already used in `reports/base.py` |
| pandas | 2.2.2 | DataFrame operations, CSV/Excel reading | Pinned in Phase 1; all existing code uses it |
| weasyprint | current (see requirements) | HTML-to-PDF rendering | All three standalone generators use it |
| pathlib.Path | stdlib | Path handling | Used throughout existing plugin |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `core.assessment_downloader` | internal | API download for diagnosticos_uim | diagnosticos_uim only |
| `core.assessment_analyzer` | internal | Analysis for diagnosticos_uim | diagnosticos_uim only |
| `core.storage` | internal | StorageClient for file ops | All three plugins inherit this pattern |
| `openpyxl` | current | Excel file reading via pandas | test_diagnostico (reads .xlsx) |

### Alternatives Considered
None — stack is locked by existing infrastructure.

**Installation:**
```bash
# No new packages — all already present in requirements.txt
```

---

## Architecture Patterns

### Recommended Project Structure

After Phase 6, `reports/` should look like:

```
reports/
├── __init__.py                 # REGISTRY with all 4 entries
├── base.py                     # BaseReportGenerator (unchanged)
├── diagnosticos/               # Phase 3 (complete)
│   ├── generator.py
│   └── report_generator.py
├── diagnosticos_uim/           # Phase 6 (new)
│   ├── generator.py            # NEW
│   └── report_generator.py    # COPIED from diagnosticos_uim/
├── ensayos_generales/          # Phase 6 (new)
│   └── generator.py            # NEW
└── test_diagnostico/           # Phase 6 (new)
    ├── generator.py            # NEW
    ├── data_loader.py          # COPIED from source
    ├── checklist_generator.py  # COPIED from source
    ├── schedule_generator.py   # COPIED from source
    ├── html_formatter.py       # COPIED from source
    └── utils.py                # COPIED from source

templates/
├── diagnosticos/               # Phase 3 (complete): CIEN.html CL.html HYST.html M1.html
├── diagnosticos_uim/           # Phase 6 (new): Portada.html Ensayo2.html
├── ensayos_generales/          # Phase 6 (new): Portada.html resultados_ensayos.html
└── test_diagnostico/           # Phase 6 (new): plantilla_plan_de_estudio.html Segmentos.xlsx
```

### Pattern 1: API-Download Plugin (diagnosticos_uim)

**What:** Mirrors `DiagnosticosGenerator` exactly but with UIM-specific assessment types and env vars.
**When to use:** Report type pulls data from LearnWorlds API via `AssessmentDownloader`.

Key differences from diagnosticos:
- `ASSESSMENT_TYPES = ["M1", "F30M", "B30M", "Q30M", "HYST"]`
- Env vars use UIM naming convention established in Phase 5: `M1_UIM_ASSESSMENT_ID`, `HYST_UIM_ASSESSMENT_ID`, etc.
- `ReportGenerator` is the one in `diagnosticos_uim/report_generator.py` (supports F30M, B30M, Q30M which diagnosticos does not)
- Question banks already exist at `diagnosticos_uim/data/questions/*.csv` — must be in the BaseReportGenerator namespaced path `data/diagnosticos_uim/questions/`

```python
# Source: reports/diagnosticos/generator.py (adapted for diagnosticos_uim)
class DiagnosticosUIMGenerator(BaseReportGenerator):
    ASSESSMENT_TYPES: List[str] = ["M1", "F30M", "B30M", "Q30M", "HYST"]

    def __init__(self):
        super().__init__("diagnosticos_uim")
        self.downloader = AssessmentDownloader(data_dir="data/diagnosticos_uim")
        self.analyzer = AssessmentAnalyzer()
        self.report_generator = ReportGenerator()  # from reports.diagnosticos_uim.report_generator
        self.storage = StorageClient()
        self._assessment_ids = {
            "M1":   os.getenv("M1_UIM_ASSESSMENT_ID"),
            "F30M": os.getenv("F30M_UIM_ASSESSMENT_ID"),
            "B30M": os.getenv("B30M_UIM_ASSESSMENT_ID"),
            "Q30M": os.getenv("Q30M_UIM_ASSESSMENT_ID"),
            "HYST": os.getenv("HYST_UIM_ASSESSMENT_ID"),
        }
```

### Pattern 2: Manual-Prep CSV Plugin (ensayos_generales)

**What:** `download()` reads a single flat CSV from disk; `render()` iterates students and produces one combined PDF per student.
**When to use:** Input data is manually prepared and placed on disk before the run.

Critical behavior:
- `download()` must fail fast with `FileNotFoundError` (not a silent skip) if the CSV is absent.
- The CSV path is at `data/ensayos_generales/analysis.csv` (using `self.analysis_dir / "analysis.csv"` from BaseReportGenerator namespaced paths).
- The existing `ensayos_generales/report_generator.py` `generate_report(username)` call is the core of `render()`.

```python
# Source: ensayos_generales/report_generator.py + reports/diagnosticos/generator.py (adapted)
class EnsayosGeneralesGenerator(BaseReportGenerator):
    def __init__(self):
        super().__init__("ensayos_generales")
        self.report_generator = ReportGenerator()  # from reports.ensayos_generales.report_generator

    def download(self) -> pd.DataFrame:
        csv_path = self.analysis_dir / "analysis.csv"
        if not csv_path.exists():
            raise FileNotFoundError(
                f"[ensayos_generales] Input file not found: {csv_path}. "
                "Prepare analysis.csv manually and place it at the expected path before running."
            )
        return pd.read_csv(str(csv_path), sep=',')

    def analyze(self, download_result: pd.DataFrame) -> pd.DataFrame:
        # No API-based analysis step — data is pre-analyzed in the CSV
        return download_result

    def render(self, analysis_result: pd.DataFrame) -> Path:
        output_dir = self.data_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        for _, row in analysis_result.iterrows():
            username = row.get("username", row.get("email", ""))
            if not username:
                continue
            pdf_content = self.report_generator.generate_report(username)
            if pdf_content:
                pdf_path = output_dir / f"resultados_{username}.pdf"
                pdf_path.write_bytes(pdf_content)
        return output_dir
```

### Pattern 3: Manual-Prep Excel Plugin (test_diagnostico)

**What:** `download()` reads `analisis de datos.xlsx` from disk; `render()` uses the `PDFGenerator` class from the standalone codebase, which has complex segment/schedule/checklist logic.
**When to use:** Input data is a multi-sheet Excel workbook manually prepared by a human.

Critical behavior:
- `download()` must fail fast if Excel file is absent.
- The standalone codebase (`reportes de test de diagnostico/`) contains five support modules that `PDFGenerator` depends on: `data_loader.py`, `checklist_generator.py`, `schedule_generator.py`, `html_formatter.py`, `utils.py`. These are needed by `PDFGenerator` and must travel with it.
- The `PDFGenerator` in `pdf_generator.py` has internal relative imports (`from data_loader import DataLoader`, `from checklist_generator import ...`, etc.) — these must be changed to package-relative imports (`from reports.test_diagnostico.data_loader import DataLoader`) when copying into the plugin directory.
- `render()` calls `PDFGenerator.generate_all_reports()` which handles both Egresado and Cuarto medio student types internally.

```python
# Source: reportes de test de diagnostico/pdf_generator.py (adapted)
class TestDiagnosticoGenerator(BaseReportGenerator):
    DEFAULT_ANALYSIS_PATH = "data/analysis/analisis de datos.xlsx"  # relative to CWD
    DEFAULT_SEGMENTOS_PATH = "templates/test_diagnostico/Segmentos.xlsx"
    DEFAULT_TEMPLATE_PATH = "templates/test_diagnostico/plantilla_plan_de_estudio.html"

    def __init__(self):
        super().__init__("test_diagnostico")

    def download(self) -> str:
        """Return the path to the Excel file; fail fast if missing."""
        # BaseReportGenerator sets self.analysis_dir = data/test_diagnostico/analysis/
        excel_path = self.analysis_dir / "analisis de datos.xlsx"
        if not excel_path.exists():
            raise FileNotFoundError(
                f"[test_diagnostico] Input file not found: {excel_path}. "
                "Manually prepare 'analisis de datos.xlsx' and place it at the expected path before running."
            )
        return str(excel_path)

    def analyze(self, download_result: str) -> str:
        # No analysis step — data is pre-analyzed in the Excel workbook
        return download_result

    def render(self, analysis_result: str) -> Path:
        output_dir = self.data_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        generator = PDFGenerator(
            analysis_excel_path=analysis_result,
            segmentos_excel_path=self.DEFAULT_SEGMENTOS_PATH,
            html_template_path=self.DEFAULT_TEMPLATE_PATH,
        )
        generator.generate_all_reports()
        return output_dir
```

### Pattern 4: REGISTRY Registration (same for all three)

One line added to `reports/__init__.py` per plugin:

```python
# Source: reports/__init__.py (current state after Phase 3)
from reports.diagnosticos_uim.generator import DiagnosticosUIMGenerator
from reports.ensayos_generales.generator import EnsayosGeneralesGenerator
from reports.test_diagnostico.generator import TestDiagnosticoGenerator

REGISTRY: Dict[str, Type[BaseReportGenerator]] = {
    "diagnosticos":      DiagnosticosGenerator,
    "diagnosticos_uim":  DiagnosticosUIMGenerator,
    "ensayos_generales": EnsayosGeneralesGenerator,
    "test_diagnostico":  TestDiagnosticoGenerator,
}
```

### Anti-Patterns to Avoid

- **Reimplementing ReportGenerator logic in generator.py:** The standalone `report_generator.py` is the rendering logic. The generator wraps it — do not port template variable substitution or table-building code into `generator.py`.
- **Silently swallowing missing-file errors:** For manual-prep plugins, use `raise FileNotFoundError(...)` not `logger.warning(...); return None`.
- **Using bare flat-directory imports in copied modules:** When copying `pdf_generator.py` and support modules to `reports/test_diagnostico/`, change `from data_loader import DataLoader` to `from reports.test_diagnostico.data_loader import DataLoader`.
- **Placing question bank CSVs outside the namespaced data dir:** The BaseReportGenerator sets `self.questions_dir = data/<report_type>/questions/`. Ensure existing question bank CSVs for diagnosticos_uim are present at `data/diagnosticos_uim/questions/*.csv` (they already exist in `diagnosticos_uim/data/questions/`).
- **Relying on render() returning a single PDF path for multi-PDF plugins:** The base class `render()` signature returns `Path`. For diagnosticos_uim, return the output directory (same pattern as diagnosticos). PipelineRunner is aware of this.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML-to-PDF conversion | Custom renderer | `weasyprint` (already in all standalone generators) | Complex CSS rendering, pagination, character encoding — weasyprint handles all of it |
| CSV/Excel reading | Custom parsers | `pandas.read_csv()` / `pd.read_excel()` | Encoding detection, separator handling, type coercion |
| Path manipulation | String concatenation | `pathlib.Path` | Cross-platform, safe join, `.exists()` |
| Assessment ID → type lookup | Custom dict building | UIM `AssessmentMapper` class (already exists in `diagnosticos_uim/`) | Already handles None env vars, reverse lookups |
| Segment schedule logic | Reimplementing from scratch | Copy `schedule_generator.py`, `checklist_generator.py`, `html_formatter.py`, `data_loader.py`, `utils.py` | These files are already correct — copy, don't rewrite |

**Key insight:** This phase is a wrapping exercise, not a rewriting exercise. Every piece of existing rendering logic already works correctly in the standalone versions. The goal is to connect it to the BaseReportGenerator lifecycle with minimal changes.

---

## Common Pitfalls

### Pitfall 1: diagnosticos_uim env var names collide with diagnosticos
**What goes wrong:** `DiagnosticosUIMGenerator` uses `os.getenv("M1_ASSESSMENT_ID")` — same env var as DiagnosticosGenerator — leading to wrong assessment IDs being used.
**Why it happens:** Phase 5 established that UIM uses different env var names (`M1_UIM_ASSESSMENT_ID`, `HYST_UIM_ASSESSMENT_ID`) to avoid collision. The standalone `diagnosticos_uim/assessment_mapper.py` still uses the bare names but the webhook service (`Phase 5`) uses the UIM variants.
**How to avoid:** In `DiagnosticosUIMGenerator.__init__`, use `os.getenv("M1_UIM_ASSESSMENT_ID")`, `os.getenv("F30M_UIM_ASSESSMENT_ID")`, etc. — consistent with Phase 5 `AssessmentMapper` in the webhook service.
**Warning signs:** Both diagnosticos and diagnosticos_uim return the same assessment data on the same run.

### Pitfall 2: diagnosticos_uim question banks not at BaseReportGenerator's expected path
**What goes wrong:** `generator.py` constructs `question_bank_path = str(self.questions_dir / f"{atype}.csv")` which resolves to `data/diagnosticos_uim/questions/M1.csv`, but the existing CSVs live at `diagnosticos_uim/data/questions/M1.csv`.
**Why it happens:** BaseReportGenerator namespaces data under `data/<report_type>/` — standalone generators use their own directory structure.
**How to avoid:** Copy existing question bank CSVs from `diagnosticos_uim/data/questions/` to `data/diagnosticos_uim/questions/` as part of plugin setup (or add a note in docstring that this must be done before the first run).
**Warning signs:** Analysis step skips all assessment types with "question bank not found" warnings.

### Pitfall 3: test_diagnostico support modules use bare relative imports
**What goes wrong:** After copying `pdf_generator.py` to `reports/test_diagnostico/pdf_generator.py`, running it raises `ModuleNotFoundError: No module named 'data_loader'`.
**Why it happens:** Standalone code uses `from data_loader import DataLoader` (flat-directory imports) which only works when running from the standalone directory.
**How to avoid:** When copying each support module to `reports/test_diagnostico/`, update all bare imports to use the full package path: `from reports.test_diagnostico.data_loader import DataLoader`.
**Warning signs:** ImportError at module load time when the generator is registered.

### Pitfall 4: ensayos_generales `ReportGenerator` hardcodes flat paths
**What goes wrong:** `ensayos_generales/report_generator.py` uses `self.analysis_file = "data/analysis/analysis.csv"` — a flat path. Under the unified framework, analysis data lives at `data/ensayos_generales/analysis/analysis.csv`.
**Why it happens:** The standalone generator was written before the namespaced data dir convention.
**How to avoid:** When instantiating `ReportGenerator` inside `EnsayosGeneralesGenerator`, patch its paths or pass the correct paths as constructor arguments. Alternatively, copy `report_generator.py` to `reports/ensayos_generales/` and update the hardcoded paths to use `data/ensayos_generales/` prefix. The preferred approach (Claude's discretion) is to copy-and-update.
**Warning signs:** `ReportGenerator.generate_report()` raises "Analysis file not found: data/analysis/analysis.csv".

### Pitfall 5: test_diagnostico Segmentos.xlsx and HTML template paths
**What goes wrong:** `PDFGenerator` defaults `segmentos_excel_path="templates/Segmentos.xlsx"` and `html_template_path="templates/plantilla_plan_de_estudio.html"` — flat paths that existed in the standalone directory. Under the unified framework, these live at `templates/test_diagnostico/`.
**Why it happens:** Standalone generator was written with its own templates directory.
**How to avoid:** When instantiating `PDFGenerator` inside `TestDiagnosticoGenerator.render()`, pass the correct paths explicitly: `segmentos_excel_path="templates/test_diagnostico/Segmentos.xlsx"`, `html_template_path="templates/test_diagnostico/plantilla_plan_de_estudio.html"`.
**Warning signs:** `FileNotFoundError: templates/Segmentos.xlsx` at render time.

### Pitfall 6: ensayos_generales CSV separator ambiguity
**What goes wrong:** `ensayos_generales/report_generator.py` tries multiple separators (`,`, `;`, `\t`, `|`) to read `analysis.csv`. If the actual file uses `;` but the generator tries `,` first and gets one column, it may silently fail.
**Why it happens:** The standalone generator has defensive separator-detection logic due to CSV variability.
**How to avoid:** The `EnsayosGeneralesGenerator.download()` should read the CSV with a known separator (inspect actual file) and fail fast if it cannot. The defensive logic in the standalone `ReportGenerator` is fine to keep for backwards compatibility.
**Warning signs:** DataFrame has only 1 column after load; all student lookups fail.

---

## Code Examples

Verified patterns from existing codebase:

### BaseReportGenerator registration (from reports/__init__.py)
```python
# Source: C:\Users\Seba\Downloads\M30M\Data-analysis\reportes\reports\__init__.py
from typing import Dict, Type
from reports.base import BaseReportGenerator
from reports.diagnosticos.generator import DiagnosticosGenerator

REGISTRY: Dict[str, Type[BaseReportGenerator]] = {
    "diagnosticos": DiagnosticosGenerator,
}

def get_generator(report_type: str) -> Type[BaseReportGenerator]:
    if report_type not in REGISTRY:
        available = list(REGISTRY.keys())
        raise KeyError(
            f"Unknown report type '{report_type}'. "
            f"Available types: {available}"
        )
    return REGISTRY[report_type]
```

### BaseReportGenerator namespaced paths (from reports/base.py)
```python
# Source: C:\Users\Seba\Downloads\M30M\Data-analysis\reportes\reports\base.py
# All plugins get these paths set automatically by super().__init__(report_type)
self.data_dir = Path("data") / report_type           # data/diagnosticos_uim/
self.raw_dir = self.data_dir / "raw"
self.processed_dir = self.data_dir / "processed"
self.analysis_dir = self.data_dir / "analysis"       # data/diagnosticos_uim/analysis/
self.questions_dir = self.data_dir / "questions"     # data/diagnosticos_uim/questions/
self.templates_dir = Path("templates") / report_type  # templates/diagnosticos_uim/
self.processed_emails_path = self.data_dir / "processed_emails.csv"
```

### Fail-fast pattern for manual-prep download()
```python
# Pattern established by CONTEXT.md decision
def download(self) -> pd.DataFrame:
    csv_path = self.analysis_dir / "analysis.csv"
    if not csv_path.exists():
        raise FileNotFoundError(
            f"[ensayos_generales] Required input file not found: {csv_path}\n"
            f"Prepare analysis.csv manually and copy it to: {csv_path.resolve()}"
        )
    return pd.read_csv(str(csv_path), sep=',')
```

### DiagnosticosGenerator download() for reference
```python
# Source: C:\Users\Seba\Downloads\M30M\Data-analysis\reportes\reports\diagnosticos\generator.py
# Full pattern for API-download plugin — diagnosticos_uim follows this identically
# except ASSESSMENT_TYPES and _assessment_ids keys
self.downloader = AssessmentDownloader(data_dir="data/diagnosticos")
# For each atype in ASSESSMENT_TYPES:
result = self.downloader.download_and_process_assessment(
    assessment_id=assessment_id,
    assessment_name=atype,
    incremental_mode=False,
)
csv_path = self.downloader.get_csv_file_path(atype)
if csv_path.exists():
    df = pd.read_csv(str(csv_path), sep=";")
    processed[atype] = df
```

### diagnosticos_uim ReportGenerator.generate_pdf() signature
```python
# Source: C:\Users\Seba\Downloads\M30M\Data-analysis\reportes\diagnosticos_uim\report_generator.py
# Supports M1, HYST, F30M, B30M, Q30M (unlike diagnosticos which only supports M1, CL, CIEN, HYST)
def generate_pdf(
    self,
    assessment_title: str,          # "M1", "F30M", "B30M", "Q30M", "HYST"
    analysis_result: Dict[str, Any],
    user_info: Dict[str, Any],
    incremental_mode: bool = False,
    analysis_df: pd.DataFrame = None
) -> Optional[bytes]:
```

### test_diagnostico PDFGenerator call pattern
```python
# Source: C:\Users\Seba\Downloads\M30M\Data-analysis\reportes\reportes de test de diagnostico\pdf_generator.py
generator = PDFGenerator(
    analysis_excel_path="data/analysis/analisis de datos.xlsx",  # update to namespaced path
    segmentos_excel_path="templates/Segmentos.xlsx",             # update to templates/test_diagnostico/
    html_template_path="templates/plantilla_plan_de_estudio.html"  # update to templates/test_diagnostico/
)
success = generator.generate_all_reports(segments=None, student_types=None)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flat-directory standalone scripts | Plugin extending BaseReportGenerator | Phase 3 established the pattern | Phase 6 applies this pattern to 3 remaining types |
| Shared `shared/` directory | `core/` package imports | Phase 2 | Already done; no action in Phase 6 |
| Per-report `processed_emails.csv` at repo root | `data/<report_type>/processed_emails.csv` | Phase 2 ORG-03 | Already done |
| Bare `from report_generator import ReportGenerator` | `from reports.<type>.report_generator import ReportGenerator` | Pattern to apply in Phase 6 | Each plugin imports from its own subpackage |

**Note on MIG-04 vs MIG-05:** REQUIREMENTS.md says MIG-04 is `assessment-analysis-project` and MIG-05 is `reportes de test de diagnostico`. The user decision overrides this: only `test_diagnostico` (from "reportes de test de diagnostico") is migrated. MIG-04 is considered satisfied by this decision (assessment-analysis-project and test-diagnostico are identical codebases).

---

## Open Questions

1. **diagnosticos_uim `lecciones.xlsx` path**
   - What we know: `diagnosticos_uim/report_generator.py` references `self.lectures_file = "data/questions/lecciones.xlsx"`. Under the unified framework this should be `data/diagnosticos_uim/questions/lecciones.xlsx`. The file exists at `diagnosticos_uim/data/questions/lecciones.xlsx`.
   - What's unclear: Whether the copied `report_generator.py` needs this path updated, or whether it can be initialized with a corrected path when instantiated from `generator.py`.
   - Recommendation: Copy `report_generator.py` to `reports/diagnosticos_uim/report_generator.py` and update `self.lectures_file = str(Path("data") / "diagnosticos_uim" / "questions" / "lecciones.xlsx")` so it uses the namespaced path.

2. **ensayos_generales question bank and processed CSV paths**
   - What we know: `ensayos_generales/report_generator.py` uses `data/questions/{assessment_type}.csv` and `data/processed/{assessment_type}.csv` flat paths. Under the framework these should be `data/ensayos_generales/questions/` and `data/ensayos_generales/processed/`.
   - What's unclear: Whether the existing question bank CSVs exist for ensayos_generales (directory scan shows `processed/`, `questions/`, `raw/` exist but not which files are present).
   - Recommendation: Copy `report_generator.py` to `reports/ensayos_generales/report_generator.py`, update `self.questions_dir = str(Path("data") / "ensayos_generales" / "questions")` and `self.processed_dir = str(Path("data") / "ensayos_generales" / "processed")`.

3. **ensayos_generales `analysis.csv` expected separator**
   - What we know: The standalone generator tries comma first, then semicolon. The actual CSV files in the `ensayos_generales/` directory are `.xlsx` and `.csv` with various naming patterns.
   - What's unclear: Whether a canonical `analysis.csv` already exists and what its separator is.
   - Recommendation: In `download()`, read with `sep=','` as primary (matches the standalone code's first attempt and is the most common CSV standard), log the column count, and fail fast with a descriptive error if only 1 column is found.

---

## Sources

### Primary (HIGH confidence)
- `C:\Users\Seba\Downloads\M30M\Data-analysis\reportes\reports\base.py` — BaseReportGenerator interface, all namespaced paths
- `C:\Users\Seba\Downloads\M30M\Data-analysis\reportes\reports\diagnosticos\generator.py` — Gold-standard plugin implementation
- `C:\Users\Seba\Downloads\M30M\Data-analysis\reportes\reports\__init__.py` — REGISTRY structure
- `C:\Users\Seba\Downloads\M30M\Data-analysis\reportes\diagnosticos_uim\report_generator.py` — UIM-specific ReportGenerator with F30M/B30M/Q30M support
- `C:\Users\Seba\Downloads\M30M\Data-analysis\reportes\ensayos_generales\report_generator.py` — Ensayos-specific ReportGenerator (1 PDF per student, analysis.csv)
- `C:\Users\Seba\Downloads\M30M\Data-analysis\reportes\reportes de test de diagnostico\pdf_generator.py` — TestDiagnostico PDFGenerator with segment/schedule/checklist logic
- `C:\Users\Seba\Downloads\M30M\Data-analysis\reportes\diagnosticos_uim\assessment_mapper.py` — UIM env var naming pattern
- `.planning/phases/06-remaining-migrations/06-CONTEXT.md` — All locked decisions

### Secondary (MEDIUM confidence)
- `C:\Users\Seba\Downloads\M30M\Data-analysis\reportes\.planning\STATE.md` — Prior phase decisions (env var naming convention for UIM established in Phase 5)
- `C:\Users\Seba\Downloads\M30M\Data-analysis\reportes\.planning\REQUIREMENTS.md` — Requirement IDs and traceability

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all existing code reads and existing versions are known
- Architecture patterns: HIGH — all three plugin patterns derived directly from existing source code
- Pitfalls: HIGH — all identified pitfalls are grounded in specific source file evidence (hardcoded paths, import style, env var naming)

**Research date:** 2026-03-01
**Valid until:** 2026-04-01 (stable domain — internal Python code, no external API changes)
