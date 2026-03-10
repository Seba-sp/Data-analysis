"""Data contract tests for the test_de_habilidad plugin."""

from pathlib import Path
from uuid import uuid4

import pandas as pd
import pytest
from openpyxl import Workbook

from reports import REGISTRY
from reports.test_de_habilidad.generator import MappingRow, TestDeHabilidadGenerator


def _workdir(prefix: str) -> Path:
    path = Path(".tmp_testdata") / f"{prefix}_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_ids_xlsx(path: Path, rows: list[tuple[str, str]]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.append(["assessment_name", "assessment_id"])
    for name, aid in rows:
        ws.append([name, aid])
    wb.save(path)


def _write_bank_xlsx(path: Path, rows: list[dict]) -> None:
    pd.DataFrame(rows).to_excel(path, index=False)


def _stub_mapping(bank_path: Path, number: int = 1) -> list[MappingRow]:
    return [
        MappingRow(
            assessment_name=f"L30M-TEST DE HABILIDAD {number}-DATA",
            assessment_type="L30M",
            assessment_number=number,
            assessment_id="a" * 24,
            bank_path=bank_path,
        )
    ]


def _student_responses(**answers) -> pd.DataFrame:
    return pd.DataFrame([{"email": "student@example.com", "user_id": "u-1", **answers}])


# ---------------------------------------------------------------------------
# REGISTRY
# ---------------------------------------------------------------------------


def test_registry_contains_test_de_habilidad_plugin():
    assert "test_de_habilidad" in REGISTRY
    assert REGISTRY["test_de_habilidad"].__name__ == "TestDeHabilidadGenerator"


# ---------------------------------------------------------------------------
# Mapping load
# ---------------------------------------------------------------------------


def test_load_mapping_accepts_valid_rows_and_sorts(monkeypatch):
    base = _workdir("tdh_mapping_sort")
    ids_path = base / "ids.xlsx"
    banks_dir = base / "banks"
    banks_dir.mkdir()

    _write_ids_xlsx(ids_path, [
        ("L30M-TEST DE HABILIDAD 2-DATA", "b" * 24),
        ("L30M-TEST DE HABILIDAD 1-DATA", "a" * 24),
    ])
    for n in [1, 2]:
        _write_bank_xlsx(
            banks_dir / f"L30M-TEST DE HABILIDAD {n}-DATA.xlsx",
            [{"pregunta": "P1", "alternativa": "A", "tarea_lectora": "T1"}],
        )

    monkeypatch.setattr("reports.test_de_habilidad.generator.IDS_LOCAL_PATH", ids_path)
    monkeypatch.setattr("reports.test_de_habilidad.generator.BANKS_DIR", banks_dir)

    gen = TestDeHabilidadGenerator()
    mapping = gen._load_test_de_habilidad_mapping()

    assert [m.assessment_number for m in mapping] == [1, 2]
    assert all(m.assessment_type == "L30M" for m in mapping)


def test_load_mapping_skips_non_tdh_rows(monkeypatch):
    base = _workdir("tdh_mapping_skip")
    ids_path = base / "ids.xlsx"
    banks_dir = base / "banks"
    banks_dir.mkdir()

    _write_ids_xlsx(ids_path, [
        ("M30M2-TEST DE EJE 1-DATA", "a" * 24),
        ("L30M-TEST DE HABILIDAD 1-DATA", "b" * 24),
    ])
    _write_bank_xlsx(
        banks_dir / "L30M-TEST DE HABILIDAD 1-DATA.xlsx",
        [{"pregunta": "P1", "alternativa": "A", "tarea_lectora": "T1"}],
    )

    monkeypatch.setattr("reports.test_de_habilidad.generator.IDS_LOCAL_PATH", ids_path)
    monkeypatch.setattr("reports.test_de_habilidad.generator.BANKS_DIR", banks_dir)

    gen = TestDeHabilidadGenerator()
    mapping = gen._load_test_de_habilidad_mapping()

    assert len(mapping) == 1
    assert mapping[0].assessment_number == 1


