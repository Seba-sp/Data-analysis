"""
Configuration settings for the Generador de Guías Escolares system.
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"

# Output subdirectories
PREGUNTAS_DIVIDIDAS_DIR = OUTPUT_DIR / "preguntas_divididas"
EXCELS_ACTUALIZADOS_DIR = OUTPUT_DIR / "excels_actualizados"
EXCELES_MAESTROS_DIR = OUTPUT_DIR / "excels_maestros"

# Subject mappings for folder organization
SUBJECT_FOLDERS = {
    "M1": "M1", 
    "M2": "M2",
    "H30M": "H30M",
    "B30M": "B30M",
    "Q30M": "Q30M",
    "F30M": "F30M",
    "Ciencias": "Ciencias"  # Combined subject: F30M + Q30M + B30M
}

# Question ID configuration
ID_CONFIG = {
    "separator": "-",
    "random_suffix_length": 4,
    "abbreviation_length": 3
}

# Excel column mappings
EXCEL_COLUMNS = {
    "eje_tematico": "Eje temático",
    "area_tematica": "Área temática", 
    "conocimiento_subtema": "Unidad temática ",
    "habilidad": "Habilidad",
    "dificultad": "Dificultad",
    "clave": "Clave",
    "descripcion": "Descripción BREVE",
    "enlace_video": "Enlace video",
    "fecha_creacion": "Fecha creacion",
    "instrumento": "Instrumento",
    "n_pregunta_instrumento": "N pregunta instrumento",
    "pregunta_id": "PreguntaID",
    "ruta_relativa": "Ruta relativa",
    "ruta_absoluta": "Ruta absoluta",
    "archivo_origen": "Archivo origen",
    "subject_source": "Subject_Source",  # For Ciencias combined subject
    "numero_usos": "Número de usos"
}

# Required columns that must be present in input Excel files
# These are the columns that users must provide before processing
REQUIRED_INPUT_COLUMNS = [
    "Eje temático",
    "Área temática",
    "Unidad temática ",
    "Habilidad",
    "Dificultad",
    "Clave",
    "Descripción BREVE",
    "Fecha creacion",
    "Instrumento",
    "N pregunta instrumento"
]

# Valid values for different columns
VALID_ANSWER_KEYS = ['A', 'B', 'C', 'D', 'E']
VALID_DIFFICULTY_VALUES = ['1', '2', '3']

# New columns to add to Excel files
NEW_COLUMNS = [
    "PreguntaID",
    "Archivo generado", 
    "Ruta absoluta"
]

# Usage tracking columns - base columns that are always present
USAGE_TRACKING_BASE_COLUMNS = [
    "Número de usos"
]

# Function to generate usage tracking column names for a specific use number
def get_usage_column_names(use_number: int) -> tuple:
    """
    Generate column names for a specific use number.
    
    Args:
        use_number: The use number (1, 2, 3, etc.)
        
    Returns:
        Tuple of (guide_name_column, date_column)
    """
    return (
        f"Nombre guía (uso {use_number})",
        f"Fecha descarga (uso {use_number})"
    )

# Difficulty levels
DIFFICULTY_LEVELS = [1, 2, 3]

# Streamlit app configuration
STREAMLIT_CONFIG = {
    "page_title": "Generador de Guías Escolares - M30M",
    "page_icon": "🧠",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# Color palette for charts
CHART_COLORS = ['#1f77b4', '#d62728', '#ff7f0e', '#2ca02c', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

# Path to allowed guide names
NOMBRES_GUIAS_PATH = "output/nombres_guias.xlsx"

# File extensions
SUPPORTED_EXTENSIONS = {
    "word": [".docx"],
    "excel": [".xlsx", ".xls"]
}

# Ensure all directories exist
def ensure_directories():
    """Create all necessary directories if they don't exist."""
    directories = [
        INPUT_DIR,
        OUTPUT_DIR,
        PREGUNTAS_DIVIDIDAS_DIR,
        EXCELS_ACTUALIZADOS_DIR,
        EXCELES_MAESTROS_DIR
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        
    # Create subject subdirectories in input/ and output/ folders
    for subject_folder in SUBJECT_FOLDERS.values():
        # Skip "Ciencias" as it's a virtual combined subject
        if subject_folder != "Ciencias":
            (INPUT_DIR / subject_folder).mkdir(parents=True, exist_ok=True)
        (PREGUNTAS_DIVIDIDAS_DIR / subject_folder).mkdir(parents=True, exist_ok=True)
        (EXCELS_ACTUALIZADOS_DIR / subject_folder).mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    ensure_directories()
    print("Directories created successfully!")
