from pathlib import Path
import json


TEMPLATE_PATH = Path("templates/examen_de_eje/body.html")
ANCHORS_PATH = Path("templates/examen_de_eje/table_anchors.json")


def _load_template() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8")


def _load_anchor_contract() -> dict:
    return json.loads(ANCHORS_PATH.read_text(encoding="utf-8"))


def test_structure_template_contains_main_sections() -> None:
    html = _load_template()

    assert "<html" in html
    assert "data-template-id=\"examen_de_eje\"" in html
    assert "data-page=\"1\"" in html
    assert "data-page=\"2\"" in html
    assert "<table" in html


def test_placeholders_include_computed_and_static_fields() -> None:
    html = _load_template()

    expected_placeholders = [
        "student_name",
        "course_name",
        "generated_at",
        "period_label",
        "report_title",
        "what_it_measures_heading",
        "important_heading",
        "states_heading",
        "how_to_use_heading",
        "closing_message",
    ]

    for placeholder in expected_placeholders:
        marker = f'data-placeholder="{placeholder}"'
        assert marker in html, f"Missing placeholder marker: {marker}"


def test_anchors_contract_matches_html_nodes() -> None:
    html = _load_template()
    contract = _load_anchor_contract()

    assert contract["template_id"] == "examen_de_eje"
    assert isinstance(contract["anchors"], list)
    assert contract["anchors"], "anchors list must not be empty"

    for anchor_spec in contract["anchors"]:
        anchor_name = anchor_spec["anchor"]
        marker = f'data-table-anchor="{anchor_name}"'
        assert marker in html, f"Missing HTML anchor node: {marker}"


def test_required_columns_schema_is_explicit_and_non_empty() -> None:
    contract = _load_anchor_contract()

    for anchor_spec in contract["anchors"]:
        required_columns = anchor_spec.get("required_columns")
        assert isinstance(required_columns, list), "required_columns must be a list"
        assert required_columns, "required_columns must not be empty"
        assert all(
            isinstance(col, str) and col.strip() for col in required_columns
        ), "required_columns values must be non-empty strings"
