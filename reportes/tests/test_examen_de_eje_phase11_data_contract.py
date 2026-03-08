"""Phase 11 – TDD RED: REGISTRY, bank column validation, and mapping load contracts.

All tests in this file must FAIL with ImportError until reports/examen_de_eje/generator.py
is implemented (Plan 02).
"""

from pathlib import Path
from uuid import uuid4

import pandas as pd
import pytest
from openpyxl import Workbook

from reports import REGISTRY
from reports.examen_de_eje.generator import ExamenDeEjeGenerator


# ---------------------------------------------------------------------------
# Helpers (mirror pattern from test_test_de_eje_phase9_data_contract.py)
# ---------------------------------------------------------------------------


def _workdir(prefix: str) -> Path:
    path = Path(".tmp_testdata") / f"{prefix}_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_ids_xlsx(path: Path, rows: list[tuple[str, str]]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.append(["assessment_name", "assessment_id"])
    for name, assessment_id in rows:
        ws.append([name, assessment_id])
    wb.save(path)


def _write_bank_xlsx(path: Path, columns: list[str]) -> None:
    """Write a minimal bank xlsx with one data row using the given column names."""
    row: dict = {}
    for i, col in enumerate(columns):
        row[col] = f"value_{i}"
    pd.DataFrame([row]).to_excel(path, index=False)


# ---------------------------------------------------------------------------
# REGISTRY test
# ---------------------------------------------------------------------------


def test_registry_contains_examen_de_eje_plugin():
    assert "examen_de_eje" in REGISTRY
    assert REGISTRY["examen_de_eje"].__name__ == "ExamenDeEjeGenerator"


# ---------------------------------------------------------------------------
# Bank column validation tests
# ---------------------------------------------------------------------------


def test_bank_columns_accepted_with_required_set(monkeypatch):
    """Bank with exactly {pregunta, alternativa, unidad} must not raise."""
    base = _workdir("phase11_bank_valid")
    bank_path = base / "M30M2-EXAMEN DE EJE 1-DATA.xlsx"
    _write_bank_xlsx(bank_path, ["pregunta", "alternativa", "unidad"])

    gen = ExamenDeEjeGenerator()
    monkeypatch.setattr(
        gen,
        "_load_examen_de_eje_mapping",
        lambda: [
            __import__(
                "reports.examen_de_eje.generator", fromlist=["MappingRow"]
            ).MappingRow(
                assessment_name="M30M2-EXAMEN DE EJE 1-DATA",
                assessment_type="M30M2",
                assessment_number=1,
                assessment_id="aaaaaaaaaaaaaaaaaaaaaaaa",
                bank_path=bank_path,
            )
        ],
    )

    responses = pd.DataFrame(
        [{"email": "student@example.com", "user_id": "u-1", "value_0": "A"}]
    )
    # Should not raise
    gen.analyze({"M30M2_EXAMEN_DE_EJE_1": responses})


def test_bank_missing_column_raises_with_name(monkeypatch):
    """Bank missing 'unidad' must raise ValueError mentioning 'unidad'."""
    base = _workdir("phase11_bank_missing_col")
    bank_path = base / "M30M2-EXAMEN DE EJE 1-DATA.xlsx"
    # Only pregunta + alternativa, no unidad
    _write_bank_xlsx(bank_path, ["pregunta", "alternativa"])

    gen = ExamenDeEjeGenerator()
    monkeypatch.setattr(
        gen,
        "_load_examen_de_eje_mapping",
        lambda: [
            __import__(
                "reports.examen_de_eje.generator", fromlist=["MappingRow"]
            ).MappingRow(
                assessment_name="M30M2-EXAMEN DE EJE 1-DATA",
                assessment_type="M30M2",
                assessment_number=1,
                assessment_id="aaaaaaaaaaaaaaaaaaaaaaaa",
                bank_path=bank_path,
            )
        ],
    )

    responses = pd.DataFrame(
        [{"email": "student@example.com", "user_id": "u-1", "pregunta_1": "A"}]
    )
    with pytest.raises(ValueError) as exc:
        gen.analyze({"M30M2_EXAMEN_DE_EJE_1": responses})
    assert "unidad" in str(exc.value)


