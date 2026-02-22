"""
CL master dataset and usage tracking utilities.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Tuple

import pandas as pd

from cl_data_processor import list_cl_input_sets, read_and_validate_cl_excel
from config import (
    BASE_DIR,
    CL_COLUMNS,
    CL_MASTER_PATH,
    CL_TRACKING_COLUMNS,
    INPUT_DIR,
    PROCESSED_DIR,
    USAGE_TRACKING_BASE_COLUMNS,
    ensure_directories,
    get_usage_column_names,
)


def _ensure_master_tracking_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure base usage tracking columns exist in the DataFrame."""
    out = df.copy()
    for column in USAGE_TRACKING_BASE_COLUMNS:
        if column not in out.columns:
            out[column] = None

    numero_usos_col = CL_TRACKING_COLUMNS["numero_usos"]
    out[numero_usos_col] = pd.to_numeric(
        out[numero_usos_col], errors="coerce"
    ).fillna(0).astype(int)
    return out


def build_cl_master_from_input(source_dir=None) -> Tuple[pd.DataFrame, List[str], "Path"]:
    """Build (overwrite) CL master from all valid Cxxx pairs in source_dir.

    Defaults to PROCESSED_DIR so the master is built from validated files.
    """
    if source_dir is None:
        source_dir = PROCESSED_DIR
    ensure_directories()

    sets = list_cl_input_sets(source_dir)
    issues: List[str] = []
    rows: List[pd.DataFrame] = []

    for set_item in sets:
        df, validation_issues = read_and_validate_cl_excel(set_item.excel_path)
        issues.extend(validation_issues)
        if df.empty:
            continue

        # keep source paths in master (relative to project root)
        df = df.copy()
        df["docx_path"] = str(set_item.docx_path.relative_to(BASE_DIR))
        df["excel_path"] = str(set_item.excel_path.relative_to(BASE_DIR))
        df["Archivo origen"] = set_item.excel_path.name
        df[CL_COLUMNS["codigo_texto"]] = str(set_item.codigo_texto)
        rows.append(df)

    if rows:
        master = pd.concat(rows, ignore_index=True)
        master = master.drop_duplicates(
            subset=[CL_COLUMNS["codigo_texto"], CL_COLUMNS["numero_pregunta"]], keep="first"
        )
        master = master.sort_values([CL_COLUMNS["codigo_texto"], CL_COLUMNS["numero_pregunta"]]).reset_index(drop=True)
    else:
        master = pd.DataFrame()

    master = _ensure_master_tracking_columns(master)
    master.to_excel(CL_MASTER_PATH, index=False)
    return master, issues, CL_MASTER_PATH


def build_cl_master_full_reset() -> Tuple[pd.DataFrame, List[str], "Path"]:
    """Reset and rebuild the master from all files in output/processed/."""
    return build_cl_master_from_input(source_dir=PROCESSED_DIR)


def build_cl_master_incremental() -> Tuple[pd.DataFrame, List[str], "Path"]:
    """Add only new processed files to the existing master."""
    ensure_directories()

    existing_master = load_cl_master()

    # Determine which source files are already in the master
    already_in_master: set[str] = set()
    if not existing_master.empty and "Archivo origen" in existing_master.columns:
        already_in_master = set(existing_master["Archivo origen"].dropna().astype(str).unique())

    sets = list_cl_input_sets(PROCESSED_DIR)
    new_sets = [s for s in sets if s.excel_path.name not in already_in_master]

    if not new_sets:
        return existing_master, ["No hay archivos nuevos para agregar al master."], CL_MASTER_PATH

    issues: List[str] = []
    new_rows: List[pd.DataFrame] = []

    for set_item in new_sets:
        df, validation_issues = read_and_validate_cl_excel(set_item.excel_path)
        issues.extend(validation_issues)
        if df.empty:
            continue

        df = df.copy()
        df["docx_path"] = str(set_item.docx_path.relative_to(BASE_DIR))
        df["excel_path"] = str(set_item.excel_path.relative_to(BASE_DIR))
        df["Archivo origen"] = set_item.excel_path.name
        df[CL_COLUMNS["codigo_texto"]] = str(set_item.codigo_texto)
        new_rows.append(df)

    if not new_rows:
        return existing_master, issues, CL_MASTER_PATH

    new_data = pd.concat(new_rows, ignore_index=True)

    if existing_master.empty:
        master = new_data
    else:
        # Align columns
        for col in existing_master.columns:
            if col not in new_data.columns:
                new_data[col] = None
        for col in new_data.columns:
            if col not in existing_master.columns:
                existing_master[col] = None
        master = pd.concat([existing_master, new_data], ignore_index=True)

    master = master.drop_duplicates(
        subset=[CL_COLUMNS["codigo_texto"], CL_COLUMNS["numero_pregunta"]], keep="first"
    )
    master = master.sort_values([CL_COLUMNS["codigo_texto"], CL_COLUMNS["numero_pregunta"]]).reset_index(drop=True)
    master = _ensure_master_tracking_columns(master)
    master.to_excel(CL_MASTER_PATH, index=False)

    return master, issues, CL_MASTER_PATH


