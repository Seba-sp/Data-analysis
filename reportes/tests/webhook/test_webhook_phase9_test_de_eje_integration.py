from pathlib import Path
import sys
import types
import logging

import pytest
from flask import Flask, request as flask_request

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
if "functions_framework" not in sys.modules:
    sys.modules["functions_framework"] = types.SimpleNamespace(http=lambda fn: fn)
if "core.firestore_service" not in sys.modules:
    sys.modules["core.firestore_service"] = types.SimpleNamespace(FirestoreService=object)
if "core.task_service" not in sys.modules:
    sys.modules["core.task_service"] = types.SimpleNamespace(TaskService=object)
if "core.batch_processor" not in sys.modules:
    sys.modules["core.batch_processor"] = types.SimpleNamespace(BatchProcessor=object)

import webhook_service


class _FakeFirestoreService:
    queue_calls = 0
    counter_calls = 0
    queued_students = []
    incremented_assessment_types = []

    def __init__(self, report_type):
        self.report_type = report_type

    def queue_student(self, student_data):
        _FakeFirestoreService.queue_calls += 1
        _FakeFirestoreService.queued_students.append(student_data)
        return True

    def increment_counter(self, assessment_type):
        _FakeFirestoreService.counter_calls += 1
        _FakeFirestoreService.incremented_assessment_types.append(assessment_type)
        return True

    def get_queue_count(self):
        return 1

    def is_batch_active(self):
        return True


class _FakeMapper:
    mapping_source = "local"
    validation_counters = {"accepted": 1, "rejected": 0}

    def extract_assessment_id(self, url):
        return url.split("unit=")[-1][:24].lower()

    def get_route(self, assessment_id):
        return ("test_de_eje", "M30M2")

    def get_route_full(self, assessment_id):
        return ("test_de_eje", "M30M2", "")


@pytest.fixture
def app():
    return Flask(__name__)


def _payload():
    return {
        "assessment": {"url": "https://example.com/course?unit=0123456789abcdef01234567"},
        "user": {"email": "student@example.com", "id": "user-1"},
    }


def test_test_de_eje_webhook_single_event_single_processing_path(app, monkeypatch):
    _FakeFirestoreService.queue_calls = 0
    _FakeFirestoreService.counter_calls = 0
    _FakeFirestoreService.queued_students = []
    _FakeFirestoreService.incremented_assessment_types = []

    monkeypatch.setattr(webhook_service, "_initialize_services", lambda: True)
    monkeypatch.setattr(webhook_service, "validate_signature", lambda request: True)
    monkeypatch.setattr(webhook_service, "FirestoreService", _FakeFirestoreService)
    monkeypatch.setattr(webhook_service, "_am", _FakeMapper())

    with app.test_request_context("/", method="POST", json=_payload()):
        response, status = webhook_service.handle_webhook(flask_request)

    assert status == 200
    body = response.get_json()
    assert body["status"] == "success"
    assert body["report_type"] == "test_de_eje"
    assert body["assessment_type"] == "M30M2"

    # one event -> one queue path + one counter increment
    assert _FakeFirestoreService.queue_calls == 1
    assert _FakeFirestoreService.counter_calls == 1

    # one event -> one downstream send intent (single queued student payload)
    assert len(_FakeFirestoreService.queued_students) == 1
    queued = _FakeFirestoreService.queued_students[0]
    assert queued["report_type"] == "test_de_eje"
    assert queued["assessment_type"] == "M30M2"
    assert queued["user_email"] == "student@example.com"
    assert queued["assessment_id"] == "0123456789abcdef01234567"

    # only one report expectation/counter increment is produced for the payload
    assert _FakeFirestoreService.incremented_assessment_types == ["M30M2"]


def test_webhook_logs_route_to_queue_context_for_success(app, monkeypatch, caplog):
    _FakeFirestoreService.queue_calls = 0
    _FakeFirestoreService.counter_calls = 0
    _FakeFirestoreService.queued_students = []
    _FakeFirestoreService.incremented_assessment_types = []

    monkeypatch.setattr(webhook_service, "_initialize_services", lambda: True)
    monkeypatch.setattr(webhook_service, "validate_signature", lambda request: True)
    monkeypatch.setattr(webhook_service, "FirestoreService", _FakeFirestoreService)
    monkeypatch.setattr(webhook_service, "_am", _FakeMapper())
    monkeypatch.setenv("IDS_XLSX_PATH", "gs://prod-mappings/ids.xlsx")
    caplog.set_level(logging.INFO, logger=webhook_service.logger.name)

    with app.test_request_context(
        "/", method="POST", json=_payload(), headers={"X-Request-Id": "req-123"}
    ):
        response, status = webhook_service.handle_webhook(flask_request)

    assert status == 200
    assert response.get_json()["status"] == "success"

    queue_records = [rec for rec in caplog.records if rec.message == "Webhook queue insertion attempted"]
    counter_records = [rec for rec in caplog.records if rec.message == "Webhook counter increment attempted"]

    assert queue_records
    assert counter_records

    queue_context = queue_records[-1].context
    counter_context = counter_records[-1].context

    assert queue_context["request_id"] == "req-123"
    assert queue_context["assessment_id"] == "0123456789abcdef01234567"
    assert queue_context["report_type"] == "test_de_eje"
    assert queue_context["assessment_type"] == "M30M2"
    assert queue_context["mapping_source"] == "local"
    assert queue_context["ids_path"] == "gs://prod-mappings/ids.xlsx"
    assert queue_context["queue_inserted"] is True

    assert counter_context["request_id"] == "req-123"
    assert counter_context["counter_incremented"] is True
    assert counter_context["report_type"] == "test_de_eje"


def test_webhook_logs_mapping_context_for_unknown_route(app, monkeypatch, caplog):
    class _UnknownRouteMapper(_FakeMapper):
        mapping_source = "gcs"
        validation_counters = {"accepted": 1, "rejected": 3}

        def get_route(self, assessment_id):
            return None

        def get_route_full(self, assessment_id):
            return None

    _FakeFirestoreService.queue_calls = 0
    _FakeFirestoreService.counter_calls = 0

    monkeypatch.setattr(webhook_service, "_initialize_services", lambda: True)
    monkeypatch.setattr(webhook_service, "validate_signature", lambda request: True)
    monkeypatch.setattr(webhook_service, "FirestoreService", _FakeFirestoreService)
    monkeypatch.setattr(webhook_service, "_am", _UnknownRouteMapper())
    monkeypatch.setenv("IDS_XLSX_PATH", "gs://prod-mappings/ids.xlsx")
    caplog.set_level(logging.INFO, logger=webhook_service.logger.name)

    with app.test_request_context("/", method="POST", json=_payload()):
        response, status = webhook_service.handle_webhook(flask_request)

    assert status == 400
    assert "Unknown assessment ID" in response.get_json()["error"]
    assert _FakeFirestoreService.queue_calls == 0
    assert _FakeFirestoreService.counter_calls == 0

    warning_records = [rec for rec in caplog.records if rec.message == "Rejected webhook: unknown assessment_id route"]
    assert warning_records

    warning_context = warning_records[-1].context
    assert warning_context["assessment_id"] == "0123456789abcdef01234567"
    assert warning_context["mapping_source"] == "gcs"
    assert warning_context["ids_path"] == "gs://prod-mappings/ids.xlsx"
    assert warning_context["rejected_rows"] == 3
