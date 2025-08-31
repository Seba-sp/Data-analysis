#!/usr/bin/env python3
"""
Data loading and caching logic for the Segment Schedule Report Generator.
"""

import logging
from typing import Dict, List, Optional

import pandas as pd

from utils import find_col_case_insensitive, find_user_row

logger = logging.getLogger(__name__)


class DataLoader:
    """Handles loading and caching of Excel workbooks and data."""
    
    def __init__(
        self,
        analysis_excel_path: str = "data/analysis/analisis de datos.xlsx",
        segmentos_excel_path: str = "templates/Segmentos.xlsx",
    ) -> None:
        self.analysis_excel_path = analysis_excel_path
        self.segmentos_excel_path = segmentos_excel_path

        # Cached analysis workbook and sheets
        self._analysis_xl: Optional[pd.ExcelFile] = None
        self._df_reporte: Optional[pd.DataFrame] = None

        # Cached Segmentos workbook mapping: segment_key (e.g., "S7") -> DataFrame
        self._segment_key_to_df: Dict[str, pd.DataFrame] = {}
        
        # Cached checklist workbooks
        self._checklist_workbooks: Dict[str, pd.ExcelFile] = {}

    def ensure_analysis_loaded(self) -> None:
        """Load analysis workbook and Reporte sheet if not already loaded."""
        if self._analysis_xl is not None:
            return
        logger.info(f"Loading analysis workbook: {self.analysis_excel_path}")
        self._analysis_xl = pd.ExcelFile(self.analysis_excel_path)
        self._df_reporte = self._safe_read_sheet(self._analysis_xl, "Reporte")
        
        # Log level distribution for each test type
        self._log_level_distribution()

    def ensure_segmentos_loaded(self) -> None:
        """Load segmentos workbook if not already loaded."""
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
        nivel_m1_col = find_col_case_insensitive(self._df_reporte, ["Nivel M1"])
        nivel_cl_col = find_col_case_insensitive(self._df_reporte, ["Nivel CL"])
        nivel_cien_col = find_col_case_insensitive(self._df_reporte, ["Nivel CIEN"])
        nivel_hyst_col = find_col_case_insensitive(self._df_reporte, ["Nivel HYST"])
        
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
        """Safely read an Excel sheet, return empty DataFrame if sheet doesn't exist."""
        try:
            return xl.parse(sheet_name=name)
        except ValueError:
            logger.warning(f"Sheet '{name}' not found in workbook {xl.io}")
            return pd.DataFrame()

    def load_checklist_workbook(self, test_type: str) -> pd.ExcelFile:
        """Load checklist workbook for a specific test type."""
        if test_type not in self._checklist_workbooks:
            checklist_path = f"data/Checklist/{test_type}.xlsx"
            logger.info(f"Loading checklist workbook: {checklist_path}")
            self._checklist_workbooks[test_type] = pd.ExcelFile(checklist_path)
        return self._checklist_workbooks[test_type]

    def get_checklist_sheets_for_nivel(self, test_type: str, nivel: str) -> List[str]:
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

    def get_student_lectures_results(self, reporte_row: pd.Series, test_type: str) -> Dict[str, str]:
        """Get student's passed/failed lectures for a specific test type."""
        # Load the analysis workbook to get the test results
        self.ensure_analysis_loaded()
        
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
        col_user_id = find_col_case_insensitive(test_sheet, ["user_id"]) or "user_id"
        col_email = find_col_case_insensitive(test_sheet, ["email"]) or "email"
        
        user_id = reporte_row.get(col_user_id)
        email = reporte_row.get(col_email)
        
        student_row = find_user_row(test_sheet, user_id, email)
        if student_row is None:
            return {}
        
        # Extract lecture results based on test type
        lecture_results = {}
        
        if test_type == "M1":
            # Look for passed_lectures and failed_lectures columns
            passed_col = find_col_case_insensitive(test_sheet, ["passed_lectures"])
            failed_col = find_col_case_insensitive(test_sheet, ["failed_lectures"])
            
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
            passed_col = find_col_case_insensitive(test_sheet, ["passed_lectures"])
            failed_col = find_col_case_insensitive(test_sheet, ["failed_lectures"])
            
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
            passed_col = find_col_case_insensitive(test_sheet, ["passed_lectures"])
            failed_col = find_col_case_insensitive(test_sheet, ["failed_lectures"])
            
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

    # Property getters for cached data
    @property
    def df_reporte(self) -> Optional[pd.DataFrame]:
        """Get the Reporte DataFrame."""
        self.ensure_analysis_loaded()
        return self._df_reporte

    @property
    def segment_key_to_df(self) -> Dict[str, pd.DataFrame]:
        """Get the segment key to DataFrame mapping."""
        self.ensure_segmentos_loaded()
        return self._segment_key_to_df

    @property
    def analysis_xl(self) -> Optional[pd.ExcelFile]:
        """Get the analysis Excel file."""
        self.ensure_analysis_loaded()
        return self._analysis_xl
