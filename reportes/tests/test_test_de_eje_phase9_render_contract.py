from pathlib import Path
from uuid import uuid4

from reports.test_de_eje.generator import (
    LessonStats,
    StudentPlan,
    TestDeEjeGenerator as TdeGenerator,
    UnitProgress,
)


def _workdir(prefix: str) -> Path:
    path = Path(".tmp_testdata") / f"{prefix}_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _make_unit(name: str, lesson_scores: list[tuple[int, int]]) -> UnitProgress:
    unit = UnitProgress(name=name)
    for idx, (correct, total) in enumerate(lesson_scores, start=1):
        lesson = LessonStats(total=total, correct=correct)
        unit.lessons[f"Leccion {idx}"] = lesson
        unit.total += total
        unit.correct += correct
    return unit


def test_render_contract_supports_dynamic_units_and_output_naming(monkeypatch):
    captured_html: list[str] = []

    class _FakeHTML:
        def __init__(self, string: str, base_url: str | None = None):
            self._string = string

        def write_pdf(self) -> bytes:
            captured_html.append(self._string)
            return b"%PDF-1.4\nphase9"

    monkeypatch.setattr("reports.test_de_eje.generator.HTML", _FakeHTML)

    gen = TdeGenerator()
    gen.data_dir = _workdir("phase9_render_dynamic") / "data" / "test_de_eje"

    plan = StudentPlan(
        assessment_type="M30M2",
        student_id="u-1",
        email="student@example.com",
        assessment_name="M30M-TEST DE EJE 1-DATA",
    )
    plan.units["Unidad 1"] = _make_unit("Unidad 1", [(2, 2)])
    plan.units["Unidad 2"] = _make_unit("Unidad 2", [(1, 2)])
    plan.units["Unidad 3"] = _make_unit("Unidad 3", [(2, 2)])
    plan.units["Unidad 4"] = _make_unit("Unidad 4", [(1, 2)])

    output_dir = gen.render({("M30M2", "student@example.com"): plan})

    expected_pdf = output_dir / "informe_test_de_eje_M30M-TEST DE EJE 1-DATA_student@example.com.pdf"
    assert output_dir == gen.data_dir / "output"
    assert expected_pdf.exists()
    assert expected_pdf.read_bytes().startswith(b"%PDF-1.4")

    html = captured_html[0]
    assert "HE hrs" not in html
    assert "El tiempo total estimado para completar este plan es de:" in html
    assert "Unidad 4" in html
    assert 1 <= html.count('<section class="page unit"') <= 4
    assert "✓" in html or "Ã¢Å“â€œ" in html
    assert "□" in html or "Ã¢â€“Â¡" in html
    assert "No requerido" in html
    assert "data-placeholder=\"estimated_total_hours\"" in html


def test_render_contract_supports_single_unit(monkeypatch):
    class _FakeHTML:
        def __init__(self, string: str, base_url: str | None = None):
            self._string = string

        def write_pdf(self) -> bytes:
            return b"%PDF-1.4\nsingle"

    monkeypatch.setattr("reports.test_de_eje.generator.HTML", _FakeHTML)

    gen = TdeGenerator()
    gen.data_dir = _workdir("phase9_render_single") / "data" / "test_de_eje"

    plan = StudentPlan(
        assessment_type="M30M2",
        student_id="u-2",
        email="single@example.com",
        assessment_name="M30M-TEST DE EJE 2-DATA",
    )
    plan.units["Unidad unica"] = _make_unit("Unidad unica", [(1, 2)])

    output_dir = gen.render({("M30M2", "single@example.com"): plan})
    pdf_path = output_dir / "informe_test_de_eje_M30M-TEST DE EJE 2-DATA_single@example.com.pdf"
    assert pdf_path.exists()
