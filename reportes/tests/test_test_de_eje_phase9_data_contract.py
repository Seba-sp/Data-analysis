from pathlib import Path
from uuid import uuid4

import pandas as pd
import pytest
from openpyxl import Workbook

from reports import REGISTRY
from reports.test_de_eje.generator import MappingRow, TestDeEjeGenerator as TdeGenerator


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
    df = pd.DataFrame(
        [
            {
                columns[0]: "Pregunta 1",
                columns[1]: "A",
                columns[2]: "Unidad 1",
                columns[3]: "Leccion 1",
                **({columns[4]: "Extra"} if len(columns) > 4 else {}),
            }
        ]
    )
    df.to_excel(path, index=False)


def test_registry_contains_test_de_eje_plugin():
    assert "test_de_eje" in REGISTRY
    assert REGISTRY["test_de_eje"].__name__ == "TestDeEjeGenerator"


def test_load_mapping_accepts_valid_rows_and_sorts(monkeypatch):
    base = _workdir("phase9_data_mapping")
    ids_path = base / "ids.xlsx"
    banks_dir = base / "banks"
    banks_dir.mkdir(parents=True, exist_ok=True)

    _write_ids_xlsx(
        ids_path,
        [
            ("M30M2-TEST DE EJE 2-DATA", "aaaaaaaaaaaaaaaaaaaaaaaa"),
            ("M30M2-TEST DE EJE 1-DATA", "bbbbbbbbbbbbbbbbbbbbbbbb"),
            ("M30M2-EXAMEN DE EJE 1-DATA", "cccccccccccccccccccccccc"),
        ],
    )
    _write_bank_xlsx(
        banks_dir / "M30M2-TEST DE EJE 1-DATA.xlsx",
        ["pregunta", "alternativa", "unidad", "leccion"],
    )
    _write_bank_xlsx(
        banks_dir / "M30M2-TEST DE EJE 2-DATA.xlsx",
        ["pregunta", "alternativa", "unidad", "leccion"],
    )

    monkeypatch.setattr("reports.test_de_eje.generator.IDS_LOCAL_PATH", ids_path)
    monkeypatch.setattr("reports.test_de_eje.generator.BANKS_DIR", banks_dir)

    gen = TdeGenerator()
    mapping = gen._load_test_de_eje_mapping()

    assert [m.assessment_number for m in mapping] == [1, 2]
    assert all(m.assessment_type == "M30M2" for m in mapping)


def test_analyze_allows_extra_columns_when_required_set_exists(monkeypatch):
    base = _workdir("phase9_data_extra_cols")
    bank_path = base / "M30M2-TEST DE EJE 1-DATA.xlsx"
    _write_bank_xlsx(
        bank_path,
        ["pregunta", "alternativa", "unidad", "leccion", "extra_col"],
    )
    gen = TdeGenerator()
    monkeypatch.setattr(
        gen,
        "_load_test_de_eje_mapping",
        lambda: [
            MappingRow(
                assessment_name="M30M2-TEST DE EJE 1-DATA",
                assessment_type="M30M2",
                assessment_number=1,
                assessment_id="aaaaaaaaaaaaaaaaaaaaaaaa",
                bank_path=bank_path,
            )
        ],
    )

    responses = pd.DataFrame(
        [
            {
                "email": "student@example.com",
                "user_id": "u-1",
                "Pregunta 1": "A",
            }
        ]
    )
    analysis = gen.analyze({"M30M2_TEST_DE_EJE_1": responses})

    assert ("M30M2", "student@example.com") in analysis
    plan = analysis[("M30M2", "student@example.com")]
    assert "Unidad 1" in plan.units


@pytest.mark.parametrize("missing_col", ["pregunta", "alternativa", "unidad", "leccion"])
def test_analyze_fails_with_explicit_message_when_required_column_missing(
    monkeypatch, missing_col: str
):
    base = _workdir(f"phase9_data_missing_{missing_col}")
    bank_path = base / "M30M2-TEST DE EJE 1-DATA.xlsx"
    cols = ["pregunta", "alternativa", "unidad", "leccion"]
    cols.remove(missing_col)
    # write xlsx with remaining columns
    row = {col: "x" for col in cols}
    pd.DataFrame([row]).to_excel(bank_path, index=False)

    gen = TdeGenerator()
    monkeypatch.setattr(
        gen,
        "_load_test_de_eje_mapping",
        lambda: [
            MappingRow(
                assessment_name="M30M2-TEST DE EJE 1-DATA",
                assessment_type="M30M2",
                assessment_number=1,
                assessment_id="aaaaaaaaaaaaaaaaaaaaaaaa",
                bank_path=bank_path,
            )
        ],
    )

    responses = pd.DataFrame(
        [
            {
                "email": "student@example.com",
                "user_id": "u-1",
                "Pregunta 1": "A",
            }
        ]
    )

    with pytest.raises(ValueError) as exc:
        gen.analyze({"M30M2_TEST_DE_EJE_1": responses})
    msg = str(exc.value)
    assert bank_path.name in msg
    assert missing_col in msg