def test_bank_extra_column_allowed(monkeypatch):
    """Bank with extra columns beyond the required set must not raise."""
    base = _workdir("phase11_bank_extra_col")
    bank_path = base / "M30M2-EXAMEN DE EJE 1-DATA.xlsx"
    _write_bank_xlsx(bank_path, ["pregunta", "alternativa", "unidad", "extra_col"])

    gen = ExamenDeEjeGenerator()
    monkeypatch.setattr(
        gen,
        "_load_examen_de_eje_mapping",
        lambda: [
            __import__(
                "reports.examen_de_eje.generator", fromlist=["MappingRow"]
            ).MappingRow(
                assessment_name="M30M2-EXAMEN DE EJE 1-DATA",
                assessment_type="M30M2",
                assessment_number=1,
                assessment_id="aaaaaaaaaaaaaaaaaaaaaaaa",
                bank_path=bank_path,
            )
        ],
    )

    responses = pd.DataFrame(
        [{"email": "student@example.com", "user_id": "u-1", "value_0": "A"}]
    )
    # Should not raise
    gen.analyze({"M30M2_EXAMEN_DE_EJE_1": responses})


# ---------------------------------------------------------------------------
# Mapping load tests
# ---------------------------------------------------------------------------


def test_load_mapping_accepts_valid_examen_de_eje_rows(monkeypatch):
    """ids.xlsx with a valid EXAMEN DE EJE row should produce 1 mapping entry."""
    import reports.examen_de_eje.generator as ede_gen

    base = _workdir("phase11_mapping_valid")
    ids_path = base / "ids.xlsx"
    banks_dir = base / "banks"
    banks_dir.mkdir(parents=True, exist_ok=True)

    _write_ids_xlsx(
        ids_path,
        [("M30M2-EXAMEN DE EJE 1-DATA", "aaaaaaaaaaaaaaaaaaaaaaaa")],
    )
    _write_bank_xlsx(
        banks_dir / "M30M2-EXAMEN DE EJE 1-DATA.xlsx",
        ["pregunta", "alternativa", "unidad"],
    )

    monkeypatch.setattr(ede_gen, "IDS_LOCAL_PATH", ids_path)
    monkeypatch.setattr(ede_gen, "BANKS_DIR", banks_dir)

    gen = ExamenDeEjeGenerator()
    mapping = gen._load_examen_de_eje_mapping()

    assert len(mapping) == 1
    assert mapping[0].assessment_number == 1
    assert mapping[0].assessment_type == "M30M2"


def test_load_mapping_skips_test_de_eje_rows(monkeypatch):
    """ids.xlsx with only TEST DE EJE rows should return empty mapping for examen_de_eje."""
    import reports.examen_de_eje.generator as ede_gen

    base = _workdir("phase11_mapping_skip_tde")
    ids_path = base / "ids.xlsx"
    banks_dir = base / "banks"
    banks_dir.mkdir(parents=True, exist_ok=True)

    _write_ids_xlsx(
        ids_path,
        [("M30M2-TEST DE EJE 1-DATA", "aaaaaaaaaaaaaaaaaaaaaaaa")],
    )

    monkeypatch.setattr(ede_gen, "IDS_LOCAL_PATH", ids_path)
    monkeypatch.setattr(ede_gen, "BANKS_DIR", banks_dir)

    gen = ExamenDeEjeGenerator()
    with pytest.raises(ValueError):
        gen._load_examen_de_eje_mapping()


def test_load_mapping_raises_when_no_valid_rows(monkeypatch):
    """ids.xlsx with only junk rows should raise ValueError."""
    import reports.examen_de_eje.generator as ede_gen

    base = _workdir("phase11_mapping_junk")
    ids_path = base / "ids.xlsx"
    banks_dir = base / "banks"
    banks_dir.mkdir(parents=True, exist_ok=True)

    _write_ids_xlsx(
        ids_path,
        [("JUNK-ROW-IGNORE", "zzzzzz")],
    )

    monkeypatch.setattr(ede_gen, "IDS_LOCAL_PATH", ids_path)
    monkeypatch.setattr(ede_gen, "BANKS_DIR", banks_dir)

    gen = ExamenDeEjeGenerator()
    with pytest.raises(ValueError):
        gen._load_examen_de_eje_mapping()
