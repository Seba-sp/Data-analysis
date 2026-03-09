from pathlib import Path
import sys
import types
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
_existing_firestore_module = sys.modules.get("core.firestore_service")
if _existing_firestore_module is not None and not hasattr(_existing_firestore_module, "__file__"):
    del sys.modules["core.firestore_service"]
if "google" not in sys.modules:
    sys.modules["google"] = types.ModuleType("google")
if "google.cloud" not in sys.modules:
    sys.modules["google.cloud"] = types.ModuleType("google.cloud")
if "google.cloud.firestore" not in sys.modules:
    fake_firestore_module = types.ModuleType("google.cloud.firestore")

    class _StubTransaction:
        pass

    fake_firestore_module.Transaction = _StubTransaction
    sys.modules["google.cloud.firestore"] = fake_firestore_module
if "google.cloud.firestore_v1" not in sys.modules:
    fake_firestore_v1 = types.ModuleType("google.cloud.firestore_v1")
    fake_firestore_v1.FieldFilter = object
    sys.modules["google.cloud.firestore_v1"] = fake_firestore_v1

sys.modules["google.cloud"].firestore = sys.modules["google.cloud.firestore"]

import core.firestore_service as firestore_service_module
from core.firestore_service import FirestoreService


class _FakeFieldFilter:
    def __init__(self, field_path, op_string, value):
        self.field_path = field_path
        self.op_string = op_string
        self.value = value


class _FakeValue:
    def __init__(self, value):
        self.value = value


class _FakeSnapshot:
    def __init__(self, doc_id, data, reference):
        self.id = doc_id
        self._data = dict(data) if data is not None else None
        self.reference = reference

    @property
    def exists(self):
        return self._data is not None

    def to_dict(self):
        return dict(self._data) if self._data is not None else None


class _FakeDocRef:
    def __init__(self, store, collection_path, doc_id):
        self._store = store
        self._collection_path = collection_path
        self.id = doc_id

    def set(self, data):
        self._store.setdefault(self._collection_path, {})[self.id] = dict(data)

    def update(self, data):
        collection = self._store.setdefault(self._collection_path, {})
        current = dict(collection.get(self.id, {}))
        current.update(dict(data))
        collection[self.id] = current

    def get(self, transaction=None):
        data = self._store.get(self._collection_path, {}).get(self.id)
        return _FakeSnapshot(self.id, data, self)

    def delete(self):
        self._store.setdefault(self._collection_path, {}).pop(self.id, None)


class _FakeAggregationQuery:
    def __init__(self, count_value):
        self._count_value = count_value

    def get(self):
        return [[_FakeValue(self._count_value)]]


class _FakeQuery:
    def __init__(self, store, collection_path, field_filter=None):
        self._store = store
        self._collection_path = collection_path
        self._field_filter = field_filter

    def _iter_filtered_docs(self):
        docs = self._store.get(self._collection_path, {})
        for doc_id, data in docs.items():
            if self._field_filter is None:
                yield doc_id, data
                continue
            if (
                getattr(self._field_filter, "op_string", None) == "=="
                and data.get(self._field_filter.field_path) == self._field_filter.value
            ):
                yield doc_id, data

    def stream(self):
        for doc_id, data in self._iter_filtered_docs():
            yield _FakeSnapshot(doc_id, data, _FakeDocRef(self._store, self._collection_path, doc_id))

    def count(self):
        return _FakeAggregationQuery(sum(1 for _ in self._iter_filtered_docs()))


class _FakeCollectionRef:
    def __init__(self, store, collection_path):
        self._store = store
        self._collection_path = collection_path

    def add(self, data):
        docs = self._store.setdefault(self._collection_path, {})
        doc_id = f"doc-{len(docs) + 1}"
        docs[doc_id] = dict(data)
        return (None, _FakeDocRef(self._store, self._collection_path, doc_id))

    def where(self, filter=None):
        return _FakeQuery(self._store, self._collection_path, field_filter=filter)

    def stream(self):
        return _FakeQuery(self._store, self._collection_path).stream()

    def document(self, doc_id):
        return _FakeDocRef(self._store, self._collection_path, doc_id)


class _FakeBatch:
    def __init__(self):
        self._ops = []

    def set(self, doc_ref, data):
        self._ops.append(("set", doc_ref, dict(data)))

    def delete(self, doc_ref):
        self._ops.append(("delete", doc_ref, None))

    def commit(self):
        for action, doc_ref, data in self._ops:
            if action == "set":
                doc_ref.set(data)
            elif action == "delete":
                doc_ref.delete()


class _FakeTransaction:
    def update(self, doc_ref, data):
        doc_ref.update(data)

    def set(self, doc_ref, data):
        doc_ref.set(data)


class _FakeClient:
    def __init__(self):
        self._store = {}

    def collection(self, collection_path):
        return _FakeCollectionRef(self._store, collection_path)

    def batch(self):
        return _FakeBatch()

    def transaction(self):
        return _FakeTransaction()


@pytest.fixture
def fake_firestore(monkeypatch):
    fake_client = _FakeClient()
    monkeypatch.setattr(
        firestore_service_module.firestore, "Client", lambda: fake_client, raising=False
    )
    monkeypatch.setattr(
        firestore_service_module.firestore, "transactional", lambda fn: fn, raising=False
    )
    monkeypatch.setattr(firestore_service_module, "FieldFilter", _FakeFieldFilter)
    return fake_client


def test_test_de_eje_queue_insert_and_read(fake_firestore):
    service = FirestoreService("test_de_eje")
    student = {
        "assessment_type": "M30M2",
        "assessment_id": "0123456789abcdef01234567",
        "user_email": "student@example.com",
    }

    queued = service.queue_student(student)
    queued_students = service.get_queued_students()

    assert queued is True
    assert service.queue_collection == "report_types/test_de_eje/queue"
    assert len(queued_students) == 1
    assert queued_students[0]["report_type"] == "test_de_eje"
    assert queued_students[0]["status"] == "queued"
    assert service.get_queue_count() == 1


def test_queue_rejects_cross_type_contamination(fake_firestore):
    service = FirestoreService("test_de_eje")

    queued = service.queue_student(
        {
            "report_type": "ensayo",
            "assessment_type": "M30M2",
            "user_email": "student@example.com",
        }
    )

    assert queued is False
    assert service.get_queue_count() == 0


def test_counter_increment_idempotence_with_event_key(fake_firestore):
    service = FirestoreService("test_de_eje")

    first = service.increment_counter("M30M2", event_key="event-1")
    duplicate = service.increment_counter("M30M2", event_key="event-1")
    second = service.increment_counter("M30M2", event_key="event-2")

    assert first is True
    assert duplicate is True
    assert second is True
    assert service.get_counters()["M30M2"] == 2


def test_batch_state_create_active_clear_lifecycle(fake_firestore):
    service = FirestoreService("test_de_eje")
    deadline = int(time.time() + 60)

    created = service.create_batch_state("batch-123", deadline)
    active_before_clear = service.is_batch_active()
    state_before_clear = service.get_batch_state()
    cleared = service.clear_batch_state()
    active_after_clear = service.is_batch_active()

    assert created is True
    assert state_before_clear is not None
    assert state_before_clear["batch_id"] == "batch-123"
    assert state_before_clear["deadline"] == deadline
    assert active_before_clear is True
    assert cleared is True
    assert active_after_clear is False
    assert service.get_batch_state() is None
