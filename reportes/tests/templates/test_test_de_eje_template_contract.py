import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
BODY_HTML_PATH = ROOT_DIR / "templates" / "test_de_eje" / "body.html"
ANCHORS_JSON_PATH = ROOT_DIR / "templates" / "test_de_eje" / "table_anchors.json"


def _load_body_html() -> str:
    assert BODY_HTML_PATH.exists(), f"Missing template: {BODY_HTML_PATH}"
    return BODY_HTML_PATH.read_text(encoding="utf-8")


def _load_anchors_json() -> dict:
    assert ANCHORS_JSON_PATH.exists(), f"Missing contract file: {ANCHORS_JSON_PATH}"
    return json.loads(ANCHORS_JSON_PATH.read_text(encoding="utf-8"))


def test_structure_body_html_is_parseable_contract():
    html = _load_body_html()
    assert "<!DOCTYPE html>" in html
    assert "<html" in html and "</html>" in html
    assert "<body" in html and "</body>" in html
    assert "data-template=\"test_de_eje_body\"" in html
    assert "page-break" in html


def test_placeholders_required_static_and_computed_fields_exist():
    html = _load_body_html()
    required_placeholders = [
        "report_title",
        "estimated_total_hours",
        "unit_1_name",
        "unit_1_initial_pd",
        "unit_1_activities_table",
        "unit_2_name",
        "unit_2_initial_pd",
        "unit_2_activities_table",
        "unit_3_name",
        "unit_3_initial_pd",
        "unit_3_activities_table",
    ]
    for name in required_placeholders:
        assert f'data-placeholder="{name}"' in html


def test_anchors_defined_in_json_are_present_in_html():
    html = _load_body_html()
    anchors = _load_anchors_json()["anchors"]
    assert anchors, "Expected at least one anchor definition."
    for anchor in anchors:
        anchor_id = anchor["anchor_id"]
        assert f'data-table-anchor="{anchor_id}"' in html


def test_required_columns_and_sample_payload_contract():
    anchors = _load_anchors_json()["anchors"]
    for anchor in anchors:
        required_columns = anchor.get("required_columns")
        sample_payload = anchor.get("sample_payload")
        assert required_columns == ["activity", "action"]
        assert isinstance(sample_payload, list) and sample_payload
        for row in sample_payload:
            assert isinstance(row, dict)
            for required_column in required_columns:
                assert required_column in row
