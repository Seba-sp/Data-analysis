from __future__ import annotations

import html
import re
from typing import Any

from reports.template_contracts import (
    discover_placeholders_in_html,
    load_report_placeholder_schema,
    load_table_anchor_contract,
)


BRACE_PLACEHOLDER_RE = re.compile(r"\{\{([a-zA-Z0-9_]+)\}\}")


def _ensure_dict(name: str, value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be a dictionary")
    return value


def _escape_text(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _replace_brace_placeholders(content: str, values: dict[str, Any]) -> str:
    def _repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            return match.group(0)
        return _escape_text(values[key])

    return BRACE_PLACEHOLDER_RE.sub(_repl, content)


def _replace_data_placeholder_elements(content: str, values: dict[str, Any]) -> str:
    result = content
    for key, value in values.items():
        escaped_key = re.escape(key)
        pattern = re.compile(
            rf"(<(?P<tag>[a-zA-Z0-9]+)(?P<attrs>[^>]*\sdata-placeholder=\"{escaped_key}\"[^>]*)>)"
            rf"(?P<inner>.*?)"
            rf"(</(?P=tag)>)",
            re.DOTALL,
        )
        def _repl(match: re.Match[str]) -> str:
            inner = match.group("inner")
            # Keep structural wrapper nodes intact (e.g. page sections).
            if "<" in inner and ">" in inner:
                return match.group(0)
            return f"{match.group(1)}{_escape_text(value)}{match.group(5)}"

        result = pattern.sub(_repl, result)
    return result


def render_with_placeholders(
    report_type: str,
    body_html: str,
    computed_values: dict[str, Any] | None,
    static_values: dict[str, Any] | None,
) -> str:
    schema = load_report_placeholder_schema(report_type)
    computed_values = _ensure_dict("computed_values", computed_values)
    static_values = _ensure_dict("static_values", static_values)

    computed_allowed = set(schema["computed"])
    static_allowed = set(schema["static"])
    allowed = computed_allowed | static_allowed

    unknown_inputs = sorted((set(computed_values) | set(static_values)) - allowed)
    if unknown_inputs:
        raise ValueError(
            f"Unknown placeholders for report_type={report_type!r}: {unknown_inputs}"
        )

    used = discover_placeholders_in_html(body_html)
    used_computed = used & computed_allowed
    used_static = used & static_allowed

    missing_computed = sorted(k for k in used_computed if k not in computed_values)
    missing_static = sorted(k for k in used_static if k not in static_values)
    if missing_computed or missing_static:
        raise ValueError(
            f"Missing placeholder values for report_type={report_type!r}. "
            f"missing_computed={missing_computed}, missing_static={missing_static}"
        )

    rendered = body_html
    all_values = {**static_values, **computed_values}
    rendered = _replace_brace_placeholders(rendered, all_values)
    rendered = _replace_data_placeholder_elements(rendered, all_values)
    return rendered


def _validate_rows(anchor: str, required_columns: list[str], rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise TypeError(f"Rows for anchor {anchor!r} must be a list of dictionaries")
    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise TypeError(f"Row {index} for anchor {anchor!r} must be a dictionary")
        missing = [column for column in required_columns if column not in row]
        if missing:
            raise ValueError(
                f"Row {index} for anchor {anchor!r} missing required columns: {missing}"
            )
        normalized.append(row)
    return normalized


def _render_table_rows(required_columns: list[str], rows: list[dict[str, Any]]) -> str:
    row_html: list[str] = []
    for row in rows:
        cells: list[str] = []
        for column in required_columns:
            value = row.get(column)
            if isinstance(value, list):
                value = ", ".join(str(item) for item in value)
            cells.append(f"<td>{_escape_text(value)}</td>")
        row_html.append("<tr>" + "".join(cells) + "</tr>")
    return "".join(row_html)


def _render_full_table(required_columns: list[str], rows: list[dict[str, Any]]) -> str:
    headers = "".join(f"<th>{_escape_text(column)}</th>" for column in required_columns)
    body_rows = _render_table_rows(required_columns, rows)
    return (
        "<table data-generated=\"dynamic-table\">"
        "<thead><tr>"
        f"{headers}"
        "</tr></thead>"
        f"<tbody>{body_rows}</tbody>"
        "</table>"
    )


def insert_dynamic_tables(
    report_type: str,
    body_html: str,
    table_payloads: dict[str, list[dict[str, Any]]],
) -> str:
    if not isinstance(table_payloads, dict):
        raise TypeError("table_payloads must be a dictionary mapping anchor -> list[dict]")

    contract = load_table_anchor_contract(report_type)
    contract_by_anchor = {item["anchor"]: item for item in contract["anchors"]}
    unknown_anchors = sorted(set(table_payloads) - set(contract_by_anchor))
    if unknown_anchors:
        raise ValueError(
            f"Unknown table anchors for report_type={report_type!r}: {unknown_anchors}"
        )

    rendered = body_html
    for anchor, rows_input in table_payloads.items():
        required_columns = contract_by_anchor[anchor]["required_columns"]
        rows = _validate_rows(anchor, required_columns, rows_input)

        escaped_anchor = re.escape(anchor)
        pattern = re.compile(
            rf"(<(?P<tag>[a-zA-Z0-9]+)(?P<attrs>[^>]*\sdata-table-anchor=\"{escaped_anchor}\"[^>]*)>)"
            rf"(?P<inner>.*?)"
            rf"(</(?P=tag)>)",
            re.DOTALL,
        )
        match = pattern.search(rendered)
        if not match:
            raise ValueError(
                f"Anchor {anchor!r} was not found in body_html for report_type={report_type!r}"
            )

        tag_name = match.group("tag").lower()
        if tag_name == "tbody":
            replacement_inner = _render_table_rows(required_columns, rows)
        else:
            replacement_inner = _render_full_table(required_columns, rows)

        replacement = f"{match.group(1)}{replacement_inner}{match.group(5)}"
        rendered = rendered[: match.start()] + replacement + rendered[match.end() :]

    return rendered
