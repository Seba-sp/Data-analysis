"""
Tests for core/runner.py â€” PipelineRunner and PipelineResult.

TDD RED phase: these tests are written before the implementation exists.
"""
import os
import logging
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
import pytest

_existing_batch_module = sys.modules.get("core.batch_processor")
if _existing_batch_module is not None and not hasattr(_existing_batch_module, "__file__"):
    del sys.modules["core.batch_processor"]
_existing_firestore_module = sys.modules.get("core.firestore_service")
if _existing_firestore_module is not None and not hasattr(_existing_firestore_module, "__file__"):
    del sys.modules["core.firestore_service"]

if "google" not in sys.modules:
    sys.modules["google"] = types.ModuleType("google")
if "google.cloud" not in sys.modules:
    sys.modules["google.cloud"] = types.ModuleType("google.cloud")
if "google.cloud.firestore" not in sys.modules:
    fake_firestore_module = types.ModuleType("google.cloud.firestore")
    fake_firestore_module.Transaction = object
    fake_firestore_module.Client = object
    fake_firestore_module.transactional = lambda fn: fn
    sys.modules["google.cloud.firestore"] = fake_firestore_module
if "google.cloud.firestore_v1" not in sys.modules:
    fake_firestore_v1_module = types.ModuleType("google.cloud.firestore_v1")
    fake_firestore_v1_module.FieldFilter = object
    sys.modules["google.cloud.firestore_v1"] = fake_firestore_v1_module
sys.modules["google.cloud"].firestore = sys.modules["google.cloud.firestore"]

# â”€â”€ Imports under test â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
from core.runner import PipelineRunner, PipelineResult
from core.email_sender import EmailSender
from core.batch_processor import BatchProcessor


# â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _make_pdf_dir(tmp_path: Path, filenames: list[str]) -> Path:
    """Create a temporary directory with fake PDF files."""
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    for name in filenames:
        (out_dir / name).write_bytes(b"%PDF fake")
    return out_dir


@pytest.fixture(autouse=True)
def _isolate_processed_emails_ledger(tmp_path, monkeypatch):
    """Prevent cross-test dedupe interference from shared ledgers."""

    def _ledger_path(self):
        return tmp_path / f"{self.report_type}_processed_emails.xlsx"

    monkeypatch.setattr(PipelineRunner, "_processed_emails_xlsx_path", _ledger_path)


# â”€â”€ PipelineResult structure â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestPipelineResultStructure:
    def test_has_four_keys(self):
        result: PipelineResult = {
            "success": True,
            "records_processed": 0,
            "emails_sent": 0,
            "errors": [],
        }
        assert set(result.keys()) == {"success", "records_processed", "emails_sent", "errors"}

    def test_typed_dict_is_importable(self):
        from core.runner import PipelineResult as PR
        assert PR is not None


# â”€â”€ PipelineRunner instantiation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestPipelineRunnerInit:
    def test_stores_report_type(self):
        runner = PipelineRunner("diagnosticos")
        assert runner.report_type == "diagnosticos"

    def test_default_dry_run_false(self):
        runner = PipelineRunner("diagnosticos")
        assert runner.dry_run is False

    def test_dry_run_true(self):
        runner = PipelineRunner("diagnosticos", dry_run=True)
        assert runner.dry_run is True

    def test_default_test_email_none(self):
        runner = PipelineRunner("diagnosticos")
        assert runner.test_email is None

    def test_test_email_stored(self):
        runner = PipelineRunner("diagnosticos", test_email="dev@example.com")
        assert runner.test_email == "dev@example.com"


