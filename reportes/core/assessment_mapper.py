"""Unified assessment mapper: assessment_id -> (report_type, assessment_type)."""

import os
import re
from typing import Dict, Optional, Tuple

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Env var names for diagnosticos assessment IDs
_DIAG_MAPPING: Dict[str, Tuple[str, str]] = {
    "M1_ASSESSMENT_ID": ("diagnosticos", "M1"),
    "CL_ASSESSMENT_ID": ("diagnosticos", "CL"),
    "CIEN_ASSESSMENT_ID": ("diagnosticos", "CIEN"),
    "HYST_ASSESSMENT_ID": ("diagnosticos", "HYST"),
}

# Env var names for diagnosticos_uim assessment IDs
_UIM_MAPPING: Dict[str, Tuple[str, str]] = {
    "M1_UIM_ASSESSMENT_ID": ("diagnosticos_uim", "M1"),
    "F30M_ASSESSMENT_ID": ("diagnosticos_uim", "F30M"),
    "B30M_ASSESSMENT_ID": ("diagnosticos_uim", "B30M"),
    "Q30M_ASSESSMENT_ID": ("diagnosticos_uim", "Q30M"),
    "HYST_UIM_ASSESSMENT_ID": ("diagnosticos_uim", "HYST"),
}


class AssessmentMapper:
    """Maps hex assessment IDs to (report_type, assessment_type) tuples.

    Reads hex values from environment variables at construction time.
    Both diagnosticos and diagnosticos_uim mappings are merged into a single
    lookup dict keyed by hex assessment ID.
    """

    def __init__(self):
        """Build the routes dict from environment variables.

        Entries with a None env var value are silently skipped.
        If the same hex value appears in both DIAG and UIM mappings
        (i.e. the same hex is used by both systems), the UIM entry wins.
        """
        self._routes: Dict[str, Tuple[str, str]] = {}

        # Load diagnosticos routes first
        for env_var, route in _DIAG_MAPPING.items():
            hex_id = os.getenv(env_var)
            if hex_id is not None:
                self._routes[hex_id] = route

        # Load diagnosticos_uim routes (override on collision)
        for env_var, route in _UIM_MAPPING.items():
            hex_id = os.getenv(env_var)
            if hex_id is not None:
                self._routes[hex_id] = route

    def get_route(self, assessment_id: str) -> Optional[Tuple[str, str]]:
        """Return (report_type, assessment_type) for a known assessment ID.

        Args:
            assessment_id: 24-character hex assessment ID from LearnWorlds.

        Returns:
            (report_type, assessment_type) tuple, or None if unknown.
        """
        return self._routes.get(assessment_id)

    def extract_assessment_id(self, url: str) -> Optional[str]:
        """Extract assessment ID from a LearnWorlds URL.

        Pattern: unit=<24-character hex id>

        Args:
            url: LearnWorlds assessment URL.

        Returns:
            24-character hex assessment ID, or None if not found.
        """
        if not url:
            return None
        match = re.search(r"unit=([a-fA-F0-9]{24})", url)
        if match:
            return match.group(1)
        return None

    def is_valid_assessment_id(self, assessment_id: str) -> bool:
        """Check whether assessment_id is in the known routes.

        Args:
            assessment_id: Hex assessment ID to validate.

        Returns:
            True if the ID maps to a known route.
        """
        return assessment_id in self._routes
