"""Phase 14-02: Contract tests for get_route_full and startup summary log."""

from io import BytesIO
from pathlib import Path
from typing import Optional
import sys
import unittest.mock as mock

import pytest
from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.assessment_mapper import AssessmentMapper


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_xlsx_bytes(rows: list) -> bytes:
    """Build an in-memory .xlsx with no header row: col A = name, col B = id."""
    wb = Workbook()
    ws = wb.active
    for name, assessment_id in rows:
        ws.append([name, assessment_id])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _make_mapper_with_xlsx(rows: list) -> AssessmentMapper:
    """Build an AssessmentMapper whose ids.xlsx is mocked with the given rows."""
    xlsx_bytes = _make_xlsx_bytes(rows)
    with mock.patch.object(AssessmentMapper, "_read_ids_xlsx_bytes", return_value=xlsx_bytes):
        # Disable env-var routes so tests are isolated
        with mock.patch.dict("os.environ", {}, clear=False):
            mapper = AssessmentMapper()
    return mapper


# A valid 24-char hex ID
_VALID_ID = "a" * 24
_VALID_NAME = "M30M2-TEST DE EJE 1-DATA"

# A name that has a valid format (group + type + DATA) but a non-hex ID
_BAD_ID_NAME = "M30M2-TEST DE EJE 2-DATA"
_BAD_ID = "NOT-A-HEX-ID"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGetRouteFull:
    """get_route_full() must return a 3-tuple (report_type, assessment_type, assessment_name)."""

    def test_get_route_full_returns_triple(self):
        """Happy path: get_route_full returns (report_type, assessment_type, assessment_name)."""
        mapper = _make_mapper_with_xlsx([(_VALID_NAME, _VALID_ID)])

        result = mapper.get_route_full(_VALID_ID)

        assert result is not None, "Expected a 3-tuple, got None"
        assert len(result) == 3, f"Expected 3-tuple, got {len(result)}-tuple"
        report_type, assessment_type, assessment_name = result
        assert report_type == "test_de_eje"
        assert assessment_type == "M2"
        assert assessment_name == _VALID_NAME

    def test_get_route_full_returns_none_for_unknown_id(self):
        """Unknown ID returns None."""
        mapper = _make_mapper_with_xlsx([(_VALID_NAME, _VALID_ID)])

        result = mapper.get_route_full("b" * 24)
        assert result is None

    def test_get_route_full_returns_none_for_empty_id(self):
        """Empty string returns None."""
        mapper = _make_mapper_with_xlsx([(_VALID_NAME, _VALID_ID)])

        result = mapper.get_route_full("")
        assert result is None

    def test_get_route_full_case_insensitive(self):
        """ID lookup is case-insensitive (matches get_route behavior)."""
        mapper = _make_mapper_with_xlsx([(_VALID_NAME, _VALID_ID.upper())])

        result = mapper.get_route_full(_VALID_ID.lower())
        assert result is not None
        assert result[2] == _VALID_NAME


class TestStartupSummaryLog:
    """Startup log must always emit a warning listing rejected assessment names."""

    def test_startup_summary_lists_rejected_names(self, caplog):
        """When a row has a valid name but invalid ID, the name appears in a startup warning."""
        rows = [
            (_BAD_ID_NAME, _BAD_ID),  # valid name, invalid (non-hex) ID
        ]
        with caplog.at_level("WARNING", logger="core.assessment_mapper"):
            mapper = _make_mapper_with_xlsx(rows)

        # Find a log record that carries rejected_names in extra data
        rejected_names_logged = []
        for record in caplog.records:
            extra_rejected = getattr(record, "rejected_names", None)
            if extra_rejected is not None:
                rejected_names_logged.extend(extra_rejected)

        assert len(rejected_names_logged) > 0, (
            "Expected a warning record with 'rejected_names' in extra data, "
            f"but found none. Records: {[r.message for r in caplog.records]}"
        )
        assert _BAD_ID_NAME in rejected_names_logged, (
            f"Expected '{_BAD_ID_NAME}' in rejected_names, got: {rejected_names_logged}"
        )

    def test_startup_summary_emitted_even_when_zero_valid_rows(self, caplog):
        """Summary warning is emitted when all rows are rejected (zero accepted)."""
        rows = [
            (_BAD_ID_NAME, _BAD_ID),
        ]
        with caplog.at_level("WARNING", logger="core.assessment_mapper"):
            mapper = _make_mapper_with_xlsx(rows)

        assert mapper.validation_counters["accepted"] == 0, "Expected 0 accepted"
        # Summary warning with rejected_names must still exist
        warning_with_rejected = [
            r for r in caplog.records if getattr(r, "rejected_names", None) is not None
        ]
        assert len(warning_with_rejected) >= 1, (
            "Expected startup warning with rejected_names even when accepted=0"
        )

    def test_startup_summary_not_warning_when_all_valid(self, caplog):
        """When all rows are valid, startup summary should not be warning-level."""
        rows = [(_VALID_NAME, _VALID_ID)]
        with caplog.at_level("INFO", logger="core.assessment_mapper"):
            _make_mapper_with_xlsx(rows)

        warning_summaries = [
            r
            for r in caplog.records
            if r.levelname == "WARNING" and getattr(r, "rejected_names", None) is not None
        ]
        assert warning_summaries == []


class TestGetRouteUnchanged:
    """get_route() must still return a 2-tuple — no regression."""

    def test_get_route_unchanged(self):
        """get_route returns a 2-tuple (report_type, assessment_type), not a 3-tuple."""
        mapper = _make_mapper_with_xlsx([(_VALID_NAME, _VALID_ID)])

        result = mapper.get_route(_VALID_ID)

        assert result is not None, "Expected 2-tuple, got None"
        assert len(result) == 2, f"Expected 2-tuple, got {len(result)}-tuple"
        report_type, assessment_type = result
        assert report_type == "test_de_eje"
        assert assessment_type == "M2"

    def test_get_route_returns_none_for_unknown(self):
        """get_route returns None for unknown ID — existing contract."""
        mapper = _make_mapper_with_xlsx([(_VALID_NAME, _VALID_ID)])

        result = mapper.get_route("c" * 24)
        assert result is None
