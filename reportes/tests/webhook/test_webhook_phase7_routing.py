from pathlib import Path
import sys
import types

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
    def __init__(self, report_type):
        self.report_type = report_type

    def queue_student(self, student_data):
        return True

    def increment_counter(self, assessment_type):
        return True

    def get_queue_count(self):
        return 1

    def is_batch_active(self):
        return True


class _FakeMapper:
    def __init__(self, route):
        self._route = route
        self.mapping_source = "local"
        self.validation_counters = {"accepted": 1, "rejected": 2}

    def extract_assessment_id(self, url):
        if "unit=" not in url:
            return None
        return url.split("unit=")[-1][:24].lower()

    def get_route(self, assessment_id):
        return self._route

    def get_route_full(self, assessment_id):
        if self._route is None:
            return None
        report_type, assessment_type = self._route
        return (report_type, assessment_type, "")


@pytest.fixture
def app():
    return Flask(__name__)


def _valid_payload():
    return {
        "assessment": {
            "url": "https://example.com/course?unit=0123456789abcdef01234567"
        },
        "user": {"email": "student@example.com", "id": "u-1"},
    }


def _setup_common(monkeypatch, mapper):
    monkeypatch.setattr(webhook_service, "_initialize_services", lambda: True)
    monkeypatch.setattr(webhook_service, "validate_signature", lambda request: True)
    monkeypatch.setattr(webhook_service, "FirestoreService", _FakeFirestoreService)
    monkeypatch.setattr(webhook_service, "_am", mapper)


def test_single_route_resolution_preserves_contract(app, monkeypatch):
    _setup_common(monkeypatch, _FakeMapper(("test_de_eje", "M1")))
    with app.test_request_context("/", method="POST", json=_valid_payload()):
        response, status_code = webhook_service.handle_webhook(flask_request)

    assert status_code == 200
    body = response.get_json()
    assert body["report_type"] == "test_de_eje"
    assert body["assessment_type"] == "M1"
    assert body["status"] == "success"


def test_unknown_assessment_id_returns_400(app, monkeypatch):
    _setup_common(monkeypatch, _FakeMapper(None))
    with app.test_request_context("/", method="POST", json=_valid_payload()):
        response, status_code = webhook_service.handle_webhook(flask_request)

    assert status_code == 400
    assert "Unknown assessment ID" in response.get_json()["error"]


def test_rejected_assessment_id_logs_context_and_returns_400(app, monkeypatch, caplog):
    _setup_common(monkeypatch, _FakeMapper(None))
    with caplog.at_level("WARNING"):
        with app.test_request_context("/", method="POST", json=_valid_payload()):
            response, status_code = webhook_service.handle_webhook(flask_request)

    assert status_code == 400
    assert "unknown assessment_id route" in caplog.text
