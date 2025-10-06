"""
Question ID generation module for the Generador de Guías Escolares system.
Generates unique PreguntaID following the format:
{EJE}-{AREA}-{SUBTEMA}-{HABILIDAD}-{DIFICULTAD}-{CLAVE}-{RANDOM}
"""

import re
import random
import string
import pandas as pd
from unidecode import unidecode
from typing import Dict, Optional

def clean_text_for_abbreviation(text: str, length: int = 3) -> str:
    """
    Clean text and create abbreviation by removing accents and taking first N characters.
    
    Args:
        text: Input text to abbreviate
        length: Length of abbreviation (default 3)
    
    Returns:
        Abbreviated text in uppercase
    """
    if not text or pd.isna(text):
        return "XXX"
    
    # Convert to string and strip whitespace
    text = str(text).strip()
    
    # Remove accents and convert to uppercase
    clean_text = unidecode(text).upper()
    
    # Remove special characters, keep only letters and numbers
    clean_text = re.sub(r'[^A-Z0-9\s]', '', clean_text)
    
    # Remove extra spaces and split into words
    words = clean_text.split()
    
    if not words:
        return "XXX"
    
    # Take first word if it's long enough, otherwise combine words
    if len(words[0]) >= length:
        return words[0][:length]
    else:
        # Combine words until we have enough characters
        combined = ""
        for word in words:
            combined += word
            if len(combined) >= length:
                break
        return combined[:length] if combined else "XXX"

def generate_random_suffix(length: int = 8) -> str:
    """
    Generate random suffix with pattern: letter, letter, number, number, letter, letter, number, number.
    
    Args:
        length: Length of random suffix (should be 8 for proper pattern)
    
    Returns:
        Random string following the pattern LLNNLLNN
    """
    if length != 8:
        # Fallback to old format if length is not 8
        characters = string.ascii_uppercase + string.digits
        return ''.join(random.choices(characters, k=length))
    
    # Generate pattern: letter, letter, number, number, letter, letter, number, number
    letters = string.ascii_uppercase
    digits = string.digits
    
    suffix = (
        random.choice(letters) +  # Position 0: letter
        random.choice(letters) +  # Position 1: letter
        random.choice(digits) +   # Position 2: number
        random.choice(digits) +   # Position 3: number
        random.choice(letters) +  # Position 4: letter
        random.choice(letters) +  # Position 5: letter
        random.choice(digits) +   # Position 6: number
        random.choice(digits)     # Position 7: number
    )
    
    return suffix

def generate_pregunta_id(
    eje_tematico: str,
    area_tematica: str, 
    conocimiento_subtema: str,
    habilidad: str,
    dificultad: str,
    clave: str,
    separator: str = "-"
) -> str:
    """
    Generate a unique PreguntaID following the specified format.
    
    Args:
        eje_tematico: Eje temático (e.g., "Ondas")
        area_tematica: Área temática (e.g., "Física")
        conocimiento_subtema: Conocimiento/Subtema (e.g., "Longitud de onda")
        habilidad: Habilidad cognitiva (e.g., "Análisis")
        dificultad: Nivel de dificultad (e.g., "Media")
        clave: Letra de respuesta correcta (e.g., "C")
        separator: Separator character (default "-")
    
    Returns:
        Generated PreguntaID (e.g., "OND-FIS-LONG-ANA-MED-C-A1B2")
    """
    # Generate abbreviations
    eje_abbr = clean_text_for_abbreviation(eje_tematico)
    area_abbr = clean_text_for_abbreviation(area_tematica)
    subtema_abbr = clean_text_for_abbreviation(conocimiento_subtema)
    habilidad_abbr = clean_text_for_abbreviation(habilidad)
    dificultad_abbr = clean_text_for_abbreviation(dificultad)
    
    # Clean clave (should be single letter A-D)
    clave_clean = str(clave).strip().upper() if clave else "X"
    if len(clave_clean) > 1:
        clave_clean = clave_clean[0]
    if clave_clean not in "ABCD":
        clave_clean = "X"
    
    # Generate random suffix
    random_suffix = generate_random_suffix()
    
    # Combine all parts
    pregunta_id = separator.join([
        eje_abbr,
        area_abbr, 
        subtema_abbr,
        habilidad_abbr,
        dificultad_abbr,
        clave_clean,
        random_suffix
    ])
    
    return pregunta_id

def validate_pregunta_id(pregunta_id: str) -> bool:
    """
    Validate if a PreguntaID follows the correct format.
    
    Args:
        pregunta_id: PreguntaID to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not pregunta_id:
        return False
    
    # Expected format: EJE-AREA-SUBTEMA-HABILIDAD-DIFICULTAD-CLAVE-RANDOM
    parts = pregunta_id.split("-")
    
    if len(parts) != 7:
        return False
    
    # Check each part
    eje, area, subtema, habilidad, dificultad, clave, random_suffix = parts
    
    # All parts except clave should be 3 characters, clave should be 1, random should be 8
    if (len(eje) != 3 or len(area) != 3 or len(subtema) != 3 or 
        len(habilidad) != 3 or len(dificultad) != 3 or 
        len(clave) != 1 or len(random_suffix) != 8):
        return False
    
    # Clave should be A-D
    if clave not in "ABCD":
        return False
    
    # All parts should be alphanumeric
    for part in [eje, area, subtema, habilidad, dificultad]:
        if not part.isalnum():
            return False
    
    # Validate random suffix pattern: LLNNLLNN (letter, letter, number, number, letter, letter, number, number)
    if len(random_suffix) == 8:
        pattern = random_suffix
        # Check positions 0,1,4,5 are letters and positions 2,3,6,7 are digits
        if (pattern[0].isalpha() and pattern[1].isalpha() and 
            pattern[2].isdigit() and pattern[3].isdigit() and
            pattern[4].isalpha() and pattern[5].isalpha() and 
            pattern[6].isdigit() and pattern[7].isdigit()):
            return True
        else:
            return False
    else:
        # Fallback for non-8 character suffixes (backward compatibility)
        return random_suffix.isalnum()

def parse_pregunta_id(pregunta_id: str) -> Optional[Dict[str, str]]:
    """
    Parse a PreguntaID into its components.
    
    Args:
        pregunta_id: PreguntaID to parse
    
    Returns:
        Dictionary with components or None if invalid
    """
    if not validate_pregunta_id(pregunta_id):
        return None
    
    parts = pregunta_id.split("-")
    return {
        "eje_tematico": parts[0],
        "area_tematica": parts[1],
        "conocimiento_subtema": parts[2], 
        "habilidad": parts[3],
        "dificultad": parts[4],
        "clave": parts[5],
        "random_suffix": parts[6]
    }

# Test the ID generation
if __name__ == "__main__":
    # Test with sample data
    test_id = generate_pregunta_id(
        eje_tematico="Ondas",
        area_tematica="Física", 
        conocimiento_subtema="Longitud de onda",
        habilidad="Análisis",
        dificultad="Media",
        clave="C"
    )
    
    print(f"Generated ID: {test_id}")
    print(f"Valid: {validate_pregunta_id(test_id)}")
    print(f"Parsed: {parse_pregunta_id(test_id)}")
