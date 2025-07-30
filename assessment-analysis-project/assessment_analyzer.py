#!/usr/bin/env python3
"""
Assessment Analyzer - Analyzes assessment responses for different assessment types
"""

import logging
import pandas as pd
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class AssessmentAnalyzer:
    def __init__(self):
        """Initialize assessment analyzer"""
        pass
    
    def analyze_lecture_based(self, user_response: Dict[str, Any], question_bank: pd.DataFrame, assessment_title: str) -> Dict[str, Any]:
        """
        Analyze lecture-based assessment (M1, HYST)
        All questions in a lecture must be correct to pass
        
        Args:
            user_response: User's assessment response
            question_bank: Question bank DataFrame with columns [question_number, correct_alternative, lecture]
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
                "type": "lecture_based",
                "total_questions": total_questions,
                "correct_questions": total_correct_questions,
                "lectures_analyzed": len(lectures),
                "lectures_passed": passed_lectures,
                "overall_percentage": overall_percentage,
                "lecture_results": lecture_results,
                "lectures": lectures
            }
            
        except Exception as e:
            logger.error(f"Error analyzing lecture-based assessment: {str(e)}")
            raise
    
    def analyze_lecture_based_with_materia(self, user_response: Dict[str, Any], question_bank: pd.DataFrame, assessment_title: str) -> Dict[str, Any]:
        """
        Analyze lecture-based assessment with Materia column (CIEN)
        Groups lectures by Materia and analyzes each group
        
        Args:
            user_response: User's assessment response
            question_bank: Question bank DataFrame with columns [question_number, correct_alternative, lecture, materia]
            assessment_title: Title of the assessment
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Normalize question bank columns
            question_bank.columns = [col.strip().lower() for col in question_bank.columns]
            
            # Validate question bank structure
            required_cols = {'question_number', 'correct_alternative', 'lecture', 'materia'}
            if not required_cols.issubset(set(question_bank.columns)):
                missing = required_cols - set(question_bank.columns)
                raise ValueError(f"Question bank missing required columns: {missing}")
            
            # Ensure question_number is integer
            question_bank["question_number"] = question_bank["question_number"].astype(int)
            
            # Get unique materias
            materias = question_bank["materia"].unique().tolist()
            
            # Analyze by materia
            materia_results = {}
            total_lectures_passed = 0
            total_lectures = 0
            
            for materia in materias:
                materia_questions = question_bank[question_bank["materia"] == materia]
                lectures = materia_questions["lecture"].unique().tolist()
                
                # Analyze lectures within this materia
                lecture_results = self._analyze_by_lecture(user_response, materia_questions, lectures)
                
                # Calculate materia statistics
                passed_lectures = sum(1 for lecture_result in lecture_results.values() 
                                    if lecture_result["status"] == "Aprobado")
                
                materia_results[materia] = {
                    "lectures": lectures,
                    "lecture_results": lecture_results,
                    "total_lectures": len(lectures),
                    "passed_lectures": passed_lectures,
                    "percentage": (passed_lectures / len(lectures) * 100) if lectures else 0
                }
                
                total_lectures += len(lectures)
                total_lectures_passed += passed_lectures
            
            # Calculate overall statistics
            total_questions = len(user_response.get("answers", []))
            total_correct_questions = sum(
                sum(lecture_result["correct_answers"] 
                    for lecture_result in materia_data["lecture_results"].values())
                for materia_data in materia_results.values()
            )
            
            overall_percentage = (total_lectures_passed / total_lectures * 100) if total_lectures > 0 else 0
            
            return {
                "user_id": user_response.get("user_id"),
                "title": assessment_title,
                "type": "lecture_based_with_materia",
                "total_questions": total_questions,
                "correct_questions": total_correct_questions,
                "materias_analyzed": len(materias),
                "total_lectures": total_lectures,
                "total_lectures_passed": total_lectures_passed,
                "overall_percentage": overall_percentage,
                "materia_results": materia_results,
                "materias": materias
            }
            
        except Exception as e:
            logger.error(f"Error analyzing lecture-based assessment with materia: {str(e)}")
            raise
    
    def analyze_percentage_based(self, user_response: Dict[str, Any], question_bank: pd.DataFrame, assessment_title: str) -> Dict[str, Any]:
        """
        Analyze percentage-based assessment (CL)
        Calculates percentage of correct answers per lecture
        
        Args:
            user_response: User's assessment response
            question_bank: Question bank DataFrame with columns [question_number, correct_alternative, lecture]
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
            
            # Analyze by lecture (percentage-based)
            lecture_results = {}
            total_correct_questions = 0
            total_questions = 0
            
            for lecture in lectures:
                # Get questions for this lecture
                lecture_questions = question_bank[question_bank["lecture"] == lecture]
                
                lecture_total_questions = len(lecture_questions)
                lecture_correct_answers = 0
                
                # Check each answer
                for _, question_row in lecture_questions.iterrows():
                    question_num = question_row["question_number"]
                    correct_alternative = question_row["correct_alternative"]
                    
                    # Find user's answer for this question (1-based indexing)
                    if question_num <= len(user_response.get("answers", [])):
                        user_answer = user_response["answers"][question_num - 1].get("answer", "")
                        if user_answer == correct_alternative:
                            lecture_correct_answers += 1
                
                # Calculate percentage for this lecture
                percentage = (lecture_correct_answers / lecture_total_questions * 100) if lecture_total_questions > 0 else 0
                
                lecture_results[lecture] = {
                    "total_questions": lecture_total_questions,
                    "correct_answers": lecture_correct_answers,
                    "percentage": percentage,
                    "status": f"{percentage:.1f}%"
                }
                
                total_questions += lecture_total_questions
                total_correct_questions += lecture_correct_answers
            
            # Calculate overall percentage
            overall_percentage = (total_correct_questions / total_questions * 100) if total_questions > 0 else 0
            
            return {
                "user_id": user_response.get("user_id"),
                "title": assessment_title,
                "type": "percentage_based",
                "total_questions": total_questions,
                "correct_questions": total_correct_questions,
                "lectures_analyzed": len(lectures),
                "overall_percentage": overall_percentage,
                "lecture_results": lecture_results,
                "lectures": lectures
            }
            
        except Exception as e:
            logger.error(f"Error analyzing percentage-based assessment: {str(e)}")
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