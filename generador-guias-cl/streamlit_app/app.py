"""
Streamlit app for CL (Comprension Lectora) guide generation.
"""

from __future__ import annotations

import sys
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Set

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.append(str(Path(__file__).parent.parent))

from cl_data_processor import apply_top_down_filters
from cl_master import (
    delete_specific_guide_usage,
    get_all_guides,
    get_cl_master_stats,
    load_cl_master,
    register_guide_download,
)
from cl_word_builder import generate_cl_outputs
from config import (
    CL_COLUMNS,
    CL_DEFAULT_TARGET_QUESTIONS,
    CL_FILTER_ORDER_TOP_DOWN,
    NOMBRES_GUIAS_PATH,
    STREAMLIT_CONFIG,
    ensure_directories,
    get_usage_column_names,
)

PAGE_TITLE = "📖 Generador CL"
SECTION_FILTERS = "🎯 Filtrar Textos"
SECTION_SELECT = "📋 Seleccionar Textos"
SECTION_REMOVE = "✂️ Eliminar Preguntas"
SECTION_SUMMARY = "📊 Resumen"
SECTION_GENERATE = "📝 Generar Guia"
SECTION_MASTER_STATS = "📊 Estadisticas Totales"
FILTER_ALL_OPTION = "Todos"

TOP_DOWN_LABELS = {
    CL_COLUMNS["tipo_texto"]: "Tipo de texto",
    CL_COLUMNS["subgenero"]: "Subgenero",
    CL_COLUMNS["titulo_texto"]: "Titulo",
    CL_COLUMNS["descripcion_texto"]: "Descripcion (busqueda)",
}

INDEPENDENT_LABELS = {
    CL_COLUMNS["programa"]: "Programa",
    CL_COLUMNS["habilidad"]: "Habilidad",
    CL_COLUMNS["tarea_lectora"]: "Tarea lectora",
}

ZIP_README_NAME = "README.txt"
ZIP_README_CONTENT = (
    "Paquete generado por Generador CL.\n"
    "Incluye: guia en Word + reporte Excel.\n"
)


st.set_page_config(
    page_title=STREAMLIT_CONFIG["page_title"],
    page_icon=STREAMLIT_CONFIG["page_icon"],
    layout=STREAMLIT_CONFIG["layout"],
    initial_sidebar_state=STREAMLIT_CONFIG["initial_sidebar_state"],
)


