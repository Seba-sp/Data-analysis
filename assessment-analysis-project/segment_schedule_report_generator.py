#!/usr/bin/env python3
"""
Segment Schedule Report Generator

Generates a plan-de-estudio PDF per user using:
- "analisis de datos.xlsx" (sheet: Reporte with columns Nivel M1, Nivel CL, Nivel CIEN, Nivel HYST, Segmento)
- "Segmentos.xlsx" (sheets named like S4, S5, S6 or composite "S1-S2-S13")
- HTML template: templates/plantilla_plan_de_estudio.html

Behavior:
- Replaces <<ALUMNO>> with the user's "nombre_y_apellido"
- Selects the appropriate Segment sheet by the user's "Segmento" value
- Builds weekly schedule tables from the Segment sheet using the user's levels from Reporte sheet
- Morning variant uses CIEN/HYST morning columns based on level; also produces a
  separate variant that uses CIEN Tarde and HYST Tarde columns
- Two schedule tables per page
"""

import os
import re
import logging
import argparse
from typing import Any, Dict, List, Optional

import pandas as pd
from weasyprint import HTML


logger = logging.getLogger(__name__)


def _find_col_case_insensitive(df: pd.DataFrame, targets: List[str]) -> Optional[str]:
    if df is None or df.empty:
        return None
    lower_to_actual = {c.strip().lower(): c for c in df.columns}
    for t in targets:
        key = t.strip().lower()
        if key in lower_to_actual:
            return lower_to_actual[key]
    return None


def _sanitize_filename(name: str) -> str:
    safe = []
    for ch in str(name):
        if ch.isalnum() or ch in ("_", "-", ".", "@"):
            safe.append(ch)
        else:
            safe.append("_")
    return "".join(safe)


