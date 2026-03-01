#!/usr/bin/env python3
"""
Utility functions for the Segment Schedule Report Generator.
"""

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def find_col_case_insensitive(df: pd.DataFrame, targets: List[str]) -> Optional[str]:
    """Find a column in DataFrame by case-insensitive matching."""
    if df is None or df.empty:
        return None
    lower_to_actual = {c.strip().lower(): c for c in df.columns}
    for t in targets:
        key = t.strip().lower()
        if key in lower_to_actual:
            return lower_to_actual[key]
    return None


def sanitize_filename(name: str) -> str:
    """Convert filename to safe characters."""
    safe = []
    for ch in str(name):
        if ch.isalnum() or ch in ("_", "-", ".", "@"):
            safe.append(ch)
        else:
            safe.append("_")
    return "".join(safe)


def find_user_row(df: pd.DataFrame, user_id: Optional[str], email: Optional[str]) -> Optional[pd.Series]:
    """Find a user's row in DataFrame by user_id or email."""
    if df is None or df.empty:
        return None
    cols = {c.lower(): c for c in df.columns}
    id_col = cols.get("user_id")
    email_col = cols.get("email")
    row = None
    if user_id and id_col in df.columns:
        matches = df[df[id_col].astype(str) == str(user_id)]
        if not matches.empty:
            row = matches.iloc[0]
    if row is None and email and email_col in df.columns:
        matches = df[df[email_col].astype(str) == str(email)]
        if not matches.empty:
            row = matches.iloc[0]
    return row


def normalize_text(value: Any) -> str:
    """Normalize text by removing accents and non-alphanumeric characters."""
    s = str(value or "").strip().lower()
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
    }
    for a, b in replacements.items():
        s = s.replace(a, b)
    # remove non alphanumeric
    return "".join(ch for ch in s if ch.isalnum())


def format_semana(value: Any) -> str:
    """Format 'Semana' value to a compact label, e.g., '11-08'."""
    try:
        dt = pd.to_datetime(value, errors="coerce")
        if pd.notna(dt):
            return dt.strftime("%d-%m")
    except Exception:
        pass
    s = str(value).strip()
    # Remove full timestamp if present (e.g., '2025-08-11T00:00:00') and keep DD-MM if possible
    if "T" in s:
        s = s.split("T", 1)[0]
    # If yyyy-mm-dd -> dd-mm
    try:
        parts = s.split("-")
        if len(parts) == 3 and len(parts[0]) == 4:
            return f"{parts[2]}-{parts[1]}"
    except Exception:
        pass
    return s


def to_hora_str(value: Any) -> str:
    """Convert hour values to string format."""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    s = str(value).strip()
    # If numeric-like, reduce to integer string (e.g., 9.0 -> "9")
    try:
        f = float(s)
        i = int(round(f))
        if abs(f - i) < 1e-6:
            return str(i)
    except Exception:
        pass
    # Remove ranges and minutes like 9:00-13:00 -> 9
    if ":" in s:
        s2 = s.split(":", 1)[0]
        # In case of ranges like 9-13 -> 9
        s2 = s2.split("-", 1)[0]
        return s2
    # In case of (9:00-13:00)
    s = s.replace("(", "").replace(")", "")
    if ":" in s:
        s = s.split(":", 1)[0]
    if "-" in s:
        s = s.split("-", 1)[0]
    return s


def match_day(series: pd.Series, target_day: str) -> pd.Series:
    """Match day names in a series to a target day."""
    target_norm = normalize_text(target_day)
    return series.astype(str).map(normalize_text) == target_norm


def match_hora(series: pd.Series, target_hora: str) -> pd.Series:
    """Match hour values in a series to a target hour."""
    target = to_hora_str(target_hora)
    return series.map(to_hora_str) == target


def level_to_index_m1_cl(level_value: Any) -> int:
    """Convert M1/CL level values to numeric indices (1-3)."""
    if level_value is None or (isinstance(level_value, float) and pd.isna(level_value)):
        return 1
    s = str(level_value).strip().lower()
    for n in (1, 2, 3):
        if s == f"nivel {n}" or s == str(n):
            return n
    # Default to 1
    return 1


def level_to_index_cien_hyst(level_value: Any) -> int:
    """Convert CIEN/HYST level values to numeric indices (1-2)."""
    if level_value is None or (isinstance(level_value, float) and pd.isna(level_value)):
        return 1
    s = str(level_value).strip().lower()
    if s == "avanzado":
        return 2
    elif s == "general":
        return 1
    # Also handle legacy "Nivel 1" and "Nivel 2" for backward compatibility
    elif s == "nivel 1" or s == "1":
        return 1
    elif s == "nivel 2" or s == "2":
        return 2
    return 1
