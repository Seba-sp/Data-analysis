"""
Merge multiple Excel files into a single Excel file.
Adds the source filename as the first column for each file.

Usage:
    python merge_excel_files.py <folder_path>
    python merge_excel_files.py data/Batch_3
    python merge_excel_files.py C:/path/to/folder
"""
import os
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime


def merge_excel_files(folder_path: str, output_filename: str = None):
    """
    Merge all Excel files in a folder into a single Excel file.
    
    Args:
        folder_path: Path to folder containing Excel files
        output_filename: Optional custom output filename
    """
    # Validate folder
    if not os.path.exists(folder_path):
        print(f"ERROR: Folder not found: {folder_path}")
        return
    
    if not os.path.isdir(folder_path):
        print(f"ERROR: Not a directory: {folder_path}")
        return
    
    # Find all .xlsx files
    files = []
    for file in Path(folder_path).glob('*.xlsx'):
        files.append(str(file))
    
    if not files:
        print(f"No .xlsx files found in: {folder_path}")
        return
    
    # Sort files for consistent processing
    files.sort()
    
    print("="*80)
    print("EXCEL FILES MERGER")
    print("="*80)
    print(f"Folder: {os.path.abspath(folder_path)}")
    print(f"Files found: {len(files)}")
    print("="*80)
    
    # List files
    print("\nFiles to merge:")
    for i, file in enumerate(files, 1):
        print(f"  {i}. {os.path.basename(file)}")
    
    # Process each file
    print("\nProcessing files...")
    all_dataframes = []
    
    for file_path in files:
        filename = os.path.basename(file_path)
        filename_without_ext = os.path.splitext(filename)[0]
        
        try:
            print(f"\n  Reading: {filename}")
            
            # Read Excel file
            df = pd.read_excel(file_path)
            
            print(f"    Rows: {len(df)}")
            print(f"    Columns: {list(df.columns)}")
            
            # Add filename as first column
            df.insert(0, 'Archivo', filename_without_ext)
            
            # Append to list
            all_dataframes.append(df)
            
            print(f"    [OK] Added with filename column")
            
        except Exception as e:
            print(f"    [ERROR] Failed to read {filename}: {e}")
            continue
    
    if not all_dataframes:
        print("\nERROR: No files were successfully processed")
        return
    
    # Merge all dataframes
    print("\n" + "="*80)
    print("MERGING FILES...")
    print("="*80)
    
    try:
        merged_df = pd.concat(all_dataframes, ignore_index=True)
        
        print(f"Total rows in merged file: {len(merged_df)}")
        print(f"Columns: {list(merged_df.columns)}")
        
        # Generate output filename
        if not output_filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            folder_name = os.path.basename(os.path.abspath(folder_path))
            output_filename = f"merged_{folder_name}_{timestamp}.xlsx"
        
        # Save to same folder as input files
        output_path = os.path.join(folder_path, output_filename)
        
        print(f"\nSaving merged file...")
        merged_df.to_excel(output_path, index=False, engine='openpyxl')
        
        print(f"[OK] Saved: {output_path}")
        print(f"Size: {os.path.getsize(output_path):,} bytes")
        
        # Show preview
        print("\n" + "="*80)
        print("PREVIEW (first 5 rows):")
        print("="*80)
        print(merged_df.head(5).to_string(index=False))
        
        # Summary
        print("\n" + "="*80)
        print("MERGE COMPLETE")
        print("="*80)
        print(f"Files merged: {len(all_dataframes)}")
        print(f"Total rows: {len(merged_df)}")
        print(f"Output file: {output_path}")
        print("="*80)
        
        return output_path
        
    except Exception as e:
        print(f"\nERROR: Failed to merge files: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main entry point."""
    # Check arguments
    if len(sys.argv) < 2:
        print("ERROR: Missing folder path argument")
        print()
        print("Usage:")
        print(f"  python {os.path.basename(__file__)} <folder_path>")
        print()
        print("Examples:")
        print(f"  python {os.path.basename(__file__)} data/Batch_3")
        print(f"  python {os.path.basename(__file__)} .")
        print(f"  python {os.path.basename(__file__)} C:/path/to/folder")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    
    # Optional: custom output filename
    output_filename = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Run merger
    merge_excel_files(folder_path, output_filename)


if __name__ == '__main__':
    main()
