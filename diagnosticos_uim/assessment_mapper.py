#!/usr/bin/env python3
"""
Assessment Mapper - Maps assessment IDs to assessment types
"""

import os
import re
from typing import Optional, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AssessmentMapper:
    def __init__(self):
        """Initialize the assessment mapper with environment variables"""
        self.assessment_ids = {
            os.getenv("M1_ASSESSMENT_ID"): "M1",
            os.getenv("F30M_ASSESSMENT_ID"): "F30M",
            os.getenv("B30M_ASSESSMENT_ID"): "B30M",
            os.getenv("Q30M_ASSESSMENT_ID"): "Q30M",
            os.getenv("HYST_ASSESSMENT_ID"): "HYST"
        }
        
        # Remove None values
        self.assessment_ids = {k: v for k, v in self.assessment_ids.items() if k is not None}
        
        # Create reverse mapping for easy lookup
        self.id_to_type = self.assessment_ids
        self.type_to_id = {v: k for k, v in self.assessment_ids.items()}
    
    def extract_assessment_id(self, url: str) -> Optional[str]:
        """
        Extract assessment ID from LearnWorlds URL
        
        Args:
            url: LearnWorlds assessment URL
            
        Returns:
            Assessment ID or None if not found
        """
        if not url:
            return None
        
        # Pattern: unit=24_character_hex_id (LearnWorlds format)
        match = re.search(r"unit=([a-fA-F0-9]{24})", url)
        if match:
            return match.group(1)
        return None
    
    def get_assessment_type(self, assessment_id: str) -> Optional[str]:
        """
        Get assessment type from assessment ID
        
        Args:
            assessment_id: Assessment ID
            
        Returns:
            Assessment type (M1, F30M, B30M, Q30M, HYST) or None if not found
        """
        return self.id_to_type.get(assessment_id)
    
    def get_assessment_id(self, assessment_type: str) -> Optional[str]:
        """
        Get assessment ID from assessment type
        
        Args:
            assessment_type: Assessment type (M1, F30M, B30M, Q30M, HYST)
            
        Returns:
            Assessment ID or None if not found
        """
        return self.type_to_id.get(assessment_type)
    
    def get_all_assessment_types(self) -> list:
        """
        Get all available assessment types
        
        Returns:
            List of assessment types
        """
        return list(self.type_to_id.keys())
    
    def get_all_assessment_ids(self) -> list:
        """
        Get all available assessment IDs
        
        Returns:
            List of assessment IDs
        """
        return list(self.id_to_type.keys())
    
    def is_valid_assessment_id(self, assessment_id: str) -> bool:
        """
        Check if assessment ID is valid
        
        Args:
            assessment_id: Assessment ID to check
            
        Returns:
            True if valid, False otherwise
        """
        return assessment_id in self.id_to_type
    
    def is_valid_assessment_type(self, assessment_type: str) -> bool:
        """
        Check if assessment type is valid
        
        Args:
            assessment_type: Assessment type to check
            
        Returns:
            True if valid, False otherwise
        """
        return assessment_type in self.type_to_id
    
    def get_mapping_info(self) -> Dict[str, str]:
        """
        Get current mapping information
        
        Returns:
            Dictionary with assessment ID to type mapping
        """
        return self.id_to_type.copy()

# Global instance
assessment_mapper = AssessmentMapper()
