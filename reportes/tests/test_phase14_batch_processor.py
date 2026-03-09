"""Phase 14-03: Tests for per-assessment queue architecture.

Tests:
  - test_webhook_stores_assessment_name: webhook stores assessment_name in student_data
  - test_batch_groups_by_assessment_name: BatchProcessor groups by assessment_name
  - test_legacy_student_no_assessment_name: legacy records without assessment_name handled gracefully
"""

from pathlib import Path
import sys
import types
import unittest.mock as mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ── Stub external modules before importing webhook_service ─────────────────────
if "functions_framework" not in sys.modules:
    sys.modules["functions_framework"] = types.SimpleNamespace(http=lambda fn: fn)
if "core.firestore_service" not in sys.modules:
    sys.modules["core.firestore_service"] = types.SimpleNamespace(
        FirestoreService=object
    )
if "core.task_service" not in sys.modules:
    sys.modules["core.task_service"] = types.SimpleNamespace(TaskService=object)
if "core.batch_processor" not in sys.modules:
    sys.modules["core.batch_processor"] = types.SimpleNamespace(
        BatchProcessor=object
    )

import webhook_service  # noqa: E402 — must come after stubs

# Remove the stub so we import the real BatchProcessor
if "core.batch_processor" in sys.modules and sys.modules["core.batch_processor"] is not None:
    _bp_mod = sys.modules.pop("core.batch_processor", None)

from core.batch_processor import BatchProcessor  # noqa: E402

# Restore stub so webhook_service keeps working
if "core.batch_processor" not in sys.modules:
    sys.modules["core.batch_processor"] = types.SimpleNamespace(BatchProcessor=BatchProcessor)


# ---------------------------------------------------------------------------
# Helpers / fakes
# ---------------------------------------------------------------------------

_VALID_ID = "a" * 24
_KNOWN_ROUTE_FULL = ("test_de_eje", "M1", "M1-TEST DE EJE 1-DATA")


class _FakeFirestoreServiceWebhook:
    """Minimal FirestoreService fake for webhook tests."""

    queued_students: list = []
    incremented_types: list = []

    def __init__(self, report_type: str) -> None:
        self.report_type = report_type

    def queue_student(self, student_data: dict) -> bool:
        _FakeFirestoreServiceWebhook.queued_students.append(student_data)
        return True

    def increment_counter(self, assessment_type: str) -> bool:
        _FakeFirestoreServiceWebhook.incremented_types.append(assessment_type)
        return True

    def get_queue_count(self) -> int:
        return 1

    def is_batch_active(self) -> bool:
        return True


class _FakeMapper:
    """Fake AssessmentMapper that supports both get_route() and get_route_full()."""

    mapping_source = "local"
    validation_counters = {"accepted": 1, "rejected": 0}

    def extract_assessment_id(self, url: str) -> str:
        return url.split("unit=")[-1][:24].lower()

    def get_route(self, assessment_id: str):
        return (_KNOWN_ROUTE_FULL[0], _KNOWN_ROUTE_FULL[1])

    def get_route_full(self, assessment_id: str):
        return _KNOWN_ROUTE_FULL  # (report_type, assessment_type, assessment_name)


def _make_flask_request(payload: dict):
    """Build a minimal Flask test request carrying the given JSON payload."""
    from flask import Flask
    app = Flask(__name__)
    with app.test_request_context(
        "/",
        method="POST",
        json=payload,
        headers={"Content-Type": "application/json", "X-Request-Id": "test-req-id"},
    ):
        from flask import request as flask_req
        return flask_req


# ---------------------------------------------------------------------------
# Test 1: webhook stores assessment_name in student_data
# ---------------------------------------------------------------------------

