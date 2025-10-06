"""
Master Excel consolidation module for combining multiple Excel files by subject.
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple

from storage import StorageClient
from config import EXCELS_ACTUALIZADOS_DIR, EXCELES_MAESTROS_DIR, SUBJECT_FOLDERS

class MasterConsolidator:
    """Handles consolidation of multiple Excel files into master files by subject."""
    
    def __init__(self, storage_client: StorageClient):
        self.storage = storage_client
    
    def get_updated_excel_files(self, subject: str) -> List[str]:
        """
        Get list of updated Excel files for a specific subject.
        
        Args:
            subject: Subject area (Física, Matemática, etc.)
            
        Returns:
            List of file paths
        """
        try:
            subject_folder = SUBJECT_FOLDERS.get(subject, subject.upper())
            excel_dir = EXCELS_ACTUALIZADOS_DIR / subject_folder
            
            if not self.storage.exists(str(excel_dir)):
                print(f"Directory {excel_dir} does not exist")
                return []
            
            # List all Excel files in the directory
            files = self.storage.list_files(str(excel_dir))
            excel_files = [f for f in files if f.endswith(('.xlsx', '.xls'))]
            
            return excel_files
            
        except Exception as e:
            print(f"Error getting Excel files for {subject}: {e}")
            return []
    
    def read_excel_file(self, file_path: str) -> pd.DataFrame:
        """
        Read an Excel file and return as DataFrame.
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            DataFrame with Excel data
        """
        try:
            df = pd.read_excel(file_path)
            return df
        except Exception as e:
            print(f"Error reading Excel file {file_path}: {e}")
            return pd.DataFrame()
    
    def consolidate_subject_excels(self, subject: str) -> pd.DataFrame:
        """
        Consolidate all Excel files for a specific subject into one master DataFrame.
        
        Args:
            subject: Subject area
            
        Returns:
            Consolidated DataFrame
        """
        try:
            # Get all Excel files for the subject
            excel_files = self.get_updated_excel_files(subject)
            
            if not excel_files:
                print(f"No Excel files found for subject: {subject}")
                return pd.DataFrame()
            
            # Read and combine all Excel files
            dataframes = []
            
            for file_path in excel_files:
                print(f"Reading {file_path}...")
                df = self.read_excel_file(file_path)
                
                if not df.empty:
                    # Add source file information
                    df['Archivo origen'] = Path(file_path).name
                    dataframes.append(df)
                else:
                    print(f"Warning: Empty or invalid file {file_path}")
            
            if not dataframes:
                print(f"No valid data found for subject: {subject}")
                return pd.DataFrame()
            
            # Concatenate all DataFrames
            consolidated_df = pd.concat(dataframes, ignore_index=True, sort=False)
            
            # Remove duplicates based on PreguntaID
            initial_count = len(consolidated_df)
            consolidated_df = consolidated_df.drop_duplicates(subset=['PreguntaID'], keep='first')
            final_count = len(consolidated_df)
            
            if initial_count != final_count:
                print(f"Removed {initial_count - final_count} duplicate questions")
            
            # Sort by PreguntaID for consistency
            consolidated_df = consolidated_df.sort_values('PreguntaID').reset_index(drop=True)
            
            return consolidated_df
            
        except Exception as e:
            print(f"Error consolidating Excel files for {subject}: {e}")
            return pd.DataFrame()
    
    def save_master_excel(self, df: pd.DataFrame, subject: str) -> str:
        """
        Save consolidated DataFrame as master Excel file.
        
        Args:
            df: Consolidated DataFrame
            subject: Subject area
            
        Returns:
            Path to the saved master file
        """
        try:
            # Ensure output directory exists
            self.storage.ensure_directory(str(EXCELES_MAESTROS_DIR))
            
            # Create filename
            filename = f"excel_maestro_{subject.lower()}.xlsx"
            output_path = EXCELES_MAESTROS_DIR / filename
            
            # Save Excel file
            df.to_excel(output_path, index=False)
            
            print(f"Master Excel saved: {output_path}")
            return str(output_path)
            
        except Exception as e:
            print(f"Error saving master Excel for {subject}: {e}")
            return ""
    
    def consolidate_and_save(self, subject: str) -> Tuple[pd.DataFrame, str]:
        """
        Complete consolidation pipeline for a subject.
        
        Args:
            subject: Subject area
            
        Returns:
            Tuple of (consolidated DataFrame, output file path)
        """
        # Consolidate Excel files
        consolidated_df = self.consolidate_subject_excels(subject)
        
        if consolidated_df.empty:
            return consolidated_df, ""
        
        # Save master Excel
        output_path = self.save_master_excel(consolidated_df, subject)
        
        return consolidated_df, output_path
    
    def get_consolidation_summary(self, df: pd.DataFrame, subject: str) -> Dict[str, any]:
        """
        Get summary statistics for consolidated data.
        
        Args:
            df: Consolidated DataFrame
            subject: Subject area
            
        Returns:
            Dictionary with summary statistics
        """
        if df.empty:
            return {'subject': subject, 'total_questions': 0}
        
        summary = {
            'subject': subject,
            'total_questions': len(df),
            'source_files': df['Archivo origen'].value_counts().to_dict() if 'Archivo origen' in df.columns else {},
            'areas': df['Área temática'].value_counts().to_dict() if 'Área temática' in df.columns else {},
            'difficulties': df['Dificultad'].value_counts().to_dict() if 'Dificultad' in df.columns else {},
            'skills': df['Habilidad'].value_counts().to_dict() if 'Habilidad' in df.columns else {},
            'answer_keys': df['Clave'].value_counts().to_dict() if 'Clave' in df.columns else {}
        }
        
        return summary
    
    def validate_consolidated_data(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """
        Validate consolidated data and return issues found.
        
        Args:
            df: Consolidated DataFrame
            
        Returns:
            Dictionary with validation results
        """
        issues = {
            'missing_pregunta_ids': [],
            'duplicate_pregunta_ids': [],
            'missing_files': [],
            'invalid_data': []
        }
        
        if df.empty:
            issues['invalid_data'].append("DataFrame is empty")
            return issues
        
        # Check for missing PreguntaIDs
        missing_ids = df[df['PreguntaID'].isna() | (df['PreguntaID'] == '')]
        if not missing_ids.empty:
            issues['missing_pregunta_ids'].append(f"{len(missing_ids)} rows with missing PreguntaID")
        
        # Check for duplicate PreguntaIDs
        duplicates = df[df.duplicated(subset=['PreguntaID'], keep=False)]
        if not duplicates.empty:
            duplicate_ids = duplicates['PreguntaID'].unique().tolist()
            issues['duplicate_pregunta_ids'].append(f"Duplicate PreguntaIDs: {duplicate_ids}")
        
        # Check for missing file paths
        missing_files = df[df['Ruta relativa'].isna() | (df['Ruta relativa'] == '')]
        if not missing_files.empty:
            issues['missing_files'].append(f"{len(missing_files)} rows with missing file paths")
        
        return issues
    
    def consolidate_all_subjects(self) -> Dict[str, Tuple[pd.DataFrame, str]]:
        """
        Consolidate Excel files for all subjects.
        
        Returns:
            Dictionary mapping subject names to (DataFrame, output_path) tuples
        """
        results = {}
        
        for subject in SUBJECT_FOLDERS.keys():
            print(f"\nConsolidating {subject}...")
            df, output_path = self.consolidate_and_save(subject)
            
            if not df.empty:
                results[subject] = (df, output_path)
                
                # Print summary
                summary = self.get_consolidation_summary(df, subject)
                print(f"Summary for {subject}:")
                print(f"  Total questions: {summary['total_questions']}")
                print(f"  Source files: {len(summary.get('source_files', {}))}")
            else:
                print(f"No data found for {subject}")
        
        return results

# Test the consolidator
if __name__ == "__main__":
    from storage import StorageClient
    
    storage = StorageClient()
    consolidator = MasterConsolidator(storage)
    
    # Test consolidation for a specific subject
    test_subject = "Física"
    df, output_path = consolidator.consolidate_and_save(test_subject)
    
    if not df.empty:
        print(f"Consolidated {len(df)} questions for {test_subject}")
        print(f"Output saved to: {output_path}")
        
        # Get summary
        summary = consolidator.get_consolidation_summary(df, test_subject)
        print(f"Summary: {summary}")
        
        # Validate data
        issues = consolidator.validate_consolidated_data(df)
        print(f"Validation issues: {issues}")
    else:
        print(f"No data to consolidate for {test_subject}")
