"""
Configuration settings for the CL-only guide generator.
"""

from pathlib import Path

BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"

# CL output structure
PROCESSED_DIR = OUTPUT_DIR / "processed"
CL_MASTER_PATH = OUTPUT_DIR / "cl_master.xlsx"

# App config
STREAMLIT_CONFIG = {
    "page_title": "Generador CL",
    "page_icon": "??",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}

# Input resources
NOMBRES_GUIAS_PATH = "output/nombres_guias.xlsx"

# CL schema
CL_COLUMNS = {
    "titulo_texto": "Titulo del texto",
    "tipo_texto": "Tipo de texto",
    "subgenero": "Subgenero",
    "descripcion_texto": "Descripcion texto",
    "programa": "Programa ",
    "n_preguntas": "N Preguntas",
    "codigo_texto": "Codigo Texto",
    "numero_pregunta": "Numero de pregunta",
    "clave": "Clave",
    "habilidad": "Habilidad",
    "tarea_lectora": "Tarea lectora",
    "justificacion": "Justificacion",
    "codigo_spot": "Codigo Spot",
}

CL_COLUMN_ALIASES = {
    "Titulo del texto": ["Título del texto"],
    "Subgenero": ["Subgénero"],
    "Descripcion texto": ["Descripción texto"],
    "N Preguntas": ["Nº Preguntas", "N° Preguntas"],
    "Codigo Texto": ["Código Texto"],
    "Numero de pregunta": ["Número de pregunta"],
    "Justificacion": ["Justificación"],
    "Codigo Spot": ["Código Spot"],
}

CL_REQUIRED_COLUMNS = list(CL_COLUMNS.values())

# Columns that must have a uniform (identical) value across all rows in a single Excel file
CL_UNIFORM_COLUMNS = [
    CL_COLUMNS["titulo_texto"],
    CL_COLUMNS["tipo_texto"],
    CL_COLUMNS["subgenero"],
    CL_COLUMNS["descripcion_texto"],
    CL_COLUMNS["programa"],
    CL_COLUMNS["n_preguntas"],
    CL_COLUMNS["codigo_texto"],
    CL_COLUMNS["codigo_spot"],
]

CL_FILTER_ORDER_TOP_DOWN = [
    CL_COLUMNS["tipo_texto"],
    CL_COLUMNS["subgenero"],
    CL_COLUMNS["titulo_texto"],
    CL_COLUMNS["descripcion_texto"],
]

CL_FILTER_ORDER_INDEPENDENT = [
    CL_COLUMNS["programa"],
    CL_COLUMNS["habilidad"],
    CL_COLUMNS["tarea_lectora"],
]

# Tracking columns persisted in master
USAGE_TRACKING_BASE_COLUMNS = ["Número de usos"]

CL_TRACKING_COLUMNS = {
    "numero_usos": "Número de usos",
}


def get_usage_column_names(usage_number: int) -> tuple[str, str]:
    """Return (guide_name_col, date_col) for a given usage number."""
    return (
        f"Nombre guía (uso {usage_number})",
        f"Fecha descarga (uso {usage_number})",
    )

CL_DEFAULT_TARGET_QUESTIONS = 25
CL_DEFAULT_TOTAL_TEXTS = 8
CL_FILENAME_PREFIX = "guia_cl"


def ensure_directories() -> None:
    """Create required CL directories."""
    for directory in [
        INPUT_DIR,
        OUTPUT_DIR,
        PROCESSED_DIR,
    ]:
        directory.mkdir(parents=True, exist_ok=True)


def ensure_cl_directories() -> None:
    """Backward-compatible wrapper."""
    ensure_directories()


if __name__ == "__main__":
    ensure_directories()
    print("Directories created successfully")
 