# â”€â”€ _extract_email_from_pdf â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestExtractEmailFromPdf:
    def _runner(self):
        return PipelineRunner("diagnosticos")

    def test_standard_pattern(self, tmp_path):
        pdf = tmp_path / "informe_diagnosticos_M1_alice@school.com.pdf"
        pdf.write_bytes(b"")
        assert self._runner()._extract_email_from_pdf(pdf) == "alice@school.com"

    def test_email_with_underscores(self, tmp_path):
        # email itself has underscores in the locked contract:
        # informe_{report_type}_{assessment_name}_{email}.pdf
        pdf = tmp_path / "informe_diagnosticos_CL_first_last@school.com.pdf"
        pdf.write_bytes(b"")
        result = PipelineRunner("diagnosticos", assessment_name="CL")._extract_email_from_pdf(pdf)
        assert result == "first_last@school.com"

    def test_email_with_underscores_is_rejected_when_assessment_unknown(self, tmp_path):
        # Without assessment_name, split can be ambiguous:
        # CL_first_last@school.com could split as:
        #   assessment=CL email=first_last@school.com
        #   assessment=CL_first email=last@school.com
        pdf = tmp_path / "informe_diagnosticos_CL_first_last@school.com.pdf"
        pdf.write_bytes(b"")
        result = PipelineRunner("diagnosticos")._extract_email_from_pdf(pdf)
        assert result is None

    def test_missing_informe_prefix_returns_none(self, tmp_path):
        pdf = tmp_path / "alice@school.com_M1.pdf"
        pdf.write_bytes(b"")
        assert self._runner()._extract_email_from_pdf(pdf) is None

    def test_too_few_parts_returns_none(self, tmp_path):
        pdf = tmp_path / "informe_M1.pdf"
        pdf.write_bytes(b"")
        assert self._runner()._extract_email_from_pdf(pdf) is None

    def test_exactly_three_parts(self, tmp_path):
        # informe_email@x.com_ATYPE â€” minimal valid
        pdf = tmp_path / "informe_diagnosticos_HYST_a@b.com.pdf"
        pdf.write_bytes(b"")
        result = self._runner()._extract_email_from_pdf(pdf)
        assert result == "a@b.com"


# â”€â”€ run() â€” dry-run mode â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestRunDryRun:
    """In dry_run=True mode: generate() runs, no emails sent, no Drive upload."""

    def test_dry_run_no_email_calls(self, tmp_path):
        runner = PipelineRunner("diagnosticos", dry_run=True)
        out_dir = _make_pdf_dir(tmp_path, [
            "informe_diagnosticos_M1_alice@s.com.pdf",
            "informe_diagnosticos_CL_bob@s.com.pdf",
        ])

        with patch("core.runner.get_generator") as mock_get_gen, \
             patch("core.runner.EmailSender") as mock_email_cls, \
             patch("core.runner.DriveService") as mock_drive_cls:

            mock_gen_instance = MagicMock()
            mock_gen_instance.generate.return_value = out_dir
            mock_get_gen.return_value = MagicMock(return_value=mock_gen_instance)

            result = runner.run()

        mock_email_cls.assert_not_called()
        mock_drive_cls.assert_not_called()
        assert result["success"] is True
        assert result["emails_sent"] == 0
        assert result["records_processed"] == 2

    def test_dry_run_records_processed_equals_pdf_count(self, tmp_path):
        runner = PipelineRunner("diagnosticos", dry_run=True)
        out_dir = _make_pdf_dir(tmp_path, [
            "informe_diagnosticos_M1_a@x.com.pdf",
            "informe_diagnosticos_CL_b@x.com.pdf",
            "informe_diagnosticos_CIEN_c@x.com.pdf",
        ])

        with patch("core.runner.get_generator") as mock_get_gen, \
             patch("core.runner.EmailSender"), \
             patch("core.runner.DriveService"):

            mock_gen = MagicMock()
            mock_gen.generate.return_value = out_dir
            mock_get_gen.return_value = MagicMock(return_value=mock_gen)

            result = runner.run()

        assert result["records_processed"] == 3


