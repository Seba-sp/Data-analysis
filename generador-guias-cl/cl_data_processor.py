"""
CL data processing utilities: file pairing, Excel normalization, and filtering.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
from unidecode import unidecode

from config import (
    CL_COLUMNS,
    CL_COLUMN_ALIASES,
    CL_FILTER_ORDER_INDEPENDENT,
    CL_FILTER_ORDER_TOP_DOWN,
    CL_REQUIRED_COLUMNS,
    CL_UNIFORM_COLUMNS,
    INPUT_DIR,
    PROCESSED_DIR,
    ensure_directories,
)


@dataclass
class CLTextSet:
    """Represents a text bundle (docx + metadata excel)."""

    codigo_texto: str
    docx_path: Path
    excel_path: Path


def normalize_text(value: object) -> str:
    """Normalize text for case/accent-insensitive filtering."""
    if value is None:
        return ""
    text = str(value).strip()
    return unidecode(text).lower()


def _rename_alias_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename known accented/variant aliases to canonical CL column names."""
    renamed = df.copy()

    # Build normalized lookup for canonical columns and aliases.
    normalized_lookup: Dict[str, str] = {}

    for canonical in CL_REQUIRED_COLUMNS:
        normalized_lookup[normalize_text(canonical)] = canonical

    for canonical, aliases in CL_COLUMN_ALIASES.items():
        normalized_lookup[normalize_text(canonical)] = canonical
        for alias in aliases:
            normalized_lookup[normalize_text(alias)] = canonical

    rename_map: Dict[str, str] = {}
    for original_col in renamed.columns:
        normalized = normalize_text(original_col)
        if normalized in normalized_lookup:
            rename_map[original_col] = normalized_lookup[normalized]

    return renamed.rename(columns=rename_map)


def list_cl_input_sets(input_dir: Path = INPUT_DIR) -> List[CLTextSet]:
    """Find CL input pairs by Codigo Texto prefix in file names."""
    files = [p for p in input_dir.glob("*") if p.is_file() and not p.name.startswith("~$")]

    docx_by_code: Dict[str, Path] = {}
    xlsx_by_code: Dict[str, Path] = {}

    for file_path in files:
        suffix = file_path.suffix.lower()
        stem = file_path.stem
        code = stem.split("-")[0].strip().upper()

        if not code.startswith("C") or len(code) < 4:
            continue

        if suffix == ".docx":
            docx_by_code[code] = file_path
        elif suffix in [".xlsx", ".xls"]:
            xlsx_by_code[code] = file_path

    pairs: List[CLTextSet] = []
    for code in sorted(set(docx_by_code.keys()) & set(xlsx_by_code.keys())):
        pairs.append(CLTextSet(code, docx_by_code[code], xlsx_by_code[code]))

    return pairs


def read_and_validate_cl_excel(excel_path: Path) -> Tuple[pd.DataFrame, List[str]]:
    """Read CL excel and validate required columns and basic rules."""
    issues: List[str] = []

    try:
        df = pd.read_excel(excel_path)
    except Exception as exc:
        return pd.DataFrame(), [f"No se pudo leer {excel_path.name}: {exc}"]

    df = _rename_alias_columns(df)

    missing = [col for col in CL_REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        issues.append(f"Columnas faltantes en {excel_path.name}: {', '.join(missing)}")
        return pd.DataFrame(), issues

    for col in CL_REQUIRED_COLUMNS:
        empty_count = int(df[col].isna().sum()) + int((df[col].astype(str).str.strip() == "").sum())
        if empty_count > 0:
            issues.append(f"{excel_path.name} -> {col}: {empty_count} vacios")

    # Basic sorting safety by question number
    df[CL_COLUMNS["numero_pregunta"]] = pd.to_numeric(df[CL_COLUMNS["numero_pregunta"]], errors="coerce")
    if df[CL_COLUMNS["numero_pregunta"]].isna().any():
        issues.append(f"{excel_path.name}: hay valores no numericos en '{CL_COLUMNS['numero_pregunta']}'")

    df = df.dropna(subset=[CL_COLUMNS["numero_pregunta"]]).copy()
    df[CL_COLUMNS["numero_pregunta"]] = df[CL_COLUMNS["numero_pregunta"]].astype(int)
    df = df.sort_values(CL_COLUMNS["numero_pregunta"]).reset_index(drop=True)

    return df, issues


def build_catalog_dataframe(text_sets: List[CLTextSet]) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame], List[str]]:
    """Build text-level catalog and keep question-level dataframes by Codigo Texto."""
    records: List[Dict[str, object]] = []
    by_codigo: Dict[str, pd.DataFrame] = {}
    issues: List[str] = []

    for text_set in text_sets:
        df, validation_issues = read_and_validate_cl_excel(text_set.excel_path)
        issues.extend(validation_issues)

        if df.empty:
            continue

        by_codigo[text_set.codigo_texto] = df

        first_row = df.iloc[0]
        records.append(
            {
                "Codigo Texto": text_set.codigo_texto,
                "docx_path": str(text_set.docx_path),
                "excel_path": str(text_set.excel_path),
                CL_COLUMNS["tipo_texto"]: first_row[CL_COLUMNS["tipo_texto"]],
                CL_COLUMNS["subgenero"]: first_row[CL_COLUMNS["subgenero"]],
                CL_COLUMNS["titulo_texto"]: first_row[CL_COLUMNS["titulo_texto"]],
                CL_COLUMNS["descripcion_texto"]: first_row[CL_COLUMNS["descripcion_texto"]],
                CL_COLUMNS["programa"]: first_row[CL_COLUMNS["programa"]],
                CL_COLUMNS["n_preguntas"]: int(len(df)),
                # For independent filters summary
                "Habilidades": ", ".join(sorted(df[CL_COLUMNS["habilidad"]].astype(str).unique().tolist())),
                "Tareas": ", ".join(sorted(df[CL_COLUMNS["tarea_lectora"]].astype(str).unique().tolist())),
            }
        )

    catalog_df = pd.DataFrame(records)
    if not catalog_df.empty:
        catalog_df = catalog_df.sort_values([CL_COLUMNS["tipo_texto"], CL_COLUMNS["subgenero"], CL_COLUMNS["titulo_texto"]]).reset_index(drop=True)

    return catalog_df, by_codigo, issues


