from pathlib import Path
from uuid import uuid4

import pandas as pd

from reports.examen_de_eje.generator import (
    ExamenDeEjeGenerator as ExamenDeEjeGeneratorCls,
    MappingRow as ExamenEjeMapping,
)
from reports.examen_de_habilidad.generator import (
    ExamenDeHabilidadGenerator as ExamenDeHabilidadGeneratorCls,
    MappingRow as ExamenHabilidadMapping,
)
from reports.test_de_eje.generator import (
    MappingRow as TdeMapping,
    TestDeEjeGenerator as TdeGeneratorCls,
)
from reports.test_de_habilidad.generator import (
    MappingRow as TdhMapping,
    TestDeHabilidadGenerator as TdhGeneratorCls,
)


def _workdir(prefix: str) -> Path:
    path = Path(".tmp_testdata") / f"{prefix}_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_bank_xlsx(path: Path, rows: list[dict]) -> None:
    pd.DataFrame(rows).to_excel(path, index=False)


def _set_context(gen, report_type: str, assessment_name: str, processed_keys: set[tuple[str, str, str]]) -> None:
    gen.set_generation_context(
        report_type=report_type,
        assessment_name=assessment_name,
        processed_email_keys=processed_keys,
        processed_emails_for_current_assessment=set(),
    )


def test_test_de_eje_prefilter_skips_processed_users(monkeypatch):
    base = _workdir("prefilter_tde")
    bank_path = base / "M30M2-TEST DE EJE 1-DATA.xlsx"
    _write_bank_xlsx(bank_path, [{"pregunta": "Q1", "alternativa": "A", "unidad": "U1", "leccion": "L1"}])

    gen = TdeGeneratorCls()
    monkeypatch.setattr(
        gen,
        "_load_test_de_eje_mapping",
        lambda: [
            TdeMapping(
                assessment_name="M30M2-TEST DE EJE 1-DATA",
                assessment_type="M30M2",
                assessment_number=1,
                assessment_id="a" * 24,
                bank_path=bank_path,
            )
        ],
    )
    _set_context(
        gen,
        "test_de_eje",
        "M30M2-TEST DE EJE 1-DATA",
        {("test_de_eje", "M30M2-TEST DE EJE 1-DATA", "done@example.com")},
    )

    responses = pd.DataFrame(
        [
            {"email": "done@example.com", "user_id": "u1", "Q1": "A"},
            {"email": "new@example.com", "user_id": "u2", "Q1": "A"},
        ]
    )
    result = gen.analyze({"M30M2_TEST_DE_EJE_1": responses})

    assert ("M30M2", "done@example.com") not in result
    assert ("M30M2", "new@example.com") in result


def test_examen_de_eje_prefilter_skips_processed_users(monkeypatch):
    base = _workdir("prefilter_ede")
    bank_path = base / "M30M2-EXAMEN DE EJE 1-DATA.xlsx"
    _write_bank_xlsx(bank_path, [{"pregunta": "Q1", "alternativa": "A", "unidad": "U1"}])

    gen = ExamenDeEjeGeneratorCls()
    monkeypatch.setattr(
        gen,
        "_load_examen_de_eje_mapping",
        lambda: [
            ExamenEjeMapping(
                assessment_name="M30M2-EXAMEN DE EJE 1-DATA",
                assessment_type="M30M2",
                assessment_number=1,
                assessment_id="a" * 24,
                bank_path=bank_path,
            )
        ],
    )
    _set_context(
        gen,
        "examen_de_eje",
        "M30M2-EXAMEN DE EJE 1-DATA",
        {("examen_de_eje", "M30M2-EXAMEN DE EJE 1-DATA", "done@example.com")},
    )

    responses = pd.DataFrame(
        [
            {"email": "done@example.com", "user_id": "u1", "Q1": "A"},
            {"email": "new@example.com", "user_id": "u2", "Q1": "A"},
        ]
    )
    result = gen.analyze({"M30M2_EXAMEN_DE_EJE_1": responses})

    assert ("M30M2", "done@example.com") not in result
    assert ("M30M2", "new@example.com") in result


