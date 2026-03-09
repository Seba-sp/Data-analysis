import json
import re
from pathlib import Path


ROOT = Path(".")
CHECKLIST_PATH = (
    ROOT
    / ".planning"
    / "phases"
    / "08-template-and-cover-foundation"
    / "08-DOCX-HTML-COMPLIANCE.md"
)
TEMPLATE_PATHS = {
    "test_de_eje": ROOT / "templates" / "test_de_eje" / "body.html",
    "examen_de_eje": ROOT / "templates" / "examen_de_eje" / "body.html",
    "ensayo": ROOT / "templates" / "ensayo" / "body.html",
}
ANCHOR_PATHS = {
    "test_de_eje": ROOT / "templates" / "test_de_eje" / "table_anchors.json",
    "examen_de_eje": ROOT / "templates" / "examen_de_eje" / "table_anchors.json",
    "ensayo": ROOT / "templates" / "ensayo" / "table_anchors.json",
}


def _read_checklist() -> str:
    assert CHECKLIST_PATH.exists(), f"Missing checklist artifact: {CHECKLIST_PATH}"
    return CHECKLIST_PATH.read_text(encoding="utf-8")


def _read_template(template_key: str) -> str:
    path = TEMPLATE_PATHS[template_key]
    assert path.exists(), f"Missing template file: {path}"
    return path.read_text(encoding="utf-8")


def _load_anchor_contract(template_key: str) -> dict:
    path = ANCHOR_PATHS[template_key]
    assert path.exists(), f"Missing anchor contract: {path}"
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _extract_style_block(html: str) -> str:
    match = re.search(r"<style>(.*?)</style>", html, flags=re.S)
    assert match, "Expected <style> block in template HTML."
    return match.group(1)


def _extract_selector_block(css: str, selector: str) -> str:
    if selector.startswith("re:"):
        selector_pattern = selector[3:]
        pattern = rf"{selector_pattern}\s*\{{(.*?)\}}"
    else:
        pattern = rf"{re.escape(selector)}\s*\{{(.*?)\}}"
    match = re.search(pattern, css, flags=re.S | re.M)
    assert match, f"Missing CSS selector block: {selector}"
    return match.group(1)


def _assert_css_property(css_block: str, prop: str, expected: str, key: str) -> None:
    pattern = rf"{re.escape(prop)}\s*:\s*{re.escape(expected)}\s*;"
    assert re.search(pattern, css_block), (
        f"[{key}] Expected `{prop}: {expected};` in selector block.\n"
        f"Selector block:\n{css_block}"
    )


def test_checklist_file_exists_and_is_nonempty() -> None:
    content = _read_checklist()
    assert "Phase 8 DOCX to HTML Compliance Checklist" in content
    assert len(content.strip()) > 200


def test_checklist_covers_all_three_templates() -> None:
    content = _read_checklist()
    assert "### test_de_eje" in content
    assert "### examen_de_eje" in content
    assert "### ensayo" in content


def test_checklist_contains_status_rows_and_key_coverage() -> None:
    content = _read_checklist()
    assert "| Key | Dimension | Status | DOCX Evidence | HTML Evidence | Notes |" in content
    for key in [
        "TDE-TYPO-01",
        "TDE-HTML-01",
        "EXA-TYPO-01",
        "EXA-HTML-01",
        "ENS-TYPO-01",
        "ENS-HTML-01",
    ]:
        assert key in content, f"Missing checklist key: {key}"
    assert "| FAIL |" not in content, "Checklist still has unresolved FAIL rows."


def test_css_font_stack_and_base_size_are_docx_aligned() -> None:
    expected_stack = '"Times New Roman", "DejaVu Serif", serif'
    for template_key in TEMPLATE_PATHS:
        css = _extract_style_block(_read_template(template_key))
        body_block = _extract_selector_block(css, "body")
        _assert_css_property(body_block, "font-family", expected_stack, f"{template_key}-FONT")
        _assert_css_property(body_block, "font-size", "12pt", f"{template_key}-SIZE")
        _assert_css_property(body_block, "line-height", "1.2", f"{template_key}-SPACE")


def test_css_heading_size_bands_are_within_expected_contract() -> None:
    test_de_eje_css = _extract_style_block(_read_template("test_de_eje"))
    _assert_css_property(
        _extract_selector_block(test_de_eje_css, ".unit-title"),
        "font-size",
        "14pt",
        "TDE-SIZE-01",
    )

    examen_css = _extract_style_block(_read_template("examen_de_eje"))
    _assert_css_property(_extract_selector_block(examen_css, r"re:^\s*h1\s*"), "font-size", "16pt", "EXA-SIZE-01")
    _assert_css_property(_extract_selector_block(examen_css, r"re:^\s*h2\s*"), "font-size", "14pt", "EXA-SIZE-01")
    _assert_css_property(_extract_selector_block(examen_css, r"re:^\s*h3\s*"), "font-size", "12pt", "EXA-SIZE-01")

    ensayo_css = _extract_style_block(_read_template("ensayo"))
    _assert_css_property(
        _extract_selector_block(ensayo_css, ".section-title"),
        "font-size",
        "14pt",
        "ENS-SIZE-01",
    )
    _assert_css_property(
        _extract_selector_block(ensayo_css, r"re:th,\s*td"),
        "font-size",
        "11pt",
        "ENS-SIZE-01",
    )


def test_css_border_and_spacing_contracts_remain_in_bounds() -> None:
    test_de_eje_css = _extract_style_block(_read_template("test_de_eje"))
    _assert_css_property(_extract_selector_block(test_de_eje_css, ".legend"), "border", "1px solid #0f2435", "TDE-BORDER-01")

    examen_css = _extract_style_block(_read_template("examen_de_eje"))
    _assert_css_property(_extract_selector_block(examen_css, ".table-shell"), "border", "1px solid #111827", "EXA-BORDER-01")

    ensayo_css = _extract_style_block(_read_template("ensayo"))
    _assert_css_property(
        _extract_selector_block(ensayo_css, r"re:th,\s*td"),
        "border",
        "1px solid #111827",
        "ENS-BORDER-01",
    )


def test_utf8_character_integrity_no_mojibake_tokens() -> None:
    mojibake_tokens = ["Ã", "â€", "âœ", "â–", "�"]
    for template_key in TEMPLATE_PATHS:
        html = _read_template(template_key)
        for token in mojibake_tokens:
            assert token not in html, f"[{template_key}-HTML] Found mojibake token: {token}"


def test_placeholder_and_anchor_contracts_preserved_after_fidelity_edits() -> None:
    for template_key, template_path in TEMPLATE_PATHS.items():
        html = _read_template(template_key)
        placeholders = set(re.findall(r'data-placeholder="([^"]+)"', html))
        assert placeholders, f"[{template_key}] No data-placeholder markers found."

        contract = _load_anchor_contract(template_key)
        for anchor in contract["anchors"]:
            anchor_id = anchor.get("anchor_id") or anchor.get("anchor")
            marker = f'data-table-anchor="{anchor_id}"'
            assert marker in html, f"[{template_key}] Missing anchor marker: {marker} in {template_path}"
