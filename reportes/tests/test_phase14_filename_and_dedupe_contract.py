from pathlib import Path
from uuid import uuid4

import pandas as pd

from core.runner import PipelineRunner
from reports.examen_de_eje.generator import ExamenDeEjeGenerator, ExamenPlan, UnitStats
from reports.test_de_eje.generator import LessonStats, StudentPlan, TestDeEjeGenerator as TdeGenerator, UnitProgress


def _workdir(prefix: str) -> Path:
    path = Path(".tmp_testdata") / f"{prefix}_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _make_tde_unit(name: str, lesson_scores: list[tuple[int, int]]) -> UnitProgress:
    unit = UnitProgress(name=name)
    for idx, (correct, total) in enumerate(lesson_scores, start=1):
        lesson = LessonStats(total=total, correct=correct)
        unit.lessons[f"Leccion {idx}"] = lesson
        unit.total += total
        unit.correct += correct
    return unit


def _make_ede_plan() -> ExamenPlan:
    plan = ExamenPlan(
        assessment_type="M30M2",
        student_id="u-1",
        email="student@example.com",
        assessment_name="M30M2-EXAMEN DE EJE 1-DATA",
    )
    plan.units["Unidad 1"] = UnitStats(name="Unidad 1", total=4, correct=2)
    plan.unit_order = ["Unidad 1"]
    return plan


def test_filename_contract_test_de_eje(monkeypatch):
    class _FakeHTML:
        def __init__(self, string: str, base_url: str | None = None):
            self._string = string

        def write_pdf(self) -> bytes:
            return b"%PDF-1.4\nphase14"

    monkeypatch.setattr("reports.test_de_eje.generator.HTML", _FakeHTML)

    gen = TdeGenerator()
    gen.data_dir = _workdir("phase14_tde_filename") / "data" / "test_de_eje"

    plan = StudentPlan(
        assessment_type="M30M2",
        student_id="u-1",
        email="student@example.com",
        assessment_name="M30M-TEST DE EJE 1-DATA",
    )
    plan.units["Unidad 1"] = _make_tde_unit("Unidad 1", [(1, 1)])

    output_dir = gen.render({("M30M2", "student@example.com"): plan})
    expected_pdf = output_dir / "informe_test_de_eje_M30M-TEST DE EJE 1-DATA_student@example.com.pdf"
    assert expected_pdf.exists()


def test_filename_contract_examen_de_eje(monkeypatch):
    class _FakeHTML:
        def __init__(self, string: str, base_url: str | None = None):
            self._string = string

        def write_pdf(self) -> bytes:
            return b"%PDF-1.4\nphase14"

    monkeypatch.setattr("reports.examen_de_eje.generator.HTML", _FakeHTML)

    gen = ExamenDeEjeGenerator()
    gen.data_dir = _workdir("phase14_ede_filename") / "data" / "examen_de_eje"

    plan = _make_ede_plan()
    output_dir = gen.render({("M30M2", "student@example.com"): plan})
    expected_pdf = output_dir / "informe_examen_de_eje_M30M2-EXAMEN DE EJE 1-DATA_student@example.com.pdf"
    assert expected_pdf.exists()


def test_runner_extracts_filename_contract():
    runner = PipelineRunner(report_type="test_de_eje", dry_run=True)
    parsed = runner._parse_filename_contract(
        Path("informe_test_de_eje_M30M-TEST DE EJE 1-DATA_student@example.com.pdf")
    )
    assert parsed == ("test_de_eje", "M30M-TEST DE EJE 1-DATA", "student@example.com")
    assert runner._extract_email_from_pdf(
        Path("informe_test_de_eje_M30M-TEST DE EJE 1-DATA_student@example.com.pdf")
    ) == "student@example.com"


def test_dedupe_key_is_report_assessment_email():
    runner = PipelineRunner(report_type="test_de_eje", dry_run=True)
    key1 = runner._dedupe_key_for_pdf(
        Path("informe_test_de_eje_M30M-TEST DE EJE 1-DATA_student@example.com.pdf")
    )
    key2 = runner._dedupe_key_for_pdf(
        Path("informe_test_de_eje_M30M-TEST DE EJE 2-DATA_student@example.com.pdf")
    )
    assert key1 == ("test_de_eje", "M30M-TEST DE EJE 1-DATA", "student@example.com")
    assert key2 == ("test_de_eje", "M30M-TEST DE EJE 2-DATA", "student@example.com")
    assert key1 != key2


def test_processed_emails_xlsx_appends_only_after_success(tmp_path):
    runner = PipelineRunner(report_type="test_de_eje", dry_run=True)
    runner.report_type = "test_de_eje"

    base = tmp_path / "data" / "test_de_eje"
    base.mkdir(parents=True, exist_ok=True)

    # Monkeypatch ledger path helper for isolated test I/O.
    runner._processed_emails_xlsx_path = lambda: base / "processed_emails.xlsx"

    ok = runner._append_processed_email_row(
        report_type="test_de_eje",
        assessment_name="M30M-TEST DE EJE 1-DATA",
        email="student@example.com",
        attachment_filename="informe_test_de_eje_M30M-TEST DE EJE 1-DATA_student@example.com.pdf",
        event_key="test_de_eje|M30M-TEST DE EJE 1-DATA|student@example.com",
    )
    assert ok is True
    ledger = base / "processed_emails.xlsx"
    assert ledger.exists()
    df = pd.read_excel(ledger, dtype=str)
    assert len(df) == 1
    assert df.iloc[0]["report_type"] == "test_de_eje"


def test_processed_emails_xlsx_uses_storage_backend(monkeypatch):
    class _FakeStorage:
        def __init__(self):
            self.files = {}

        def exists(self, path):
            return path in self.files

        def read_bytes(self, path):
            return self.files[path]

        def write_bytes(self, path, data, content_type=None):
            self.files[path] = data
            return True

        def ensure_directory(self, path):
            return None

    fake_storage = _FakeStorage()
    monkeypatch.setattr("core.runner.StorageClient", lambda: fake_storage)

    runner = PipelineRunner(report_type="examen_de_eje", dry_run=True)
    ledger_path = runner._processed_emails_xlsx_path()

    ok = runner._append_processed_email_row(
        report_type="examen_de_eje",
        assessment_name="M30M2-EXAMEN DE EJE 1-DATA",
        email="student@example.com",
        attachment_filename="informe_examen_de_eje_M30M2-EXAMEN DE EJE 1-DATA_student@example.com.pdf",
        event_key="examen_de_eje|M30M2-EXAMEN DE EJE 1-DATA|student@example.com",
    )
    assert ok is True
    assert str(ledger_path) in fake_storage.files

    keys = runner._load_processed_email_keys()
    assert ("examen_de_eje", "M30M2-EXAMEN DE EJE 1-DATA", "student@example.com") in keys
