import re
from pathlib import Path

import pytest

from reports.template_contracts import (
    load_body_template,
    load_placeholder_schema,
    load_report_placeholder_schema,
    load_table_anchor_contract,
    validate_template_placeholders,
)
from reports.template_renderer import insert_dynamic_tables, render_with_placeholders


ROOT_DIR = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = ROOT_DIR / "templates"
REPORT_TYPES = ["test_de_eje", "examen_de_eje", "ensayo"]


def _cover_path(report_type: str) -> Path:
    return TEMPLATES_DIR / report_type / "cover.html"


def test_cover_files_exist_for_all_report_types():
    for report_type in REPORT_TYPES:
        assert _cover_path(report_type).exists(), f"Missing cover.html for {report_type}"


def test_cover_files_are_single_page_insertable_page1_artifacts():
    for report_type in REPORT_TYPES:
        content = _cover_path(report_type).read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "img.folio{width:210mm;height:297mm;display:block;}" in content
        assert content.count('<img class="folio"') == 1


def test_placeholder_schema_is_loadable_and_complete_for_three_report_types():
    schema = load_placeholder_schema()
    for report_type in REPORT_TYPES:
        assert report_type in schema
        assert schema[report_type]["computed"]
        assert schema[report_type]["static"]


@pytest.mark.parametrize("report_type", REPORT_TYPES)
def test_placeholder_schema_matches_template_markers(report_type: str):
    html = load_body_template(report_type)
    validation = validate_template_placeholders(report_type, html)
    assert validation["is_valid"], (
        f"Unknown placeholders for {report_type}: {validation['unknown_placeholders']}"
    )


@pytest.mark.parametrize("report_type", REPORT_TYPES)
def test_render_with_placeholders_requires_known_schema_fields(report_type: str):
    html = load_body_template(report_type)
    with pytest.raises(ValueError):
        render_with_placeholders(
            report_type,
            html,
            computed_values={"not_in_schema": "x"},
            static_values={},
        )


@pytest.mark.parametrize("report_type", REPORT_TYPES)
def test_render_with_placeholders_fills_template_from_computed_and_static_payload(report_type: str):
    html = load_body_template(report_type)
    schema = load_report_placeholder_schema(report_type)
    computed_values = {name: f"computed_{name}" for name in schema["computed"]}
    static_values = {name: f"static_{name}" for name in schema["static"]}

    rendered = render_with_placeholders(
        report_type=report_type,
        body_html=html,
        computed_values=computed_values,
        static_values=static_values,
    )

    expected_value = next(iter(computed_values.values()))
    assert expected_value in rendered
    assert "{{" not in rendered


@pytest.mark.parametrize("report_type", REPORT_TYPES)
def test_anchor_contract_entries_are_present_in_body(report_type: str):
    html = load_body_template(report_type)
    contract = load_table_anchor_contract(report_type)
    for anchor in contract["anchors"]:
        anchor_name = anchor["anchor"]
        assert f'data-table-anchor="{anchor_name}"' in html


def test_table_insertion_for_test_de_eje_inserts_rows_at_unit_anchor():
    html = load_body_template("test_de_eje")
    rendered = insert_dynamic_tables(
        "test_de_eje",
        html,
        {
            "unit_1_activity_status": [
                {"activity": "Leccion 1", "action": "pending"},
                {"activity": "Guia 1", "action": "required"},
            ]
        },
    )
    assert "Leccion 1" in rendered
    assert "required" in rendered
    assert re.search(r'data-table-anchor="unit_1_activity_status".*Leccion 1', rendered, re.DOTALL)


def test_table_insertion_for_examen_de_eje_inserts_rows_at_tbody_anchor():
    html = load_body_template("examen_de_eje")
    rendered = insert_dynamic_tables(
        "examen_de_eje",
        html,
        {
            "unit_status_rows": [
                {"unidad": "Unidad A", "estado": "Riesgo", "recomendacion": "RR"},
                {"unidad": "Unidad B", "estado": "Solido", "recomendacion": "RS"},
            ]
        },
    )
    assert "Unidad A" in rendered
    assert "RR" in rendered
    assert re.search(r'data-table-anchor="unit_status_rows".*Unidad A', rendered, re.DOTALL)


def test_table_insertion_for_ensayo_inserts_rows_at_anchor():
    html = load_body_template("ensayo")
    rendered = insert_dynamic_tables(
        "ensayo",
        html,
        {
            "ensayo_dominio_por_eje": [
                {
                    "eje": "Eje 1",
                    "correctas_totales": "12/20",
                    "porcentaje_dominio": "60%",
                }
            ]
        },
    )
    assert "Eje 1" in rendered
    assert "60%" in rendered
    assert re.search(r'data-table-anchor="ensayo_dominio_por_eje".*Eje 1', rendered, re.DOTALL)


@pytest.mark.parametrize(
    "report_type,anchor,payload",
    [
        ("test_de_eje", "unit_1_activity_status", [{"activity": "X"}]),
        ("examen_de_eje", "unit_status_rows", [{"unidad": "X", "estado": "Riesgo"}]),
        ("ensayo", "ensayo_dominio_por_eje", [{"eje": "Eje 1"}]),
    ],
)
def test_table_insertion_fails_when_required_columns_are_missing(
    report_type: str, anchor: str, payload: list[dict]
):
    html = load_body_template(report_type)
    with pytest.raises(ValueError):
        insert_dynamic_tables(report_type, html, {anchor: payload})