class SegmentScheduleReportGenerator:
    def __init__(
        self,
        analysis_excel_path: str = "data/analysis/analisis de datos.xlsx",
        segmentos_excel_path: str = "templates/Segmentos.xlsx",
        html_template_path: str = "templates/plantilla_plan_de_estudio.html",
    ) -> None:
        self.analysis_excel_path = analysis_excel_path
        self.segmentos_excel_path = segmentos_excel_path
        self.html_template_path = html_template_path

        # Cached analysis workbook and sheets
        self._analysis_xl: Optional[pd.ExcelFile] = None
        self._df_reporte: Optional[pd.DataFrame] = None

        # Cached Segmentos workbook mapping: segment_key (e.g., "S7") -> DataFrame
        self._segment_key_to_df: Dict[str, pd.DataFrame] = {}
        
        # Cached checklist workbooks
        self._checklist_workbooks: Dict[str, pd.ExcelFile] = {}

    # ------------------------- Loading -------------------------
    def _ensure_analysis_loaded(self) -> None:
        if self._analysis_xl is not None:
            return
        logger.info(f"Loading analysis workbook: {self.analysis_excel_path}")
        self._analysis_xl = pd.ExcelFile(self.analysis_excel_path)
        self._df_reporte = self._safe_read_sheet(self._analysis_xl, "Reporte")
        
        # Log level distribution for each test type
        self._log_level_distribution()

    def _ensure_segmentos_loaded(self) -> None:
        if self._segment_key_to_df:
            return
        logger.info(f"Loading segmentos workbook: {self.segmentos_excel_path}")
        seg_xl = pd.ExcelFile(self.segmentos_excel_path)
        
        # Special handling for S7, S8, S15 - they all use the "S7-S8-S15" sheet
        special_segments = {"S7", "S8", "S15"}
        
        for sheet_name in seg_xl.sheet_names:
            if not sheet_name or not sheet_name.strip().upper().startswith("S"):
                continue
            df = seg_xl.parse(sheet_name=sheet_name)
            keys = [s.strip() for s in sheet_name.split("-") if s.strip()]
            for key in keys:
                # Normalize like "S7" etc
                norm_key = key.upper()
                
                # Special case: S7, S8, S15 all use the "S7-S8-S15" sheet
                if norm_key in special_segments:
                    self._segment_key_to_df[norm_key] = df
                else:
                    self._segment_key_to_df[norm_key] = df
                    
        logger.info(f"Loaded {len(self._segment_key_to_df)} segment sheet mappings")

    def _log_level_distribution(self) -> None:
        """Log the distribution of levels for each test type."""
        if self._df_reporte is None or self._df_reporte.empty:
            return
            
        # Find level columns
        nivel_m1_col = _find_col_case_insensitive(self._df_reporte, ["Nivel M1"])
        nivel_cl_col = _find_col_case_insensitive(self._df_reporte, ["Nivel CL"])
        nivel_cien_col = _find_col_case_insensitive(self._df_reporte, ["Nivel CIEN"])
        nivel_hyst_col = _find_col_case_insensitive(self._df_reporte, ["Nivel HYST"])
        
        logger.info("=== Level Distribution Analysis ===")
        
        # Analyze M1 levels
        if nivel_m1_col:
            m1_counts = self._df_reporte[nivel_m1_col].value_counts(dropna=False)
            logger.info(f"M1 Level Distribution:")
            for level, count in m1_counts.items():
                level_str = "NaN" if pd.isna(level) else str(level)
                logger.info(f"  {level_str}: {count}")
        else:
            logger.info("M1 Level column not found")
            
        # Analyze CL levels
        if nivel_cl_col:
            cl_counts = self._df_reporte[nivel_cl_col].value_counts(dropna=False)
            logger.info(f"CL Level Distribution:")
            for level, count in cl_counts.items():
                level_str = "NaN" if pd.isna(level) else str(level)
                logger.info(f"  {level_str}: {count}")
        else:
            logger.info("CL Level column not found")
            
        # Analyze CIEN levels
        if nivel_cien_col:
            cien_counts = self._df_reporte[nivel_cien_col].value_counts(dropna=False)
            logger.info(f"CIEN Level Distribution:")
            for level, count in cien_counts.items():
                level_str = "NaN" if pd.isna(level) else str(level)
                logger.info(f"  {level_str}: {count}")
        else:
            logger.info("CIEN Level column not found")
            
        # Analyze HYST levels
        if nivel_hyst_col:
            hyst_counts = self._df_reporte[nivel_hyst_col].value_counts(dropna=False)
            logger.info(f"HYST Level Distribution:")
            for level, count in hyst_counts.items():
                level_str = "NaN" if pd.isna(level) else str(level)
                logger.info(f"  {level_str}: {count}")
        else:
            logger.info("HYST Level column not found")
            
        logger.info("=== End Level Distribution ===")

    def _safe_read_sheet(self, xl: pd.ExcelFile, name: str) -> pd.DataFrame:
        try:
            return xl.parse(sheet_name=name)
        except ValueError:
            logger.warning(f"Sheet '{name}' not found in workbook {xl.io}")
            return pd.DataFrame()

    def _load_checklist_workbook(self, test_type: str) -> pd.ExcelFile:
        """Load checklist workbook for a specific test type."""
        if test_type not in self._checklist_workbooks:
            checklist_path = f"data/Checklist/{test_type}.xlsx"
            logger.info(f"Loading checklist workbook: {checklist_path}")
            self._checklist_workbooks[test_type] = pd.ExcelFile(checklist_path)
        return self._checklist_workbooks[test_type]

    def _get_checklist_sheets_for_nivel(self, test_type: str, nivel: str) -> List[str]:
        """Get the appropriate checklist sheets based on test type and nivel."""
        if test_type == "M1":
            if nivel == "Nivel 1":
                return ["N1 1", "N1 2", "0"]
            elif nivel == "Nivel 2":
                return ["N2 1", "0"]
            elif nivel == "Nivel 3":
                return ["N3", "0"]
        elif test_type == "CL":
            if nivel == "Nivel 1":
                return ["N1", "N2", "N3"]
            elif nivel == "Nivel 2":
                return ["N2", "N3"]
            elif nivel == "Nivel 3":
                return ["N3"]
        elif test_type == "CIEN":
            if nivel == "Nivel 1":
                return ["N1 1", "N1 2", "0"]
            elif nivel == "Nivel 2":
                return ["N2", "0"]
        elif test_type == "HYST":
            if nivel == "General":
                return ["Nivel General", "Nivel avanzado"]
            elif nivel == "Avanzado":
                return ["Nivel avanzado"]
        
        # Default fallback
        return ["0"]

    def _get_student_lectures_results(self, reporte_row: pd.Series, test_type: str) -> Dict[str, str]:
        """Get student's passed/failed lectures for a specific test type."""
        # Load the analysis workbook to get the test results
        self._ensure_analysis_loaded()
        
        # Get the sheet with test results
        test_sheet = None
        if test_type == "M1":
            test_sheet = self._safe_read_sheet(self._analysis_xl, "M1")
        elif test_type == "CL":
            test_sheet = self._safe_read_sheet(self._analysis_xl, "CL")
        elif test_type == "CIEN":
            test_sheet = self._safe_read_sheet(self._analysis_xl, "CIEN")
        elif test_type == "HYST":
            test_sheet = self._safe_read_sheet(self._analysis_xl, "HYST")
        
        if test_sheet is None:
            return {}
        
        # Find the student's row in the test results
        col_user_id = _find_col_case_insensitive(test_sheet, ["user_id"]) or "user_id"
        col_email = _find_col_case_insensitive(test_sheet, ["email"]) or "email"
        
        user_id = reporte_row.get(col_user_id)
        email = reporte_row.get(col_email)
        
        student_row = self._find_user_row(test_sheet, user_id, email)
        if student_row is None:
            return {}
        
        # Extract lecture results based on test type
        lecture_results = {}
        
        if test_type == "M1":
            # Look for passed_lectures and failed_lectures columns
            passed_col = _find_col_case_insensitive(test_sheet, ["passed_lectures"])
            failed_col = _find_col_case_insensitive(test_sheet, ["failed_lectures"])
            
            if passed_col and passed_col in student_row:
                passed_lectures = student_row[passed_col]
                if pd.notna(passed_lectures) and passed_lectures != "":
                    # Split the passed lectures string and mark each as "Aprobado"
                    if isinstance(passed_lectures, str):
                        # Handle both " | " and "|" separators
                        passed_list = [lecture.strip() for lecture in passed_lectures.replace(" | ", "|").split("|")]
                        for lecture in passed_list:
                            if lecture:
                                lecture_results[lecture] = "Aprobado"
            
            if failed_col and failed_col in student_row:
                failed_lectures = student_row[failed_col]
                if pd.notna(failed_lectures) and failed_lectures != "":
                    # Split the failed lectures string and mark each as "Reprobado"
                    if isinstance(failed_lectures, str):
                        # Handle both " | " and "|" separators
                        failed_list = [lecture.strip() for lecture in failed_lectures.replace(" | ", "|").split("|")]
                        for lecture in failed_list:
                            if lecture:
                                lecture_results[lecture] = "Reprobado"
            
            # If no passed/failed columns found, fall back to individual lecture columns
            if not lecture_results:
                for col in test_sheet.columns:
                    if "lecture" in col.lower() or "tema" in col.lower() or "materia" in col.lower():
                        lecture_name = col
                        result = student_row.get(col)
                        if pd.notna(result) and result != "":
                            # Determine if passed or failed based on the result
                            if isinstance(result, (int, float)):
                                # If numeric, assume it's a score
                                lecture_results[lecture_name] = "Aprobado" if result >= 0.6 else "Reprobado"
                            else:
                                # If string, use as is
                                lecture_results[lecture_name] = str(result)
        
        elif test_type == "CIEN":
            # For CIEN, get results from the main CIEN sheet in analysis workbook
            passed_col = _find_col_case_insensitive(test_sheet, ["passed_lectures"])
            failed_col = _find_col_case_insensitive(test_sheet, ["failed_lectures"])
            
            if passed_col and passed_col in student_row:
                passed_lectures = student_row[passed_col]
                if pd.notna(passed_lectures) and passed_lectures != "":
                    if isinstance(passed_lectures, str):
                        # Handle both " | " and "|" separators
                        passed_list = [lecture.strip() for lecture in passed_lectures.replace(" | ", "|").split("|")]
                        for lecture in passed_list:
                            if lecture:
                                lecture_results[lecture] = "Aprobado"
            
            if failed_col and failed_col in student_row:
                failed_lectures = student_row[failed_col]
                if pd.notna(failed_lectures) and failed_lectures != "":
                    if isinstance(failed_lectures, str):
                        # Handle both " | " and "|" separators
                        failed_list = [lecture.strip() for lecture in failed_lectures.replace(" | ", "|").split("|")]
                        for lecture in failed_list:
                            if lecture:
                                lecture_results[lecture] = "Reprobado"
        
        elif test_type in ["CL", "HYST"]:
            # Similar logic for other test types
            passed_col = _find_col_case_insensitive(test_sheet, ["passed_lectures"])
            failed_col = _find_col_case_insensitive(test_sheet, ["failed_lectures"])
            
            if passed_col and passed_col in student_row:
                passed_lectures = student_row[passed_col]
                if pd.notna(passed_lectures) and passed_lectures != "":
                    if isinstance(passed_lectures, str):
                        # Handle both " | " and "|" separators
                        passed_list = [lecture.strip() for lecture in passed_lectures.replace(" | ", "|").split("|")]
                        for lecture in passed_list:
                            if lecture:
                                lecture_results[lecture] = "Aprobado"
            
            if failed_col and failed_col in student_row:
                failed_lectures = student_row[failed_col]
                if pd.notna(failed_lectures) and failed_lectures != "":
                    if isinstance(failed_lectures, str):
                        # Handle both " | " and "|" separators
                        failed_list = [lecture.strip() for lecture in failed_lectures.replace(" | ", "|").split("|")]
                        for lecture in failed_list:
                            if lecture:
                                lecture_results[lecture] = "Reprobado"
            
            # Fall back to individual lecture columns
            if not lecture_results:
                for col in test_sheet.columns:
                    if "lecture" in col.lower() or "tema" in col.lower() or "materia" in col.lower() or "skill" in col.lower():
                        lecture_name = col
                        result = student_row.get(col)
                        if pd.notna(result) and result != "":
                            if isinstance(result, (int, float)):
                                lecture_results[lecture_name] = "Aprobado" if result >= 0.6 else "Reprobado"
                            else:
                                lecture_results[lecture_name] = str(result)
        
        return lecture_results

    def _generate_checklist_tables_html(self, reporte_row: pd.Series, test_type: str, is_cuarto_medio: bool = False) -> str:
        """Generate HTML tables for checklist based on student's test type and level."""
        # For Cuarto Medio students, always generate checklists regardless of preparar_* values
        if not is_cuarto_medio:
            # Check if student should prepare this test (only for Egresado students)
            prepare_col_map = {
                "M1": "preparar_matemática_m1",
                "CL": "preparar_competencia_lectora", 
                "CIEN": "preparar_ciencias",
                "HYST": "preparar_historia"
            }
            prepare_col = prepare_col_map.get(test_type, f"preparar_{test_type.lower()}")
            
            # Special logic for M1: Show checklist if student is preparing for M1, OR completed M1, OR is preparing for M2
            if test_type == "M1":
                preparar_m1 = reporte_row.get("preparar_matemática_m1", 0)
                rindio_m1 = reporte_row.get("Rindió M1", 0)
                preparar_m2 = reporte_row.get("preparar_matemática_m2", 0)
                
                # Show M1 checklist if: preparing for M1, OR completed M1, OR preparing for M2
                if not (preparar_m1 == 1 or rindio_m1 == 1 or preparar_m2 == 1):
                    return ""
            elif test_type == "CL":
                # Special logic for CL: Show checklist if student is preparing for CL, OR completed CL
                preparar_cl = reporte_row.get("preparar_competencia_lectora", 0)
                rindio_cl = reporte_row.get("Rindió CL", 0)
                
                # Show CL checklist if: preparing for CL, OR completed CL
                if not (preparar_cl == 1 or rindio_cl == 1):
                    return ""
            else:
                # For other test types, use the original logic
                if prepare_col not in reporte_row or reporte_row[prepare_col] != 1:
                    return ""
        
        # Load checklist workbook
        try:
            checklist_xl = self._load_checklist_workbook(test_type)
        except Exception as e:
            logger.warning(f"Could not load checklist for {test_type}: {e}")
            return ""
        
        # Check if student completed the test
        rindio_col = f"Rindió {test_type}"
        rindio_value = reporte_row.get(rindio_col, 0)
        
        # Get student's nivel
        nivel_col = f"Nivel {test_type}"
        nivel = reporte_row.get(nivel_col, "")
        
        if is_cuarto_medio:
            # For Cuarto medio students
            if test_type == "CL":
                # For CL, show skills table if student completed the test
                rindio_cl = reporte_row.get("Rindió CL", 0)
                if rindio_cl == 1:
                    return self._generate_cl_skill_percentage_table(reporte_row, is_cuarto_medio)
                else:
                    return ""
            elif test_type == "CIEN":
                # For CIEN, always show "Cuarto medio" sheet, but only fill when completed
                return self._generate_cuarto_medio_checklist_table(checklist_xl, reporte_row, test_type)
            else:
                # For M1, always generate the table from "Cuarto medio" sheet
                return self._generate_cuarto_medio_checklist_table(checklist_xl, reporte_row, test_type)
        else:
            # For Egresado students:
            if test_type == "HYST":
                # Special handling for HYST: Show both Nivel General and Nivel Avanzado tables
                # regardless of whether student completed the test or not
                return self._generate_egresado_checklist_tables(checklist_xl, reporte_row, test_type, nivel)
            else:
                # For other test types:
                if rindio_value != 1:
                    # If Egresado student didn't complete the test, show Nivel 1 format (empty Check cells)
                    return self._generate_egresado_checklist_tables(checklist_xl, reporte_row, test_type, "Nivel 1")
                else:
                    # If Egresado student completed the test, use their actual nivel
                    return self._generate_egresado_checklist_tables(checklist_xl, reporte_row, test_type, nivel)



    def _calculate_column_widths(self, df: pd.DataFrame, test_type: str = "M1") -> Dict[str, str]:
        """Calculate optimal column widths based on content length and test type."""
        widths = {}
        total_width = 100  # Total percentage
        
        # Get maximum content length for each column
        max_lengths = {}
        for col in df.columns:
            # Get the maximum length of header and all values
            header_length = len(str(col))
            max_value_length = df[col].astype(str).str.len().max()
            max_lengths[col] = max(header_length, max_value_length)
        
        # Calculate total content length
        total_content_length = sum(max_lengths.values())
        
        # Define column priorities for each test type
        if test_type == "M1":
            column_priorities = {
                'Nivel': 12,      # Narrow for level column
                'Día': 10,        # Narrow for day column
                'Tarea a realizar': 35,  # Wide for task description
                'Tiempo (en horas)': 10,  # Medium for time column
                'Check': 10       # Medium for check column
            }
        elif test_type == "CL":
            column_priorities = {
                'Nivel': 10,      # Narrow for level column
                'Día': 8,         # Narrow for day column
                'Habilidad': 15,  # Medium for skill column (CL specific)
                'Tarea a realizar': 35,  # Wide for task description
                'Tipo de texto': 12,  # Medium for text type column (CL specific)
                'Tiempo (en horas)': 10,  # Medium for time column
                'Check': 10       # Medium for check column
            }
        elif test_type == "HYST":
            column_priorities = {
                'Nivel': 10,      # Narrow for level column
                'Día': 8,         # Narrow for day column
                'Tarea a realizar': 35,  # Wide for task description
                'Tiempo (en horas)': 10,  # Medium for time column
                'Check': 10       # Medium for check column
            }
        elif test_type == "CIEN":
            column_priorities = {
                'Nivel': 10,      # Narrow for level column
                'Día': 8,         # Narrow for day column
                'Tarea a realizar': 35,  # Wide for task description
                'Tiempo (en horas)': 10,  # Medium for time column
                'Check': 10       # Medium for check column
            }
        else:
            # Default priorities for other test types
            column_priorities = {
                'Nivel': 12,      # Narrow for level column
                'Día': 10,        # Narrow for day column
                'Tarea a realizar': 35,  # Wide for task description
                'Tiempo (en horas)': 10,  # Medium for time column
                'Check': 10       # Medium for check column
            }
        
        # Calculate percentage for each column
        for col in df.columns:
            if col in column_priorities:
                # Use predefined widths for known columns
                widths[col] = f"{column_priorities[col]}%"
            elif total_content_length > 0:
                percentage = (max_lengths[col] / total_content_length) * total_width
                # Set minimum and maximum bounds
                percentage = max(8, min(35, percentage))  # Between 8% and 35%
                widths[col] = f"{percentage:.1f}%"
            else:
                widths[col] = "16.67%"  # Equal distribution for 6 columns
        
        return widths

    def _generate_cuarto_medio_checklist_table(self, checklist_xl: pd.ExcelFile, reporte_row: pd.Series, test_type: str) -> str:
        """Generate checklist table for Cuarto medio students."""
        try:
            df = checklist_xl.parse("Cuarto medio")
        except Exception as e:
            logger.warning(f"Could not parse 'Cuarto medio' sheet from {test_type} checklist: {e}")
            return ""
        
        # Get student's lecture results
        lecture_results = self._get_student_lectures_results(reporte_row, test_type)
        
        # Get all columns from the dataframe
        columns = df.columns.tolist()
        
        # Calculate column widths
        column_widths = self._calculate_column_widths(df, test_type)
        
        # Add title for checklist on the first page
        html = ""
        if test_type == "M1":
            html += f"""
            <div style="margin: 40px 0 20px 0; text-align: center;">
                <h2 style="font-family:'Times New Roman', Times, serif; font-size: 18px; font-weight: bold; margin: 0; color: #333;">
                    Checklist M1
                </h2>
            </div>
            """
        elif test_type == "CIEN":
            html += f"""
            <div style="page-break-before: always; margin: 40px 0 20px 0; text-align: center;">
                <h2 style="font-family:'Times New Roman', Times, serif; font-size: 18px; font-weight: bold; margin: 0; color: #333;">
                    Checklist CIEN
                </h2>
            </div>
            """
        
        # Generate HTML table with pagination (20 rows per page)
        rows_per_page = 20
        total_rows = len(df)
        
        for page_start in range(0, total_rows, rows_per_page):
            page_end = min(page_start + rows_per_page, total_rows)
            page_df = df.iloc[page_start:page_end]
            
            html += f"""
            <div class="checklist-section" style="margin: 30px 20px; page-break-inside: avoid;">
                <table class="checklist-table" style="width: calc(100% - 40px); border-collapse:collapse; margin: 0 auto; font-size:11px; font-family:'Times New Roman', Times, serif; table-layout: fixed;">
                    <colgroup>
            """
            
            # Add column width definitions
            for col in columns:
                width = column_widths.get(col, "16.67%")
                html += f'<col style="width: {width};">'
            
            html += """
                    </colgroup>
                    <thead>
                        <tr style="background:#d9d9d9;">
            """
            
            # Add all columns as headers
            for col in columns:
                html += f'<th style="border:1px solid #000; padding:6px 4px; text-align:left; font-weight:bold; word-wrap: break-word; font-size:10px;">{col}</th>'
            
            html += """
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for _, row in page_df.iterrows():
                tarea = row.get('Tarea a realizar', '')
                check_value = ''
                
                # Check if student completed the test
                rindio_col = f"Rindió {test_type}"
                rindio_value = reporte_row.get(rindio_col, 0)
                
                # Only fill check values if student completed the test
                if rindio_value == 1 and tarea in lecture_results:
                    check_value = lecture_results[tarea]
                
                html += '<tr>'
                for col in columns:
                    if col == 'Check':
                        # Add conditional styling for Cuarto medio students
                        cell_style = "border:1px solid #000; padding:4px 6px; vertical-align:top; word-wrap: break-word; font-size:10px;"
                        if rindio_value == 1 and check_value:
                            if check_value == "Aprobado":
                                cell_style += "background-color: #90EE90;"  # Light green
                            elif check_value == "Reprobado":
                                cell_style += "background-color: #FFB6C1;"  # Light red
                        html += f'<td style="{cell_style}">{check_value}</td>'
                    else:
                        html += f'<td style="border:1px solid #000; padding:4px 6px; vertical-align:top; word-wrap: break-word; font-size:10px;">{row.get(col, "")}</td>'
                html += '</tr>'
            
            html += """
                    </tbody>
                </table>
            </div>
            """
            
            # Add page break if not the last page
            if page_end < total_rows:
                html += '<div style="page-break-before: always;"></div>'
        
        return html

    def _generate_egresado_checklist_tables(self, checklist_xl: pd.ExcelFile, reporte_row: pd.Series, test_type: str, nivel: str) -> str:
        """Generate checklist tables for Egresado students based on their nivel."""
        sheets = self._get_checklist_sheets_for_nivel(test_type, nivel)
        html = ""
        
        # Get student's lecture results
        lecture_results = self._get_student_lectures_results(reporte_row, test_type)
        
        # Add title for M1 checklist on the first page
        if test_type == "M1":
            html += f"""
            <div style="margin: 40px 0 20px 0; text-align: center;">
                <h2 style="font-family:'Times New Roman', Times, serif; font-size: 18px; font-weight: bold; margin: 0; color: #333;">
                    Checklist M1
                </h2>
            </div>
            """
        elif test_type == "CL":
            html += f"""
            <div style="page-break-before: always; margin: 40px 0 20px 0; text-align: center;">
                <h2 style="font-family:'Times New Roman', Times, serif; font-size: 18px; font-weight: bold; margin: 0; color: #333;">
                    Checklist CL
                </h2>
            </div>
            """
        elif test_type == "HYST":
            html += f"""
            <div style="page-break-before: always; margin: 40px 0 20px 0; text-align: center;">
                <h2 style="font-family:'Times New Roman', Times, serif; font-size: 18px; font-weight: bold; margin: 0; color: #333;">
                    Checklist HYST
                </h2>
            </div>
            """
        elif test_type == "CIEN":
            html += f"""
            <div style="page-break-before: always; margin: 40px 0 20px 0; text-align: center;">
                <h2 style="font-family:'Times New Roman', Times, serif; font-size: 18px; font-weight: bold; margin: 0; color: #333;">
                    Checklist CIEN
                </h2>
            </div>
            """
        
        for i, sheet_name in enumerate(sheets):
            try:
                df = checklist_xl.parse(sheet_name)
            except Exception as e:
                logger.warning(f"Could not parse sheet '{sheet_name}' from {test_type} checklist: {e}")
                continue
            
            # Add page break before the last table if it's likely to be large (N3 for CL, "0" for CIEN)
            # But only if there are multiple sheets (not for CL Nivel 3 which only has N3)
            needs_page_break = i == len(sheets) - 1 and sheet_name in ["N3", "0"] and len(sheets) > 1
            if needs_page_break:
                html += '<div style="page-break-before: always;"></div>'
            
            # Get all columns from the dataframe
            columns = df.columns.tolist()
            
            # Calculate column widths with better optimization
            column_widths = self._calculate_column_widths(df, test_type)
                    
            # Generate HTML table with pagination (20 rows per page)
            rows_per_page = 20
            total_rows = len(df)
            
            for page_start in range(0, total_rows, rows_per_page):
                page_end = min(page_start + rows_per_page, total_rows)
                page_df = df.iloc[page_start:page_end]
                
                # Adjust margin based on whether this is the first page or a continuation
                if page_start == 0:
                    margin_style = "margin: 30px 20px;"
                else:
                    margin_style = "margin: 60px 20px 30px 20px;"  # Extra top margin for continuation pages
                
                html += f"""
                <div class="checklist-section" style="{margin_style} page-break-inside: avoid;">
                    <table class="checklist-table" style="width: calc(100% - 40px); border-collapse:collapse; margin: 0 auto; font-size:11px; font-family:'Times New Roman', Times, serif; table-layout: fixed;">
                        <colgroup>
                """
                
                # Add column width definitions
                for col in columns:
                    width = column_widths.get(col, "16.67%")
                    html += f'<col style="width: {width};">'
                
                html += """
                        </colgroup>
                        <thead>
                            <tr style="background:#d9d9d9;">
                """
                
                # Add all columns as headers
                for col in columns:
                    html += f'<th style="border:1px solid #000; padding:6px 4px; text-align:left; font-weight:bold; word-wrap: break-word; font-size:10px;">{col}</th>'
                
                html += """
                            </tr>
                        </thead>
                        <tbody>
                """
                
                for _, row in page_df.iterrows():
                    tarea = row.get('Tarea a realizar', '')
                    check_value = ''
                    
                    # Check if student completed the test
                    rindio_col = f"Rindió {test_type}"
                    rindio_value = reporte_row.get(rindio_col, 0)
                    
                    # Only fill check values for students who completed the test
                    if test_type == "HYST":
                        # For HYST, fill check values if student completed the test
                        if rindio_value == 1 and tarea in lecture_results:
                            check_value = lecture_results[tarea]
                    elif test_type == "CIEN":
                        # For CIEN, fill check values if student completed the test
                        if rindio_value == 1 and tarea in lecture_results:
                            check_value = lecture_results[tarea]
                    else:
                        # For other test types, only fill check values for students who completed the test and are not nivel 1
                        if rindio_value == 1 and nivel != "Nivel 1" and tarea in lecture_results:
                            check_value = lecture_results[tarea]
                    
                    html += '<tr>'
                    for col in columns:
                        if col == 'Check':
                            # Add conditional styling for completed tests
                            cell_style = "border:1px solid #000; padding:4px 6px; vertical-align:top; word-wrap: break-word; font-size:10px;"
                            if test_type == "HYST":
                                # For HYST, apply styling if student completed the test
                                if rindio_value == 1 and check_value:
                                    if check_value == "Aprobado":
                                        cell_style += "background-color: #90EE90;"  # Light green
                                    elif check_value == "Reprobado":
                                        cell_style += "background-color: #FFB6C1;"  # Light red
                            elif test_type == "CIEN":
                                # For CIEN, apply styling if student completed the test
                                if rindio_value == 1 and check_value:
                                    if check_value == "Aprobado":
                                        cell_style += "background-color: #90EE90;"  # Light green
                                    elif check_value == "Reprobado":
                                        cell_style += "background-color: #FFB6C1;"  # Light red
                            else:
                                # For other test types, apply styling for Nivel 2 and Nivel 3
                                if rindio_value == 1 and nivel in ["Nivel 2", "Nivel 3"] and check_value:
                                    if check_value == "Aprobado":
                                        cell_style += "background-color: #90EE90;"  # Light green
                                    elif check_value == "Reprobado":
                                        cell_style += "background-color: #FFB6C1;"  # Light red
                            html += f'<td style="{cell_style}">{check_value}</td>'
                        else:
                            html += f'<td style="border:1px solid #000; padding:4px 6px; vertical-align:top; word-wrap: break-word; font-size:10px;">{row.get(col, "")}</td>'
                    html += '</tr>'
                
                html += """
                        </tbody>
                    </table>
                </div>
                """
                
                # Add page break if not the last page
                if page_end < total_rows:
                    html += '<div style="page-break-before: always;"></div>'
            
            # Add separation between different sheets
            if sheet_name != sheets[-1]:  # If not the last sheet
                # Add extra separation before "0" sheet
                if sheets[sheets.index(sheet_name) + 1] == "0":
                    html += '<div style="height: 60px;"></div>'
                else:
                    html += '<div style="height: 40px;"></div>'
        
        # Add skill percentage table for CL if student completed the test
        if test_type == "CL":
            rindio_col = f"Rindió {test_type}"
            rindio_value = reporte_row.get(rindio_col, 0)
            
            if rindio_value == 1:
                html += self._generate_cl_skill_percentage_table(reporte_row, is_cuarto_medio=False)
        
        return html

    def _generate_cl_skill_percentage_table(self, reporte_row: pd.Series, is_cuarto_medio: bool = False) -> str:
        """Generate CL skill percentage table for students who completed the CL test."""
        # Get student's CL test results
        self._ensure_analysis_loaded()
        cl_test_sheet = self._safe_read_sheet(self._analysis_xl, "CL")
        
        if cl_test_sheet is None:
            return ""
        
        # Find the student's row in the CL test results
        col_user_id = _find_col_case_insensitive(cl_test_sheet, ["user_id"]) or "user_id"
        col_email = _find_col_case_insensitive(cl_test_sheet, ["email"]) or "email"
        
        user_id = reporte_row.get(col_user_id)
        email = reporte_row.get(col_email)
        
        student_row = self._find_user_row(cl_test_sheet, user_id, email)
        if student_row is None:
            return ""
        
        # Get skill percentage values
        skill_localizar = student_row.get('skill_localizar_percentage', 0)
        skill_interpretar = student_row.get('skill_interpretar_percentage', 0)
        skill_evaluar = student_row.get('skill_evaluar_percentage', 0)
        
        # Format percentages - convert decimal to percentage (e.g., 0.7 -> 70%)
        def format_percentage(value):
            if pd.isna(value) or value is None:
                return "0%"
            try:
                # Convert decimal to percentage (multiply by 100)
                percentage = float(value) * 100
                return f"{percentage:.0f}%"
            except (ValueError, TypeError):
                return "0%"
        
        # Add title and page break for Cuarto medio students
        title_html = ""
        if is_cuarto_medio:
            title_html = """
            <div style="page-break-before: always; margin: 40px 0 20px 0; text-align: center;">
                <h2 style="font-family:'Times New Roman', Times, serif; font-size: 18px; font-weight: bold; margin: 0; color: #333;">
                    Checklist CL
                </h2>
            </div>
            """
        
        html = f"""
        {title_html}
        <div class="checklist-section" style="margin: 30px 20px; page-break-inside: avoid;">
            <table class="checklist-table" style="width: calc(100% - 40px); border-collapse:collapse; margin: 0 auto; font-size:11px; font-family:'Times New Roman', Times, serif; table-layout: fixed;">
                <colgroup>
                    <col style="width: 50%;">
                    <col style="width: 50%;">
                </colgroup>
                <thead>
                    <tr style="background:#d9d9d9;">
                        <th style="border:1px solid #000; padding:6px 4px; text-align:left; font-weight:bold; word-wrap: break-word; font-size:10px;">Habilidad</th>
                        <th style="border:1px solid #000; padding:6px 4px; text-align:left; font-weight:bold; word-wrap: break-word; font-size:10px;">% Dominio</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td style="border:1px solid #000; padding:4px 6px; vertical-align:top; word-wrap: break-word; font-size:10px;">Localizar</td>
                        <td style="border:1px solid #000; padding:4px 6px; vertical-align:top; word-wrap: break-word; font-size:10px;">{format_percentage(skill_localizar)}</td>
                    </tr>
                    <tr>
                        <td style="border:1px solid #000; padding:4px 6px; vertical-align:top; word-wrap: break-word; font-size:10px;">Interpretar</td>
                        <td style="border:1px solid #000; padding:4px 6px; vertical-align:top; word-wrap: break-word; font-size:10px;">{format_percentage(skill_interpretar)}</td>
                    </tr>
                    <tr>
                        <td style="border:1px solid #000; padding:4px 6px; vertical-align:top; word-wrap: break-word; font-size:10px;">Evaluar</td>
                        <td style="border:1px solid #000; padding:4px 6px; vertical-align:top; word-wrap: break-word; font-size:10px;">{format_percentage(skill_evaluar)}</td>
                    </tr>
                </tbody>
            </table>
        </div>
        """
        
        return html

    def _add_checklist_to_html(self, html_content: str, reporte_row: pd.Series, is_cuarto_medio: bool = False) -> str:
        """Add checklist tables to the HTML content."""
        checklist_html = ""
        
        if is_cuarto_medio:
            # For Cuarto medio students, handle each test type differently
            test_types = ["M1", "CL", "CIEN"]  # Exclude HYST for Cuarto medio
            generated_checklists = []
            
            for test_type in test_types:
                if test_type == "CL":
                    # For CL, only show if student completed the test
                    rindio_cl = reporte_row.get("Rindió CL", 0)
                    if rindio_cl == 1:
                        generated_checklists.append(self._generate_checklist_tables_html(reporte_row, test_type, is_cuarto_medio))
                elif test_type == "CIEN":
                    # For CIEN, always show (but only fill when completed)
                    generated_checklists.append(self._generate_checklist_tables_html(reporte_row, test_type, is_cuarto_medio))
                else:
                    # For M1, always show
                    generated_checklists.append(self._generate_checklist_tables_html(reporte_row, test_type, is_cuarto_medio))
            
            # Join the generated checklists with spacing
            for i, checklist in enumerate(generated_checklists):
                checklist_html += checklist
                # Add spacing between different assessment types (except after the last one)
                if i < len(generated_checklists) - 1:
                    checklist_html += '<div style="height: 40px;"></div>'
        else:
            # For Egresado students, use original logic
            test_types = ["M1", "CL", "CIEN", "HYST"]
            
            # Check which checklists will actually be generated
            actual_checklists = []
            for test_type in test_types:
                checklist_content = self._generate_checklist_tables_html(reporte_row, test_type, is_cuarto_medio)
                if checklist_content:  # Only add non-empty checklists
                    actual_checklists.append((test_type, checklist_content))
            
            # Check if HYST is the only checklist (S11 case)
            hyst_only = len(actual_checklists) == 1 and actual_checklists[0][0] == "HYST"
            
            # Generate checklists with special handling for HYST-only case
            for i, (test_type, checklist_content) in enumerate(actual_checklists):
                if test_type == "HYST" and hyst_only:
                    # For HYST-only case (S11), remove the page break only from the title div
                    # Look for the specific HYST title div with page-break-before
                    title_pattern = '<div style="page-break-before: always; margin: 40px 0 20px 0; text-align: center;">'
                    title_replacement = '<div style="margin: 40px 0 20px 0; text-align: center;">'
                    checklist_content = checklist_content.replace(title_pattern, title_replacement)
                
                checklist_html += checklist_content
                
                # Add spacing between different assessment types (except after the last one)
                if i < len(actual_checklists) - 1:
                    checklist_html += '<div style="height: 40px;"></div>'
        
        # Replace placeholder in template
        if "<<CHECKLIST>>" in html_content:
            html_content = html_content.replace("<<CHECKLIST>>", checklist_html)
        else:
            # If no placeholder, append after schedule tables
            html_content = html_content.replace("</body>", f"{checklist_html}</body>")
        
        return html_content

    # ------------------------- User helpers -------------------------
    def _find_user_row(self, df: pd.DataFrame, user_id: Optional[str], email: Optional[str]) -> Optional[pd.Series]:
        if df is None or df.empty:
            return None
        cols = {c.lower(): c for c in df.columns}
        id_col = cols.get("user_id")
        email_col = cols.get("email")
        row = None
        if user_id and id_col in df.columns:
            matches = df[df[id_col].astype(str) == str(user_id)]
            if not matches.empty:
                row = matches.iloc[0]
        if row is None and email and email_col in df.columns:
            matches = df[df[email_col].astype(str) == str(email)]
            if not matches.empty:
                row = matches.iloc[0]
        return row

    # ------------------------- Level helpers -------------------------
    def _level_to_index_m1_cl(self, level_value: Any) -> int:
        # Accept values like "Nivel 1", "1", 1 -> return 1..3 (clamp to 1..3)
        if level_value is None or (isinstance(level_value, float) and pd.isna(level_value)):
            return 1
        s = str(level_value).strip().lower()
        for n in (1, 2, 3):
            if s == f"nivel {n}" or s == str(n):
                return n
        # Default to 1
        return 1

    def _level_to_index_cien_hyst(self, level_value: Any) -> int:
        # CIEN/HYST levels expected: "General" or "Avanzado"
        if level_value is None or (isinstance(level_value, float) and pd.isna(level_value)):
            return 1
        s = str(level_value).strip().lower()
        if s == "avanzado":
            return 2
        elif s == "general":
            return 1
        # Also handle legacy "Nivel 1" and "Nivel 2" for backward compatibility
        elif s == "nivel 1" or s == "1":
            return 1
        elif s == "nivel 2" or s == "2":
            return 2
        return 1

    # ------------------------- Template -------------------------
    def _load_html_template(self) -> str:
        if not os.path.exists(self.html_template_path):
            raise FileNotFoundError(f"HTML template not found: {self.html_template_path}")
        with open(self.html_template_path, "r", encoding="utf-8") as f:
            return f.read()

    def _format_preparar_value(self, value: Any) -> str:
        """Format preparar column value to Sí/No."""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return "No"
        s = str(value).strip()
        if s == "1":
            return "Sí"
        return "No"

    def _format_nivel_value(self, value: Any, test_type: str, is_cuarto_medio: bool = False) -> str:
        """Format nivel column value based on test type and student type."""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return "N/A"
        
        s = str(value).strip()
        
        # For "Cuarto medio" students, apply special formatting
        if is_cuarto_medio:
            if test_type == "M1":
                # M1: Nivel 1 -> "General", Nivel 2 -> "Intermedio", Nivel 3 -> "Avanzado"
                if s.lower() in ["nivel 1", "1"]:
                    return "General"
                elif s.lower() in ["nivel 2", "2"]:
                    return "Intermedio"
                elif s.lower() in ["nivel 3", "3"]:
                    return "Avanzado"
                return s
            elif test_type == "CL":
                # CL: Nivel 1 -> "General", Nivel 2/3 -> "Avanzado"
                if s.lower() in ["nivel 1", "1"]:
                    return "General"
                elif s.lower() in ["nivel 2", "nivel 3", "2", "3"]:
                    return "Avanzado"
                return s
            elif test_type in ["CIEN", "HYST"]:
                # CIEN/HYST: Nivel 1 -> "General", Nivel 2 -> "Avanzado"
                if s.lower() in ["nivel 1", "1", "general"]:
                    return "General"
                elif s.lower() in ["nivel 2", "2", "avanzado"]:
                    return "Avanzado"
                return s
        
        # For regular students (Egresado), use original logic
        # For M1 and CL, return the level number
        if test_type in ["M1", "CL", "CIEN"]:
            # Extract number from "Nivel 1", "1", etc.
            for n in (1, 2, 3):
                if s.lower() in [f"nivel {n}", str(n)]:
                    return str(n)
            return s
        
        # For CIEN and HYST, return General/Avanzado
        elif test_type in ["HYST"]:
            if s.lower() in ["avanzado", "nivel 2", "2"]:
                return "Avanzado"
            elif s.lower() in ["general", "nivel 1", "1"]:
                return "General"
            return s
        
        return s

    def _format_dominio_value(self, value: Any) -> str:
        """Format dominio column value from decimal to percentage."""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return "N/A"
        
        s = str(value).strip()
        
        # If it's "Diagnóstico no rendido", return as is
        if s.lower() == "diagnóstico no rendido":
            return s
        
        try:
            # Handle string format like "0,53"
            if isinstance(value, str):
                # Replace comma with dot for decimal parsing
                value = value.replace(",", ".")
            
            # Convert to float and format as percentage
            float_val = float(value)
            percentage = int(round(float_val * 100))
            return f"{percentage}%"
        except (ValueError, TypeError):
            # If conversion fails, return the original value
            return str(value)

    def _populate_results_table_placeholders(self, html_content: str, reporte_row: pd.Series, is_cuarto_medio: bool = False) -> str:
        """Populate the results table placeholders with actual data from the Reporte sheet."""
        
        # Find the relevant columns in the Reporte sheet
        preparar_m1_col = _find_col_case_insensitive(reporte_row.to_frame().T, ["preparar_matemática_m1", "preparar_matematica_m1"])
        preparar_m2_col = _find_col_case_insensitive(reporte_row.to_frame().T, ["preparar_matemática_m2", "preparar_matematica_m2"])
        preparar_cl_col = _find_col_case_insensitive(reporte_row.to_frame().T, ["preparar_competencia_lectora"])
        preparar_cien_col = _find_col_case_insensitive(reporte_row.to_frame().T, ["preparar_ciencias"])
        preparar_hyst_col = _find_col_case_insensitive(reporte_row.to_frame().T, ["preparar_historia"])
        
        nivel_m1_col = _find_col_case_insensitive(reporte_row.to_frame().T, ["Nivel M1"])
        nivel_cl_col = _find_col_case_insensitive(reporte_row.to_frame().T, ["Nivel CL"])
        nivel_cien_col = _find_col_case_insensitive(reporte_row.to_frame().T, ["Nivel CIEN"])
        nivel_hyst_col = _find_col_case_insensitive(reporte_row.to_frame().T, ["Nivel HYST"])
        
        dominio_m1_col = _find_col_case_insensitive(reporte_row.to_frame().T, ["Dominio M1"])
        dominio_cl_col = _find_col_case_insensitive(reporte_row.to_frame().T, ["Dominio CL"])
        dominio_cien_col = _find_col_case_insensitive(reporte_row.to_frame().T, ["Dominio CIEN"])
        dominio_hyst_col = _find_col_case_insensitive(reporte_row.to_frame().T, ["Dominio HYST"])
        
        # Get values and format them
        replacements = {}
        
        # Preparar values
        if preparar_m1_col:
            replacements["<<PREPARAR_M1>>"] = self._format_preparar_value(reporte_row.get(preparar_m1_col))
        else:
            replacements["<<PREPARAR_M1>>"] = "N/A"
            
        if preparar_m2_col:
            replacements["<<PREPARAR_M2>>"] = self._format_preparar_value(reporte_row.get(preparar_m2_col))
        else:
            replacements["<<PREPARAR_M2>>"] = "N/A"
            
        if preparar_cl_col:
            replacements["<<PREPARAR_CL>>"] = self._format_preparar_value(reporte_row.get(preparar_cl_col))
        else:
            replacements["<<PREPARAR_CL>>"] = "N/A"
            
        if preparar_cien_col:
            replacements["<<PREPARAR_CIEN>>"] = self._format_preparar_value(reporte_row.get(preparar_cien_col))
        else:
            replacements["<<PREPARAR_CIEN>>"] = "N/A"
            
        if preparar_hyst_col:
            replacements["<<PREPARAR_HYST>>"] = self._format_preparar_value(reporte_row.get(preparar_hyst_col))
        else:
            replacements["<<PREPARAR_HYST>>"] = "N/A"
        
        # Nivel values
        if nivel_m1_col:
            replacements["<<NIVEL_M1>>"] = self._format_nivel_value(reporte_row.get(nivel_m1_col), "M1", is_cuarto_medio)
        else:
            replacements["<<NIVEL_M1>>"] = "N/A"
            
        # For M2, check if student prepares M2 first
        if preparar_m2_col and self._format_preparar_value(reporte_row.get(preparar_m2_col)) == "Sí":
            replacements["<<NIVEL_M2>>"] = "Revisar anexo M2"
        else:
            replacements["<<NIVEL_M2>>"] = ""
            
        if nivel_cl_col:
            replacements["<<NIVEL_CL>>"] = self._format_nivel_value(reporte_row.get(nivel_cl_col), "CL", is_cuarto_medio)
        else:
            replacements["<<NIVEL_CL>>"] = "N/A"
            
        if nivel_cien_col:
            replacements["<<NIVEL_CIEN>>"] = self._format_nivel_value(reporte_row.get(nivel_cien_col), "CIEN", is_cuarto_medio)
        else:
            replacements["<<NIVEL_CIEN>>"] = "N/A"
            
        if nivel_hyst_col:
            replacements["<<NIVEL_HYST>>"] = self._format_nivel_value(reporte_row.get(nivel_hyst_col), "HYST", is_cuarto_medio)
        else:
            replacements["<<NIVEL_HYST>>"] = "N/A"
        
        # Dominio values
        if dominio_m1_col:
            replacements["<<DOMINIO_M1>>"] = self._format_dominio_value(reporte_row.get(dominio_m1_col))
        else:
            replacements["<<DOMINIO_M1>>"] = "N/A"
            
        # For M2, check if student prepares M2 first
        if preparar_m2_col and self._format_preparar_value(reporte_row.get(preparar_m2_col)) == "Sí":
            replacements["<<DOMINIO_M2>>"] = "Revisar anexo M2"
        else:
            replacements["<<DOMINIO_M2>>"] = ""
            
        if dominio_cl_col:
            replacements["<<DOMINIO_CL>>"] = self._format_dominio_value(reporte_row.get(dominio_cl_col))
        else:
            replacements["<<DOMINIO_CL>>"] = "N/A"
            
        if dominio_cien_col:
            replacements["<<DOMINIO_CIEN>>"] = self._format_dominio_value(reporte_row.get(dominio_cien_col))
        else:
            replacements["<<DOMINIO_CIEN>>"] = "N/A"
            
        if dominio_hyst_col:
            replacements["<<DOMINIO_HYST>>"] = self._format_dominio_value(reporte_row.get(dominio_hyst_col))
        else:
            replacements["<<DOMINIO_HYST>>"] = "N/A"
        
        # Apply all replacements
        for placeholder, value in replacements.items():
            html_content = html_content.replace(placeholder, value)
        
        return html_content

    def _populate_calendario_general_section(self, html_content: str, reporte_row: pd.Series) -> str:
        """Populate the Calendario General section conditionally based on user type."""
        
        # Find the student type column
        col_tipo_estudiante = _find_col_case_insensitive(
            reporte_row.to_frame().T, 
            ["qué_tipo_de_estudiante_eres", "que_tipo_de_estudiante_eres"]
        ) or "qué_tipo_de_estudiante_eres"
        
        # Check if user is "Egresado"
        is_egresado = False
        if col_tipo_estudiante in reporte_row.index:
            tipo_estudiante = str(reporte_row.get(col_tipo_estudiante, "")).strip().lower()
            is_egresado = tipo_estudiante == "egresado"
        
        # Define the Calendario General section HTML
        calendario_general_html = """<!-- =========== PÁGINA 4 - CALENDARIO GENERAL ========== -->
