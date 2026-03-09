from pathlib import Path
import sys

import pytest
from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.assessment_mapper import AssessmentMapper


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("  examen   de  eje  ", "EXAMEN DE EJE"),
        ("ensáyo", "ENSAYO"),
    ],
)
def test_normalize_text(raw, expected):
    mapper = AssessmentMapper()
    assert mapper._normalize_text(raw) == expected


@pytest.mark.parametrize("group", ["M1", "M2", "H30M", "Q30M", "F30M", "B30M", "CL"])
@pytest.mark.parametrize(
    "assessment_name,expected_report",
    [
        ("{group}-TEST DE EJE 1-DATA", "test_de_eje"),
        ("{group}-EXAMEN DE EJE 2-DATA", "examen_de_eje"),
        ("{group}-ENSAYO 3-DATA", "ensayo"),
    ],
)
def test_parse_supported_group(group, assessment_name, expected_report):
    mapper = AssessmentMapper()
    parsed = mapper._parse_assessment_name(assessment_name.format(group=group))
    assert parsed == (group, expected_report, group)

@pytest.mark.parametrize(
    "raw_group,canonical_group",
    [("M20M2", "M2"), ("M30M2", "M2"), ("M30M1", "M1"), ("M30M", "M1")],
)
def test_parse_accepts_group_aliases(raw_group, canonical_group):
    mapper = AssessmentMapper()
    parsed = mapper._parse_assessment_name(f"{raw_group}-TEST DE EJE 1-DATA")
    assert parsed == (canonical_group, "test_de_eje", canonical_group)


def test_parse_allows_lowercase_and_accent_variants():
    mapper = AssessmentMapper()
    parsed = mapper._parse_assessment_name("m1-exámen de eje 1-data")
    assert parsed == ("M1", "examen_de_eje", "M1")


def test_parse_rejects_unsupported_group(caplog):
    mapper = AssessmentMapper()
    with caplog.at_level("WARNING"):
        parsed = mapper._parse_assessment_name("X1-TEST DE EJE 1-DATA")
    assert parsed is None
    assert "unsupported group" in caplog.text


def test_parse_rejects_invalid_pattern(caplog):
    mapper = AssessmentMapper()
    with caplog.at_level("WARNING"):
        parsed = mapper._parse_assessment_name("M1-TEST DE EJE-DATA")
    assert parsed is None
    assert "invalid type segment" in caplog.text


def test_validation_rejects_missing_name_and_tracks_counters():
    mapper = AssessmentMapper()
    accepted_before = mapper.validation_counters["accepted"]
    rejected_before = mapper.validation_counters["rejected"]

    ok = mapper.register_ids_row("0123456789abcdef01234567", "", row_index=1)
    assert ok is False
    assert mapper.validation_counters["accepted"] == accepted_before
    assert mapper.validation_counters["rejected"] == rejected_before + 1
    assert mapper.validation_errors["missing_assessment_name"] == 1


def test_validation_rejects_invalid_assessment_id_and_does_not_mutate_routes():
    mapper = AssessmentMapper()
    route_before = mapper.get_route("not-a-real-id")

    ok = mapper.register_ids_row("not-a-real-id", "M1-TEST DE EJE 1-DATA", row_index=2)
    assert ok is False
    assert route_before is None
    assert mapper.get_route("not-a-real-id") is None
    assert mapper.validation_errors["invalid_assessment_id"] == 1


def test_duplicate_idempotent_same_target_is_accepted():
    mapper = AssessmentMapper()
    assessment_id = "0123456789abcdef01234567"
    accepted_before = mapper.validation_counters["accepted"]
    rejected_before = mapper.validation_counters["rejected"]

    first = mapper.register_ids_row(assessment_id, "M1-TEST DE EJE 1-DATA", row_index=1)
    second = mapper.register_ids_row(assessment_id, "M1-TEST DE EJE 1-DATA", row_index=2)

    assert first is True
    assert second is True
    assert mapper.get_route(assessment_id) == ("test_de_eje", "M1")
    assert mapper.validation_counters["accepted"] == accepted_before + 2
    assert mapper.validation_counters["rejected"] == rejected_before


