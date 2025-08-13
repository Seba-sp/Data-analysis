#!/usr/bin/env python3
"""
Checklist table generation for the Segment Schedule Report Generator.
"""

import logging
from typing import Dict, List, Optional

import pandas as pd

from data_loader import DataLoader
from utils import find_col_case_insensitive, find_user_row

logger = logging.getLogger(__name__)


class ChecklistGenerator:
    """Handles generation of checklist tables for different student types and test types."""
    
    def __init__(self, data_loader: DataLoader):
        self.data_loader = data_loader

    def generate_checklist_tables_html(self, reporte_row: pd.Series, test_type: str, is_cuarto_medio: bool = False) -> str:
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
            checklist_xl = self.data_loader.load_checklist_workbook(test_type)
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
                    return self.generate_cl_skill_percentage_table(reporte_row, is_cuarto_medio)
                else:
                    return ""
            elif test_type == "CIEN":
                # For CIEN, always show "Cuarto medio" sheet, but only fill when completed
                return self.generate_cuarto_medio_checklist_table(checklist_xl, reporte_row, test_type)
            else:
                # For M1, always generate the table from "Cuarto medio" sheet
                return self.generate_cuarto_medio_checklist_table(checklist_xl, reporte_row, test_type)
        else:
            # For Egresado students:
            if test_type == "HYST":
                # Special handling for HYST: Show both Nivel General and Nivel Avanzado tables
                # regardless of whether student completed the test or not
                return self.generate_egresado_checklist_tables(checklist_xl, reporte_row, test_type, nivel)
            else:
                # For other test types:
                if rindio_value != 1:
                    # If Egresado student didn't complete the test, show Nivel 1 format (empty Check cells)
                    return self.generate_egresado_checklist_tables(checklist_xl, reporte_row, test_type, "Nivel 1")
                else:
                    # If Egresado student completed the test, use their actual nivel
                    return self.generate_egresado_checklist_tables(checklist_xl, reporte_row, test_type, nivel)

    def calculate_column_widths(self, df: pd.DataFrame, test_type: str = "M1") -> Dict[str, str]:
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

    def generate_cuarto_medio_checklist_table(self, checklist_xl: pd.ExcelFile, reporte_row: pd.Series, test_type: str) -> str:
        """Generate checklist table for Cuarto medio students."""
        try:
            df = checklist_xl.parse("Cuarto medio")
        except Exception as e:
            logger.warning(f"Could not parse 'Cuarto medio' sheet from {test_type} checklist: {e}")
            return ""
        
        # Get student's lecture results
        lecture_results = self.data_loader.get_student_lectures_results(reporte_row, test_type)
        
        # Get all columns from the dataframe
        columns = df.columns.tolist()
        
        # Calculate column widths
        column_widths = self.calculate_column_widths(df, test_type)
        
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

    def generate_egresado_checklist_tables(self, checklist_xl: pd.ExcelFile, reporte_row: pd.Series, test_type: str, nivel: str) -> str:
        """Generate checklist tables for Egresado students based on their nivel."""
        sheets = self.data_loader.get_checklist_sheets_for_nivel(test_type, nivel)
        html = ""
        
        # Get student's lecture results
        lecture_results = self.data_loader.get_student_lectures_results(reporte_row, test_type)
        
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
            column_widths = self.calculate_column_widths(df, test_type)
                    
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
                html += self.generate_cl_skill_percentage_table(reporte_row, is_cuarto_medio=False)
        
        return html

    def generate_cl_skill_percentage_table(self, reporte_row: pd.Series, is_cuarto_medio: bool = False) -> str:
        """Generate CL skill percentage table for students who completed the CL test."""
        # Get student's CL test results
        self.data_loader.ensure_analysis_loaded()
        cl_test_sheet = self.data_loader._safe_read_sheet(self.data_loader.analysis_xl, "CL")
        
        if cl_test_sheet is None:
            return ""
        
        # Find the student's row in the CL test results
        col_user_id = find_col_case_insensitive(cl_test_sheet, ["user_id"]) or "user_id"
        col_email = find_col_case_insensitive(cl_test_sheet, ["email"]) or "email"
        
        user_id = reporte_row.get(col_user_id)
        email = reporte_row.get(col_email)
        
        student_row = find_user_row(cl_test_sheet, user_id, email)
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

    def add_checklist_to_html(self, html_content: str, reporte_row: pd.Series, is_cuarto_medio: bool = False) -> str:
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
                        generated_checklists.append(self.generate_checklist_tables_html(reporte_row, test_type, is_cuarto_medio))
                elif test_type == "CIEN":
                    # For CIEN, always show (but only fill when completed)
                    generated_checklists.append(self.generate_checklist_tables_html(reporte_row, test_type, is_cuarto_medio))
                else:
                    # For M1, always show
                    generated_checklists.append(self.generate_checklist_tables_html(reporte_row, test_type, is_cuarto_medio))
            
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
                checklist_content = self.generate_checklist_tables_html(reporte_row, test_type, is_cuarto_medio)
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