<section class="page">
  <div class="content">
    <h2>2. Calendario General</h2>
    
    <p>El calendario que verás ahora es el calendario general para egresados, sin embargo el Calendario Personalizado es aquel que te recomendaremos a ti en función de tu diagnóstico y tus respuestas en las encuestas.</p>
    
    <table style="width: 60%; border-collapse: collapse; margin: 10px 0; margin-right: 40px; border: 1px solid #000; font-family: 'Times New Roman', Times, serif; font-size: 12px;">
        <thead>
            <tr>
                <th style="border: 1px solid #000; padding: 10px; text-align: center; background-color: #f0f0f0;"></th>
                <th style="border: 1px solid #000; padding: 10px; text-align: center; background-color: #f0f0f0;">Lunes</th>
                <th style="border: 1px solid #000; padding: 10px; text-align: center; background-color: #f0f0f0;">Martes</th>
                <th style="border: 1px solid #000; padding: 10px; text-align: center; background-color: #f0f0f0;">Miércoles</th>
                <th style="border: 1px solid #000; padding: 10px; text-align: center; background-color: #f0f0f0;">Jueves</th>
                <th style="border: 1px solid #000; padding: 10px; text-align: center; background-color: #f0f0f0;">Viernes</th>
                <th style="border: 1px solid #000; padding: 10px; text-align: center; background-color: #f0f0f0;">Sábado</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td style="border: 1px solid #000; padding: 10px; text-align: center;">(9:00-13:00)</td>
                <td style="border: 1px solid #000; padding: 10px; text-align: center;">Matemática M1</td>
                <td style="border: 1px solid #000; padding: 10px; text-align: center;">Competencia Lectora</td>
                <td style="border: 1px solid #000; padding: 10px; text-align: center;">Matemática M1</td>
                <td style="border: 1px solid #000; padding: 10px; text-align: center;">Competencia Lectora</td>
                <td style="border: 1px solid #000; padding: 10px; text-align: center;">Matemática M1</td>
                <td style="border: 1px solid #000; padding: 10px; text-align: center;" rowspan="5">Matemática M2</td>
            </tr>
            <tr>
                <td style="border: 1px solid #000; padding: 10px; text-align: center;">(13:00-14:00)</td>
                <td colspan="5" style="border: 1px solid #000; padding: 10px; text-align: center; font-style: italic;">Almuerzo</td>
            </tr>
            <tr>
                <td style="border: 1px solid #000; padding: 10px; text-align: center;">(14:00-16:00)</td>
                <td style="border: 1px solid #000; padding: 10px;">Matemática M1</td>
                <td style="border: 1px solid #000; padding: 10px;">Libre</td>
                <td style="border: 1px solid #000; padding: 10px;">Matemática M1</td>
                <td style="border: 1px solid #000; padding: 10px;">Libre</td>
                <td style="border: 1px solid #000; padding: 10px;">Matemática M1</td>
            </tr>
            <tr>
                <td style="border: 1px solid #000; padding: 10px; text-align: center;">(16:00-18:00)</td>
                <td colspan="4" style="border: 1px solid #000; padding: 10px; text-align: center; font-style: italic;">Ayudantías M30M</td>
                <td style="border: 1px solid #000; padding: 10px; text-align: center;">Ayudantía Electivo</td>
            </tr>
            <tr>
                <td style="border: 1px solid #000; padding: 10px; text-align: center;">(18:00-21:00)</td>
                <td style="border: 1px solid #000; padding: 10px;">Libre</td>
                <td style="border: 1px solid #000; padding: 10px;">Electivo</td>
                <td style="border: 1px solid #000; padding: 10px;">Libre</td>
                <td style="border: 1px solid #000; padding: 10px;">Electivo</td>
                <td style="border: 1px solid #000; padding: 10px;"><strong>Viernes M30M</strong></td>
            </tr>
        </tbody>
    </table>
    
    <div style="margin-top: 20px;">
        <p><strong>Puntos importantes:</strong></p>
        <ol style="margin-left: 20px;">
            <li>Recuerda que Electivo puede ser Ciencias o Historia.</li>
            <li>Las Ayudantías M30M son opcionales, sin embargo las ayudantías de electivo son obligatorias, en caso de que no puedas asistir, <strong>siempre quedarán grabadas</strong>.</li>
            <li>Los Viernes M30M son actividades programadas donde haremos concursos, competencias y eventos.</li>
            <li>Si preparas electivo los fines de semana se te enviarán tareas a completar.</li>
            <li>Este horario es un horario general, tu horario personalizado lo encontrarás en las siguientes páginas.</li>
        </ol>
    </div>
  </div>
