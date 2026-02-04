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
            excel_files = [f for f in files if f.lower().endswith(('.xlsx', '.xls'))]
            
            return excel_files
            
        except Exception as e:
            print(f"Error getting Excel files for {subject}: {e}")
            return []
    
    def get_already_processed_files(self, subject: str) -> List[str]:
        """
        Get list of files that are already included in the master Excel.
        
        Args:
            subject: Subject area
            
        Returns:
            List of already processed file names
        """
        try:
            # Check if master Excel exists
            filename = f"excel_maestro_{subject.lower()}.xlsx"
            master_path = EXCELES_MAESTROS_DIR / filename
            
            if not self.storage.exists(str(master_path)):
                return []
            
            # Read master Excel and get unique source files
            df = pd.read_excel(master_path)
            if 'Archivo origen' in df.columns:
                return df['Archivo origen'].unique().tolist()
            else:
                return []
                
        except Exception as e:
            print(f"Error getting processed files for {subject}: {e}")
            return []
    
    def get_new_excel_files(self, subject: str) -> List[str]:
        """
        Get list of new Excel files that haven't been processed yet.
        
        Args:
            subject: Subject area
            
        Returns:
            List of new file paths
        """
        try:
            all_files = self.get_updated_excel_files(subject)
            processed_files = self.get_already_processed_files(subject)
            
            # Filter out already processed files
            new_files = []
            for file_path in all_files:
                file_name = Path(file_path).name
                if file_name not in processed_files:
                    new_files.append(file_path)
            
            return new_files
            
        except Exception as e:
            print(f"Error getting new Excel files for {subject}: {e}")
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
    
    def _consolidate_files_list(self, excel_files: List[str], file_label: str = "file") -> pd.DataFrame:
        """
        Private helper method to consolidate a list of Excel files.
        
        Args:
            excel_files: List of file paths to consolidate
            file_label: Label for print messages (e.g., "file", "new file")
            
        Returns:
            Consolidated DataFrame
        """
        if not excel_files:
            return pd.DataFrame()
        
        # Read and combine Excel files
        dataframes = []
        
        for file_path in excel_files:
            print(f"Reading {file_label}: {file_path}...")
            df = self.read_excel_file(file_path)
            
            if not df.empty:
                # Add source file information
                df['Archivo origen'] = Path(file_path).name
                dataframes.append(df)
            else:
                print(f"Warning: Empty or invalid file {file_path}")
        
        if not dataframes:
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
            
            # Use helper method to consolidate
            consolidated_df = self._consolidate_files_list(excel_files, file_label="file")
            
            if consolidated_df.empty:
                print(f"No valid data found for subject: {subject}")
            
            return consolidated_df
            
        except Exception as e:
            print(f"Error consolidating Excel files for {subject}: {e}")
            return pd.DataFrame()
    
    def consolidate_new_excels_only(self, subject: str) -> pd.DataFrame:
        """
        Consolidate only new Excel files that haven't been processed yet.
        
        Args:
            subject: Subject area
            
        Returns:
            DataFrame with only new data
        """
        try:
            # Get only new Excel files
            new_excel_files = self.get_new_excel_files(subject)
            
            if not new_excel_files:
                print(f"No new Excel files found for subject: {subject}")
                return pd.DataFrame()
            
            print(f"Found {len(new_excel_files)} new files to process for {subject}")
            
            # Use helper method to consolidate
            new_data_df = self._consolidate_files_list(new_excel_files, file_label="new file")
            
            if new_data_df.empty:
                print(f"No valid new data found for subject: {subject}")
            
            return new_data_df
            
        except Exception as e:
            print(f"Error consolidating new Excel files for {subject}: {e}")
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
    
    def append_to_master_excel(self, new_df: pd.DataFrame, subject: str) -> str:
        """
        Append new data to existing master Excel file, preserving existing columns.
        
        Args:
            new_df: New data to append
            subject: Subject area
            
        Returns:
            Path to the updated master file
        """
        try:
            # Ensure output directory exists
            self.storage.ensure_directory(str(EXCELES_MAESTROS_DIR))
            
            # Create filename
            filename = f"excel_maestro_{subject.lower()}.xlsx"
            output_path = EXCELES_MAESTROS_DIR / filename
            
            # Check if master file exists
            if self.storage.exists(str(output_path)):
                # Read existing master file
                existing_df = pd.read_excel(output_path)
                
                # Ensure new data has same columns as existing data
                # Add missing columns to new data with default values
                for col in existing_df.columns:
                    if col not in new_df.columns:
                        new_df[col] = None  # or appropriate default value
                
                # Add missing columns to existing data
                for col in new_df.columns:
                    if col not in existing_df.columns:
                        existing_df[col] = None
                
                # Combine dataframes
                combined_df = pd.concat([existing_df, new_df], ignore_index=True, sort=False)
                
                # Remove duplicates based on PreguntaID (keep first occurrence)
                initial_count = len(combined_df)
                combined_df = combined_df.drop_duplicates(subset=['PreguntaID'], keep='first')
                final_count = len(combined_df)
                
                if initial_count != final_count:
                    print(f"Removed {initial_count - final_count} duplicate questions when appending")
                
                # Sort by PreguntaID for consistency
                combined_df = combined_df.sort_values('PreguntaID').reset_index(drop=True)
                
                # Save updated master file
                combined_df.to_excel(output_path, index=False)
                print(f"Appended {len(new_df)} new questions to master Excel: {output_path}")
                
            else:
                # No existing master file, save new data as master
                new_df.to_excel(output_path, index=False)
                print(f"Created new master Excel with {len(new_df)} questions: {output_path}")
            
            return str(output_path)
            
        except Exception as e:
            print(f"Error appending to master Excel for {subject}: {e}")
            return ""
    
    def consolidate_and_save(self, subject: str) -> Tuple[pd.DataFrame, str]:
        """
        Complete FULL consolidation pipeline for a subject.
        This RESETS the master file by processing ALL Excel files.
        
        Use this when you want to rebuild the master file from scratch.
        For adding only new files, use consolidate_and_append_new() instead.
        
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
    
    def consolidate_and_append_new(self, subject: str) -> Tuple[pd.DataFrame, str]:
        """
        INCREMENTAL consolidation pipeline - only processes new files and appends to existing master.
        This is the RECOMMENDED default method as it's faster and preserves existing data.
        
        Only processes Excel files that are not already in the master file.
        If the master file doesn't exist, it creates a new one.
        
        Args:
            subject: Subject area
            
        Returns:
            Tuple of (new data DataFrame, output file path)
        """
        # Get only new Excel files and consolidate them
        new_data_df = self.consolidate_new_excels_only(subject)
        
        if new_data_df.empty:
            print(f"No new data to process for {subject}")
            return new_data_df, ""
        
        # Append new data to existing master Excel
        output_path = self.append_to_master_excel(new_data_df, subject)
        
        return new_data_df, output_path
    
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
        FULL consolidation of Excel files for all subjects.
        This RESETS all master files by processing ALL Excel files.
        
        Use this when you want to rebuild all master files from scratch.
        For adding only new files, use consolidate_all_subjects_incremental() instead.
        
        Returns:
            Dictionary mapping subject names to (DataFrame, output_path) tuples
        """
        results = {}
        
        for subject in SUBJECT_FOLDERS.keys():
            print(f"\nFull consolidation for {subject}...")
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
    
    def consolidate_all_subjects_incremental(self) -> Dict[str, Tuple[pd.DataFrame, str]]:
        """
        INCREMENTAL consolidation for all subjects - only processes new files.
        This is the RECOMMENDED default method as it's faster and preserves existing data.
        
        Only processes Excel files that are not already in the master files.
        If a master file doesn't exist, it creates a new one.
        
        Returns:
            Dictionary mapping subject names to (new_data_DataFrame, output_path) tuples
        """
        results = {}
        
        for subject in SUBJECT_FOLDERS.keys():
            print(f"\nIncremental consolidation for {subject}...")
            new_df, output_path = self.consolidate_and_append_new(subject)
            
            if not new_df.empty:
                results[subject] = (new_df, output_path)
                
                # Print summary for new data
                summary = self.get_consolidation_summary(new_df, subject)
                print(f"New data summary for {subject}:")
                print(f"  New questions added: {summary['total_questions']}")
                print(f"  New source files: {len(summary.get('source_files', {}))}")
            else:
                print(f"No new data found for {subject}")
        
        return results

# Test the consolidator
if __name__ == "__main__":
    from storage import StorageClient
    
    storage = StorageClient()
    consolidator = MasterConsolidator(storage)
    
    # Test incremental consolidation for a specific subject
    test_subject = "Física"
    
    print("Testing incremental consolidation...")
    new_df, output_path = consolidator.consolidate_and_append_new(test_subject)
    
    if not new_df.empty:
        print(f"Added {len(new_df)} new questions for {test_subject}")
        print(f"Output saved to: {output_path}")
        
        # Get summary for new data
        summary = consolidator.get_consolidation_summary(new_df, test_subject)
        print(f"New data summary: {summary}")
        
        # Validate new data
        issues = consolidator.validate_consolidated_data(new_df)
        print(f"Validation issues: {issues}")
    else:
        print(f"No new data to consolidate for {test_subject}")
    
    # Test full consolidation (original method)
    print("\nTesting full consolidation...")
    df, output_path = consolidator.consolidate_and_save(test_subject)
    
    if not df.empty:
        print(f"Consolidated {len(df)} total questions for {test_subject}")
        print(f"Output saved to: {output_path}")
    else:
        print(f"No data to consolidate for {test_subject}")