def load_cl_master() -> pd.DataFrame:
    """Load CL master file if present."""
    if not CL_MASTER_PATH.exists():
        return pd.DataFrame()
    df = pd.read_excel(CL_MASTER_PATH)
    return _ensure_master_tracking_columns(df)


def register_guide_download(guide_name: str, report_df: pd.DataFrame) -> Dict[str, int]:
    """
    Update master usage counters using dynamic numbered columns.

    For each question included in the guide, increments 'Número de usos' and
    adds 'Nombre guía (uso N)' / 'Fecha descarga (uso N)' columns.
    """
    ensure_directories()

    master_df = load_cl_master()
    if master_df.empty or report_df.empty:
        return {"updated_questions": 0, "updated_texts": 0}

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    numero_usos_col = CL_TRACKING_COLUMNS["numero_usos"]

    key_code = "Codigo Texto"
    key_num = "N original del documento"

    updated_questions = 0

    for _, row in report_df.iterrows():
        code = str(row.get(key_code, "")).strip()
        try:
            num = int(row.get(key_num))
        except Exception:
            continue

        mask = (
            master_df[CL_COLUMNS["codigo_texto"]].astype(str).str.strip() == code
        ) & (
            pd.to_numeric(master_df[CL_COLUMNS["numero_pregunta"]], errors="coerce") == num
        )

        if not mask.any():
            continue

        row_idx = master_df[mask].index[0]

        # Get current usage count
        current_uses = master_df.loc[row_idx, numero_usos_col]
        if pd.isna(current_uses):
            current_uses = 0
        else:
            current_uses = int(current_uses)

        # Increment usage count
        new_uses = current_uses + 1
        master_df.loc[row_idx, numero_usos_col] = new_uses

        # Add dynamic columns for this usage
        guide_name_col, date_col = get_usage_column_names(new_uses)

        if guide_name_col not in master_df.columns:
            master_df[guide_name_col] = None
        if date_col not in master_df.columns:
            master_df[date_col] = None

        master_df.loc[row_idx, guide_name_col] = guide_name
        master_df.loc[row_idx, date_col] = now

        updated_questions += 1

    # Count unique texts updated
    unique_codes = set(report_df[key_code].dropna().astype(str).str.strip().tolist())
    updated_texts = 0
    for code in unique_codes:
        text_mask = master_df[CL_COLUMNS["codigo_texto"]].astype(str).str.strip() == code
        if text_mask.any():
            updated_texts += 1

    master_df.to_excel(CL_MASTER_PATH, index=False)

    return {"updated_questions": updated_questions, "updated_texts": updated_texts}


def get_cl_master_stats(master_df: pd.DataFrame) -> Dict[str, object]:
    """Return high-level CL stats for dashboards/CLI."""
    if master_df.empty:
        return {
            "total_textos": 0,
            "total_preguntas": 0,
            "textos_usados": 0,
            "preguntas_usadas": 0,
            "pct_preguntas_usadas": 0.0,
            "habilidad_dist": {},
            "tarea_dist": {},
            "tipo_texto_dist": {},
        }

    code_col = CL_COLUMNS["codigo_texto"]
    numero_usos_col = CL_TRACKING_COLUMNS["numero_usos"]

    total_textos = int(master_df[code_col].astype(str).nunique())
    total_preguntas = int(len(master_df))

    usage_counts = pd.to_numeric(master_df[numero_usos_col], errors="coerce").fillna(0)
    preguntas_usadas = int((usage_counts > 0).sum())

    # A text is considered "used" if any of its questions have been used
    texto_usage = master_df.copy()
    texto_usage["_used"] = usage_counts > 0
    textos_usados = int(texto_usage.groupby(code_col)["_used"].any().sum())

    return {
        "total_textos": total_textos,
        "total_preguntas": total_preguntas,
        "textos_usados": textos_usados,
        "preguntas_usadas": preguntas_usadas,
        "pct_preguntas_usadas": round((preguntas_usadas / total_preguntas * 100.0), 2) if total_preguntas else 0.0,
        "habilidad_dist": master_df[CL_COLUMNS["habilidad"]].astype(str).value_counts().to_dict(),
        "tarea_dist": master_df[CL_COLUMNS["tarea_lectora"]].astype(str).value_counts().to_dict(),
        "tipo_texto_dist": master_df[CL_COLUMNS["tipo_texto"]].astype(str).value_counts().to_dict(),
    }


