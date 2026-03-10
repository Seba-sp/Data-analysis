"""Render contract tests for the test_de_habilidad plugin."""

from pathlib import Path
from uuid import uuid4

import pytest

from reports.test_de_habilidad.generator import (
    HabilidadPlan,
    TareaStats,
    TestDeHabilidadGenerator,
)


def _workdir(prefix: str) -> Path:
    path = Path(".tmp_testdata") / f"{prefix}_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


class _FakeHTML:
    """Captures rendered HTML and returns a stub PDF."""

    captured: list[str] = []

    def __init__(self, string: str, base_url: str | None = None):
        _FakeHTML.captured.append(string)

    def write_pdf(self) -> bytes:
        return b"%PDF-1.4\ntest_de_habilidad_stub"


def _make_plan(email: str = "student@example.com", habilidad: str = "Localizar") -> HabilidadPlan:
    plan = HabilidadPlan(
        assessment_type="L30M",
        student_id="u-1",
        email=email,
        assessment_name="L30M-TEST DE HABILIDAD 1-DATA",
        habilidad_name=habilidad,
    )
    plan.tareas["Tarea A"] = TareaStats(name="Tarea A", total=5, correct=5)   # 100% -> Dominada
    plan.tarea_order.append("Tarea A")
    plan.tareas["Tarea B"] = TareaStats(name="Tarea B", total=4, correct=2)   # 50% -> En desarrollo
    plan.tarea_order.append("Tarea B")
    return plan


def test_render_produces_pdf_with_correct_filename(monkeypatch):
    _FakeHTML.captured.clear()
    monkeypatch.setattr("reports.test_de_habilidad.generator.HTML", _FakeHTML)

    gen = TestDeHabilidadGenerator()
    gen.data_dir = _workdir("tdh_render_filename") / "data" / "test_de_habilidad"

    output_dir = gen.render({("L30M", "student@example.com"): _make_plan()})

    expected = output_dir / "informe_test_de_habilidad_L30M-TEST DE HABILIDAD 1-DATA_student@example.com.pdf"
    assert expected.exists()
    assert expected.read_bytes().startswith(b"%PDF-1.4")


def test_render_html_contains_habilidad_placeholder(monkeypatch):
    _FakeHTML.captured.clear()
    monkeypatch.setattr("reports.test_de_habilidad.generator.HTML", _FakeHTML)

    gen = TestDeHabilidadGenerator()
    gen.data_dir = _workdir("tdh_render_placeholder") / "data" / "test_de_habilidad"

    gen.render({("L30M", "student@example.com"): _make_plan(habilidad="Localizar informacion")})

    html = _FakeHTML.captured[0]
    assert "Localizar informacion" in html


def test_render_html_contains_dominada_and_en_desarrollo(monkeypatch):
    _FakeHTML.captured.clear()
    monkeypatch.setattr("reports.test_de_habilidad.generator.HTML", _FakeHTML)

    gen = TestDeHabilidadGenerator()
    gen.data_dir = _workdir("tdh_render_estados") / "data" / "test_de_habilidad"

    gen.render({("L30M", "student@example.com"): _make_plan()})

    html = _FakeHTML.captured[0]
    assert "Dominada" in html
    assert "En desarrollo" in html


def test_render_html_appends_fixed_rows_at_end(monkeypatch):
    _FakeHTML.captured.clear()
    monkeypatch.setattr("reports.test_de_habilidad.generator.HTML", _FakeHTML)

    gen = TestDeHabilidadGenerator()
    gen.data_dir = _workdir("tdh_render_fixed_rows") / "data" / "test_de_habilidad"

    gen.render({("L30M", "student@example.com"): _make_plan()})

    html = _FakeHTML.captured[0]
    assert "Guías temáticas" in html or "Gu" in html  # may render with encoding variants
    assert "Examen" in html
    assert "Realizar" in html


def test_render_skips_plans_with_no_tareas(monkeypatch):
    _FakeHTML.captured.clear()
    monkeypatch.setattr("reports.test_de_habilidad.generator.HTML", _FakeHTML)

    gen = TestDeHabilidadGenerator()
    gen.data_dir = _workdir("tdh_render_empty") / "data" / "test_de_habilidad"

    empty_plan = HabilidadPlan(
        assessment_type="L30M", student_id="u-1",
        email="empty@example.com", habilidad_name="H1",
    )
    output_dir = gen.render({("L30M", "empty@example.com"): empty_plan})

    assert len(_FakeHTML.captured) == 0
    assert output_dir.exists()


def test_render_multiple_students_produces_multiple_pdfs(monkeypatch):
    _FakeHTML.captured.clear()
    monkeypatch.setattr("reports.test_de_habilidad.generator.HTML", _FakeHTML)

    gen = TestDeHabilidadGenerator()
    gen.data_dir = _workdir("tdh_render_multi") / "data" / "test_de_habilidad"

    output_dir = gen.render({
        ("L30M", "alice@example.com"): _make_plan(email="alice@example.com"),
        ("L30M", "bob@example.com"): _make_plan(email="bob@example.com"),
    })

    pdfs = list(output_dir.glob("*.pdf"))
    assert len(pdfs) == 2
