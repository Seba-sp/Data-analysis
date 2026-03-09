from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
PLACEHOLDER_SCHEMA_PATH = ROOT_DIR / "templates" / "contracts" / "new_report_placeholders.yaml"
TEMPLATES_DIR = ROOT_DIR / "templates"

DATA_PLACEHOLDER_RE = re.compile(r'data-placeholder="([^"]+)"')
BRACE_PLACEHOLDER_RE = re.compile(r"\{\{([a-zA-Z0-9_]+)\}\}")


def _load_yaml_like(path: Path) -> dict[str, Any]:
    raw_text = path.read_text(encoding="utf-8")
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "PyYAML is required when placeholder schema is not JSON-compatible YAML."
            ) from exc
        loaded = yaml.safe_load(raw_text)
        if not isinstance(loaded, dict):
            raise ValueError(f"Expected mapping at root in schema: {path}")
        return loaded


def _normalize_report_type(report_type: str) -> str:
    if not isinstance(report_type, str) or not report_type.strip():
        raise ValueError("report_type must be a non-empty string")
    return report_type.strip()


def discover_placeholders_in_html(html: str) -> set[str]:
    from_data_attr = set(DATA_PLACEHOLDER_RE.findall(html))
    from_braces = set(BRACE_PLACEHOLDER_RE.findall(html))
    return from_data_attr | from_braces


def load_placeholder_schema() -> dict[str, dict[str, list[str]]]:
    if not PLACEHOLDER_SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Missing placeholder schema: {PLACEHOLDER_SCHEMA_PATH}")
    data = _load_yaml_like(PLACEHOLDER_SCHEMA_PATH)
    if not isinstance(data, dict):
        raise ValueError("Placeholder schema must be a mapping")

    normalized: dict[str, dict[str, list[str]]] = {}
    for report_type, report_schema in data.items():
        if not isinstance(report_schema, dict):
            raise ValueError(f"Schema for {report_type!r} must be a mapping")
        computed = report_schema.get("computed", [])
        static = report_schema.get("static", [])
        if not isinstance(computed, list) or not isinstance(static, list):
            raise ValueError(f"Schema for {report_type!r} requires list fields computed/static")
        for name in computed + static:
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"Invalid placeholder name in schema for {report_type!r}: {name!r}")
        normalized[str(report_type)] = {
            "computed": list(dict.fromkeys(computed)),
            "static": list(dict.fromkeys(static)),
        }
    return normalized


def load_report_placeholder_schema(report_type: str) -> dict[str, list[str]]:
    normalized_report_type = _normalize_report_type(report_type)
    schema = load_placeholder_schema()
    if normalized_report_type not in schema:
        raise KeyError(
            f"Unknown report type {normalized_report_type!r}. "
            f"Available: {sorted(schema.keys())}"
        )
    return schema[normalized_report_type]


def body_template_path(report_type: str) -> Path:
    return TEMPLATES_DIR / _normalize_report_type(report_type) / "body.html"


def load_body_template(report_type: str) -> str:
    path = body_template_path(report_type)
    if not path.exists():
        raise FileNotFoundError(f"Missing body template for report type {report_type!r}: {path}")
    return path.read_text(encoding="utf-8")


def validate_template_placeholders(report_type: str, body_html: str | None = None) -> dict[str, Any]:
    schema = load_report_placeholder_schema(report_type)
    allowed = set(schema["computed"]) | set(schema["static"])
    html = body_html if body_html is not None else load_body_template(report_type)
    used = discover_placeholders_in_html(html)

    unknown = sorted(used - allowed)
    unused = sorted(allowed - used)

    return {
        "report_type": _normalize_report_type(report_type),
        "used_placeholders": sorted(used),
        "allowed_placeholders": sorted(allowed),
        "unknown_placeholders": unknown,
        "unused_schema_placeholders": unused,
        "is_valid": not unknown,
    }


def assert_template_placeholders_valid(report_type: str, body_html: str | None = None) -> None:
    validation = validate_template_placeholders(report_type, body_html=body_html)
    if not validation["is_valid"]:
        unknown = ", ".join(validation["unknown_placeholders"])
        raise ValueError(
            f"Template for {report_type!r} uses unknown placeholders: {unknown}. "
            f"Update templates/contracts/new_report_placeholders.yaml."
        )


def load_table_anchor_contract(report_type: str) -> dict[str, Any]:
    report = _normalize_report_type(report_type)
    path = TEMPLATES_DIR / report / "table_anchors.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing table anchor contract for {report!r}: {path}")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    anchors = data.get("anchors", [])
    if not isinstance(anchors, list):
        raise ValueError(f"Invalid anchors contract in {path}")

    normalized_anchors: list[dict[str, Any]] = []
    for item in anchors:
        if not isinstance(item, dict):
            raise ValueError(f"Invalid anchor contract entry in {path}: {item!r}")
        anchor_name = item.get("anchor") or item.get("anchor_id")
        required_columns = item.get("required_columns", [])
        if not isinstance(anchor_name, str) or not anchor_name.strip():
            raise ValueError(f"Anchor entry missing anchor/anchor_id in {path}")
        if not isinstance(required_columns, list) or not required_columns:
            raise ValueError(f"Anchor {anchor_name!r} missing required_columns in {path}")
        normalized_item = dict(item)
        normalized_item["anchor"] = anchor_name
        normalized_item["required_columns"] = required_columns
        normalized_anchors.append(normalized_item)

    data["anchors"] = normalized_anchors
    return data


def required_columns_for_anchor(report_type: str, anchor: str) -> list[str]:
    contract = load_table_anchor_contract(report_type)
    for item in contract["anchors"]:
        if item["anchor"] == anchor:
            return item["required_columns"]
    raise KeyError(f"Unknown anchor {anchor!r} for report type {report_type!r}")

