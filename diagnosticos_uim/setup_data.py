#!/usr/bin/env python3
"""
Setup script to copy question files from the existing project
"""

import os
import shutil
from pathlib import Path

def setup_data():
    """Copy question files from the existing project"""
    
    # Source and destination paths
    source_dir = Path("../reportes de test de diagnostico/data/questions")
    dest_dir = Path("data/questions")
    
    # Create destination directory if it doesn't exist
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    # Question files to copy
    question_files = [
        "M1.csv",
        "CL.csv", 
        "CIEN.csv",
        "HYST.csv"
    ]
    
    print("Setting up data files...")
    
    for file_name in question_files:
        source_file = source_dir / file_name
        dest_file = dest_dir / file_name
        
        if source_file.exists():
            shutil.copy2(source_file, dest_file)
            print(f"✓ Copied {file_name}")
        else:
            print(f"✗ Source file not found: {source_file}")
    
    print("\nData setup complete!")
    print(f"Question files copied to: {dest_dir.absolute()}")

if __name__ == "__main__":
    setup_data()