def test_conflict_duplicate_is_rejected_without_mutating_existing_route():
    mapper = AssessmentMapper()
    assessment_id = "0123456789abcdef01234567"

    assert mapper.register_ids_row(
        assessment_id, "M1-TEST DE EJE 1-DATA", row_index=10
    )
    accepted_before = mapper.validation_counters["accepted"]
    rejected_before = mapper.validation_counters["rejected"]

    conflict_ok = mapper.register_ids_row(
        assessment_id, "M1-EXAMEN DE EJE 1-DATA", row_index=11
    )
    assert conflict_ok is False
    assert mapper.get_route(assessment_id) == ("test_de_eje", "M1")
    assert mapper.validation_counters["accepted"] == accepted_before
    assert mapper.validation_counters["rejected"] == rejected_before + 1
    assert mapper.validation_errors["conflicting_duplicate_id"] == 1


def _build_workbook_bytes(rows):
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    from io import BytesIO

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def test_local_source_loads_routes_from_ids_xlsx(monkeypatch):
    workspace_tmp_dir = Path(__file__).resolve().parents[2] / ".tmp_testdata"
    workspace_tmp_dir.mkdir(parents=True, exist_ok=True)
    workbook_path = workspace_tmp_dir / "ids-local.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["assessment_name", "assessment_id"])
    ws.append(["M1-TEST DE EJE 1-DATA", "0123456789abcdef01234567"])
    wb.save(workbook_path)

    monkeypatch.setenv("ASSESSMENT_MAPPING_SOURCE", "local")
    monkeypatch.setenv("IDS_XLSX_LOCAL_PATH", str(workbook_path))
    monkeypatch.delenv("IDS_XLSX_GCS_PATH", raising=False)

    try:
        mapper = AssessmentMapper()
        assert mapper.mapping_source == "local"
        assert mapper.get_route("0123456789abcdef01234567") == ("test_de_eje", "M1")
    finally:
        workbook_path.unlink(missing_ok=True)


def test_gcs_source_loads_routes_from_ids_xlsx(monkeypatch):
    workbook_bytes = _build_workbook_bytes(
        [
            ("assessment_name", "assessment_id"),
            ("L30M-ENSAYO 1-DATA", "fedcba987654321001234567"),
        ]
    )
    monkeypatch.setenv("ASSESSMENT_MAPPING_SOURCE", "gcs")
    monkeypatch.setenv("IDS_XLSX_GCS_PATH", "gs://bucket/ids.xlsx")
    monkeypatch.setattr(
        AssessmentMapper,
        "_read_gcs_ids_xlsx_bytes",
        lambda self: workbook_bytes,
    )

    mapper = AssessmentMapper()
    assert mapper.mapping_source == "gcs"
    assert mapper.get_route("fedcba987654321001234567") == ("ensayo", "CL")


def test_headerless_ids_xlsx_rows_are_supported(monkeypatch):
    workbook_bytes = _build_workbook_bytes(
        [
            ("M2-EXAMEN DE EJE 3-DATA", "aaaaaaaaaaaaaaaaaaaaaaaa"),
            ("L30M-ENSAYO 4-DATA", "bbbbbbbbbbbbbbbbbbbbbbbb"),
        ]
    )
    monkeypatch.setattr(
        AssessmentMapper,
        "_read_local_ids_xlsx_bytes",
        lambda self: workbook_bytes,
    )
    monkeypatch.setenv("ASSESSMENT_MAPPING_SOURCE", "local")
    mapper = AssessmentMapper()

    assert mapper.get_route("aaaaaaaaaaaaaaaaaaaaaaaa") == ("examen_de_eje", "M2")
    assert mapper.get_route("bbbbbbbbbbbbbbbbbbbbbbbb") == ("ensayo", "CL")


def test_headered_ids_xlsx_rows_are_supported(monkeypatch):
    workbook_bytes = _build_workbook_bytes(
        [
            ("assessment_name", "assessment_id", "ignored"),
            ("F30M-TEST DE EJE 7-DATA", "cccccccccccccccccccccccc", "x"),
        ]
    )
    monkeypatch.setattr(
        AssessmentMapper,
        "_read_local_ids_xlsx_bytes",
        lambda self: workbook_bytes,
    )
    monkeypatch.setenv("ASSESSMENT_MAPPING_SOURCE", "local")
    mapper = AssessmentMapper()

    assert mapper.get_route("cccccccccccccccccccccccc") == ("test_de_eje", "F30M")