def _init_session_state() -> None:
    defaults = {
        "selected_codes": set(),
        "selected_order": [],
        "text_positions": {},
        "target_questions": CL_DEFAULT_TARGET_QUESTIONS,
        "active_remove_code": None,
        "removed_by_code": {},
        "zip_payload_key": None,
        "zip_payload_bytes": None,
        "zip_payload_name": None,
        "report_df_for_tracking": None,
        "guide_name_for_tracking": None,
        "tracking_message": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _load_available_guide_names() -> List[str]:
    path = Path(__file__).parent.parent / NOMBRES_GUIAS_PATH
    if not path.exists():
        return []

    try:
        df = pd.read_excel(path)
    except Exception:
        return []

    if df.empty:
        return []

    first_col = df.columns[0]
    names = (
        df[first_col]
        .dropna()
        .astype(str)
        .str.strip()
        .loc[lambda s: s != ""]
        .unique()
        .tolist()
    )
    return sorted(names)


def _build_catalog_from_master(master_df: pd.DataFrame) -> tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
    records: List[Dict[str, object]] = []
    by_code: Dict[str, pd.DataFrame] = {}

    if master_df.empty:
        return pd.DataFrame(), by_code

    code_col = CL_COLUMNS["codigo_texto"]
    num_col = CL_COLUMNS["numero_pregunta"]

    for code, group in master_df.groupby(code_col, dropna=False):
        code_str = str(code)
        g = group.sort_values(num_col).reset_index(drop=True)
        by_code[code_str] = g

        first = g.iloc[0]
        records.append(
            {
                "Codigo Texto": code_str,
                "docx_path": first.get("docx_path", ""),
                "excel_path": first.get("excel_path", ""),
                CL_COLUMNS["tipo_texto"]: first.get(CL_COLUMNS["tipo_texto"], ""),
                CL_COLUMNS["subgenero"]: first.get(CL_COLUMNS["subgenero"], ""),
                CL_COLUMNS["titulo_texto"]: first.get(CL_COLUMNS["titulo_texto"], ""),
                CL_COLUMNS["descripcion_texto"]: first.get(CL_COLUMNS["descripcion_texto"], ""),
                CL_COLUMNS["programa"]: first.get(CL_COLUMNS["programa"], ""),
                CL_COLUMNS["n_preguntas"]: int(len(g)),
                "Habilidades": ", ".join(sorted(g[CL_COLUMNS["habilidad"]].dropna().astype(str).unique().tolist())),
                "Tareas": ", ".join(sorted(g[CL_COLUMNS["tarea_lectora"]].dropna().astype(str).unique().tolist())),
            }
        )

    catalog = pd.DataFrame(records)
    if not catalog.empty:
        catalog = catalog.sort_values(
            [CL_COLUMNS["tipo_texto"], CL_COLUMNS["subgenero"], CL_COLUMNS["titulo_texto"]]
        ).reset_index(drop=True)

    return catalog, by_code


def _build_cascading_top_filters(catalog_df: pd.DataFrame) -> Dict[str, str]:
    filters: Dict[str, str] = {}
    working_df = catalog_df.copy()

    for col in CL_FILTER_ORDER_TOP_DOWN:
        label = TOP_DOWN_LABELS[col]
        key = f"flt_{col}"

        if col == CL_COLUMNS["descripcion_texto"]:
            value = st.text_input(label, value=st.session_state.get(key, ""), key=key)
            filters[col] = value.strip()
            if filters[col]:
                working_df = apply_top_down_filters(working_df, {col: filters[col]})
            continue

        options = sorted(working_df[col].dropna().astype(str).unique().tolist())
        options = [FILTER_ALL_OPTION] + options
        selected = st.selectbox(label, options=options, key=key)
        filters[col] = selected

        if selected and selected != FILTER_ALL_OPTION:
            working_df = working_df[working_df[col].astype(str) == selected]

    return filters


def _extract_option_values_from_questions(base_df: pd.DataFrame, by_codigo_df: Dict[str, pd.DataFrame], question_column: str) -> List[str]:
    values: Set[str] = set()
    for _, row in base_df.iterrows():
        code = str(row["Codigo Texto"])
        q_df = by_codigo_df.get(code)
        if q_df is None or q_df.empty or question_column not in q_df.columns:
            continue
        for value in q_df[question_column].dropna().astype(str):
            val = value.strip()
            if val:
                values.add(val)
    return sorted(values)


def _build_independent_filters(base_df: pd.DataFrame, by_codigo_df: Dict[str, pd.DataFrame]) -> Dict[str, str]:
    filters: Dict[str, str] = {}

    programa_col = CL_COLUMNS["programa"]
    programa_opts = [FILTER_ALL_OPTION] + sorted(base_df[programa_col].dropna().astype(str).unique().tolist())
    filters[programa_col] = st.selectbox(INDEPENDENT_LABELS[programa_col], options=programa_opts, key="flt_programa")

    n_preg_col = CL_COLUMNS["n_preguntas"]
    n_preg_values = sorted(base_df[n_preg_col].dropna().astype(int).unique().tolist())
    n_preg_opts = [FILTER_ALL_OPTION] + [str(v) for v in n_preg_values]
    filters[n_preg_col] = st.selectbox("N Preguntas", options=n_preg_opts, key="flt_n_preguntas")

    habilidad_col = CL_COLUMNS["habilidad"]
    habilidad_opts = [FILTER_ALL_OPTION] + _extract_option_values_from_questions(base_df, by_codigo_df, habilidad_col)
    filters[habilidad_col] = st.selectbox(INDEPENDENT_LABELS[habilidad_col], options=habilidad_opts, key="flt_habilidad")

    tarea_col = CL_COLUMNS["tarea_lectora"]
    tarea_opts = [FILTER_ALL_OPTION] + _extract_option_values_from_questions(base_df, by_codigo_df, tarea_col)
    filters[tarea_col] = st.selectbox(INDEPENDENT_LABELS[tarea_col], options=tarea_opts, key="flt_tarea")

    return filters


def _apply_independent_filters(df: pd.DataFrame, filters: Dict[str, str], by_codigo_df: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    filtered = df.copy()

    programa_val = filters.get(CL_COLUMNS["programa"], "")
    if programa_val and programa_val != FILTER_ALL_OPTION:
        filtered = filtered[filtered[CL_COLUMNS["programa"]].astype(str) == str(programa_val)]

    n_preg_val = filters.get(CL_COLUMNS["n_preguntas"], "")
    if n_preg_val and n_preg_val != FILTER_ALL_OPTION:
        filtered = filtered[filtered[CL_COLUMNS["n_preguntas"]].astype(int) == int(n_preg_val)]

    habilidad_val = filters.get(CL_COLUMNS["habilidad"], "")
    if habilidad_val and habilidad_val != FILTER_ALL_OPTION:
        keep_codes: Set[str] = set()
        for _, row in filtered.iterrows():
            code = str(row["Codigo Texto"])
            q_df = by_codigo_df.get(code)
            if q_df is None or q_df.empty:
                continue
            if (q_df[CL_COLUMNS["habilidad"]].astype(str) == str(habilidad_val)).any():
                keep_codes.add(code)
        filtered = filtered[filtered["Codigo Texto"].astype(str).isin(keep_codes)]

    tarea_val = filters.get(CL_COLUMNS["tarea_lectora"], "")
    if tarea_val and tarea_val != FILTER_ALL_OPTION:
        keep_codes: Set[str] = set()
        for _, row in filtered.iterrows():
            code = str(row["Codigo Texto"])
            q_df = by_codigo_df.get(code)
            if q_df is None or q_df.empty:
                continue
            if (q_df[CL_COLUMNS["tarea_lectora"]].astype(str) == str(tarea_val)).any():
                keep_codes.add(code)
        filtered = filtered[filtered["Codigo Texto"].astype(str).isin(keep_codes)]

    return filtered


def _assign_next_position(code: str) -> None:
    positions: Dict[str, int] = st.session_state["text_positions"]
    current_positions = set(positions.values())
    next_pos = 1
    while next_pos in current_positions:
        next_pos += 1
    positions[code] = next_pos


def _remove_text_and_renumber(code: str) -> None:
    positions: Dict[str, int] = st.session_state["text_positions"]
    if code not in positions:
        return
    removed_pos = positions[code]
    del positions[code]
    for c, pos in positions.items():
        if pos > removed_pos:
            positions[c] = pos - 1


def _update_text_position(code: str, new_pos: int) -> None:
    positions: Dict[str, int] = st.session_state["text_positions"]
    if code not in positions:
        return
    old_pos = positions[code]
    if old_pos == new_pos:
        return
    positions[code] = new_pos
    if new_pos > old_pos:
        for c, pos in positions.items():
            if c != code and old_pos < pos <= new_pos:
                positions[c] = pos - 1
    else:
        for c, pos in positions.items():
            if c != code and new_pos <= pos < old_pos:
                positions[c] = pos + 1
    _update_ordered_list_from_positions()


def _update_ordered_list_from_positions() -> None:
    sorted_items = sorted(
        st.session_state["text_positions"].items(),
        key=lambda x: x[1],
    )
    st.session_state["selected_order"] = [code for code, _ in sorted_items]


def _collect_selected_texts(filtered_df: pd.DataFrame, by_codigo_df: Dict[str, pd.DataFrame]) -> List[Dict[str, object]]:
    st.subheader(SECTION_SELECT)
    selected_codes: Set[str] = st.session_state["selected_codes"]
    positions: Dict[str, int] = st.session_state["text_positions"]

    # --- Pagination ---
    PAGE_SIZE_OPTIONS = [5, 10, 30, 50, 100]
    if "texts_per_page" not in st.session_state:
        st.session_state["texts_per_page"] = 10
    if "texts_current_page" not in st.session_state:
        st.session_state["texts_current_page"] = 1

    total_texts = len(filtered_df)
    texts_per_page = st.session_state["texts_per_page"]
    total_pages = max(1, (total_texts + texts_per_page - 1) // texts_per_page)

    if st.session_state["texts_current_page"] > total_pages:
        st.session_state["texts_current_page"] = total_pages

    current_page = st.session_state["texts_current_page"]
    start_idx = (current_page - 1) * texts_per_page
    end_idx = min(start_idx + texts_per_page, total_texts)
    page_df = filtered_df.iloc[start_idx:end_idx]

    for _, row in page_df.iterrows():
        code = str(row["Codigo Texto"])
        is_selected = code in selected_codes

        title = f"{code} | {row.get(CL_COLUMNS['tipo_texto'], '')} | {row.get(CL_COLUMNS['subgenero'], '')}"
        with st.container(border=True):
            col_left, col_right = st.columns([8, 2])
            with col_left:
                st.markdown(f"**{title}**")
                st.write(str(row.get(CL_COLUMNS["titulo_texto"], "")))
                st.caption(str(row.get(CL_COLUMNS["descripcion_texto"], "")))
                st.caption(f"Programa: {row.get(CL_COLUMNS['programa'], '')} | Preguntas: {row.get(CL_COLUMNS['n_preguntas'], 0)}")

            with col_right:
                checked = st.checkbox("Seleccionar", value=is_selected, key=f"sel_{code}")
                if checked != is_selected:
                    if checked:
                        selected_codes.add(code)
                        _assign_next_position(code)
                    else:
                        selected_codes.discard(code)
                        _remove_text_and_renumber(code)

    # Pagination controls
    col_pagination, col_per_page = st.columns([3, 1])
    with col_per_page:
        new_per_page = st.selectbox(
            "Textos por página",
            options=PAGE_SIZE_OPTIONS,
            index=PAGE_SIZE_OPTIONS.index(texts_per_page),
            key="per_page_select",
        )
        if new_per_page != texts_per_page:
            st.session_state["texts_per_page"] = new_per_page
            st.session_state["texts_current_page"] = 1
            st.rerun()
    with col_pagination:
        col_prev, col_info, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.button("⬅️ Anterior", disabled=current_page <= 1, key="prev_texts"):
                st.session_state["texts_current_page"] -= 1
                st.rerun()
        with col_info:
            st.markdown(
                f"<div style='text-align: center; padding-top: 5px;'>"
                f"Página <b>{current_page}</b> de <b>{total_pages}</b><br>"
                f"<small>Mostrando {start_idx + 1}-{end_idx} de {total_texts}</small></div>",
                unsafe_allow_html=True,
            )
        with col_next:
            if st.button("Siguiente ➡️", disabled=current_page >= total_pages, key="next_texts"):
                st.session_state["texts_current_page"] += 1
                st.rerun()

    st.session_state["selected_codes"] = selected_codes

    # Sync ordered list from positions.
    _update_ordered_list_from_positions()
    current_order: List[str] = st.session_state["selected_order"]

    # --- Order section with numbered dropdowns ---
    st.markdown("---")
    if len(current_order) >= 1:
        n = len(current_order)
        position_options = list(range(1, n + 1))

        # Detect change from widget cache BEFORE rendering any selectbox.
        for code in list(positions):
            widget_val = st.session_state.get(f"ord_{code}")
            if widget_val is not None and widget_val != positions.get(code):
                _update_text_position(code, int(widget_val))
                break

        # Sync all widget keys to updated positions so selectboxes render correctly.
        for code in positions:
            st.session_state[f"ord_{code}"] = positions[code]

        # Re-derive order after potential update.
        _update_ordered_list_from_positions()
        current_order = st.session_state["selected_order"]

        # Compute total questions across selected texts.
        total_questions = 0
        q_counts: Dict[str, int] = {}
        for code in current_order:
            q_df = by_codigo_df.get(code)
            cnt = len(q_df) if q_df is not None else 0
            q_counts[code] = cnt
            total_questions += cnt

        # Header row: label + input on the left, total on the right.
        col_label, col_input, col_spacer, col_total = st.columns([2, 1, 3, 2])
        with col_label:
            st.markdown("### Número objetivo de preguntas")
        with col_input:
            st.number_input(
                "Objetivo de preguntas",
                min_value=1,
                value=CL_DEFAULT_TARGET_QUESTIONS,
                step=1,
                key="target_questions",
                label_visibility="collapsed",
            )
        with col_total:
            st.markdown(f"### Total preguntas en textos seleccionados: {total_questions}")

        st.markdown("---")
        st.markdown("### Orden de textos")

        sorted_texts = sorted(positions.items(), key=lambda x: x[1])
        for code, _ in sorted_texts:
            current_pos = positions[code]
            current_index = position_options.index(current_pos) if current_pos in position_options else 0

            match = filtered_df[filtered_df["Codigo Texto"].astype(str) == code]
            if not match.empty:
                r = match.iloc[0]
                txt = r.get(CL_COLUMNS["titulo_texto"], "")
                tipo = r.get(CL_COLUMNS["tipo_texto"], "")
                subgenero = r.get(CL_COLUMNS["subgenero"], "")
            else:
                txt, tipo, subgenero = "", "", ""
            q_count = q_counts.get(code, 0)
            label = f"{code} | {txt} | {q_count} preguntas | {tipo} | {subgenero}"

            col_num, col_label = st.columns([1, 15])
            with col_num:
                st.selectbox(
                    "pos",
                    options=position_options,
                    index=current_index,
                    key=f"ord_{code}",
                    label_visibility="collapsed",
                )
            with col_label:
                st.markdown(label)

    # Build result sorted by order.
    selected_rows_df = filtered_df[filtered_df["Codigo Texto"].astype(str).isin(current_order)].copy()
    if current_order:
        selected_rows_df["_order"] = selected_rows_df["Codigo Texto"].astype(str).apply(lambda c: current_order.index(c))
        selected_rows_df = selected_rows_df.sort_values("_order").drop(columns=["_order"])

    return selected_rows_df.to_dict("records")


def _render_question_removal(selected_rows: List[Dict[str, object]], by_codigo_df: Dict[str, pd.DataFrame]) -> int:
    st.subheader(SECTION_REMOVE)
    removed_by_code: Dict[str, Set[int]] = st.session_state["removed_by_code"]
    total_kept = 0

    for row in selected_rows:
        code = str(row["Codigo Texto"])
        df = by_codigo_df.get(code)
        if df is None or df.empty:
            continue

        if code not in removed_by_code:
            removed_by_code[code] = set()

        with st.expander(f"{code} - {row.get(CL_COLUMNS['titulo_texto'], '')}"):
            st.caption("Marca las preguntas que quieres eliminar.")
            for _, q_row in df.iterrows():
                q_num = int(q_row[CL_COLUMNS["numero_pregunta"]])
                default_removed = q_num in removed_by_code[code]
                q_key = f"rm_{code}_{q_num}"

                # Build usage badge
                n_usos = int(q_row.get("Número de usos", 0) or 0)
                if n_usos > 0:
                    last_guide = ""
                    for u in range(n_usos, 0, -1):
                        g_col, _ = get_usage_column_names(u)
                        val = q_row.get(g_col)
                        if pd.notna(val) and str(val).strip():
                            last_guide = str(val).strip()
                            break
                    usage_badge = f" | 🔄 Usada {n_usos} veces (última: {last_guide})" if last_guide else f" | Usada {n_usos} veces"
                else:
                    usage_badge = ""

                label = f"Eliminar P{q_num} | Habilidad: {q_row.get(CL_COLUMNS['habilidad'], '')} | Tarea: {q_row.get(CL_COLUMNS['tarea_lectora'], '')}{usage_badge}"

                col_cb, col_toggle = st.columns([10, 2])
                with col_cb:
                    removed = st.checkbox(label, value=default_removed, key=q_key)
                with col_toggle:
                    if n_usos > 0:
                        show_hist = st.toggle("Historial", value=False, key=f"hist_{code}_{q_num}")
                    else:
                        show_hist = False

                if removed:
                    removed_by_code[code].add(q_num)
                else:
                    removed_by_code[code].discard(q_num)

                if show_hist:
                    history_rows = []
                    for u in range(1, n_usos + 1):
                        g_col, d_col = get_usage_column_names(u)
                        history_rows.append({
                            "Uso #": u,
                            "Nombre de Guía": str(q_row.get(g_col, "")) if pd.notna(q_row.get(g_col)) else "",
                            "Fecha de Descarga": str(q_row.get(d_col, "")) if pd.notna(q_row.get(d_col)) else "",
                        })
                    st.dataframe(pd.DataFrame(history_rows), use_container_width=True, hide_index=True)

            kept_count = len(df) - len(removed_by_code[code])
            total_kept += kept_count
            st.info(f"Preguntas conservadas en {code}: {kept_count}/{len(df)}")

    st.session_state["removed_by_code"] = removed_by_code
    return total_kept


def _compute_kept_questions_df(selected_rows: List[Dict[str, object]], by_codigo_df: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    removed_by_code: Dict[str, Set[int]] = st.session_state["removed_by_code"]
    frames: List[pd.DataFrame] = []

    for row in selected_rows:
        code = str(row["Codigo Texto"])
        df = by_codigo_df.get(code)
        if df is None or df.empty:
            continue

        removed = removed_by_code.get(code, set())
        frame = df[~df[CL_COLUMNS["numero_pregunta"]].isin(list(removed))].copy()
        frame["Codigo Texto"] = code
        frames.append(frame)

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _plot_pie_from_series(series: pd.Series, title: str) -> None:
    counts = series.astype(str).value_counts().reset_index()
    counts.columns = ["categoria", "cantidad"]
    fig = px.pie(counts, names="categoria", values="cantidad", title=title)
    st.plotly_chart(fig, use_container_width=True)


def _plot_bar_from_series(series: pd.Series, title: str) -> None:
    counts = series.astype(str).value_counts().reset_index()
    counts.columns = ["categoria", "cantidad"]
    fig = px.bar(counts, x="categoria", y="cantidad", title=title)
    fig.update_layout(xaxis_title="", yaxis_title="Cantidad")
    st.plotly_chart(fig, use_container_width=True)


def _render_summary(kept_df: pd.DataFrame, selected_rows: List[Dict[str, object]], target_questions: int) -> None:
    st.subheader(SECTION_SUMMARY)

    selected_texts_count = len(selected_rows)
    kept_questions_count = len(kept_df)
    diff_target = kept_questions_count - target_questions

    c1, c2, c3 = st.columns(3)
    c1.metric("Textos seleccionados", selected_texts_count)
    c2.metric("Preguntas finales", kept_questions_count)
    c3.metric("Diferencia vs objetivo", diff_target)

    if not kept_df.empty:
        col_a, col_b = st.columns(2)
        with col_a:
            _plot_pie_from_series(kept_df[CL_COLUMNS["habilidad"]], "Distribucion por Habilidad")
        with col_b:
            _plot_bar_from_series(kept_df[CL_COLUMNS["tarea_lectora"]], "Distribucion por Tarea lectora")


def _render_master_stats(master_df: pd.DataFrame) -> None:
    st.subheader("📊 Estadísticas y Gestión")

    col_stats, col_guides = st.columns(2)

    # --- Left column: Ver Estadísticas ---
    with col_stats:
        st.markdown("**📈 Estadísticas de Uso**")
        if st.button("Ver Estadísticas", key="btn_show_stats"):
            st.session_state["show_stats"] = not st.session_state.get("show_stats", False)

    # --- Right column: Eliminar Guías ---
    with col_guides:
        st.markdown("**🗑️ Eliminar Guías**")
        if st.button("Ver Guías Creadas", key="btn_show_guides"):
            if not st.session_state.get("show_guide_deletion", False):
                st.session_state["available_guides"] = get_all_guides()
                st.session_state["show_guide_deletion"] = True
            else:
                st.session_state["show_guide_deletion"] = False

        # Guide deletion panel (inside the right column)
        if st.session_state.get("show_guide_deletion", False):
            guides = st.session_state.get("available_guides", [])
            if not guides:
                st.info("No se encontraron guías creadas.")
            else:
                st.markdown(f"**Guías encontradas:**")

                guide_options = []
                for i, guide in enumerate(guides):
                    date_str = guide["date"] if guide["date"] else "Sin fecha"
                    creation_order = guide.get("creation_order", i + 1)
                    option_text = f"{guide['guide_name']} - {date_str} - {guide['question_count']} preguntas [#{creation_order}]"
                    guide_options.append((option_text, i))

                options_with_empty = [""] + [opt[0] for opt in guide_options]

                selected_option = st.selectbox(
                    "Seleccionar guía a eliminar:",
                    options=options_with_empty,
                    index=0,
                    key="guide_deletion_selectbox",
                )

                if selected_option:
                    selected_index = next(i for i, (opt, _) in enumerate(guide_options) if opt == selected_option)
                    selected_guide = guides[selected_index]

                    st.markdown("**Detalles de la guía:**")
                    st.write(f"- Nombre: {selected_guide['guide_name']}")
                    st.write(f"- Fecha: {selected_guide['date'] or 'Sin fecha'}")
                    st.write(f"- Preguntas: {selected_guide['question_count']}")
                    st.warning("ADVERTENCIA: Esta acción eliminará el registro de uso de esta guía de todas las preguntas afectadas.")

                    if st.button("ELIMINAR GUÍA", type="secondary", key="btn_delete_guide"):
                        result = delete_specific_guide_usage(
                            guide_name=selected_guide["guide_name"],
                            guide_date=selected_guide["date"],
                        )
                        if result["success"]:
                            st.success(result["message"])
                            st.session_state["show_guide_deletion"] = False
                            st.session_state["available_guides"] = []
                            st.rerun()
                        else:
                            st.error(result.get("error", "Error desconocido"))
                else:
                    st.info("Selecciona una guía para ver sus detalles y eliminarla.")

            if st.button("❌ Cerrar", key="btn_close_guides"):
                st.session_state["show_guide_deletion"] = False
                st.session_state["available_guides"] = []
                st.rerun()

    # --- Stats panel (full width below) ---
    if st.session_state.get("show_stats", False) and not master_df.empty:
        stats = get_cl_master_stats(master_df)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Textos", stats["total_textos"])
        c2.metric("Preguntas", stats["total_preguntas"])
        c3.metric("Textos usados", stats["textos_usados"])
        c4.metric("Preguntas usadas", f"{stats['preguntas_usadas']} ({stats['pct_preguntas_usadas']}%)")

        usage_counts = pd.to_numeric(master_df["Número de usos"], errors="coerce").fillna(0).astype(int)
        buckets = {
            "No usadas": int((usage_counts == 0).sum()),
            "1 vez": int((usage_counts == 1).sum()),
            "2 veces": int((usage_counts == 2).sum()),
            "3 veces": int((usage_counts == 3).sum()),
            "Más de 3": int((usage_counts > 3).sum()),
        }
        usage_df = pd.DataFrame({"estado": list(buckets.keys()), "cantidad": list(buckets.values())})
        usage_df = usage_df[usage_df["cantidad"] > 0]

        col_y, col_z, col_x = st.columns(3)
        with col_y:
            _plot_pie_from_series(master_df[CL_COLUMNS["habilidad"]], "Distribucion por Habilidad")
        with col_z:
            _plot_bar_from_series(master_df[CL_COLUMNS["tarea_lectora"]], "Distribucion por Tarea lectora")
        with col_x:
            fig = px.pie(usage_df, names="estado", values="cantidad", title="Cobertura de preguntas")
            st.plotly_chart(fig, use_container_width=True)


def _build_zip_payload(word_bytes: bytes, word_filename: str, excel_bytes: bytes, excel_filename: str) -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(word_filename, word_bytes)
        zf.writestr(excel_filename, excel_bytes)
        zf.writestr(ZIP_README_NAME, ZIP_README_CONTENT)
    buf.seek(0)
    return buf.getvalue()


def _on_download_click() -> None:
    report_records = st.session_state.get("report_df_for_tracking")
    guide_name = st.session_state.get("guide_name_for_tracking")
    if not report_records or not guide_name:
        return

    report_df = pd.DataFrame(report_records)
    result = register_guide_download(guide_name=guide_name, report_df=report_df)
    st.session_state["tracking_message"] = (
        f"Uso actualizado: {result.get('updated_texts', 0)} textos y {result.get('updated_questions', 0)} preguntas."
    )


def main() -> None:
    ensure_directories()
    _init_session_state()

    st.title(PAGE_TITLE)
    st.markdown("---")

    master_df = load_cl_master()
    if master_df.empty:
        st.error("No hay datos disponibles. Ejecuta `python main.py process-cl` para consolidar antes de usar la app.")
        return

    catalog_df, by_codigo_df = _build_catalog_from_master(master_df)
    if catalog_df.empty:
        st.error("No se pudo construir el catalogo desde master CL.")
        return

    _render_master_stats(master_df)

    # Data summary metrics
    st.markdown("---")
    st.markdown("### 📊 Resumen de Datos")

    c_total, c_texts, c_tipos = st.columns(3)
    with c_total:
        st.metric(
            label="📚 Total Preguntas",
            value=len(master_df),
            help="Número total de preguntas disponibles",
        )
    with c_texts:
        n_texts = master_df[CL_COLUMNS["codigo_texto"]].nunique()
        st.metric(
            label="📄 Textos",
            value=n_texts,
            help="Número de textos únicos en el banco",
        )
    with c_tipos:
        n_tipos = master_df[CL_COLUMNS["tipo_texto"]].nunique()
        st.metric(
            label="📂 Tipos de Texto",
            value=n_tipos,
            help="Tipos de texto distintos",
        )

    st.markdown("---")
    st.subheader(SECTION_FILTERS)
    top_filters = _build_cascading_top_filters(catalog_df)
    normalized_top_filters = {
        key: ("" if value == FILTER_ALL_OPTION else value)
        for key, value in top_filters.items()
    }
    top_filtered_df = apply_top_down_filters(catalog_df, normalized_top_filters)

    independent_filters = _build_independent_filters(top_filtered_df, by_codigo_df)
    final_filtered_df = _apply_independent_filters(top_filtered_df, independent_filters, by_codigo_df)
    st.caption(f"Textos encontrados: {len(final_filtered_df)}")

    st.markdown("---")
    selected_rows = _collect_selected_texts(final_filtered_df, by_codigo_df)

    target_questions = st.session_state.get("target_questions", CL_DEFAULT_TARGET_QUESTIONS)

    st.markdown("---")
    kept_count = _render_question_removal(selected_rows, by_codigo_df)
    kept_df = _compute_kept_questions_df(selected_rows, by_codigo_df)

    st.markdown("---")
    _render_summary(kept_df, selected_rows, target_questions)

    st.markdown("---")
    st.subheader(SECTION_GENERATE)

    available_names = _load_available_guide_names()
    selected_guide_name = st.selectbox(
        "Nombre de guia",
        options=[""] + available_names,
        index=0,
        help="Se carga desde output/nombres_guias.xlsx (columna A)",
    )

    if kept_count != target_questions:
        st.warning(
            f"Ajusta eliminaciones antes de generar. Actualmente hay {kept_count} preguntas y el objetivo es {target_questions}."
        )

    if not selected_guide_name:
        st.warning("Debes seleccionar un nombre de guia antes de descargar.")

    can_generate = kept_count == target_questions and len(selected_rows) > 0 and bool(selected_guide_name)
    if not available_names:
        st.error("No se encontraron nombres de guias en output/nombres_guias.xlsx")
        can_generate = False

    if can_generate:
        selected_payload: List[Dict[str, object]] = []
        removed_by_code: Dict[str, Set[int]] = st.session_state["removed_by_code"]

        for row in selected_rows:
            code = str(row["Codigo Texto"])
            payload = dict(row)
            payload["removed_questions"] = sorted(list(removed_by_code.get(code, set())))
            selected_payload.append(payload)

        build_key = str((selected_payload, int(target_questions), selected_guide_name))

        if st.session_state["zip_payload_key"] != build_key:
            try:
                word_bytes, word_filename, excel_bytes, excel_filename, report_df = generate_cl_outputs(
                    selected_texts=selected_payload,
                    by_codigo_df=by_codigo_df,
                    target_questions=int(target_questions),
                    guide_name=selected_guide_name,
                )
                st.session_state["zip_payload_key"] = build_key
                st.session_state["zip_payload_bytes"] = _build_zip_payload(
                    word_bytes=word_bytes,
                    word_filename=word_filename,
                    excel_bytes=excel_bytes,
                    excel_filename=excel_filename,
                )
                st.session_state["zip_payload_name"] = f"{selected_guide_name}.zip"
                st.session_state["report_df_for_tracking"] = report_df.to_dict("records")
                st.session_state["guide_name_for_tracking"] = selected_guide_name
                st.success(f"Paquete listo ({len(report_df)} preguntas).")
            except Exception as exc:
                st.error(f"Error generando salida: {exc}")
                st.session_state["zip_payload_key"] = None
                st.session_state["zip_payload_bytes"] = None
                st.session_state["zip_payload_name"] = None
                st.session_state["report_df_for_tracking"] = None
                st.session_state["guide_name_for_tracking"] = None

    if st.session_state.get("tracking_message"):
        st.success(st.session_state["tracking_message"])
        st.session_state["tracking_message"] = ""

    if st.session_state.get("zip_payload_bytes") and st.session_state.get("zip_payload_name") and can_generate:
        st.download_button(
            "📥 Descargar guia completa (ZIP)",
            data=st.session_state["zip_payload_bytes"],
            file_name=st.session_state["zip_payload_name"],
            mime="application/zip",
            type="primary",
            on_click=_on_download_click,
        )


if __name__ == "__main__":
    main()