</section>"""
        
        # Replace the placeholder with the section HTML if user is "Egresado", otherwise remove it
        if is_egresado:
            html_content = html_content.replace("<<CALENDARIO_GENERAL_SECTION>>", calendario_general_html)
        else:
            html_content = html_content.replace("<<CALENDARIO_GENERAL_SECTION>>", "")
        
        return html_content

    # ------------------------- Normalization helpers -------------------------
    def _normalize_text(self, value: Any) -> str:
        s = str(value or "").strip().lower()
        replacements = {
            "á": "a",
            "é": "e",
            "í": "i",
            "ó": "o",
            "ú": "u",
            "ñ": "n",
        }
        for a, b in replacements.items():
            s = s.replace(a, b)
        # remove non alphanumeric
        return "".join(ch for ch in s if ch.isalnum())

    def _format_semana(self, value: Any) -> str:
        """Format 'Semana' value (date-like or string) to a compact label, e.g., '11-08'."""
        try:
            dt = pd.to_datetime(value, errors="coerce")
            if pd.notna(dt):
                return dt.strftime("%d-%m")
        except Exception:
            pass
        s = str(value).strip()
        # Remove full timestamp if present (e.g., '2025-08-11T00:00:00') and keep DD-MM if possible
        if "T" in s:
            s = s.split("T", 1)[0]
        # If yyyy-mm-dd -> dd-mm
        try:
            parts = s.split("-")
            if len(parts) == 3 and len(parts[0]) == 4:
                return f"{parts[2]}-{parts[1]}"
        except Exception:
            pass
        return s

    def _find_column_fuzzy(self, df: pd.DataFrame, desired: str) -> Optional[str]:
        """Find a column in df that matches desired, ignoring accents, spaces, and case."""
        desired_norm = self._normalize_text(desired)
        mapping = {self._normalize_text(c): c for c in df.columns}
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
            v_norm = self._normalize_text(v)
            if v_norm in mapping:
                return mapping[v_norm]
        
        # Debug logging for column search
        logger.debug(f"Column '{desired}' not found in segment sheet. Available columns: {list(df.columns)}")
        return None

    def _match_day(self, series: pd.Series, target_day: str) -> pd.Series:
        target_norm = self._normalize_text(target_day)
        return series.astype(str).map(self._normalize_text) == target_norm

    def _to_hora_str(self, value: Any) -> str:
        try:
            if pd.isna(value):
                return ""
        except Exception:
            pass
        s = str(value).strip()
        # If numeric-like, reduce to integer string (e.g., 9.0 -> "9")
        try:
            f = float(s)
            i = int(round(f))
            if abs(f - i) < 1e-6:
                return str(i)
        except Exception:
            pass
        # Remove ranges and minutes like 9:00-13:00 -> 9
        if ":" in s:
            s2 = s.split(":", 1)[0]
            # In case of ranges like 9-13 -> 9
            s2 = s2.split("-", 1)[0]
            return s2
        # In case of (9:00-13:00)
        s = s.replace("(", "").replace(")", "")
        if ":" in s:
            s = s.split(":", 1)[0]
        if "-" in s:
            s = s.split("-", 1)[0]
        return s

    def _match_hora(self, series: pd.Series, target_hora: str) -> pd.Series:
        target = self._to_hora_str(target_hora)
        return series.map(self._to_hora_str) == target

    # ------------------------- Schedule selection -------------------------
    def _select_schedule_columns(
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
        nivel_m1_col = _find_col_case_insensitive(reporte_row.to_frame().T, ["Nivel M1"])
        nivel_cl_col = _find_col_case_insensitive(reporte_row.to_frame().T, ["Nivel CL"])
        nivel_cien_col = _find_col_case_insensitive(reporte_row.to_frame().T, ["Nivel CIEN"])
        nivel_hyst_col = _find_col_case_insensitive(reporte_row.to_frame().T, ["Nivel HYST"])

        # M1 level - only if allowed for this segment
        if "M1" in allowed_tests and nivel_m1_col:
            m1_level = reporte_row.get(nivel_m1_col)
            if m1_level is not None and not (isinstance(m1_level, float) and pd.isna(m1_level)):
                idx = self._level_to_index_m1_cl(m1_level)
                mapping["M1"] = f"M1 N{idx}"

        # CL level - only if allowed for this segment
        if "CL" in allowed_tests and nivel_cl_col:
            cl_level = reporte_row.get(nivel_cl_col)
            if cl_level is not None and not (isinstance(cl_level, float) and pd.isna(cl_level)):
                idx = self._level_to_index_m1_cl(cl_level)
                mapping["CL"] = f"CL N{idx}"

        # Special handling for CIEN/HYST in S7, S8, S15
        # For S15 behavior flags, use standard logic instead of complex logic
        if test_type_filter in ["S7_BEHAVIOR", "S8_BEHAVIOR"]:
            # Standard CIEN/HYST logic for S15 behavior flags
            # CIEN level - only if allowed for this segment
            if "CIEN" in allowed_tests and nivel_cien_col:
                cien_level = reporte_row.get(nivel_cien_col)
                if cien_level is not None and not (isinstance(cien_level, float) and pd.isna(cien_level)):
                    idx = self._level_to_index_cien_hyst(cien_level)
                    if variant == "tarde":
                        mapping["CIEN"] = "CIEN Tarde"
                    else:
                        mapping["CIEN"] = f"CIEN N{idx} Mañana"
            
            # HYST level - only if allowed for this segment
            if "HYST" in allowed_tests and nivel_hyst_col:
                hyst_level = reporte_row.get(nivel_hyst_col)
                if hyst_level is not None and not (isinstance(hyst_level, float) and pd.isna(hyst_level)):
                    idx = self._level_to_index_cien_hyst(hyst_level)
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
                    m1_level = self._level_to_index_m1_cl(m1_level)
            if nivel_cl_col:
                cl_level = reporte_row.get(nivel_cl_col)
                if cl_level is not None and not (isinstance(cl_level, float) and pd.isna(cl_level)):
                    cl_level = self._level_to_index_m1_cl(cl_level)

            # CIEN logic for S7 and S15
            if "CIEN" in allowed_tests and nivel_cien_col:
                cien_level = reporte_row.get(nivel_cien_col)
                if cien_level is not None and not (isinstance(cien_level, float) and pd.isna(cien_level)):
                    cien_idx = self._level_to_index_cien_hyst(cien_level)
                    
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
                    hyst_idx = self._level_to_index_cien_hyst(hyst_level)
                    
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
                    idx = self._level_to_index_cien_hyst(cien_level)
                    if variant == "tarde":
                        mapping["CIEN"] = "CIEN Tarde"
                    else:
                        mapping["CIEN"] = f"CIEN N{idx} Mañana"

            # HYST level - only if allowed for this segment
            if "HYST" in allowed_tests and nivel_hyst_col:
                hyst_level = reporte_row.get(nivel_hyst_col)
                if hyst_level is not None and not (isinstance(hyst_level, float) and pd.isna(hyst_level)):
                    idx = self._level_to_index_cien_hyst(hyst_level)
                    if variant == "tarde":
                        mapping["HYST"] = "HYST Tarde"
                    else:
                        mapping["HYST"] = f"HYST N{idx} Mañana"

        return mapping

    # ------------------------- HTML table builders -------------------------
    def _build_week_tables_html(self, seg_df: pd.DataFrame, col_map: Dict[str, Optional[str]]) -> str:
        """Render weekly tables EXACTLY like the provided layout image.

        We generate one fixed-layout table per Semana value and then place two per page.
        Only placeholders like lunes_9, martes_14, etc., are replaced with actual data.
        All other texts, borders, and styles are preserved.
        """
        if seg_df is None or seg_df.empty:
            return ""

        semana_col = _find_col_case_insensitive(seg_df, ["Semana"]) or "Semana"
        dia_col = _find_col_case_insensitive(seg_df, ["Día", "Dia"]) or "Día"
        hora_col = _find_col_case_insensitive(seg_df, ["Hora"]) or "Hora"

        # Helper to extract combined cell content from segment df
        def slot_value(week_value: Any, day_name: str, hora_target: str) -> str:
            mask = (
                (seg_df[semana_col] == week_value)
                & self._match_day(seg_df[dia_col], day_name)
                & self._match_hora(seg_df[hora_col], hora_target)
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
                actual_col = self._find_column_fuzzy(seg_df, desired_col)
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
            semana_display = self._format_semana(week_value)
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

    # ------------------------- Public API -------------------------
    def generate_pdf_for_user(
        self,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        variant: str = "manana",  # "manana" or "tarde"
        test_type_filter: Optional[str] = None,  # "CIEN" or "HYST" for special segments
    ) -> bytes:
        if not (user_id or email):
            raise ValueError("Must provide user_id or email")

        self._ensure_analysis_loaded()
        self._ensure_segmentos_loaded()

        # Fetch user row from Reporte
        reporte_row = self._find_user_row(self._df_reporte, user_id, email)
        if reporte_row is None:
            raise ValueError("User not found in 'Reporte' sheet")

        # Get segment key and user display name
        col_segmento = _find_col_case_insensitive(self._df_reporte, ["Segmento"]) or "Segmento"
        col_nombre = _find_col_case_insensitive(self._df_reporte, ["nombre_y_apellido"]) or "nombre_y_apellido"
        segmento_value = str(reporte_row.get(col_segmento, "")).strip()
        alumno_nombre = str(reporte_row.get(col_nombre, "Alumno")).strip()

        if not segmento_value:
            raise ValueError("User has empty 'Segmento' value")

        seg_df = self._segment_key_to_df.get(segmento_value.upper())
        if seg_df is None:
            raise ValueError(f"Segment sheet for '{segmento_value}' not found in Segmentos.xlsx")

        # Select which segment sheet columns to use for this user based on levels from Reporte
        col_map = self._select_schedule_columns(reporte_row, variant, segmento_value, test_type_filter)

        # Build schedule HTML
        schedule_html = self._build_week_tables_html(seg_df, col_map)

        # Load template and inject content
        html_content = self._load_html_template()
        html_content = html_content.replace("<<ALUMNO>>", alumno_nombre)
        
        # Populate results table placeholders
        html_content = self._populate_results_table_placeholders(html_content, reporte_row, is_cuarto_medio=False)
        
        # Check if user is "Egresado" and conditionally include Calendario General section
        html_content = self._populate_calendario_general_section(html_content, reporte_row)
        
        if schedule_html:
            html_content = html_content.replace("</body>", f"{schedule_html}\n</body>")
        
        # Add checklist tables for Egresado students
        html_content = self._add_checklist_to_html(html_content, reporte_row, is_cuarto_medio=False)

        # Render PDF
        html_doc = HTML(string=html_content)
        pdf_content = html_doc.write_pdf()
        return pdf_content

    def _check_existing_pdfs(self, output_dir: str) -> set:
        """
        Check for existing PDFs in the output directory and return a set of user identifiers
        that already have PDFs generated.
        
        Args:
            output_dir: Directory to check for existing PDFs
            
        Returns:
            Set of user identifiers (email or user_id) that already have PDFs
        """
        existing_users = set()
        
        if not os.path.exists(output_dir):
            return existing_users
            
        # Walk through all subdirectories in the output directory
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                if file.endswith('.pdf'):
                    # Extract user identifier from filename
                    # Filename format: {base}_{variant}.pdf or {base}_CIEN_{variant}.pdf, etc.
                    filename_without_ext = file[:-4]  # Remove .pdf extension
                    
                    # Split by underscore and take the first part as the base identifier
                    parts = filename_without_ext.split('_')
                    if parts:
                        base_identifier = parts[0]
                        existing_users.add(base_identifier)
        
        logger.info(f"Found {len(existing_users)} users with existing PDFs")
        return existing_users

    def generate_pdf_for_cuarto_medio_user(
        self,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
    ) -> bytes:
        """
        Generate PDF for a "Cuarto medio" student (no schedule, only results table).
        
        Args:
            user_id: User ID
            email: User email
            
        Returns:
            PDF content as bytes
        """
        if not (user_id or email):
            raise ValueError("Must provide user_id or email")

        self._ensure_analysis_loaded()

        # Fetch user row from Reporte
        reporte_row = self._find_user_row(self._df_reporte, user_id, email)
        if reporte_row is None:
            raise ValueError("User not found in 'Reporte' sheet")

        # Get user display name
        col_nombre = _find_col_case_insensitive(self._df_reporte, ["nombre_y_apellido"]) or "nombre_y_apellido"
        alumno_nombre = str(reporte_row.get(col_nombre, "Alumno")).strip()

        # Load template and inject content
        html_content = self._load_html_template()
        html_content = html_content.replace("<<ALUMNO>>", alumno_nombre)
        
        # Populate results table placeholders
        html_content = self._populate_results_table_placeholders(html_content, reporte_row, is_cuarto_medio=True)
        
        # For Cuarto medio students, do NOT include Calendario General section
        # (it's already excluded by default in _populate_calendario_general_section)
        
        # Do NOT include schedule tables for Cuarto medio students
        
        # Add checklist tables for Cuarto medio students
        html_content = self._add_checklist_to_html(html_content, reporte_row, is_cuarto_medio=True)
        
        # Render PDF
        html_doc = HTML(string=html_content)
        pdf_content = html_doc.write_pdf()
        return pdf_content

    def generate_pdfs_for_cuarto_medio_students(
        self,
        output_dir: str = "reports/Cuarto medio",
        existing_users: set = None
    ) -> Dict[str, int]:
        """
        Generate PDFs for all students with "Cuarto medio" status.
        
        Args:
            output_dir: Directory to save PDFs
            existing_users: Set of user identifiers that already have PDFs
            
        Returns:
            Dictionary with counts of generated PDFs
        """
        self._ensure_analysis_loaded()
        
        # Find the student type column
        col_tipo_estudiante = _find_col_case_insensitive(
            self._df_reporte, 
            ["qué_tipo_de_estudiante_eres", "que_tipo_de_estudiante_eres"]
        ) or "qué_tipo_de_estudiante_eres"
        
        col_user_id = _find_col_case_insensitive(self._df_reporte, ["user_id"]) or "user_id"
        col_email = _find_col_case_insensitive(self._df_reporte, ["email"]) or "email"

        # Filter for "Cuarto medio" students only
        if col_tipo_estudiante not in self._df_reporte.columns:
            logger.warning(f"Column '{col_tipo_estudiante}' not found. No PDFs will be generated.")
            return {}
            
        # Case-insensitive filtering for "Cuarto medio" and empty values
        eligible = self._df_reporte[
            (self._df_reporte[col_tipo_estudiante].astype(str).str.strip().str.lower() == "cuarto medio") |
            (self._df_reporte[col_tipo_estudiante].isna()) |
            (self._df_reporte[col_tipo_estudiante].astype(str).str.strip() == "")
        ]
        
        logger.info(f"Found {len(eligible)} students with 'Cuarto medio' status or empty value")
        
        if len(eligible) == 0:
            logger.warning("No students with 'Cuarto medio' status or empty value found")
            return {}
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        total_count = 0
        skipped_count = 0
        
        for _, r in eligible.iterrows():
            user_id = r.get(col_user_id)
            email = r.get(col_email)
            
            # Create base identifier for checking existing PDFs
            base = email if pd.notna(email) and email else (user_id if pd.notna(user_id) else "user")
            base = _sanitize_filename(base)
            
            # Check if user already has PDFs
            if existing_users and base in existing_users:
                logger.info(f"Skipping user {user_id}/{email} - PDF already exists")
                skipped_count += 1
                continue
            
            try:
                pdf = self.generate_pdf_for_cuarto_medio_user(
                    user_id=user_id if pd.notna(user_id) else None,
                    email=email if pd.notna(email) else None,
                )
                
                out_path = os.path.join(output_dir, f"{base}.pdf")
                with open(out_path, "wb") as f:
                    f.write(pdf)
                logger.info(f"Saved: {out_path}")
                total_count += 1
                
            except Exception as e:
                logger.error(f"Failed to generate PDF for user_id={user_id}, email={email}: {e}")
                continue
        
        logger.info(f"Generated {total_count} PDFs for Cuarto medio students, skipped {skipped_count} existing PDFs")
        return {"Cuarto medio": total_count}

    def generate_pdfs_for_egresado_students(
        self,
        output_dir: str = "reports",
        variants: List[str] = None,
        existing_users: set = None,
        segments_filter: Optional[List[str]] = None
    ) -> Dict[str, int]:
        """
        Generate PDFs for all students with "Egresado" status.
        
        Args:
            output_dir: Directory to save PDFs
            variants: List of variants to generate ("manana", "tarde") - only used for segments that support both
            
        Returns:
            Dictionary with counts of generated PDFs per segment
        """
        # Segments that get both mañana and tarde variants
        dual_variant_segments = {"S1", "S2", "S4", "S5"}
        
        # Special segments that need separate PDFs for CIEN and HYST
        # Note: S13 and S14 are now handled separately in the main logic
        
        # Special segments S7, S8, S15 with specific PDF generation rules
        special_s7_s8_s15_segments = {"S7", "S8", "S15"}
        
        if variants is None:
            variants = ["manana", "tarde"]
            
        self._ensure_analysis_loaded()
        
        # Find the student type column
        col_tipo_estudiante = _find_col_case_insensitive(
            self._df_reporte, 
            ["qué_tipo_de_estudiante_eres", "que_tipo_de_estudiante_eres"]
        ) or "qué_tipo_de_estudiante_eres"
        
        col_user_id = _find_col_case_insensitive(self._df_reporte, ["user_id"]) or "user_id"
        col_email = _find_col_case_insensitive(self._df_reporte, ["email"]) or "email"
        col_segmento = _find_col_case_insensitive(self._df_reporte, ["Segmento"]) or "Segmento"

        # Filter for "Egresado" students only
        if col_tipo_estudiante not in self._df_reporte.columns:
            logger.warning(f"Column '{col_tipo_estudiante}' not found. No PDFs will be generated.")
            return {}
            
        # Case-insensitive filtering for "Egresado"
        eligible = self._df_reporte[
            self._df_reporte[col_tipo_estudiante].astype(str).str.strip().str.lower() == "egresado"
        ]
        
        logger.info(f"Found {len(eligible)} students with 'Egresado' status")
        
        if len(eligible) == 0:
            logger.warning("No students with 'Egresado' status found")
            return {}
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        segment_counts = {}
        total_count = 0
        
        for _, r in eligible.iterrows():
            user_id = r.get(col_user_id)
            email = r.get(col_email)
            segmento = r.get(col_segmento)
            
            # Skip if no segmento value
            if pd.isna(segmento) or not str(segmento).strip():
                logger.warning(f"Skipping user {user_id}/{email} - no segmento value")
                continue
                
            # Create segment folder
            segmento_str = str(segmento).strip().upper()
            
            # Skip if segment is not in the filter
            if segments_filter and segmento_str not in segments_filter:
                logger.info(f"Skipping user {user_id}/{email} - segment {segmento_str} not in filter {segments_filter}")
                continue
                
            segment_folder = os.path.join(output_dir, segmento_str)
            os.makedirs(segment_folder, exist_ok=True)
            
            # Initialize count for this segment
            if segmento_str not in segment_counts:
                segment_counts[segmento_str] = 0
            
            base = email if pd.notna(email) and email else (user_id if pd.notna(user_id) else "user")
            base = _sanitize_filename(base)
            
            # Check if user already has PDFs
            if existing_users and base in existing_users:
                logger.info(f"Skipping user {user_id}/{email} - PDF already exists")
                continue

            # Determine which variants to generate based on segment
            if segmento_str == "S13":
                # S13: Generate 4 PDFs total - S1 behavior (M1+CIEN) + S2 behavior (M1+HYST)
                # 1. S1 behavior: M1 + CIEN (mañana variant)
                # 2. S1 behavior: M1 + CIEN (tarde variant)
                # 3. S2 behavior: M1 + HYST (mañana variant)  
                # 4. S2 behavior: M1 + HYST (tarde variant)
                
                # Generate S1 behavior PDFs (M1 + CIEN)
                for variant in variants:
                    try:
                        # For S1 behavior, we need to temporarily modify the segment config to show M1 + CIEN
                        # We'll do this by calling generate_pdf_for_user with a custom segment mapping
                        pdf = self.generate_pdf_for_user(
                            user_id=user_id if pd.notna(user_id) else None,
                            email=email if pd.notna(email) else None,
                            variant=variant,
                            test_type_filter="S1_BEHAVIOR",  # Custom flag for S1 behavior
                        )
                        out_path = os.path.join(segment_folder, f"{base}_CIEN_{variant}.pdf")
                        with open(out_path, "wb") as f:
                            f.write(pdf)
                        logger.info(f"Saved: {out_path}")
                        segment_counts[segmento_str] += 1
                        total_count += 1
                    except Exception as e:
                        logger.error(f"Failed to generate S1 behavior for user_id={user_id}, email={email}, variant={variant}: {e}")
                        continue
                
                # Generate S2 behavior PDFs (M1 + HYST)
                for variant in variants:
                    try:
                        # For S2 behavior, we need to temporarily modify the segment config to show M1 + HYST
                        pdf = self.generate_pdf_for_user(
                            user_id=user_id if pd.notna(user_id) else None,
                            email=email if pd.notna(email) else None,
                            variant=variant,
                            test_type_filter="S2_BEHAVIOR",  # Custom flag for S2 behavior
                        )
                        out_path = os.path.join(segment_folder, f"{base}_HYST_{variant}.pdf")
                        with open(out_path, "wb") as f:
                            f.write(pdf)
                        logger.info(f"Saved: {out_path}")
                        segment_counts[segmento_str] += 1
                        total_count += 1
                    except Exception as e:
                        logger.error(f"Failed to generate S2 behavior for user_id={user_id}, email={email}, variant={variant}: {e}")
                        continue
                        
            elif segmento_str == "S14":
                # S14: Generate 4 PDFs total - S4 behavior (CL+CIEN) + S5 behavior (CL+HYST)
                # 1. S4 behavior: CL + CIEN (mañana variant)
                # 2. S4 behavior: CL + CIEN (tarde variant)
                # 3. S5 behavior: CL + HYST (mañana variant)  
                # 4. S5 behavior: CL + HYST (tarde variant)
                
                # Generate S4 behavior PDFs (CL + CIEN)
                for variant in variants:
                    try:
                        pdf = self.generate_pdf_for_user(
                            user_id=user_id if pd.notna(user_id) else None,
                            email=email if pd.notna(email) else None,
                            variant=variant,
                            test_type_filter="S4_BEHAVIOR",  # This will show CL + CIEN (S4 behavior)
                        )
                        out_path = os.path.join(segment_folder, f"{base}_CIEN_{variant}.pdf")
                        with open(out_path, "wb") as f:
                            f.write(pdf)
                        logger.info(f"Saved: {out_path}")
                        segment_counts[segmento_str] += 1
                        total_count += 1
                    except Exception as e:
                        logger.error(f"Failed to generate S4 behavior for user_id={user_id}, email={email}, variant={variant}: {e}")
                        continue
                
                # Generate S5 behavior PDFs (CL + HYST)
                for variant in variants:
                    try:
                        pdf = self.generate_pdf_for_user(
                            user_id=user_id if pd.notna(user_id) else None,
                            email=email if pd.notna(email) else None,
                            variant=variant,
                            test_type_filter="S5_BEHAVIOR",  # This will show CL + HYST (S5 behavior)
                        )
                        out_path = os.path.join(segment_folder, f"{base}_HYST_{variant}.pdf")
                        with open(out_path, "wb") as f:
                            f.write(pdf)
                        logger.info(f"Saved: {out_path}")
                        segment_counts[segmento_str] += 1
                        total_count += 1
                    except Exception as e:
                        logger.error(f"Failed to generate S5 behavior for user_id={user_id}, email={email}, variant={variant}: {e}")
                        continue
                        
            elif segmento_str in special_s7_s8_s15_segments:
                # Special handling for S7, S8, S15 with conditional PDF generation
                if segmento_str == "S7":
                    # S7: Conditional PDFs (mañana/tarde with CIEN based on student levels)
                    for variant in variants:
                        try:
                            # Check if this variant should be generated for this student
                            mapping = self._select_schedule_columns(r, variant, segmento_str, "CIEN")
                            if mapping["CIEN"] is None:
                                logger.info(f"Skipping S7 {variant} variant for user {user_id}/{email} - no valid CIEN mapping")
                                continue
                                
                            pdf = self.generate_pdf_for_user(
                                user_id=user_id if pd.notna(user_id) else None,
                                email=email if pd.notna(email) else None,
                                variant=variant,
                                test_type_filter="CIEN",
                            )
                            out_path = os.path.join(segment_folder, f"{base}_{variant}.pdf")
                            with open(out_path, "wb") as f:
                                f.write(pdf)
                            logger.info(f"Saved: {out_path}")
                            segment_counts[segmento_str] += 1
                            total_count += 1
                        except Exception as e:
                            logger.error(f"Failed to generate S7 CIEN schedule for user_id={user_id}, email={email}, variant={variant}: {e}")
                            continue
                            
                elif segmento_str == "S8":
                    # S8: Conditional PDFs (mañana/tarde with HYST based on student levels)
                    for variant in variants:
                        try:
                            # Check if this variant should be generated for this student
                            mapping = self._select_schedule_columns(r, variant, segmento_str, "HYST")
                            if mapping["HYST"] is None:
                                logger.info(f"Skipping S8 {variant} variant for user {user_id}/{email} - no valid HYST mapping")
                                continue
                                
                            pdf = self.generate_pdf_for_user(
                                user_id=user_id if pd.notna(user_id) else None,
                                email=email if pd.notna(email) else None,
                                variant=variant,
                                test_type_filter="HYST",
                            )
                            out_path = os.path.join(segment_folder, f"{base}_{variant}.pdf")
                            with open(out_path, "wb") as f:
                                f.write(pdf)
                            logger.info(f"Saved: {out_path}")
                            segment_counts[segmento_str] += 1
                            total_count += 1
                        except Exception as e:
                            logger.error(f"Failed to generate S8 HYST schedule for user_id={user_id}, email={email}, variant={variant}: {e}")
                            continue
                            
                elif segmento_str == "S15":
                    # S15: Generate maximum 4 PDFs - S7 behavior (M1+CL+CIEN) + S8 behavior (M1+CL+HYST)
                    # Uses conditional logic from S7 and S8 to determine which variants are available
                    
                    # Generate S7 behavior PDFs (M1 + CL + CIEN) - conditional based on student levels
                    for variant in variants:
                        try:
                            # Check if this variant should be generated for this student using S7 logic
                            mapping = self._select_schedule_columns(r, variant, "S7", "CIEN")
                            if mapping["CIEN"] is not None:
                                pdf = self.generate_pdf_for_user(
                                    user_id=user_id if pd.notna(user_id) else None,
                                    email=email if pd.notna(email) else None,
                                    variant=variant,
                                    test_type_filter="S7_BEHAVIOR",  # Custom flag for S7 behavior
                                )
                                out_path = os.path.join(segment_folder, f"{base}_S7_{variant}.pdf")
                                with open(out_path, "wb") as f:
                                    f.write(pdf)
                                logger.info(f"Saved: {out_path}")
                                segment_counts[segmento_str] += 1
                                total_count += 1
                            else:
                                logger.info(f"Skipping S15 S7 {variant} variant for user {user_id}/{email} - no valid CIEN mapping")
                        except Exception as e:
                            logger.error(f"Failed to generate S7 behavior for user_id={user_id}, email={email}, variant={variant}: {e}")
                            continue
                    
                    # Generate S8 behavior PDFs (M1 + CL + HYST) - conditional based on student levels
                    for variant in variants:
                        try:
                            # Check if this variant should be generated for this student using S8 logic
                            mapping = self._select_schedule_columns(r, variant, "S8", "HYST")
                            if mapping["HYST"] is not None:
                                pdf = self.generate_pdf_for_user(
                                    user_id=user_id if pd.notna(user_id) else None,
                                    email=email if pd.notna(email) else None,
                                    variant=variant,
                                    test_type_filter="S8_BEHAVIOR",  # Custom flag for S8 behavior
                                )
                                out_path = os.path.join(segment_folder, f"{base}_S8_{variant}.pdf")
                                with open(out_path, "wb") as f:
                                    f.write(pdf)
                                logger.info(f"Saved: {out_path}")
                                segment_counts[segmento_str] += 1
                                total_count += 1
                            else:
                                logger.info(f"Skipping S15 S8 {variant} variant for user {user_id}/{email} - no valid HYST mapping")
                        except Exception as e:
                            logger.error(f"Failed to generate S8 behavior for user_id={user_id}, email={email}, variant={variant}: {e}")
                            continue
                        
            elif segmento_str in dual_variant_segments:
                # Generate both mañana and tarde variants
                for variant in variants:
                    try:
                        pdf = self.generate_pdf_for_user(
                            user_id=user_id if pd.notna(user_id) else None,
                            email=email if pd.notna(email) else None,
                            variant=variant,
                        )
                        
                        # For dual variant segments, include the variant in filename
                        out_path = os.path.join(segment_folder, f"{base}_segmento_{variant}.pdf")
                        
                        with open(out_path, "wb") as f:
                            f.write(pdf)
                        logger.info(f"Saved: {out_path}")
                        segment_counts[segmento_str] += 1
                        total_count += 1
                    except Exception as e:
                        logger.error(f"Failed to generate schedule for user_id={user_id}, email={email}, variant={variant}: {e}")
                        continue
            else:
                # Generate only one PDF (mañana variant)
                try:
                    pdf = self.generate_pdf_for_user(
                        user_id=user_id if pd.notna(user_id) else None,
                        email=email if pd.notna(email) else None,
                        variant="manana",
                    )
                    
                    # For single variant segments, don't include variant in filename
                    out_path = os.path.join(segment_folder, f"{base}.pdf")
                    
                    with open(out_path, "wb") as f:
                        f.write(pdf)
                    logger.info(f"Saved: {out_path}")
                    segment_counts[segmento_str] += 1
                    total_count += 1
                except Exception as e:
                    logger.error(f"Failed to generate schedule for user_id={user_id}, email={email}: {e}")
                    continue

        logger.info(f"Generated {total_count} schedule PDFs for Egresado students across {len(segment_counts)} segments")
        return segment_counts



    # ------------------------- Main Orchestration -------------------------
    def generate_all_reports(
        self, 
        segments: Optional[List[str]] = None, 
        student_types: Optional[List[str]] = None
    ) -> bool:
        """
        Generate segment schedule reports for both "Egresado" and "Cuarto medio" students.
        Includes duplicate checking to avoid regenerating existing PDFs.
        
        Args:
            segments: List of segments to generate PDFs for (e.g., ["S1", "S2", "S7"]). 
                     If None, generates for all segments.
            student_types: List of student types to generate PDFs for (e.g., ["Egresado", "Cuarto medio"]).
                          If None, generates for both types.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Starting segment schedule report generation...")
            
            # Set defaults if not provided
            if segments is None:
                segments = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10", "S11", "S12", "S13", "S14", "S15"]
            if student_types is None:
                student_types = ["Egresado", "Cuarto medio"]
            
            logger.info(f"Generating PDFs for segments: {segments}")
            logger.info(f"Generating PDFs for student types: {student_types}")
            
            # Check for existing PDFs in both output directories
            logger.info("Checking for existing PDFs...")
            existing_egresado_pdfs = self._check_existing_pdfs("reports")
            existing_cuarto_medio_pdfs = self._check_existing_pdfs("reports/Cuarto medio")
            
            # Combine all existing users to avoid duplicates
            all_existing_users = existing_egresado_pdfs.union(existing_cuarto_medio_pdfs)
            logger.info(f"Found {len(all_existing_users)} total users with existing PDFs")
            
            egresado_results = {}
            cuarto_medio_results = {}
            
            # Generate PDFs for Egresado students
            if "Egresado" in student_types:
                logger.info("Generating PDFs for Egresado students...")
                egresado_results = self.generate_pdfs_for_egresado_students(
                    output_dir="reports",
                    variants=["manana", "tarde"],
                    existing_users=all_existing_users,
                    segments_filter=segments
                )
            
            # Generate PDFs for Cuarto medio students
            if "Cuarto medio" in student_types:
                logger.info("Generating PDFs for Cuarto medio students...")
                cuarto_medio_results = self.generate_pdfs_for_cuarto_medio_students(
                    output_dir="reports/Cuarto medio",
                    existing_users=all_existing_users
                )
            
            # Log results
            logger.info("=== Report Generation Results ===")
            if egresado_results:
                logger.info("Egresado students:")
                for segment, count in egresado_results.items():
                    logger.info(f"  {segment}: {count} PDFs")
            
            if cuarto_medio_results:
                logger.info("Cuarto medio students:")
                for category, count in cuarto_medio_results.items():
                    logger.info(f"  {category}: {count} PDFs")
            
            total_egresado = sum(egresado_results.values())
            total_cuarto_medio = sum(cuarto_medio_results.values())
            logger.info(f"Total PDFs generated: {total_egresado + total_cuarto_medio}")
            logger.info("=== End Results ===")
            
            return True
            
        except Exception as e:
            logger.error(f"Error generating segment schedule reports: {e}")
            return False


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Segment Schedule Report Generator')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--analysis-excel', default="data/analysis/analisis de datos.xlsx", 
                       help='Path to analysis Excel file')
    parser.add_argument('--segmentos-excel', default="templates/Segmentos.xlsx", 
                       help='Path to segmentos Excel file')
    parser.add_argument('--html-template', default="templates/plantilla_plan_de_estudio.html", 
                       help='Path to HTML template file')
    parser.add_argument('--segments', nargs='+', 
                       help='Specific segments to generate PDFs for (e.g., S1 S2 S7). Default: all segments')
    parser.add_argument('--student-types', nargs='+', choices=['Egresado', 'Cuarto medio'],
                       help='Student types to generate PDFs for. Default: both Egresado and Cuarto medio')
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize the generator
    generator = SegmentScheduleReportGenerator(
        analysis_excel_path=args.analysis_excel,
        segmentos_excel_path=args.segmentos_excel,
        html_template_path=args.html_template,
    )
    
    # Generate all reports (both Egresado and Cuarto medio students)
    success = generator.generate_all_reports(
        segments=args.segments,
        student_types=args.student_types
    )
    
    if success:
        print("Segment schedule reports generated successfully")
    else:
        print("Failed to generate segment schedule reports")
        exit(1)