def test_test_de_habilidad_prefilter_skips_processed_users(monkeypatch):
    base = _workdir("prefilter_tdh")
    bank_path = base / "L30M-TEST DE HABILIDAD 1-DATA.xlsx"
    _write_bank_xlsx(bank_path, [{"pregunta": "Q1", "alternativa": "A", "tarea_lectora": "T1"}])

    gen = TdhGeneratorCls()
    monkeypatch.setattr(
        gen,
        "_load_test_de_habilidad_mapping",
        lambda: [
            TdhMapping(
                assessment_name="L30M-TEST DE HABILIDAD 1-DATA",
                assessment_type="L30M",
                assessment_number=1,
                assessment_id="a" * 24,
                bank_path=bank_path,
            )
        ],
    )
    _set_context(
        gen,
        "test_de_habilidad",
        "L30M-TEST DE HABILIDAD 1-DATA",
        {("test_de_habilidad", "L30M-TEST DE HABILIDAD 1-DATA", "done@example.com")},
    )

    responses = pd.DataFrame(
        [
            {"email": "done@example.com", "user_id": "u1", "Q1": "A"},
            {"email": "new@example.com", "user_id": "u2", "Q1": "A"},
        ]
    )
    result = gen.analyze({"L30M_TEST_DE_HABILIDAD_1": responses})

    assert ("L30M", "done@example.com") not in result
    assert ("L30M", "new@example.com") in result


def test_examen_de_habilidad_prefilter_skips_processed_users(monkeypatch):
    base = _workdir("prefilter_edh")
    bank_path = base / "L30M-EXAMEN DE HABILIDAD 1-DATA.xlsx"
    _write_bank_xlsx(bank_path, [{"pregunta": "Q1", "alternativa": "A", "tarea_lectora": "T1"}])

    gen = ExamenDeHabilidadGeneratorCls()
    monkeypatch.setattr(
        gen,
        "_load_examen_de_habilidad_mapping",
        lambda: [
            ExamenHabilidadMapping(
                assessment_name="L30M-EXAMEN DE HABILIDAD 1-DATA",
                assessment_type="L30M",
                assessment_number=1,
                assessment_id="a" * 24,
                bank_path=bank_path,
            )
        ],
    )
    _set_context(
        gen,
        "examen_de_habilidad",
        "L30M-EXAMEN DE HABILIDAD 1-DATA",
        {("examen_de_habilidad", "L30M-EXAMEN DE HABILIDAD 1-DATA", "done@example.com")},
    )

    responses = pd.DataFrame(
        [
            {"email": "done@example.com", "user_id": "u1", "Q1": "A"},
            {"email": "new@example.com", "user_id": "u2", "Q1": "A"},
        ]
    )
    result = gen.analyze({"L30M_EXAMEN_DE_HABILIDAD_1": responses})

    assert ("L30M", "done@example.com") not in result
    assert ("L30M", "new@example.com") in result


def test_same_email_different_assessment_name_is_not_skipped(monkeypatch):
    base = _workdir("prefilter_cross_assessment")
    bank_path = base / "L30M-TEST DE HABILIDAD 1-DATA.xlsx"
    _write_bank_xlsx(bank_path, [{"pregunta": "Q1", "alternativa": "A", "tarea_lectora": "T1"}])

    gen = TdhGeneratorCls()
    monkeypatch.setattr(
        gen,
        "_load_test_de_habilidad_mapping",
        lambda: [
            TdhMapping(
                assessment_name="L30M-TEST DE HABILIDAD 1-DATA",
                assessment_type="L30M",
                assessment_number=1,
                assessment_id="a" * 24,
                bank_path=bank_path,
            )
        ],
    )
    _set_context(
        gen,
        "test_de_habilidad",
        "L30M-TEST DE HABILIDAD 1-DATA",
        {("test_de_habilidad", "L30M-TEST DE HABILIDAD 2-DATA", "student@example.com")},
    )

    responses = pd.DataFrame([{"email": "student@example.com", "user_id": "u1", "Q1": "A"}])
    result = gen.analyze({"L30M_TEST_DE_HABILIDAD_1": responses})

    assert ("L30M", "student@example.com") in result