def get_all_guides() -> List[Dict[str, object]]:
    """Return a list of all distinct guides found in the master usage columns."""
    master_df = load_cl_master()
    if master_df.empty:
        return []

    numero_usos_col = CL_TRACKING_COLUMNS["numero_usos"]
    code_col = CL_COLUMNS["codigo_texto"]
    num_col = CL_COLUMNS["numero_pregunta"]

    # Scan all usage columns to collect unique (guide_name, date) pairs
    unique_guides: Dict[tuple, Dict[str, object]] = {}

    for col in master_df.columns:
        if not col.startswith("Nombre guía (uso "):
            continue
        usage_num = int(col.split("(uso ")[1].rstrip(")"))
        _, date_col = get_usage_column_names(usage_num)

        guide_names = master_df[col].dropna().unique()
        for gname in guide_names:
            gname_str = str(gname).strip()
            if not gname_str:
                continue

            # Find all rows with this guide name in this usage column
            mask = master_df[col] == gname
            if date_col in master_df.columns and mask.any():
                date_val = master_df.loc[mask, date_col].iloc[0]
            else:
                date_val = None

            key = (gname_str, str(date_val) if pd.notna(date_val) else "")

            if key not in unique_guides:
                # Collect all question rows across all usage columns for this guide+date
                all_question_rows = set()
                for ucol in master_df.columns:
                    if not ucol.startswith("Nombre guía (uso "):
                        continue
                    un = int(ucol.split("(uso ")[1].rstrip(")"))
                    _, dc = get_usage_column_names(un)
                    if dc in master_df.columns:
                        gmask = (master_df[ucol] == gname) & (master_df[dc].astype(str) == str(date_val))
                    else:
                        gmask = master_df[ucol] == gname
                    for idx in master_df[gmask].index:
                        all_question_rows.add(idx)

                unique_guides[key] = {
                    "guide_name": gname_str,
                    "date": str(date_val) if pd.notna(date_val) else None,
                    "question_count": len(all_question_rows),
                    "question_indices": all_question_rows,
                }

    # Sort by date descending, assign creation order
    guides = list(unique_guides.values())
    guides_sorted_asc = sorted(guides, key=lambda g: g["date"] or "")
    for i, g in enumerate(guides_sorted_asc, 1):
        g["creation_order"] = i

    return sorted(guides_sorted_asc, key=lambda g: g["date"] or "", reverse=True)


def delete_specific_guide_usage(guide_name: str, guide_date: str | None = None) -> Dict[str, object]:
    """
    Delete a specific guide's usage from the master by matching name and date.

    For each affected question row, clears the matching usage columns and shifts
    higher-numbered usages down, then decrements 'Número de usos'.
    """
    ensure_directories()

    master_df = load_cl_master()
    if master_df.empty:
        return {"success": False, "error": "Master vacío"}

    numero_usos_col = CL_TRACKING_COLUMNS["numero_usos"]

    # Find which (row_index, usage_number) pairs to remove
    to_remove: Dict[int, List[int]] = {}  # row_idx -> [usage_nums]

    for col in master_df.columns:
        if not col.startswith("Nombre guía (uso "):
            continue
        usage_num = int(col.split("(uso ")[1].rstrip(")"))
        _, date_col = get_usage_column_names(usage_num)

        mask = master_df[col].astype(str).str.strip() == guide_name
        if guide_date and date_col in master_df.columns:
            mask = mask & (master_df[date_col].astype(str) == guide_date)

        for idx in master_df[mask].index:
            to_remove.setdefault(int(idx), []).append(usage_num)

    if not to_remove:
        return {"success": False, "error": f"Guía '{guide_name}' no encontrada"}

    # For each affected row, shift usages down
    for row_idx, usage_nums_to_remove in to_remove.items():
        current_uses = int(pd.to_numeric(master_df.loc[row_idx, numero_usos_col], errors="coerce") or 0)
        if current_uses == 0:
            continue

        # Build mapping: old_usage -> new_usage (skipping removed ones)
        usage_mapping: Dict[int, int] = {}
        new_count = 0
        for old_u in range(1, current_uses + 1):
            if old_u not in usage_nums_to_remove:
                new_count += 1
                usage_mapping[old_u] = new_count

        # Collect surviving data
        new_guides: Dict[str, object] = {}
        new_dates: Dict[str, object] = {}
        for old_u, new_u in usage_mapping.items():
            old_g, old_d = get_usage_column_names(old_u)
            new_g, new_d = get_usage_column_names(new_u)
            if old_g in master_df.columns:
                new_guides[new_g] = master_df.loc[row_idx, old_g]
            if old_d in master_df.columns:
                new_dates[new_d] = master_df.loc[row_idx, old_d]

        # Clear all old usage columns for this row
        for old_u in range(1, current_uses + 1):
            g_col, d_col = get_usage_column_names(old_u)
            if g_col in master_df.columns:
                master_df.loc[row_idx, g_col] = None
            if d_col in master_df.columns:
                master_df.loc[row_idx, d_col] = None

        # Write shifted data
        for col_name, val in {**new_guides, **new_dates}.items():
            if col_name not in master_df.columns:
                master_df[col_name] = None
            master_df.loc[row_idx, col_name] = val

        master_df.loc[row_idx, numero_usos_col] = new_count

    master_df.to_excel(CL_MASTER_PATH, index=False)

    return {
        "success": True,
        "questions_affected": len(to_remove),
        "message": f"Guía '{guide_name}' eliminada de {len(to_remove)} preguntas",
    }