def apply_top_down_filters(df: pd.DataFrame, filters: Dict[str, str]) -> pd.DataFrame:
    """Apply ordered top-down + independent filters to text-level dataframe."""
    filtered = df.copy()

    # Top-down filters
    for col in CL_FILTER_ORDER_TOP_DOWN:
        value = filters.get(col)
        if not value:
            continue

        if col == CL_COLUMNS["descripcion_texto"]:
            target = normalize_text(value)
            filtered = filtered[filtered[col].astype(str).apply(normalize_text).str.contains(target, na=False)]
        else:
            filtered = filtered[filtered[col].astype(str) == str(value)]

    # Independent filters, based on question-level aggregations present in catalog
    for col in CL_FILTER_ORDER_INDEPENDENT:
        value = filters.get(col)
        if not value:
            continue

        if col == CL_COLUMNS["programa"]:
            filtered = filtered[filtered[col].astype(str) == str(value)]
        elif col == CL_COLUMNS["habilidad"]:
            filtered = filtered["Habilidades"].astype(str).str.contains(str(value), na=False)
        elif col == CL_COLUMNS["tarea_lectora"]:
            filtered = filtered["Tareas"].astype(str).str.contains(str(value), na=False)

    return filtered


def validate_uniform_columns(df: pd.DataFrame, excel_name: str) -> List[str]:
    """Check that columns expected to be uniform have a single value across all rows."""
    issues: List[str] = []
    for col in CL_UNIFORM_COLUMNS:
        if col not in df.columns:
            continue
        unique_vals = df[col].dropna().astype(str).str.strip().unique()
        unique_vals = [v for v in unique_vals if v != ""]
        if len(unique_vals) > 1:
            issues.append(
                f"{excel_name} -> {col}: se esperaba un valor uniforme pero se encontraron {len(unique_vals)}: {unique_vals[:5]}"
            )
    return issues


def _is_already_processed(text_set: CLTextSet) -> bool:
    """Check if both files for this set already exist in the processed folder."""
    docx_dest = PROCESSED_DIR / text_set.docx_path.name
    xlsx_dest = PROCESSED_DIR / text_set.excel_path.name
    return docx_dest.exists() and xlsx_dest.exists()


def process_cl_set(text_set: CLTextSet) -> Tuple[bool, List[str]]:
    """Validate a single CL set and copy to processed folder if valid.

    Returns (success, issues_list).
    """
    from cl_word_builder import parse_cl_source_docx

    ensure_directories()
    issues: List[str] = []

    # Check if already processed
    if _is_already_processed(text_set):
        return False, [f"{text_set.codigo_texto}: ya fue procesado (archivos existen en output/processed/)"]

    # Step 1: validate Excel
    df, validation_issues = read_and_validate_cl_excel(text_set.excel_path)
    issues.extend(validation_issues)

    if df.empty:
        return False, issues

    # Step 2: validate uniform columns
    uniform_issues = validate_uniform_columns(df, text_set.excel_path.name)
    if uniform_issues:
        issues.extend(uniform_issues)
        return False, issues

    # Step 3: validate Word page count matches Excel question count
    expected_questions = len(df)
    try:
        parse_cl_source_docx(text_set.docx_path, expected_questions=expected_questions)
    except ValueError as exc:
        issues.append(str(exc))
        return False, issues

    # Step 4: copy files to processed folder
    shutil.copy2(text_set.docx_path, PROCESSED_DIR / text_set.docx_path.name)
    shutil.copy2(text_set.excel_path, PROCESSED_DIR / text_set.excel_path.name)

    return True, issues


def process_from_list(list_path: Path | None = None) -> List[Dict[str, object]]:
    """Process sets listed in procesar.txt (one Codigo Texto prefix per line)."""
    if list_path is None:
        list_path = INPUT_DIR / "procesar.txt"

    if not list_path.exists():
        print(f"Archivo no encontrado: {list_path}")
        return []

    lines = [line.strip().upper() for line in list_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        print("procesar.txt esta vacio.")
        return []

    available = {s.codigo_texto: s for s in list_cl_input_sets()}
    results: List[Dict[str, object]] = []

    for code in lines:
        if code not in available:
            print(f"[WARNING] {code}: no se encontro par docx+xlsx en input/")
            results.append({"code": code, "success": False, "issues": ["Par no encontrado en input/"]})
            continue

        success, issues = process_cl_set(available[code])
        results.append({"code": code, "success": success, "issues": issues})

    return results


def process_all_sets() -> List[Dict[str, object]]:
    """Process all available CL sets in input/."""
    sets = list_cl_input_sets()
    results: List[Dict[str, object]] = []

    for text_set in sets:
        success, issues = process_cl_set(text_set)
        results.append({"code": text_set.codigo_texto, "success": success, "issues": issues})

    return results