# â”€â”€ run() â€” test-email mode â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestRunTestEmail:
    """In test_email mode: emails go to override address, Drive suppressed."""

    def test_email_sent_to_test_address(self, tmp_path):
        runner = PipelineRunner("diagnosticos", test_email="dev@example.com")
        out_dir = _make_pdf_dir(tmp_path, ["informe_diagnosticos_M1_student@s.com.pdf"])

        with patch("core.runner.get_generator") as mock_get_gen, \
             patch("core.runner.EmailSender") as mock_email_cls, \
             patch("core.runner.DriveService") as mock_drive_cls:

            mock_gen = MagicMock()
            mock_gen.generate.return_value = out_dir
            mock_get_gen.return_value = MagicMock(return_value=mock_gen)

            mock_sender = MagicMock()
            mock_sender.send_comprehensive_report_email.return_value = True
            mock_email_cls.return_value = mock_sender

            result = runner.run()

        # Drive must NOT be called
        mock_drive_cls.assert_not_called()

        # Email must be sent to test address, not student address
        call_kwargs = mock_sender.send_comprehensive_report_email.call_args
        assert call_kwargs.kwargs.get("recipient_email") == "dev@example.com" or \
               call_kwargs.args[0] == "dev@example.com"

        assert result["emails_sent"] == 1

    def test_drive_suppressed_in_test_email_mode(self, tmp_path):
        runner = PipelineRunner("diagnosticos", test_email="dev@example.com")
        out_dir = _make_pdf_dir(tmp_path, ["informe_diagnosticos_CL_x@y.com.pdf"])

        with patch("core.runner.get_generator") as mock_get_gen, \
             patch("core.runner.EmailSender") as mock_email_cls, \
             patch("core.runner.DriveService") as mock_drive_cls:

            mock_gen = MagicMock()
            mock_gen.generate.return_value = out_dir
            mock_get_gen.return_value = MagicMock(return_value=mock_gen)

            mock_sender = MagicMock()
            mock_sender.send_comprehensive_report_email.return_value = True
            mock_email_cls.return_value = mock_sender

            runner.run()

        mock_drive_cls.assert_not_called()


# â”€â”€ run() â€” normal mode â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestRunNormalMode:
    """Normal mode: email to student, Drive upload attempted."""

    def test_email_sent_to_student_address(self, tmp_path):
        runner = PipelineRunner("diagnosticos")
        out_dir = _make_pdf_dir(tmp_path, ["informe_diagnosticos_M1_student@s.com.pdf"])

        with patch("core.runner.get_generator") as mock_get_gen, \
             patch("core.runner.EmailSender") as mock_email_cls, \
             patch("core.runner.DriveService") as mock_drive_cls:

            mock_gen = MagicMock()
            mock_gen.generate.return_value = out_dir
            mock_get_gen.return_value = MagicMock(return_value=mock_gen)

            mock_sender = MagicMock()
            mock_sender.send_comprehensive_report_email.return_value = True
            mock_email_cls.return_value = mock_sender

            mock_drive = MagicMock()
            mock_drive.upload_file.return_value = "file-id-123"
            mock_drive_cls.return_value = mock_drive

            result = runner.run()

        call_kwargs = mock_sender.send_comprehensive_report_email.call_args
        recipient = call_kwargs.kwargs.get("recipient_email") or call_kwargs.args[0]
        assert recipient == "student@s.com"
        assert call_kwargs.kwargs["filename"] == "informe_diagnosticos_M1_student@s.com.pdf"
        assert call_kwargs.kwargs["correlation_key"] == "diagnosticos|M1|student@s.com"
        assert result["emails_sent"] == 1

    def test_drive_upload_attempted_in_normal_mode(self, tmp_path):
        runner = PipelineRunner("diagnosticos")
        out_dir = _make_pdf_dir(tmp_path, ["informe_diagnosticos_M1_a@b.com.pdf"])

        with patch("core.runner.get_generator") as mock_get_gen, \
             patch("core.runner.EmailSender") as mock_email_cls, \
             patch("core.runner.DriveService") as mock_drive_cls:

            mock_gen = MagicMock()
            mock_gen.generate.return_value = out_dir
            mock_get_gen.return_value = MagicMock(return_value=mock_gen)

            mock_sender = MagicMock()
            mock_sender.send_comprehensive_report_email.return_value = True
            mock_email_cls.return_value = mock_sender

            mock_drive = MagicMock()
            mock_drive.upload_file.return_value = "fid"
            mock_drive_cls.return_value = mock_drive

            runner.run()

        mock_drive_cls.assert_called_once()
        mock_drive.upload_file.assert_called_once()


