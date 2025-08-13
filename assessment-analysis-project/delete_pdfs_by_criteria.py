#!/usr/bin/env python3
"""
PDF Deletion Script - Deletes PDF files based on specific criteria from the Reporte sheet.
"""

import os
import argparse
import pandas as pd
import glob
from typing import List, Set, Tuple
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PDFDeleter:
    def __init__(self, analysis_excel_path: str = "data/analysis/analisis de datos.xlsx"):
        self.analysis_excel_path = analysis_excel_path
        self._df_reporte = None
        
    def _load_reporte_sheet(self) -> pd.DataFrame:
        if self._df_reporte is not None:
            return self._df_reporte
            
        try:
            logger.info(f"Loading analysis workbook: {self.analysis_excel_path}")
            excel_file = pd.ExcelFile(self.analysis_excel_path)
            self._df_reporte = excel_file.parse(sheet_name="Reporte")
            logger.info(f"Loaded {len(self._df_reporte)} rows from Reporte sheet")
            return self._df_reporte
        except Exception as e:
            logger.error(f"Error loading Excel file: {e}")
            raise
    
    def _find_col_case_insensitive(self, df: pd.DataFrame, targets: List[str]) -> str:
        if df is None or df.empty:
            return None
        lower_to_actual = {c.strip().lower(): c for c in df.columns}
        for t in targets:
            key = t.strip().lower()
            if key in lower_to_actual:
                return lower_to_actual[key]
        return None
    
    def filter_students_by_criteria(self, nivel: str = None, rindio: int = None, test_type: str = None, 
                                  unprepared_took_test: bool = False) -> pd.DataFrame:
        df = self._load_reporte_sheet()
        
        nivel_col = None
        rindio_col = None
        prepara_col = None
        
        if test_type:
            nivel_col = self._find_col_case_insensitive(df, [f"Nivel {test_type}"])
            rindio_col = self._find_col_case_insensitive(df, [f"Rindio {test_type}", f"Rindió {test_type}"])
            prepara_col = self._find_col_case_insensitive(df, [f"Prepara {test_type}", f"Prepara y rindió {test_type}"])
            
            if not nivel_col:
                logger.warning(f"Column 'Nivel {test_type}' not found")
            if not rindio_col:
                logger.warning(f"Column 'Rindió {test_type}' not found")
            if not prepara_col:
                logger.warning(f"Column 'Prepara {test_type}' not found")
        
        filtered_df = df.copy()
        
        if unprepared_took_test and rindio_col and prepara_col:
            # Filter for students who took the test (rindió = 1) but didn't prepare (prepara = 0)
            filtered_df = filtered_df[(filtered_df[rindio_col] == 1) & (filtered_df[prepara_col] == 0)]
            logger.info(f"Filtered by unprepared students who took {test_type}: {len(filtered_df)} students")
        else:
            if nivel and nivel_col:
                filtered_df = filtered_df[filtered_df[nivel_col] == nivel]
                logger.info(f"Filtered by {nivel_col} = {nivel}: {len(filtered_df)} students")
                
            if rindio is not None and rindio_col:
                filtered_df = filtered_df[filtered_df[rindio_col] == rindio]
                logger.info(f"Filtered by {rindio_col} = {rindio}: {len(filtered_df)} students")
        
        return filtered_df
    
    def find_pdfs_for_students(self, students_df: pd.DataFrame) -> List[str]:
        pdf_files = []
        
        email_col = self._find_col_case_insensitive(students_df, ["email", "correo"])
        if not email_col:
            logger.error("Email column not found in Reporte sheet")
            return []
        
        for _, student in students_df.iterrows():
            email = student[email_col]
            if pd.isna(email) or not email:
                continue
                
            email_clean = str(email).strip()
            
            # Find PDFs in all segment directories
            segment_dirs = glob.glob("reports/S*") + ["reports/Cuarto medio"]
            
            for segment_dir in segment_dirs:
                if not os.path.exists(segment_dir):
                    continue
                    
                # Look for PDFs with this email
                patterns = [
                    f"{email_clean}_segmento_*.pdf",
                    f"{email_clean}.pdf"
                ]
                
                for pattern in patterns:
                    matching_files = glob.glob(os.path.join(segment_dir, pattern))
                    pdf_files.extend(matching_files)
        
        # Remove duplicates and sort by creation time (newest first)
        unique_pdfs = list(set(pdf_files))
        unique_pdfs.sort(key=lambda x: os.path.getctime(x), reverse=True)
        
        return unique_pdfs
    
    def delete_pdfs(self, pdf_files: List[str], dry_run: bool = True) -> Tuple[int, List[str]]:
        deleted_files = []
        
        for pdf_file in pdf_files:
            if os.path.exists(pdf_file):
                if dry_run:
                    logger.info(f"Would delete: {pdf_file}")
                else:
                    try:
                        os.remove(pdf_file)
                        deleted_files.append(pdf_file)
                        logger.info(f"Deleted: {pdf_file}")
                    except Exception as e:
                        logger.error(f"Error deleting {pdf_file}: {e}")
            else:
                logger.warning(f"File not found: {pdf_file}")
        
        return len(deleted_files), deleted_files
    
    def run_deletion(self, nivel: str = None, rindio: int = None, test_type: str = None, 
                    unprepared_took_test: bool = False, dry_run: bool = True) -> None:
        logger.info("Starting PDF deletion process...")
        
        filtered_students = self.filter_students_by_criteria(nivel, rindio, test_type, unprepared_took_test)
        
        if filtered_students.empty:
            logger.warning("No students found matching the criteria")
            return
        
        logger.info(f"Found {len(filtered_students)} students matching criteria")
        
        pdf_files = self.find_pdfs_for_students(filtered_students)
        
        if not pdf_files:
            logger.warning("No PDF files found for the filtered students")
            return
        
        logger.info(f"Found {len(pdf_files)} PDF files to delete")
        
        print(f"\n{'='*60}")
        print(f"PDF DELETION SUMMARY")
        print(f"{'='*60}")
        print(f"Criteria:")
        if unprepared_took_test:
            print(f"  - Unprepared students who took {test_type} test")
        else:
            if nivel:
                print(f"  - Nivel: {nivel}")
            if rindio is not None:
                print(f"  - Rindió: {rindio}")
            if test_type:
                print(f"  - Test Type: {test_type}")
        print(f"Students matching criteria: {len(filtered_students)}")
        print(f"PDF files to delete: {len(pdf_files)}")
        print(f"{'='*60}")
        
        if dry_run:
            print("\nDRY RUN - No files will be deleted")
            print("Files that would be deleted (sorted by creation time, newest first):")
            for pdf_file in pdf_files:
                try:
                    creation_time = os.path.getctime(pdf_file)
                    from datetime import datetime
                    creation_date = datetime.fromtimestamp(creation_time).strftime('%Y-%m-%d %H:%M:%S')
                    print(f"  - {pdf_file} (created: {creation_date})")
                except Exception as e:
                    print(f"  - {pdf_file} (creation time unavailable)")
        else:
            response = input(f"\nDo you want to delete {len(pdf_files)} PDF files? (Y/N): ").strip().upper()
            
            if response == 'Y':
                deleted_count, deleted_files = self.delete_pdfs(pdf_files, dry_run=False)
                print(f"\nSuccessfully deleted {deleted_count} PDF files")
            else:
                print("Deletion cancelled by user")


