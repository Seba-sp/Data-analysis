#!/usr/bin/env python3
"""
Assessment analyzer for individual student assessments
Handles analysis logic for webhook-based individual reports
"""

import logging
import pandas as pd
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

class AssessmentAnalyzer:
    def __init__(self):
        """Initialize assessment analyzer"""
        pass
    
    def analyze_user_assessment(self, user_response: Dict[str, Any], question_bank: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze individual user assessment results
        
        Args:
            user_response: User's assessment response from API
            question_bank: Question bank DataFrame with correct answers and areas
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Normalize question bank columns
            question_bank.columns = [col.strip().lower() for col in question_bank.columns]
            
            # Validate question bank structure
            required_cols = {'question_number', 'correct_answer', 'area'}
            if not required_cols.issubset(set(question_bank.columns)):
                missing = required_cols - set(question_bank.columns)
                raise ValueError(f"Question bank missing required columns: {missing}")
            
            # Ensure question_number is integer
            question_bank["question_number"] = question_bank["question_number"].astype(int)
            
            # Get unique areas
            areas = question_bank["area"].unique().tolist()
            
            # Analyze by area
            area_results = self._analyze_by_area(user_response, question_bank, areas)
            
            # Calculate overall statistics
            total_questions = len(user_response.get("answers", []))
            correct_answers = sum(1 for area_result in area_results.values() 
                                if area_result["status"] == "Aprobado")
            overall_percentage = (correct_answers / len(areas) * 100) if areas else 0
            
            # Determine level
            level = self._calculate_level(overall_percentage)
            
            return {
                "user_id": user_response.get("user_id"),
                "total_questions": total_questions,
                "areas_analyzed": len(areas),
                "areas_passed": correct_answers,
                "overall_percentage": overall_percentage,
                "level": level,
                "area_results": area_results,
                "areas": areas
            }
            
        except Exception as e:
            logger.error(f"Error analyzing user assessment: {str(e)}")
            raise
    
    def _analyze_by_area(self, user_response: Dict[str, Any], question_bank: pd.DataFrame, areas: List[str]) -> Dict[str, Dict[str, Any]]:
        """Analyze user performance by area"""
        area_results = {}
        
        for area in areas:
            # Get questions for this area
            area_questions = question_bank[question_bank["area"] == area]
            
            total_questions = len(area_questions)
            correct_answers = 0
            
            # Check each answer
            for _, question_row in area_questions.iterrows():
                question_num = question_row["question_number"]
                correct_answer = question_row["correct_answer"]
                
                # Find user's answer for this question (1-based indexing)
                if question_num <= len(user_response.get("answers", [])):
                    user_answer = user_response["answers"][question_num - 1].get("answer", "")
                    if user_answer == correct_answer:
                        correct_answers += 1
            
            # Determine area status
            status = "Aprobado" if correct_answers == total_questions else "Reprobado"
            percentage = (correct_answers / total_questions * 100) if total_questions > 0 else 0
            
            area_results[area] = {
                "total_questions": total_questions,
                "correct_answers": correct_answers,
                "percentage": percentage,
                "status": status
            }
        
        return area_results
    
    def _calculate_level(self, percentage: float) -> str:
        """Calculate student level based on percentage"""
        if percentage >= 55:
            return "Nivel 3"
        else:
            return "Nivel 2"
    
    def get_failed_areas(self, area_results: Dict[str, Dict[str, Any]]) -> List[str]:
        """Get list of areas where student failed"""
        return [area for area, result in area_results.items() 
                if result["status"] == "Reprobado"]
    
    def get_passed_areas(self, area_results: Dict[str, Dict[str, Any]]) -> List[str]:
        """Get list of areas where student passed"""
        return [area for area, result in area_results.items() 
                if result["status"] == "Aprobado"] 