def test_webhook_stores_assessment_name(monkeypatch):
    """
    FAILS (RED): handle_webhook() calls get_route() which returns 2-tuple.
    After fix it must call get_route_full() and store assessment_name.
    """
    _FakeFirestoreServiceWebhook.queued_students = []
    _FakeFirestoreServiceWebhook.incremented_types = []

    monkeypatch.setattr(webhook_service, "_initialize_services", lambda: True)
    monkeypatch.setattr(webhook_service, "validate_signature", lambda req: True)
    monkeypatch.setattr(webhook_service, "FirestoreService", _FakeFirestoreServiceWebhook)
    monkeypatch.setattr(webhook_service, "_am", _FakeMapper())

    payload = {
        "assessment": {"url": f"https://example.com/course?unit={_VALID_ID}"},
        "user": {"email": "student@example.com", "id": "user-1"},
    }

    from flask import Flask
    app = Flask(__name__)
    with app.test_request_context("/", method="POST", json=payload):
        from flask import request as flask_req
        response, status = webhook_service.handle_webhook(flask_req)

    assert status == 200, f"Expected 200, got {status}"
    assert len(_FakeFirestoreServiceWebhook.queued_students) == 1
    stored = _FakeFirestoreServiceWebhook.queued_students[0]
    assert "assessment_name" in stored, (
        "student_data must contain 'assessment_name' key — "
        "handle_webhook() must call get_route_full() not get_route()"
    )
    assert stored["assessment_name"] == "M1-TEST DE EJE 1-DATA"


# ---------------------------------------------------------------------------
# Test 2: BatchProcessor groups by assessment_name
# ---------------------------------------------------------------------------

def test_batch_groups_by_assessment_name():
    """
    FAILS (RED): process_batch() currently calls process_report_type once.
    After fix it must call it once per distinct assessment_name group.
    """
    student_a = {
        "report_type": "test_de_eje",
        "assessment_type": "M1",
        "assessment_name": "M1-TEST DE EJE 1-DATA",
        "user_email": "alice@example.com",
    }
    student_b = {
        "report_type": "test_de_eje",
        "assessment_type": "M1",
        "assessment_name": "M1-TEST DE EJE 2-DATA",
        "user_email": "bob@example.com",
    }

    call_args: list = []

    def fake_get_queued_students():
        return [student_a, student_b]

    def fake_clear_queue():
        return True

    def fake_clear_batch_state():
        return True

    def fake_is_batch_active():
        return True

    def fake_get_batch_state():
        return {}

    fake_fs = mock.MagicMock()
    fake_fs.get_queued_students.return_value = [student_a, student_b]
    fake_fs.clear_queue.return_value = True
    fake_fs.clear_batch_state.return_value = True

    bp = BatchProcessor()

    def fake_process_report_type(report_type: str, assessment_name: str = "") -> dict:
        call_args.append((report_type, assessment_name))
        return {"success": True, "records_processed": 1, "emails_sent": 1, "errors": []}

    bp.process_report_type = fake_process_report_type

    with mock.patch("core.batch_processor.FirestoreService", return_value=fake_fs):
        result = bp.process_batch("test_de_eje", "batch-001")

    assert len(call_args) == 2, (
        f"process_report_type() must be called ONCE per distinct assessment_name, "
        f"got {len(call_args)} calls: {call_args}"
    )
    called_names = {args[1] for args in call_args}
    assert "M1-TEST DE EJE 1-DATA" in called_names
    assert "M1-TEST DE EJE 2-DATA" in called_names


# ---------------------------------------------------------------------------
# Test 3: Legacy student without assessment_name — no crash, graceful fallback
# ---------------------------------------------------------------------------

def test_legacy_student_no_assessment_name():
    """
    Legacy student records have no assessment_name key.
    process_batch() must NOT raise; it should group them under empty string and
    call process_report_type() once for them.
    """
    legacy_student = {
        "report_type": "test_de_eje",
        "assessment_type": "M1",
        # no assessment_name key
        "user_email": "legacy@example.com",
    }

    call_args: list = []

    fake_fs = mock.MagicMock()
    fake_fs.get_queued_students.return_value = [legacy_student]
    fake_fs.clear_queue.return_value = True
    fake_fs.clear_batch_state.return_value = True

    bp = BatchProcessor()

    def fake_process_report_type(report_type: str, assessment_name: str = "") -> dict:
        call_args.append((report_type, assessment_name))
        return {"success": True, "records_processed": 1, "emails_sent": 1, "errors": []}

    bp.process_report_type = fake_process_report_type

    with mock.patch("core.batch_processor.FirestoreService", return_value=fake_fs):
        result = bp.process_batch("test_de_eje", "batch-legacy")

    assert len(call_args) == 1, f"Expected 1 call for legacy student, got {call_args}"
    # Legacy records grouped under empty string key
    report_type_called, assessment_name_called = call_args[0]
    assert assessment_name_called == "", (
        f"Legacy student must be grouped under '' key, got '{assessment_name_called}'"
    )