def test_load_mapping_raises_when_no_valid_rows(monkeypatch):
    base = _workdir("tdh_mapping_empty")
    ids_path = base / "ids.xlsx"
    banks_dir = base / "banks"
    banks_dir.mkdir()

    _write_ids_xlsx(ids_path, [("JUNK-ROW", "z" * 24)])

    monkeypatch.setattr("reports.test_de_habilidad.generator.IDS_LOCAL_PATH", ids_path)
    monkeypatch.setattr("reports.test_de_habilidad.generator.BANKS_DIR", banks_dir)

    gen = TestDeHabilidadGenerator()
    with pytest.raises(ValueError):
        gen._load_test_de_habilidad_mapping()


# ---------------------------------------------------------------------------
# Bank column validation
# ---------------------------------------------------------------------------


def test_analyze_accepts_required_bank_columns(monkeypatch):
    base = _workdir("tdh_bank_valid")
    bank_path = base / "L30M-TEST DE HABILIDAD 1-DATA.xlsx"
    _write_bank_xlsx(bank_path, [{"pregunta": "Pregunta 1", "alternativa": "A", "tarea_lectora": "T1"}])

    gen = TestDeHabilidadGenerator()
    monkeypatch.setattr(gen, "_load_test_de_habilidad_mapping", lambda: _stub_mapping(bank_path))

    gen.analyze({"L30M_TEST_DE_HABILIDAD_1": _student_responses(**{"Pregunta 1": "A"})})


def test_analyze_accepts_extra_bank_columns(monkeypatch):
    base = _workdir("tdh_bank_extra")
    bank_path = base / "L30M-TEST DE HABILIDAD 1-DATA.xlsx"
    _write_bank_xlsx(bank_path, [
        {"pregunta": "Pregunta 1", "alternativa": "A", "tarea_lectora": "T1", "habilidad": "H1", "extra": "x"}
    ])

    gen = TestDeHabilidadGenerator()
    monkeypatch.setattr(gen, "_load_test_de_habilidad_mapping", lambda: _stub_mapping(bank_path))

    gen.analyze({"L30M_TEST_DE_HABILIDAD_1": _student_responses(**{"Pregunta 1": "A"})})


@pytest.mark.parametrize("missing_col", ["pregunta", "alternativa", "tarea_lectora"])
def test_analyze_raises_on_missing_required_bank_column(monkeypatch, missing_col: str):
    base = _workdir(f"tdh_missing_{missing_col}")
    bank_path = base / "L30M-TEST DE HABILIDAD 1-DATA.xlsx"
    cols = {"pregunta", "alternativa", "tarea_lectora"} - {missing_col}
    pd.DataFrame([{c: "x" for c in cols}]).to_excel(bank_path, index=False)

    gen = TestDeHabilidadGenerator()
    monkeypatch.setattr(gen, "_load_test_de_habilidad_mapping", lambda: _stub_mapping(bank_path))

    with pytest.raises(ValueError) as exc:
        gen.analyze({"L30M_TEST_DE_HABILIDAD_1": _student_responses(**{"Pregunta 1": "A"})})
    assert missing_col in str(exc.value)


# ---------------------------------------------------------------------------
# analyze() correctness
# ---------------------------------------------------------------------------