def main():
    parser = argparse.ArgumentParser(description="Delete PDF files based on specific criteria")
    parser.add_argument("--nivel", type=str, help="Level to filter by (e.g., 'Nivel 3', 'Nivel 2')")
    parser.add_argument("--rindio", type=int, choices=[0, 1], help="Whether they completed the test (0 or 1)")
    parser.add_argument("--test_type", type=str, choices=["CL", "M1", "CIEN", "HYST"], 
                       help="Type of test to filter by")
    parser.add_argument("--unprepared_took_test", action="store_true",
                       help="Filter for students who took the test (rindió=1) but didn't prepare (prepara=0)")
    parser.add_argument("--excel_path", type=str, default="data/analysis/analisis de datos.xlsx",
                       help="Path to the analysis Excel file")
    parser.add_argument("--dry_run", action="store_true", default=True,
                       help="Show what would be deleted without actually deleting (default)")
    parser.add_argument("--execute", action="store_true",
                       help="Actually delete the files (overrides --dry_run)")
    
    args = parser.parse_args()
    
    if not args.nivel and args.rindio is None and not args.unprepared_took_test:
        print("Error: You must specify at least one of --nivel, --rindio, or --unprepared_took_test")
        return
    
    if not args.test_type:
        print("Error: You must specify --test_type")
        return
    
    dry_run = not args.execute
    
    deleter = PDFDeleter(args.excel_path)
    deleter.run_deletion(
        nivel=args.nivel,
        rindio=args.rindio,
        test_type=args.test_type,
        unprepared_took_test=args.unprepared_took_test,
        dry_run=dry_run
    )


if __name__ == "__main__":
    main()