# â”€â”€ run() â€” error handling â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestRunErrorHandling:
    def test_generate_failure_returns_success_false(self):
        runner = PipelineRunner("diagnosticos")

        with patch("core.runner.get_generator") as mock_get_gen:
            mock_gen = MagicMock()
            mock_gen.generate.side_effect = RuntimeError("generation exploded")
            mock_get_gen.return_value = MagicMock(return_value=mock_gen)

            result = runner.run()

        assert result["success"] is False
        assert len(result["errors"]) > 0
        assert "generation exploded" in result["errors"][0]

    def test_email_failure_does_not_abort_loop(self, tmp_path):
        """If one email fails, the loop must continue to the next student."""
        runner = PipelineRunner("diagnosticos")
        out_dir = _make_pdf_dir(tmp_path, [
            "informe_diagnosticos_M1_fail@s.com.pdf",
            "informe_diagnosticos_M1_ok@s.com.pdf",
        ])

        with patch("core.runner.get_generator") as mock_get_gen, \
             patch("core.runner.EmailSender") as mock_email_cls, \
             patch("core.runner.DriveService") as mock_drive_cls:

            mock_gen = MagicMock()
            mock_gen.generate.return_value = out_dir
            mock_get_gen.return_value = MagicMock(return_value=mock_gen)

            mock_drive = MagicMock()
            mock_drive.upload_file.return_value = None
            mock_drive_cls.return_value = mock_drive

            # First call raises, second returns True
            mock_sender = MagicMock()
            mock_sender.send_comprehensive_report_email.side_effect = [
                Exception("SMTP timeout"),
                True,
            ]
            mock_email_cls.return_value = mock_sender

            result = runner.run()

        assert result["success"] is True
        assert result["emails_sent"] == 1
        assert result["records_processed"] == 2
        assert len(result["errors"]) == 1

    def test_send_returning_false_appended_to_errors(self, tmp_path):
        runner = PipelineRunner("diagnosticos")
        out_dir = _make_pdf_dir(tmp_path, ["informe_diagnosticos_M1_x@y.com.pdf"])

        with patch("core.runner.get_generator") as mock_get_gen, \
             patch("core.runner.EmailSender") as mock_email_cls, \
             patch("core.runner.DriveService") as mock_drive_cls:

            mock_gen = MagicMock()
            mock_gen.generate.return_value = out_dir
            mock_get_gen.return_value = MagicMock(return_value=mock_gen)

            mock_drive = MagicMock()
            mock_drive.upload_file.return_value = None
            mock_drive_cls.return_value = mock_drive

            mock_sender = MagicMock()
            mock_sender.send_comprehensive_report_email.return_value = False
            mock_email_cls.return_value = mock_sender

            result = runner.run()

        assert result["emails_sent"] == 0
        assert len(result["errors"]) == 1
        assert "recipient=x@y.com" in result["errors"][0]
        assert "attachment=informe_diagnosticos_M1_x@y.com.pdf" in result["errors"][0]
        assert "event_key=diagnosticos|M1|x@y.com" in result["errors"][0]

    def test_unextractable_email_skipped_with_error(self, tmp_path):
        runner = PipelineRunner("diagnosticos")
        out_dir = _make_pdf_dir(tmp_path, ["bad_filename.pdf"])

        with patch("core.runner.get_generator") as mock_get_gen, \
             patch("core.runner.EmailSender"), \
             patch("core.runner.DriveService"):

            mock_gen = MagicMock()
            mock_gen.generate.return_value = out_dir
            mock_get_gen.return_value = MagicMock(return_value=mock_gen)

            result = runner.run()

        assert result["success"] is True
        assert result["emails_sent"] == 0
        assert len(result["errors"]) > 0
        assert "attachment=bad_filename.pdf" in result["errors"][0]

    def test_drive_upload_failure_does_not_abort(self, tmp_path):
        """Drive upload failure (exception or None) must not stop the email loop."""
        runner = PipelineRunner("diagnosticos")
        out_dir = _make_pdf_dir(tmp_path, ["informe_diagnosticos_M1_s@x.com.pdf"])

        with patch("core.runner.get_generator") as mock_get_gen, \
             patch("core.runner.EmailSender") as mock_email_cls, \
             patch("core.runner.DriveService") as mock_drive_cls:

            mock_gen = MagicMock()
            mock_gen.generate.return_value = out_dir
            mock_get_gen.return_value = MagicMock(return_value=mock_gen)

            mock_drive = MagicMock()
            mock_drive.upload_file.side_effect = Exception("Drive quota exceeded")
            mock_drive_cls.return_value = mock_drive

            mock_sender = MagicMock()
            mock_sender.send_comprehensive_report_email.return_value = True
            mock_email_cls.return_value = mock_sender

            result = runner.run()

        # Email still sent despite Drive failure
        assert result["emails_sent"] == 1
        assert result["success"] is True