def test_analyze_builds_plan_with_correct_tarea_mastery(monkeypatch):
    """Tarea A: 2/2 = 100% (Dominada). Tarea B: 1/3 = ~33% (En desarrollo)."""
    base = _workdir("tdh_analyze_mastery")
    bank_path = base / "L30M-TEST DE HABILIDAD 1-DATA.xlsx"
    _write_bank_xlsx(bank_path, [
        {"pregunta": "Pregunta 1", "alternativa": "A", "tarea_lectora": "Tarea A"},
        {"pregunta": "Pregunta 2", "alternativa": "B", "tarea_lectora": "Tarea A"},
        {"pregunta": "Pregunta 3", "alternativa": "C", "tarea_lectora": "Tarea B"},
        {"pregunta": "Pregunta 4", "alternativa": "A", "tarea_lectora": "Tarea B"},
        {"pregunta": "Pregunta 5", "alternativa": "A", "tarea_lectora": "Tarea B"},
    ])

    gen = TestDeHabilidadGenerator()
    monkeypatch.setattr(gen, "_load_test_de_habilidad_mapping", lambda: _stub_mapping(bank_path))

    responses = _student_responses(**{
        "Pregunta 1": "A",   # correct
        "Pregunta 2": "B",   # correct
        "Pregunta 3": "X",   # wrong
        "Pregunta 4": "X",   # wrong
        "Pregunta 5": "A",   # correct
    })

    result = gen.analyze({"L30M_TEST_DE_HABILIDAD_1": responses})

    assert ("L30M", "student@example.com") in result
    plan = result[("L30M", "student@example.com")]
    assert plan.tareas["Tarea A"].percent == 100.0
    assert plan.tareas["Tarea B"].percent == pytest.approx(33.33, abs=0.1)


def test_analyze_reads_habilidad_name_from_bank(monkeypatch):
    base = _workdir("tdh_habilidad_name")
    bank_path = base / "L30M-TEST DE HABILIDAD 1-DATA.xlsx"
    _write_bank_xlsx(bank_path, [
        {"pregunta": "Pregunta 1", "alternativa": "A", "tarea_lectora": "T1", "habilidad": "Comprension lectora"}
    ])

    gen = TestDeHabilidadGenerator()
    monkeypatch.setattr(gen, "_load_test_de_habilidad_mapping", lambda: _stub_mapping(bank_path))

    result = gen.analyze({"L30M_TEST_DE_HABILIDAD_1": _student_responses(**{"Pregunta 1": "A"})})

    assert result[("L30M", "student@example.com")].habilidad_name == "Comprension lectora"


def test_analyze_skips_students_without_email(monkeypatch):
    base = _workdir("tdh_no_email")
    bank_path = base / "L30M-TEST DE HABILIDAD 1-DATA.xlsx"
    _write_bank_xlsx(bank_path, [{"pregunta": "Pregunta 1", "alternativa": "A", "tarea_lectora": "T1"}])

    gen = TestDeHabilidadGenerator()
    monkeypatch.setattr(gen, "_load_test_de_habilidad_mapping", lambda: _stub_mapping(bank_path))

    responses = pd.DataFrame([{"email": "", "user_id": "u-1", "Pregunta 1": "A"}])
    result = gen.analyze({"L30M_TEST_DE_HABILIDAD_1": responses})

    assert len(result) == 0


def test_analyze_preserves_tarea_insertion_order(monkeypatch):
    base = _workdir("tdh_tarea_order")
    bank_path = base / "L30M-TEST DE HABILIDAD 1-DATA.xlsx"
    _write_bank_xlsx(bank_path, [
        {"pregunta": "Pregunta 1", "alternativa": "A", "tarea_lectora": "Zeta"},
        {"pregunta": "Pregunta 2", "alternativa": "A", "tarea_lectora": "Alfa"},
        {"pregunta": "Pregunta 3", "alternativa": "A", "tarea_lectora": "Beta"},
    ])

    gen = TestDeHabilidadGenerator()
    monkeypatch.setattr(gen, "_load_test_de_habilidad_mapping", lambda: _stub_mapping(bank_path))

    responses = _student_responses(**{"Pregunta 1": "A", "Pregunta 2": "A", "Pregunta 3": "A"})
    result = gen.analyze({"L30M_TEST_DE_HABILIDAD_1": responses})

    plan = result[("L30M", "student@example.com")]
    assert plan.tarea_order == ["Zeta", "Alfa", "Beta"]
