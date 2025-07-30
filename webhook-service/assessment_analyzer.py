#!/usr/bin/env python3
"""
Assessment analyzer for individual student assessments
Handles analysis logic for webhook-based individual reports
"""

import logging
import pandas as pd
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class AssessmentAnalyzer:
    def __init__(self):
        """Initialize assessment analyzer"""
        pass
    
    def analyze_user_assessment(self, user_response: Dict[str, Any], question_bank: pd.DataFrame, assessment_title: str = None) -> Dict[str, Any]:
        """
        Analyze individual user assessment results
        
        Args:
            user_response: User's assessment response from API
            question_bank: Question bank DataFrame with correct answers and lectures
            assessment_title: Title of the assessment
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Normalize question bank columns
            question_bank.columns = [col.strip().lower() for col in question_bank.columns]
            
            # Validate question bank structure
            required_cols = {'question_number', 'correct_alternative', 'lecture'}
            if not required_cols.issubset(set(question_bank.columns)):
                missing = required_cols - set(question_bank.columns)
                raise ValueError(f"Question bank missing required columns: {missing}")
            
            # Ensure question_number is integer
            question_bank["question_number"] = question_bank["question_number"].astype(int)
            
            # Get unique lectures
            lectures = question_bank["lecture"].unique().tolist()
            
            # Analyze by lecture
            lecture_results = self._analyze_by_lecture(user_response, question_bank, lectures)
            
            # Calculate overall statistics
            total_questions = len(user_response.get("answers", []))
            passed_lectures = sum(1 for lecture_result in lecture_results.values() 
                                if lecture_result["status"] == "Aprobado")
            
            # Calculate total correct questions across all lectures
            total_correct_questions = sum(lecture_result["correct_answers"] 
                                        for lecture_result in lecture_results.values())
            
            overall_percentage = (passed_lectures / len(lectures) * 100) if lectures else 0
            
            return {
                "user_id": user_response.get("user_id"),
                "title": assessment_title,
                "total_questions": total_questions,
                "correct_questions": total_correct_questions,
                "lectures_analyzed": len(lectures),
                "lectures_passed": passed_lectures,
                "overall_percentage": overall_percentage,
                "lecture_results": lecture_results,
                "lectures": lectures
            }
            
        except Exception as e:
            logger.error(f"Error analyzing user assessment: {str(e)}")
            raise
    
    def _analyze_by_lecture(self, user_response: Dict[str, Any], question_bank: pd.DataFrame, lectures: List[str]) -> Dict[str, Dict[str, Any]]:
        """Analyze user performance by lecture"""
        lecture_results = {}
        
        for lecture in lectures:
            # Get questions for this lecture
            lecture_questions = question_bank[question_bank["lecture"] == lecture]
            
            total_questions = len(lecture_questions)
            correct_answers = 0
            
            # Check each answer
            for _, question_row in lecture_questions.iterrows():
                question_num = question_row["question_number"]
                correct_alternative = question_row["correct_alternative"]
                
                # Find user's answer for this question (1-based indexing)
                if question_num <= len(user_response.get("answers", [])):
                    user_answer = user_response["answers"][question_num - 1].get("answer", "")
                    if user_answer == correct_alternative:
                        correct_answers += 1
            
            # Determine lecture status: ALL questions must be correct to pass
            status = "Aprobado" if correct_answers == total_questions else "Reprobado"
            percentage = (correct_answers / total_questions * 100) if total_questions > 0 else 0
            
            lecture_results[lecture] = {
                "total_questions": total_questions,
                "correct_answers": correct_answers,
                "percentage": percentage,
                "status": status
            }
        
        return lecture_results