# â”€â”€ run() â€” always returns PipelineResult â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestRunAlwaysReturnsResult:
    def test_result_never_none_on_success(self, tmp_path):
        runner = PipelineRunner("diagnosticos", dry_run=True)
        out_dir = _make_pdf_dir(tmp_path, [])

        with patch("core.runner.get_generator") as mock_get_gen:
            mock_gen = MagicMock()
            mock_gen.generate.return_value = out_dir
            mock_get_gen.return_value = MagicMock(return_value=mock_gen)
            result = runner.run()

        assert result is not None
        assert "success" in result

    def test_result_never_none_on_generate_failure(self):
        runner = PipelineRunner("diagnosticos")

        with patch("core.runner.get_generator") as mock_get_gen:
            mock_gen = MagicMock()
            mock_gen.generate.side_effect = ValueError("no data")
            mock_get_gen.return_value = MagicMock(return_value=mock_gen)
            result = runner.run()

        assert result is not None
        assert result["success"] is False


# â”€â”€ Logging (no bare print calls) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestNoBarePrints:
    def test_runner_module_has_no_print_calls(self):
        import ast
        import inspect
        import core.runner as runner_module

        src_file = Path(inspect.getfile(runner_module))
        tree = ast.parse(src_file.read_text(encoding="utf-8"))

        print_calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "print"
        ]
        assert print_calls == [], f"Found {len(print_calls)} bare print() calls in runner.py"


# â”€â”€ Task 1 TDD: email_template module â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestTestDeEjeEmailTemplate:
    """tests/test_runner.py â€” Task 1 RED: email_template module contract."""

    def test_template_module_importable(self):
        from reports.test_de_eje.email_template import SUBJECT, BODY
        assert SUBJECT is not None
        assert BODY is not None

    def test_subject_is_non_empty_string(self):
        from reports.test_de_eje.email_template import SUBJECT
        assert isinstance(SUBJECT, str) and len(SUBJECT) > 0

    def test_body_is_non_empty_string(self):
        from reports.test_de_eje.email_template import BODY
        assert isinstance(BODY, str) and len(BODY) > 0

    def test_subject_differs_from_generic_diagnostic(self):
        from reports.test_de_eje.email_template import SUBJECT
        assert "Resultados de DiagnÃ³stico" not in SUBJECT

    def test_body_differs_from_generic_diagnostic(self):
        from reports.test_de_eje.email_template import BODY
        assert "test de diagnÃ³stico" not in BODY

    def test_import_is_idempotent(self):
        import importlib
        mod1 = importlib.import_module("reports.test_de_eje.email_template")
        mod2 = importlib.import_module("reports.test_de_eje.email_template")
        assert mod1.SUBJECT is mod2.SUBJECT
        assert mod1.BODY is mod2.BODY


