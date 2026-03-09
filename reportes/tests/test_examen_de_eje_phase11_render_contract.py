"""Phase 11 – TDD RED: render() output path, PDF filename, and HTML injection contracts.

All tests in this file must FAIL with ImportError until reports/examen_de_eje/generator.py
is implemented (Plan 02).
"""

from pathlib import Path
from uuid import uuid4

from reports.examen_de_eje.generator import ExamenDeEjeGenerator, ExamenPlan, UnitStats


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _workdir(prefix: str) -> Path:
    path = Path(".tmp_testdata") / f"{prefix}_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _make_plan_with_units() -> ExamenPlan:
    """Build a minimal ExamenPlan fixture with 3 units."""
    plan = ExamenPlan(
        assessment_type="M30M2",
        student_id="u-1",
        email="student@example.com",
        assessment_name="M30M2-EXAMEN DE EJE 1-DATA",
    )
    plan.units["Matematica financiera"] = UnitStats(
        name="Matematica financiera", total=5, correct=2
    )
    plan.units["Logaritmos"] = UnitStats(name="Logaritmos", total=4, correct=4)
    plan.units["Numeros reales"] = UnitStats(name="Numeros reales", total=3, correct=1)
    plan.unit_order = ["Matematica financiera", "Logaritmos", "Numeros reales"]
    return plan


# ---------------------------------------------------------------------------
# Render contract tests
# ---------------------------------------------------------------------------


def test_render_writes_pdf_with_correct_filename(monkeypatch):
    """render() must create a PDF file named informe_{report_type}_{assessment_name}_{email}.pdf."""
    captured_html: list[str] = []

    class _FakeHTML:
        def __init__(self, string: str, base_url: str | None = None):
            self._string = string

        def write_pdf(self) -> bytes:
            captured_html.append(self._string)
            return b"%PDF-1.4\nphase11"

    monkeypatch.setattr("reports.examen_de_eje.generator.HTML", _FakeHTML)

    gen = ExamenDeEjeGenerator()
    gen.data_dir = _workdir("phase11_render_filename") / "data" / "examen_de_eje"

    plan = _make_plan_with_units()
    output_dir = gen.render({("M30M2", "student@example.com"): plan})

    expected_pdf = output_dir / "informe_examen_de_eje_M30M2-EXAMEN DE EJE 1-DATA_student@example.com.pdf"
    assert expected_pdf.exists(), f"Expected PDF not found: {expected_pdf}"
    assert expected_pdf.read_bytes().startswith(b"%PDF-1.4")


def test_render_inserts_unit_status_rows_in_html(monkeypatch):
    """HTML passed to weasyprint must contain <tr> rows and unit names."""
    captured_html: list[str] = []

    class _FakeHTML:
        def __init__(self, string: str, base_url: str | None = None):
            self._string = string

        def write_pdf(self) -> bytes:
            captured_html.append(self._string)
            return b"%PDF-1.4\nphase11"

    monkeypatch.setattr("reports.examen_de_eje.generator.HTML", _FakeHTML)

    gen = ExamenDeEjeGenerator()
    gen.data_dir = _workdir("phase11_render_html") / "data" / "examen_de_eje"

    plan = _make_plan_with_units()
    gen.render({("M30M2", "student@example.com"): plan})

    assert captured_html, "No HTML was captured — write_pdf was not called"
    html = captured_html[0]
    assert "<tr>" in html, "Expected <tr> rows in rendered HTML"
    assert "Matematica financiera" in html, "Expected unit name in rendered HTML"


def test_render_output_dir_is_data_examen_de_eje_output(monkeypatch):
    """render() must return gen.data_dir / 'output' as the output directory."""

    class _FakeHTML:
        def __init__(self, string: str, base_url: str | None = None):
            pass

        def write_pdf(self) -> bytes:
            return b"%PDF-1.4\nphase11"

    monkeypatch.setattr("reports.examen_de_eje.generator.HTML", _FakeHTML)

    gen = ExamenDeEjeGenerator()
    gen.data_dir = _workdir("phase11_render_outdir") / "data" / "examen_de_eje"

    plan = _make_plan_with_units()
    output_dir = gen.render({("M30M2", "student@example.com"): plan})

    assert output_dir == gen.data_dir / "output"


def test_render_skips_plan_with_no_units(monkeypatch):
    """render() with an empty plan must produce no PDF and not crash."""

    class _FakeHTML:
        def __init__(self, string: str, base_url: str | None = None):
            pass

        def write_pdf(self) -> bytes:
            return b"%PDF-1.4\nphase11"

    monkeypatch.setattr("reports.examen_de_eje.generator.HTML", _FakeHTML)

    gen = ExamenDeEjeGenerator()
    base = _workdir("phase11_render_empty")
    gen.data_dir = base / "data" / "examen_de_eje"

    empty_plan = ExamenPlan(
        assessment_type="M30M2",
        student_id="u-2",
        email="empty@example.com",
        assessment_name="M30M2-EXAMEN DE EJE 2-DATA",
    )
    empty_plan.units = {}
    empty_plan.unit_order = []

    output_dir = gen.render({("M30M2", "empty@example.com"): empty_plan})

    # No PDF should be created for an empty plan
    pdfs = list(output_dir.glob("*.pdf")) if output_dir.exists() else []
    assert len(pdfs) == 0, f"Expected no PDFs for empty plan, found: {pdfs}"
