#!/usr/bin/env python3
"""
Schedule table generation for the Segment Schedule Report Generator.
"""

import logging
import re
from typing import Dict, List, Optional, Any

import pandas as pd

from data_loader import DataLoader
from utils import (
    find_col_case_insensitive, 
    format_semana, 
    level_to_index_m1_cl, 
    level_to_index_cien_hyst,
    match_day,
    match_hora,
    normalize_text
)

logger = logging.getLogger(__name__)


class ScheduleGenerator:
    """Handles generation of schedule tables for different segments and variants."""
    
    def __init__(self, data_loader: DataLoader):
        self.data_loader = data_loader

    def select_schedule_columns(
        self,
        reporte_row: pd.Series,
        variant: str,
        segmento: str,
        test_type_filter: Optional[str] = None,
    ) -> Dict[str, Optional[str]]:
        """Return mapping of column names to use from the Segment df for each test.

        variant: "manana" or "tarde". Only CIEN/HYST differ for "tarde".
        segmento: The segment identifier (e.g., "S1", "S2", etc.)
        test_type_filter: Optional filter for specific test type ("CIEN" or "HYST") for special segments
        """
        mapping: Dict[str, Optional[str]] = {
            "M1": None,
            "CL": None,
            "CIEN": None,
            "HYST": None,
        }

        # Define which test types to show for each segment
        segment_test_config = {
            "S1": ["M1", "CIEN"],
            "S2": ["M1", "HYST"],
            "S3": ["M1"],
            "S4": ["CL", "CIEN"],
            "S5": ["CL", "HYST"],
            "S6": ["CL"],
            "S7": ["M1", "CL", "CIEN"],
            "S8": ["M1", "CL", "HYST"],
            "S9": ["M1", "CL"],
            "S10": ["CIEN"],
            "S11": ["HYST"],
            "S12": ["M1"],
            "S13": ["M1"],  # Special handling for CIEN/HYST
            "S14": ["CL"],  # Special handling for CIEN/HYST
            "S15": ["M1", "CL"],  # Special handling for CIEN/HYST
        }

        # Get the allowed test types for this segment
        allowed_tests = segment_test_config.get(segmento.upper(), [])
        
        # For special segments (S13, S14, S15), if test_type_filter is provided, 
        # handle custom behavior
        if test_type_filter and segmento.upper() in ["S13", "S14", "S15"]:
            if test_type_filter == "S1_BEHAVIOR":
                # S1 behavior: M1 + CIEN
                allowed_tests = ["M1", "CIEN"]
            elif test_type_filter == "S2_BEHAVIOR":
                # S2 behavior: M1 + HYST
                allowed_tests = ["M1", "HYST"]
            elif test_type_filter == "S4_BEHAVIOR":
                # S4 behavior: CL + CIEN
                allowed_tests = ["CL", "CIEN"]
            elif test_type_filter == "S5_BEHAVIOR":
                # S5 behavior: CL + HYST
                allowed_tests = ["CL", "HYST"]
            elif test_type_filter == "S7_BEHAVIOR":
                # S7 behavior: M1 + CL + CIEN
                allowed_tests = ["M1", "CL", "CIEN"]
            elif test_type_filter == "S8_BEHAVIOR":
                # S8 behavior: M1 + CL + HYST
                allowed_tests = ["M1", "CL", "HYST"]
            else:
                # Original behavior for other test_type_filters
                allowed_tests = [test_type_filter]

        # Get levels from Reporte sheet columns
        nivel_m1_col = find_col_case_insensitive(reporte_row.to_frame().T, ["Nivel M1"])
        nivel_cl_col = find_col_case_insensitive(reporte_row.to_frame().T, ["Nivel CL"])
        nivel_cien_col = find_col_case_insensitive(reporte_row.to_frame().T, ["Nivel CIEN"])
        nivel_hyst_col = find_col_case_insensitive(reporte_row.to_frame().T, ["Nivel HYST"])

        # M1 level - only if allowed for this segment
        if "M1" in allowed_tests and nivel_m1_col:
            m1_level = reporte_row.get(nivel_m1_col)
            if m1_level is not None and not (isinstance(m1_level, float) and pd.isna(m1_level)):
                idx = level_to_index_m1_cl(m1_level)
                mapping["M1"] = f"M1 N{idx}"

        # CL level - only if allowed for this segment
        if "CL" in allowed_tests and nivel_cl_col:
            cl_level = reporte_row.get(nivel_cl_col)
            if cl_level is not None and not (isinstance(cl_level, float) and pd.isna(cl_level)):
                idx = level_to_index_m1_cl(cl_level)
                mapping["CL"] = f"CL N{idx}"

        # Special handling for CIEN/HYST in S7, S8, S15
        # For S15 behavior flags, use standard logic instead of complex logic
        if test_type_filter in ["S7_BEHAVIOR", "S8_BEHAVIOR"]:
            # Standard CIEN/HYST logic for S15 behavior flags
            # CIEN level - only if allowed for this segment
            if "CIEN" in allowed_tests and nivel_cien_col:
                cien_level = reporte_row.get(nivel_cien_col)
                if cien_level is not None and not (isinstance(cien_level, float) and pd.isna(cien_level)):
                    idx = level_to_index_cien_hyst(cien_level)
                    if variant == "tarde":
                        mapping["CIEN"] = "CIEN Tarde"
                    else:
                        mapping["CIEN"] = f"CIEN N{idx} Mañana"
            
            # HYST level - only if allowed for this segment
            if "HYST" in allowed_tests and nivel_hyst_col:
                hyst_level = reporte_row.get(nivel_hyst_col)
                if hyst_level is not None and not (isinstance(hyst_level, float) and pd.isna(hyst_level)):
                    idx = level_to_index_cien_hyst(hyst_level)
                    if variant == "tarde":
                        mapping["HYST"] = "HYST Tarde"
                    else:
                        mapping["HYST"] = f"HYST N{idx} Mañana"
        elif segmento.upper() in ["S7", "S8", "S15"]:
            # Get M1 and CL levels for conditional logic
            m1_level = None
            cl_level = None
            if nivel_m1_col:
                m1_level = reporte_row.get(nivel_m1_col)
                if m1_level is not None and not (isinstance(m1_level, float) and pd.isna(m1_level)):
                    m1_level = level_to_index_m1_cl(m1_level)
            if nivel_cl_col:
                cl_level = reporte_row.get(nivel_cl_col)
                if cl_level is not None and not (isinstance(cl_level, float) and pd.isna(cl_level)):
                    cl_level = level_to_index_m1_cl(cl_level)

            # CIEN logic for S7 and S15
            if "CIEN" in allowed_tests and nivel_cien_col:
                cien_level = reporte_row.get(nivel_cien_col)
                if cien_level is not None and not (isinstance(cien_level, float) and pd.isna(cien_level)):
                    cien_idx = level_to_index_cien_hyst(cien_level)
                    
                    if variant == "tarde":
                        mapping["CIEN"] = "CIEN Tarde"
                    else:
                        # Morning variant logic
                        if m1_level == 3 and cl_level in [1, 2]:
                            # M1 N3 and CL N1/N2
                            mapping["CIEN"] = f"CIEN N{cien_idx} M1 N3"
                        elif cl_level == 3 and m1_level in [1, 2]:
                            # CL N3 and M1 N1/N2
                            if cien_idx == 2:
                                mapping["CIEN"] = "CIEN N2 CL N3"
                            else:
                                # CIEN N1 - only tarde variant, no mañana
                                mapping["CIEN"] = None
                        elif m1_level == 3 and cl_level == 3:
                            # M1 N3 and CL N3
                            if cien_idx == 1:
                                mapping["CIEN"] = "CIEN N1 M1 N3 CL N3"
                            else:
                                mapping["CIEN"] = "CIEN N2 M1 N3"
                        else:
                            # All other combinations (M1 N1/2 and CL N1/2)
                            mapping["CIEN"] = None  # Only tarde variant

            # HYST logic for S8 and S15
            if "HYST" in allowed_tests and nivel_hyst_col:
                hyst_level = reporte_row.get(nivel_hyst_col)
                if hyst_level is not None and not (isinstance(hyst_level, float) and pd.isna(hyst_level)):
                    hyst_idx = level_to_index_cien_hyst(hyst_level)
                    
                    if variant == "tarde":
                        mapping["HYST"] = "HYST Tarde"
                    else:
                        # Morning variant logic
                        if m1_level == 3 and cl_level in [1, 2]:
                            # M1 N3 and CL N1/N2
                            mapping["HYST"] = f"HYST N{hyst_idx} M1 N3"
                        elif cl_level == 3 and m1_level in [1, 2]:
                            # CL N3 and M1 N1/N2
                            if hyst_idx == 2:
                                mapping["HYST"] = "HYST N2 CL N3"
                            else:
                                # HYST N1 - only tarde variant, no mañana
                                mapping["HYST"] = None
                        elif m1_level == 3 and cl_level == 3:
                            # M1 N3 and CL N3 - use same logic as CL N1/N2
                            if hyst_idx == 2:
                                mapping["HYST"] = "HYST N2 CL N3"
                            else:
                                # HYST N1 - only tarde variant, no mañana
                                mapping["HYST"] = None
                        else:
                            # All other combinations (M1 N1/2 and CL N1/2)
                            mapping["HYST"] = None  # Only tarde variant

        else:
            # Standard CIEN/HYST logic for other segments
            # CIEN level - only if allowed for this segment
            if "CIEN" in allowed_tests and nivel_cien_col:
                cien_level = reporte_row.get(nivel_cien_col)
                if cien_level is not None and not (isinstance(cien_level, float) and pd.isna(cien_level)):
                    idx = level_to_index_cien_hyst(cien_level)
                    if variant == "tarde":
                        mapping["CIEN"] = "CIEN Tarde"
                    else:
                        mapping["CIEN"] = f"CIEN N{idx} Mañana"

            # HYST level - only if allowed for this segment
            if "HYST" in allowed_tests and nivel_hyst_col:
                hyst_level = reporte_row.get(nivel_hyst_col)
                if hyst_level is not None and not (isinstance(hyst_level, float) and pd.isna(hyst_level)):
                    idx = level_to_index_cien_hyst(hyst_level)
                    if variant == "tarde":
                        mapping["HYST"] = "HYST Tarde"
                    else:
                        mapping["HYST"] = f"HYST N{idx} Mañana"

        return mapping

    def find_column_fuzzy(self, df: pd.DataFrame, desired: str) -> Optional[str]:
        """Find a column in df that matches desired, ignoring accents, spaces, and case."""
        desired_norm = normalize_text(desired)
        mapping = {normalize_text(c): c for c in df.columns}
        # try exact normalized
        if desired_norm in mapping:
            return mapping[desired_norm]
        # try some common variants for N1/N2 and spaces/underscores
        variants = [
            desired,
            desired.replace(" ", ""),
            desired.replace(" ", "_"),
            desired.replace("Mañana", "Manana"),
            desired.replace(" ", "").replace("Mañana", "Manana"),
        ]
        for v in variants:
            v_norm = normalize_text(v)
            if v_norm in mapping:
                return mapping[v_norm]
        
        # Debug logging for column search
        logger.debug(f"Column '{desired}' not found in segment sheet. Available columns: {list(df.columns)}")
        return None

    def build_week_tables_html(self, seg_df: pd.DataFrame, col_map: Dict[str, Optional[str]]) -> str:
        """Render weekly tables EXACTLY like the provided layout image.

        We generate one fixed-layout table per Semana value and then place two per page.
        Only placeholders like lunes_9, martes_14, etc., are replaced with actual data.
        All other texts, borders, and styles are preserved.
        """
        if seg_df is None or seg_df.empty:
            return ""

        semana_col = find_col_case_insensitive(seg_df, ["Semana"]) or "Semana"
        dia_col = find_col_case_insensitive(seg_df, ["Día", "Dia"]) or "Día"
        hora_col = find_col_case_insensitive(seg_df, ["Hora"]) or "Hora"

        # Helper to extract combined cell content from segment df
        def slot_value(week_value: Any, day_name: str, hora_target: str) -> str:
            mask = (
                (seg_df[semana_col] == week_value)
                & match_day(seg_df[dia_col], day_name)
                & match_hora(seg_df[hora_col], hora_target)
            )
            slot_df = seg_df[mask]
            if slot_df.empty:
                return ""
            row = slot_df.iloc[0]
            entries: List[str] = []
            for key in ["M1", "CL", "CIEN", "HYST"]:
                desired_col = col_map.get(key)
                if not desired_col:
                    logger.debug(f"No desired column for {key}")
                    continue
                actual_col = self.find_column_fuzzy(seg_df, desired_col)
                if not actual_col or actual_col not in row.index:
                    logger.debug(f"Column '{desired_col}' not found for {key}")
                    continue
                val = row[actual_col]
                if pd.notna(val) and str(val).strip():
                    entries.append(str(val).strip())
                    logger.debug(f"Added {key} content: {str(val).strip()}")
                else:
                    logger.debug(f"Empty value for {key} in column {actual_col}")
            return "<br/>".join(entries)

        # Ordered week values
        weeks = list(pd.unique(seg_df[semana_col]))

        def render_week(week_value: Any) -> str:
            # Compute all placeholders
            # Days as they appear in the table header
            days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
            # Time windows used by placeholders
            # Map placeholders to Hora values present in Segmentos (9,14,18)
            time_map = {
                "_9": "9",
                "_14": "14",
                "_18": "18",
            }
            # Mapping day label -> placeholder base
            base_key = {
                "Lunes": "lunes",
                "Martes": "martes",
                "Miércoles": "miercoles",
                "Jueves": "jueves",
                "Viernes": "viernes",
                "Sábado": "sabado",
            }

            replacements: Dict[str, str] = {}
            # Display labels to match the example screenshot (case/accents)
            display_label = {
                "Lunes": "Lunes",
                "Martes": "Martes",
                "Miércoles": "miércoles",
                "Jueves": "jueves",
                "Viernes": "viernes",
                "Sábado": "sábado",
            }
            for day in days:
                for suff, tb in time_map.items():
                    key = f"{base_key[day]}{suff}"
                    # Saturday has content only for morning according to layout
                    if day == "Sábado" and suff != "_9":
                        replacements[key] = ""
                        continue
                    # First try to load real data; if empty, fall back to showing placeholder text
                    val = slot_value(week_value, day, tb)
                    if not val:
                        val = f"{display_label[day]}{suff}"
                    replacements[key] = val

            # Fixed HTML table copied to match the style and structure in the image
            semana_display = format_semana(week_value)
            table_html = f"""
<div class=\"schedule-week\"> 
  <div class="schedule-week-title" style="font-family:'Times New Roman', Times, serif; font-size:20pt; margin:0 0 20px 0; text-align:center;">Semana {semana_display}</div> 
  <table class="image-style-schedule" style="width:95%; margin:20px auto; border-collapse:collapse; table-layout:fixed; font-family:'Times New Roman', Times, serif; font-size:8pt;">
    <colgroup>
      <col style=\"width:10%\" />
      <col style=\"width:15%\" />
      <col style=\"width:15%\" />
      <col style=\"width:15%\" />
      <col style=\"width:15%\" />
      <col style=\"width:15%\" />
      <col style=\"width:15%\" />
    </colgroup>
    <thead>
      <tr style=\"background:#d9d9d9;\">
        <th style=\"border:1px solid #000; padding:8px; text-align:center;\">{semana_display}</th>
        <th style=\"border:1px solid #000; padding:8px; text-align:center;\">Lunes</th>
        <th style=\"border:1px solid #000; padding:8px; text-align:center;\">Martes</th>
        <th style=\"border:1px solid #000; padding:8px; text-align:center;\">Miércoles</th>
        <th style=\"border:1px solid #000; padding:8px; text-align:center;\">Jueves</th>
        <th style=\"border:1px solid #000; padding:8px; text-align:center;\">Viernes</th>
        <th style=\"border:1px solid #000; padding:8px; text-align:center;\">Sábado</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td style=\"border:1px solid #000; padding:10px; vertical-align:middle; text-align:center;\">(9:00-13:00)</td>
        <td style=\"border:1px solid #000; padding:10px;\">{replacements['lunes_9']}</td>
        <td style=\"border:1px solid #000; padding:10px;\">{replacements['martes_9']}</td>
        <td style=\"border:1px solid #000; padding:10px;\">{replacements['miercoles_9']}</td>
        <td style=\"border:1px solid #000; padding:10px;\">{replacements['jueves_9']}</td>
        <td style=\"border:1px solid #000; padding:10px;\">{replacements['viernes_9']}</td>
        <td style=\"border:1px solid #000; padding:10px;\" rowspan=\"5\">{replacements['sabado_9']}</td>
      </tr>
      <tr>
        <td style=\"border:1px solid #000; padding:10px; vertical-align:middle; text-align:center;\">(13:00-14:00)</td>
        <td colspan=\"5\" style=\"border:1px solid #000; padding:10px; text-align:center; font-style:italic;\">Almuerzo</td>
      </tr>
      <tr>
        <td style=\"border:1px solid #000; padding:10px; vertical-align:middle; text-align:center;\">(14:00-16:00)</td>
        <td style=\"border:1px solid #000; padding:10px;\">{replacements['lunes_14']}</td>
        <td style=\"border:1px solid #000; padding:10px;\">{replacements['martes_14']}</td>
        <td style=\"border:1px solid #000; padding:10px;\">{replacements['miercoles_14']}</td>
        <td style=\"border:1px solid #000; padding:10px;\">{replacements['jueves_14']}</td>
        <td style=\"border:1px solid #000; padding:10px;\">{replacements['viernes_14']}</td>
      </tr>
      <tr>
        <td style=\"border:1px solid #000; padding:10px; vertical-align:middle; text-align:center;\">(16:00-18:00)</td>
        <td colspan=\"5\" style=\"border:1px solid #000; padding:10px; text-align:center; font-style:italic;\">Ayudantías M30M</td>
      </tr>
      <tr>
        <td style=\"border:1px solid #000; padding:10px; vertical-align:middle; text-align:center;\">(18:00-21:00)</td>
        <td style=\"border:1px solid #000; padding:10px;\">{replacements['lunes_18']}</td>
        <td style=\"border:1px solid #000; padding:10px;\">{replacements['martes_18']}</td>
        <td style=\"border:1px solid #000; padding:10px;\">{replacements['miercoles_18']}</td>
        <td style=\"border:1px solid #000; padding:10px;\">{replacements['jueves_18']}</td>
        <td style=\"border:1px solid #000; padding:10px;\">{replacements['viernes_18']}</td>
      </tr>
    </tbody>
  </table>
</div>
"""
            # After filling, remove any leftover placeholder labels like lunes_9, miércoles_14, sabado_9, etc.
            placeholder_pattern = r"(?i)\b(lunes|martes|miercoles|miércoles|jueves|viernes|sabado|sábado)_(9|14|18)\b"
            table_html = re.sub(placeholder_pattern, "", table_html)
            return table_html

        # Render and paginate (ensure consistent spacing and page breaks)
        rendered = [render_week(w) for w in weeks]
        sections: List[str] = []
        for i in range(0, len(rendered), 2):
            pair = rendered[i : i + 2]
            # Add heading only to the first page
            if i == 0:
                sections.append(
                    "<section class=\"page schedule-page\" style=\"page-break-after:always; margin:0; padding:0;\">"
                    + "<div style=\"height:100px\"></div>"
                    + "<h2 style=\"padding: 20px 0; margin-left: 95px;\">3. Calendario Personalizado</h2>"
                    + "<div style=\"height:50px\"></div>"
                    + ("<div style=\"height:100px\"></div>".join(pair))
                    + "</section>"
                )
            else:
                sections.append(
                    "<section class=\"page schedule-page\" style=\"page-break-after:always; margin:0; padding:0;\">"
                    + "<div style=\"height:100px\"></div>"
                    + ("<div style=\"height:100px\"></div>".join(pair))
                    + "</section>"
                )
        return "".join(sections)