# â”€â”€ Task 2 TDD: EmailSender subject/body overrides + runner template resolution â”€

class TestEmailSenderSubjectBodyOverrides:
    """Task 2 RED: EmailSender accepts optional subject/body without breaking callers."""

    def test_subject_override_used_when_provided(self, monkeypatch):
        monkeypatch.setenv("EMAIL_FROM", "noreply@example.com")
        monkeypatch.setenv("EMAIL_PASS", "secret")

        captured = {}

        def fake_send_message(msg):
            captured["subject"] = msg["Subject"]

        with patch("core.email_sender.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_server.__enter__ = lambda s: mock_server
            mock_server.__exit__ = MagicMock(return_value=False)
            mock_server.send_message.side_effect = fake_send_message
            mock_smtp.return_value = mock_server

            sender = EmailSender()
            sender.send_comprehensive_report_email(
                recipient_email="student@example.com",
                pdf_content=b"%PDF fake",
                username="student@example.com",
                filename="informe_diagnosticos_M1_student@example.com.pdf",
                subject="Tu informe Test de Eje",
            )

        assert captured.get("subject") == "Tu informe Test de Eje"

    def test_default_subject_used_when_not_provided(self, monkeypatch):
        monkeypatch.setenv("EMAIL_FROM", "noreply@example.com")
        monkeypatch.setenv("EMAIL_PASS", "secret")

        captured = {}

        def fake_send_message(msg):
            captured["subject"] = msg["Subject"]

        with patch("core.email_sender.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_server.__enter__ = lambda s: mock_server
            mock_server.__exit__ = MagicMock(return_value=False)
            mock_server.send_message.side_effect = fake_send_message
            mock_smtp.return_value = mock_server

            sender = EmailSender()
            sender.send_comprehensive_report_email(
                recipient_email="student@example.com",
                pdf_content=b"%PDF fake",
                username="student@example.com",
                filename="informe_diagnosticos_M1_student@example.com.pdf",
            )

        assert captured.get("subject") == "Resultados de Diagnóstico"

    def test_body_override_used_when_provided(self, monkeypatch):
        monkeypatch.setenv("EMAIL_FROM", "noreply@example.com")
        monkeypatch.setenv("EMAIL_PASS", "secret")

        captured = {}

        def fake_attach(part):
            # Capture first text/plain part payload
            if hasattr(part, "get_content_type") and part.get_content_type() == "text/plain":
                captured["body"] = part.get_payload(decode=True).decode("utf-8")

        with patch("core.email_sender.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_server.__enter__ = lambda s: mock_server
            mock_server.__exit__ = MagicMock(return_value=False)
            mock_smtp.return_value = mock_server

            sender = EmailSender()
            result = sender.send_comprehensive_report_email(
                recipient_email="student@example.com",
                pdf_content=b"%PDF fake",
                username="student@example.com",
                filename="informe_diagnosticos_M1_student@example.com.pdf",
                body="Custom body for test_de_eje",
            )

        # Verify call reached SMTP (not rejected by validation)
        assert result is True

    def test_none_subject_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("EMAIL_FROM", "noreply@example.com")
        monkeypatch.setenv("EMAIL_PASS", "secret")

        captured = {}

        def fake_send_message(msg):
            captured["subject"] = msg["Subject"]

        with patch("core.email_sender.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_server.__enter__ = lambda s: mock_server
            mock_server.__exit__ = MagicMock(return_value=False)
            mock_server.send_message.side_effect = fake_send_message
            mock_smtp.return_value = mock_server

            sender = EmailSender()
            sender.send_comprehensive_report_email(
                recipient_email="student@example.com",
                pdf_content=b"%PDF fake",
                username="student@example.com",
                filename="informe_diagnosticos_M1_student@example.com.pdf",
                subject=None,
            )

        assert captured.get("subject") == "Resultados de Diagnóstico"


class TestRunnerEmailTemplateResolution:
    """Task 2 RED: PipelineRunner._get_email_template() resolves per-type templates."""

    def test_test_de_eje_sends_typed_email_subject(self):
        runner = PipelineRunner("test_de_eje")
        subject, body = runner._get_email_template()
        assert subject is not None
        assert subject != "Resultados de DiagnÃ³stico"
        assert len(subject) > 0

    def test_test_de_eje_sends_typed_email_body(self):
        runner = PipelineRunner("test_de_eje")
        subject, body = runner._get_email_template()
        assert body is not None
        assert len(body) > 0

    def test_unknown_report_type_email_template_falls_back(self):
        runner = PipelineRunner("nonexistent_type_xyz")
        subject, body = runner._get_email_template()
        assert subject is None
        assert body is None

    def test_template_resolution_does_not_raise_on_missing_module(self):
        runner = PipelineRunner("no_such_report_type_abc")
        # Must not raise
        result = runner._get_email_template()
        assert result == (None, None)

    def test_runner_passes_subject_to_sender_for_test_de_eje(self, tmp_path):
        runner = PipelineRunner("test_de_eje")
        out_dir = _make_pdf_dir(tmp_path, ["informe_test_de_eje_TDE_student@s.com.pdf"])

        with patch("core.runner.get_generator") as mock_get_gen, \
             patch("core.runner.EmailSender") as mock_email_cls, \
             patch("core.runner.DriveService") as mock_drive_cls:

            mock_gen = MagicMock()
            mock_gen.generate.return_value = out_dir
            mock_get_gen.return_value = MagicMock(return_value=mock_gen)

            mock_sender = MagicMock()
            mock_sender.send_comprehensive_report_email.return_value = True
            mock_email_cls.return_value = mock_sender

            mock_drive = MagicMock()
            mock_drive.upload_file.return_value = "fid"
            mock_drive_cls.return_value = mock_drive

            runner.run()

        call_kwargs = mock_sender.send_comprehensive_report_email.call_args
        subject_kwarg = call_kwargs.kwargs.get("subject")
        assert subject_kwarg is not None
        assert subject_kwarg != "Resultados de DiagnÃ³stico"

    def test_runner_passes_none_subject_for_templateless_type(self, tmp_path):
        runner = PipelineRunner("diagnosticos")
        out_dir = _make_pdf_dir(tmp_path, ["informe_diagnosticos_M1_student@s.com.pdf"])

        with patch("core.runner.get_generator") as mock_get_gen, \
             patch("core.runner.EmailSender") as mock_email_cls, \
             patch("core.runner.DriveService") as mock_drive_cls:

            mock_gen = MagicMock()
            mock_gen.generate.return_value = out_dir
            mock_get_gen.return_value = MagicMock(return_value=mock_gen)

            mock_sender = MagicMock()
            mock_sender.send_comprehensive_report_email.return_value = True
            mock_email_cls.return_value = mock_sender

            mock_drive = MagicMock()
            mock_drive.upload_file.return_value = "fid"
            mock_drive_cls.return_value = mock_drive

            runner.run()

        call_kwargs = mock_sender.send_comprehensive_report_email.call_args
        # diagnosticos has no email_template.py â€” subject should be None (fallback)
        subject_kwarg = call_kwargs.kwargs.get("subject")
        assert subject_kwarg is None


class TestEmailSenderValidation:
    def test_empty_attachment_returns_false_without_smtp(self, monkeypatch):
        monkeypatch.setenv("EMAIL_FROM", "noreply@example.com")
        monkeypatch.setenv("EMAIL_PASS", "secret")

        with patch("core.email_sender.smtplib.SMTP") as mock_smtp:
            sender = EmailSender()
            sent = sender.send_comprehensive_report_email(
                recipient_email="student@example.com",
                pdf_content=b"",
                username="student@example.com",
                filename="informe_diagnosticos_M1_student@example.com.pdf",
                correlation_key="diagnosticos|M1|student@example.com",
            )

        assert sent is False
        mock_smtp.assert_not_called()


class TestBatchProcessorResultSemantics:
    def test_batch_result_is_unsuccessful_when_pipeline_reports_errors(self):
        processor = BatchProcessor()
        fake_fs = MagicMock()
        fake_fs.get_queued_students.return_value = [{"user_email": "student@example.com"}]
        fake_fs.clear_queue.return_value = True
        fake_fs.clear_batch_state.return_value = True

        with patch("core.batch_processor.FirestoreService", return_value=fake_fs), \
             patch.object(
                 processor,
                 "process_report_type",
                 return_value={
                     "success": False,
                     "records_processed": 1,
                     "emails_sent": 0,
                     "errors": ["smtp timeout"],
                 },
             ):
            result = processor.process_batch("test_de_eje", "batch-1")

        assert result["success"] is False
        assert result["records_processed"] == 1
        assert result["emails_sent"] == 0
        assert "smtp timeout" in result["errors"]
        assert any("Pipeline failed for test_de_eje" in e for e in result["errors"])

    def test_batch_result_exposes_success_metrics_when_pipeline_is_clean(self):
        processor = BatchProcessor()
        fake_fs = MagicMock()
        fake_fs.get_queued_students.return_value = [{"user_email": "student@example.com"}]
        fake_fs.clear_queue.return_value = True
        fake_fs.clear_batch_state.return_value = True

        with patch("core.batch_processor.FirestoreService", return_value=fake_fs), \
             patch.object(
                 processor,
                 "process_report_type",
                 return_value={
                     "success": True,
                     "records_processed": 2,
                     "emails_sent": 2,
                     "errors": [],
                 },
             ):
            result = processor.process_batch("test_de_eje", "batch-2")

        assert result["success"] is True
        assert result["records_processed"] == 2
        assert result["emails_sent"] == 2
        assert result["errors"] == []

    def test_batch_result_marks_cleanup_failures_as_errors(self):
        processor = BatchProcessor()
        fake_fs = MagicMock()
        fake_fs.get_queued_students.return_value = [{"user_email": "student@example.com"}]
        fake_fs.clear_queue.return_value = False
        fake_fs.clear_batch_state.return_value = False

        with patch("core.batch_processor.FirestoreService", return_value=fake_fs), \
             patch.object(
                 processor,
                 "process_report_type",
                 return_value={
                     "success": True,
                     "records_processed": 1,
                     "emails_sent": 1,
                     "errors": [],
                 },
             ):
            result = processor.process_batch("test_de_eje", "batch-3")

        assert result["success"] is False
        assert "Failed to clear queue for test_de_eje" in result["errors"]
        assert "Failed to clear batch state for test_de_eje" in result["errors"]

    def test_invalid_attachment_filename_returns_false_without_smtp(self, monkeypatch):
        monkeypatch.setenv("EMAIL_FROM", "noreply@example.com")
        monkeypatch.setenv("EMAIL_PASS", "secret")

        with patch("core.email_sender.smtplib.SMTP") as mock_smtp:
            sender = EmailSender()
            sent = sender.send_comprehensive_report_email(
                recipient_email="student@example.com",
                pdf_content=b"%PDF fake",
                username="student@example.com",
                filename="not-a-pdf.txt",
                correlation_key="diagnosticos|M1|student@example.com",
            )

        assert sent is False
        mock_smtp.assert_not_called()


