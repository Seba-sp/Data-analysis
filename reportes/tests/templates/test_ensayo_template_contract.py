import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

TEMPLATE_PATH = Path("templates/ensayo/body.html")
ANCHORS_PATH = Path("templates/ensayo/table_anchors.json")


class StrictHTMLParser(HTMLParser):
    def error(self, message):
        raise AssertionError(message)


def _read_template() -> str:
    assert TEMPLATE_PATH.exists(), "Expected ensayo body template to exist"
    return TEMPLATE_PATH.read_text(encoding="utf-8")


def _read_anchor_contract() -> dict:
    assert ANCHORS_PATH.exists(), "Expected ensayo table anchor contract to exist"
    return json.loads(ANCHORS_PATH.read_text(encoding="utf-8-sig"))


def _extract_values(pattern: str, html: str) -> set[str]:
    return set(re.findall(pattern, html))


@pytest.mark.template_contract
def test_structure_template_is_parseable_html():
    html = _read_template()
    parser = StrictHTMLParser()
    parser.feed(html)
    parser.close()


@pytest.mark.template_contract
def test_structure_docx_sections_present():
    html = _read_template()

    expected_snippets = [
        "Resultados Ensayo",
        "Puntaje:",
        "Tabla de dominio por eje tipo:",
        "Reporte Rapido",
        "Correctas totales (incluye piloto)",
    ]
    for snippet in expected_snippets:
        assert snippet in html


@pytest.mark.template_contract
def test_structure_no_base64_heavy_assets_in_body_template():
    html = _read_template()
    assert "data:image/" not in html


@pytest.mark.template_contract
def test_placeholders_required_markers_exist_for_computed_and_static_content():
    html = _read_template()
    placeholders = _extract_values(r'data-placeholder="([^"]+)"', html)

    required_placeholders = {
        "overall_score",
        "correct_total_with_pilot",
        "correct_total_without_pilot",
        "domain_table_title",
        "quick_report_title",
        "pilot_note",
    }

    missing = required_placeholders - placeholders
    assert not missing, f"Missing placeholder markers: {sorted(missing)}"


@pytest.mark.template_contract
def test_anchors_html_and_json_contract_are_consistent():
    html = _read_template()
    contract = _read_anchor_contract()

    html_anchors = _extract_values(r'data-table-anchor="([^"]+)"', html)
    json_anchors = {entry["anchor"] for entry in contract["anchors"]}

    assert html_anchors == json_anchors


@pytest.mark.template_contract
def test_required_columns_and_sample_payload_are_complete():
    contract = _read_anchor_contract()

    for entry in contract["anchors"]:
        required_columns = entry.get("required_columns", [])
        sample_payload = entry.get("sample_payload", [])

        assert required_columns, f"Anchor {entry['anchor']} has no required_columns"
        assert sample_payload, f"Anchor {entry['anchor']} has no sample_payload"

        for row in sample_payload:
            missing_columns = [column for column in required_columns if column not in row]
            assert not missing_columns, (
                f"Anchor {entry['anchor']} sample payload missing columns: "
                f"{missing_columns}"
            )
