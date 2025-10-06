"""
Excel processing module for handling question metadata and file paths.
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict

from storage import StorageClient
from config import EXCELS_ACTUALIZADOS_DIR, EXCEL_COLUMNS, SUBJECT_FOLDERS
from id_generator import generate_pregunta_id

# =============================================================================
# CONFIGURATION CONSTANTS - All hardcoded values here at the top
# =============================================================================

# Valid values for different columns
VALID_ANSWER_KEYS = ['A', 'B', 'C', 'D']
VALID_DIFFICULTY_VALUES = ['1', '2', '3']

# New columns to add to Excel files
NEW_COLUMNS = ['PreguntaID', 'Archivo generado', 'Ruta relativa']

# Default file suffix for updated Excel files
DEFAULT_SUFFIX = "_actualizado"

# Excel formatting settings
MAX_COLUMN_WIDTH = 50
MIN_COLUMN_WIDTH = 10


class ExcelProcessor:
    """Handles Excel file operations for question metadata."""
    
    def __init__(self, storage_client: StorageClient):
        self.storage = storage_client
    
    def read_excel_metadata(self, excel_path: str) -> pd.DataFrame:
        """Read Excel file with question metadata."""
        try:
            df = pd.read_excel(excel_path)
            print(f"Loaded Excel with {len(df)} rows and {len(df.columns)} columns")
            return df
        except FileNotFoundError:
            print(f"Error: Excel file not found: {excel_path}")
            return pd.DataFrame()
        except Exception as e:
            print(f"Error reading Excel file {excel_path}: {e}")
            return pd.DataFrame()
    
    def generate_pregunta_ids(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate PreguntaID for each row in the DataFrame."""
        if df.empty:
            return df
            
        df = df.copy()
        
        def _generate_id_for_row(row: pd.Series) -> str:
            """Generate ID for a single row."""
            try:
                return generate_pregunta_id(
                    eje_tematico=row.get(EXCEL_COLUMNS['eje_tematico'], ''),
                    area_tematica=row.get(EXCEL_COLUMNS['area_tematica'], ''),
                    conocimiento_subtema=row.get(EXCEL_COLUMNS['conocimiento_subtema'], ''),
                    habilidad=row.get(EXCEL_COLUMNS['habilidad'], ''),
                    dificultad=row.get(EXCEL_COLUMNS['dificultad'], ''),
                    clave=row.get(EXCEL_COLUMNS['clave'], '')
                )
            except Exception as e:
                print(f"Warning: Error generating PreguntaID for row {row.name}: {e}")
                return f"ERROR-{row.name:03d}"
        
        df['PreguntaID'] = df.apply(_generate_id_for_row, axis=1)
        
        # Check for duplicate IDs
        duplicates = df['PreguntaID'].duplicated().sum()
        if duplicates > 0:
            print(f"Warning: Found {duplicates} duplicate PreguntaIDs")
        
        return df
    
    def add_file_paths(
        self, 
        df: pd.DataFrame, 
        processing_results: List[Dict[str, str]], 
        subject: str
    ) -> pd.DataFrame:
        """Add file paths and names to the DataFrame based on processing results."""
        if df.empty:
            return df
            
        df = df.copy()
        
        # Initialize new columns
        for col in NEW_COLUMNS[1:]:  # Skip PreguntaID as it's already added
            df[col] = ''
        
        # Create mapping from pregunta_id to processing results
        results_map = {result['pregunta_id']: result for result in processing_results}
        
        # Update DataFrame with file information
        for idx, row in df.iterrows():
            pregunta_id = row.get('PreguntaID', '')
            
            if pregunta_id in results_map:
                result = results_map[pregunta_id]
                df.at[idx, 'Archivo generado'] = result.get('filename', '')
                
                # Convert absolute path to relative path from project root
                file_path = result.get('file_path', '')
                if file_path:
                    try:
                        # Convert to Path object and make relative to current working directory
                        abs_path = Path(file_path)
                        rel_path = abs_path.relative_to(Path.cwd())
                        df.at[idx, 'Ruta relativa'] = str(rel_path)
                    except ValueError:
                        # If path is not under current directory, keep as is
                        df.at[idx, 'Ruta relativa'] = file_path
                else:
                    df.at[idx, 'Ruta relativa'] = ''
            else:
                print(f"Warning: No processing result found for PreguntaID {pregunta_id}")
        
        # Report statistics
        successful_files = sum(1 for result in results_map.values() if result.get('filename'))
        print(f"Added file paths for {successful_files}/{len(df)} questions")
        
        return df
    
    def save_updated_excel(
        self, 
        df: pd.DataFrame, 
        original_path: str, 
        subject: str,
        suffix: str = DEFAULT_SUFFIX
    ) -> str:
        """Save updated Excel file with new columns."""
        if df.empty:
            print("Warning: Cannot save empty DataFrame")
            return ""
            
        try:
            # Determine output directory
            subject_folder = SUBJECT_FOLDERS.get(subject, subject.upper())
            output_dir = EXCELS_ACTUALIZADOS_DIR / subject_folder
            self.storage.ensure_directory(str(output_dir))
            
            # Create output filename
            original_name = Path(original_path).stem
            output_filename = f"{original_name}{suffix}.xlsx"
            output_path = output_dir / output_filename
            
            # Save Excel file with proper formatting
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Preguntas')
                
                # Auto-adjust column widths
                worksheet = writer.sheets['Preguntas']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max(max_length + 2, MIN_COLUMN_WIDTH), MAX_COLUMN_WIDTH)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            print(f"Saved updated Excel with {len(df)} rows to: {output_path}")
            return str(output_path)
            
        except Exception as e:
            print(f"Error saving updated Excel file: {e}")
            return ""
    
    def validate_excel_structure(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """Validate Excel structure and return issues found."""
        issues = {
            'missing_columns': [],
            'empty_values': [],
            'invalid_values': []
        }
        
        if df.empty:
            issues['missing_columns'].append("DataFrame is empty")
            return issues
        
        # Check for missing required columns
        required_columns = list(EXCEL_COLUMNS.values())
        missing_columns = [col for col in required_columns if col not in df.columns]
        issues['missing_columns'] = missing_columns
        
        # Check for empty values in required columns
        for col in required_columns:
            if col in df.columns:
                empty_count = df[col].isna().sum() + (df[col] == '').sum()
                if empty_count > 0:
                    issues['empty_values'].append(f"{col}: {empty_count} empty values")
        
        # Check for invalid values using constants defined at the top
        if EXCEL_COLUMNS['clave'] in df.columns:
            invalid_claves = df[~df[EXCEL_COLUMNS['clave']].isin(VALID_ANSWER_KEYS)]
            if not invalid_claves.empty:
                issues['invalid_values'].append(f"Invalid clave values: {invalid_claves[EXCEL_COLUMNS['clave']].tolist()}")
        
        if EXCEL_COLUMNS['dificultad'] in df.columns:
            invalid_difficulties = df[~df[EXCEL_COLUMNS['dificultad']].astype(str).isin(VALID_DIFFICULTY_VALUES)]
            if not invalid_difficulties.empty:
                issues['invalid_values'].append(f"Invalid dificultad values: {invalid_difficulties[EXCEL_COLUMNS['dificultad']].tolist()}")
        
        return issues
    


# Test the processor
if __name__ == "__main__":
    from storage import StorageClient
    
    storage = StorageClient()
    processor = ExcelProcessor(storage)
    
    # Test with sample file if it exists
    sample_file = "input/test base.xlsx"
    if storage.exists(sample_file):
        print(f"Testing with file: {sample_file}")
        
        # Read and validate
        df = processor.read_excel_metadata(sample_file)
        
        if not df.empty:
            print(f"\nExcel Summary:")
            print(f"   Total questions: {len(df)}")
            print(f"   Columns: {len(df.columns)}")
            print(f"   Memory usage: {df.memory_usage(deep=True).sum():,} bytes")
            
            # Show value counts for key fields
            key_columns = {
                'subjects': EXCEL_COLUMNS.get('area_tematica'),
                'difficulties': EXCEL_COLUMNS.get('dificultad'),
                'skills': EXCEL_COLUMNS.get('habilidad'),
                'answer_keys': EXCEL_COLUMNS.get('clave')
            }
            
            for key, column_name in key_columns.items():
                if column_name and column_name in df.columns:
                    value_counts = df[column_name].value_counts().to_dict()
                    print(f"   {key.title()}: {value_counts}")
            
            # Validation
            issues = processor.validate_excel_structure(df)
            print(f"\nValidation Results:")
            print(f"   Missing columns: {len(issues['missing_columns'])}")
            print(f"   Empty values: {len(issues['empty_values'])}")
            print(f"   Invalid values: {len(issues['invalid_values'])}")
            
            if any(issues.values()):
                print(f"   Issues: {issues}")
        else:
            print("Error: Could not load Excel file")
    else:
        print(f"Sample file {sample_file} not found")
        print("Available files in input/:")
        try:
            input_files = list(Path("input").glob("*.xlsx"))
            for file in input_files:
                print(f"  - {file.name}")
        except:
            print("  No input directory found")