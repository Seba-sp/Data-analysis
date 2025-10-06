#!/usr/bin/env python3
"""
Assessment Analyzer - Analyzes assessment responses for different assessment types
"""

import logging
import pandas as pd
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class AssessmentAnalyzer:
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize assessment analyzer with configuration
        
        Args:
            config: Configuration dictionary for assessment types and parameters
        """
        # Default configuration
        self.config = config or self._get_default_config()
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for all assessment types"""
        return {
            "assessment_types": {
                "M1": {
                    "type": "difficulty_based",
                    "columns": ["question_number", "correct_alternative", "lecture", "question_difficulty"],
                    "difficulties": [1, 2],
                    "level_thresholds": {
                        "nivel_1": {"diff1": 75, "diff2": None},
                        "nivel_2": {"diff1": 75, "diff2": 70},
                        "nivel_3": {"diff1": 75, "diff2": 70},
                        "nivel_4": {"diff1": 95, "diff2": 90}
                    },
                    "reported_levels": ["Nivel 1", "Nivel 2", "Nivel 3"],
                    "internal_levels": ["Nivel 1", "Nivel 2", "Nivel 3", "Nivel 4"]
                },
                "CL": {
                    "type": "skill_based", 
                    "columns": ["question_number", "correct_alternative", "skill"],
                    "skills": ["Localizar", "Interpretar", "Evaluar"],
                    "level_thresholds": {
                        "nivel_1": {"interpretar": 80, "evaluar": None},
                        "nivel_2": {"interpretar": 80, "evaluar": 85},
                        "nivel_3": {"interpretar": 80, "evaluar": 85},
                        "nivel_4": {"interpretar": 92, "evaluar": 92}
                    },
                    "reported_levels": ["Nivel 1", "Nivel 2", "Nivel 3"],
                    "internal_levels": ["Nivel 1", "Nivel 2", "Nivel 3", "Nivel 4"]
                },
                "CIEN": {
                    "type": "materia_based",
                    "columns": ["question_number", "correct_alternative", "lecture", "materia"],
                    "failed_lectures_threshold": 30,
                    "reported_levels": ["Nivel 1", "Nivel 2"],
                    "internal_levels": ["Nivel 1", "Nivel 2"]
                },
                "HYST": {
                    "type": "percentage_based",
                    "columns": ["question_number", "correct_alternative", "lecture"],
                    "level_thresholds": {
                        "nivel_1": {"overall_percentage": 80},
                        "nivel_2": {"overall_percentage": 80}
                    },
                    "reported_levels": ["General", "Avanzado"],
                    "internal_levels": ["General", "Avanzado"]
                }
            },
            "csv_settings": {
                "separator": ";",
                "decimal_separator": ",",
                "thousand_separator": ".",
                "lecture_separator": " | "
            },
            "question_column_prefix": "Pregunta",
            "answer_column_name": "answer"
        }

    def _format_percentage_for_excel(self, percentage: float) -> str:
        """
        Format percentage as decimal for Excel compatibility (comma as decimal separator)
        
        Args:
            percentage: Percentage value (0-100)
            
        Returns:
            Formatted percentage string (e.g., "0,56" for 56%)
        """
        decimal_sep = self.config["csv_settings"]["decimal_separator"]
        return f"{percentage / 100:.2f}".replace(".", decimal_sep)

    def _extract_answers_from_response(self, user_response: Dict[str, Any], total_questions: int) -> List[Dict[str, str]]:
        """
        Extract answers from user response in a standardized format
        
        Args:
            user_response: User's assessment response
            total_questions: Total number of questions
            
        Returns:
            List of answer dictionaries
        """
        answers = []
        question_prefix = self.config["question_column_prefix"]
        answer_col = self.config["answer_column_name"]
        
        # Check if response has individual question columns (CSV format)
        if any(f'{question_prefix} {i}' in user_response for i in range(1, total_questions + 1)):
            for i in range(1, total_questions + 1):
                pregunta_col = f'{question_prefix} {i}'
                if pregunta_col in user_response:
                    answer = user_response[pregunta_col]
                    if pd.isna(answer) or answer == '':
                        answer = ''
                    answers.append({answer_col: str(answer)})
                else:
                    answers.append({answer_col: ''})
        else:
            # Check if response has answers array (JSON format)
            answers_array = user_response.get("answers", [])
            for i in range(total_questions):
                if i < len(answers_array):
                    answer = answers_array[i].get(answer_col, "")
                    answers.append({answer_col: str(answer)})
                else:
                    answers.append({answer_col: ''})
        
        return answers

    def analyze_assessment(self, user_response: Dict[str, Any], question_bank: pd.DataFrame, assessment_name: str) -> Dict[str, Any]:
        """
        Generic assessment analysis function that uses configuration
        
        Args:
            user_response: User's assessment response
            question_bank: Question bank DataFrame
            assessment_name: Name of the assessment (must be in config)
            
        Returns:
            Dictionary with analysis results
        """
        try:
            if assessment_name not in self.config["assessment_types"]:
                raise ValueError(f"Unknown assessment type: {assessment_name}")
            
            assessment_config = self.config["assessment_types"][assessment_name]
            assessment_type = assessment_config["type"]
            
            # Normalize question bank columns
            question_bank.columns = [col.strip().lower() for col in question_bank.columns]
            
            # Validate required columns
            required_cols = set(assessment_config["columns"])
            if not required_cols.issubset(set(question_bank.columns)):
                missing = required_cols - set(question_bank.columns)
                raise ValueError(f"Question bank missing required columns: {missing}")
            
            # Route to appropriate analysis method
            if assessment_type == "difficulty_based":
                return self._analyze_by_category_generic(user_response, question_bank, assessment_name, assessment_config)
            elif assessment_type == "skill_based":
                return self._analyze_by_category_generic(user_response, question_bank, assessment_name, assessment_config)
            elif assessment_type == "materia_based":
                return self._analyze_by_category_generic(user_response, question_bank, assessment_name, assessment_config)
            elif assessment_type == "percentage_based":
                return self._analyze_percentage_based_generic(user_response, question_bank, assessment_name, assessment_config)
            else:
                raise ValueError(f"Unknown assessment type: {assessment_type}")
            
        except Exception as e:
            logger.error(f"Error analyzing {assessment_name} assessment: {str(e)}")
            raise
    
    def _analyze_by_category_generic(self, user_response: Dict[str, Any], question_bank: pd.DataFrame, assessment_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generic category-based analysis (difficulty, skill, materia)
        
        Args:
            user_response: User response data
            question_bank: Question bank DataFrame
            assessment_name: Name of the assessment
            config: Assessment configuration
            
        Returns:
            Dictionary with analysis results
        """
        try:
            assessment_type = config["type"]
            
            # Determine category column and categories based on assessment type
            if assessment_type == "difficulty_based":
                category_column = "question_difficulty"
                categories = config["difficulties"]
                result_key = "difficulty_results"
            elif assessment_type == "skill_based":
                category_column = "skill"
                categories = config["skills"]
                result_key = "skill_results"
            elif assessment_type == "materia_based":
                category_column = "materia"
                categories = question_bank["materia"].unique().tolist()
                result_key = "materia_results"
            else:
                raise ValueError(f"Unknown assessment type: {assessment_type}")
            
            # Analyze by category
            category_results = {}
            total_correct_questions = 0
            total_questions = 0
            
            for category in categories:
                # Get questions for this category
                category_questions = question_bank[question_bank[category_column] == category]
                
                category_total_questions = len(category_questions)
                category_correct_answers = 0
                
                # Check each answer
                for _, question_row in category_questions.iterrows():
                    try:
                        # Ensure question_number is a valid integer
                        question_num = question_row["question_number"]
                        if pd.isna(question_num):
                            continue  # Skip questions with NaN question numbers
                        
                        question_num = int(question_num)
                        correct_alternative = question_row["correct_alternative"]
                        
                        # Find user's answer for this question
                        answers = self._extract_answers_from_response(user_response, len(question_bank))
                        if question_num <= len(answers):
                            user_answer = answers[question_num - 1].get(self.config["answer_column_name"], "")
                            if user_answer == correct_alternative:
                                category_correct_answers += 1
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error processing question {question_row.get('question_number', 'unknown')}: {e}")
                        continue
                
                # Calculate percentage for this category
                percentage = (category_correct_answers / category_total_questions * 100) if category_total_questions > 0 else 0
                
                # Store results with appropriate keys based on assessment type
                if assessment_type == "materia_based":
                    category_results[category] = {
                        "total": category_total_questions,
                        "correct": category_correct_answers,
                        "percentage": percentage
                    }
                else:
                    category_results[category] = {
                        "total_questions": category_total_questions,
                        "correct_answers": category_correct_answers,
                        "percentage": percentage,
                        "status": f"{percentage:.1f}%"
                    }
                
                total_questions += category_total_questions
                total_correct_questions += category_correct_answers
            
            # Determine level based on configuration
            # For CIEN, we need to determine level after lecture analysis is complete
            if assessment_name == "CIEN":
                # We'll determine the level after the result is built
                level = "Nivel 1"  # Default, will be updated later
            else:
                level = self._determine_level_unified(category_results, assessment_name)
            
            # Build result dictionary
            result = {
                "user_id": user_response.get("user_id"),
                "title": assessment_name,
                "type": f"{assessment_name.lower()}_{assessment_type}",
                "total_questions": total_questions,
                "correct_questions": total_correct_questions,
                result_key: category_results,
                "level": level,
                "overall_percentage": (total_correct_questions / total_questions * 100) if total_questions > 0 else 0
            }
            
            # Add assessment-specific data
            if assessment_type == "materia_based":
                # For CIEN: Analyze lectures within each materia
                materia_lecture_results = {}
                passed_lectures = []
                failed_lectures = []
                lecture_pass_threshold = config.get("passed_lectures_threshold", 100) # Use config or default
                
                for materia, data in category_results.items():
                    # Get all lectures for this materia
                    materia_questions = question_bank[question_bank["materia"] == materia]
                    materia_lectures = materia_questions["lecture"].unique().tolist()
                    
                    # Analyze lectures within this materia
                    materia_passed_lectures = []
                    materia_failed_lectures = []
                    
                    for lecture in materia_lectures:
                        # Get questions for this lecture within this materia
                        lecture_questions = materia_questions[materia_questions["lecture"] == lecture]
                        lecture_total_questions = len(lecture_questions)
                        lecture_correct_answers = 0
                        
                        # Check each answer for this lecture
                        for _, question_row in lecture_questions.iterrows():
                            try:
                                question_num = question_row["question_number"]
                                if pd.isna(question_num):
                                    continue
                                
                                question_num = int(question_num)
                                correct_alternative = question_row["correct_alternative"]
                                
                                # Find user's answer for this question
                                answers = self._extract_answers_from_response(user_response, len(question_bank))
                                if question_num <= len(answers):
                                    user_answer = answers[question_num - 1].get(self.config["answer_column_name"], "")
                                    if user_answer == correct_alternative:
                                        lecture_correct_answers += 1
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Error processing question {question_row.get('question_number', 'unknown')}: {e}")
                                continue
                        
                        # Determine if lecture is passed (ALL questions must be correct)
                        if lecture_correct_answers == lecture_total_questions and lecture_total_questions > 0:
                            materia_passed_lectures.append(lecture)
                            passed_lectures.append(lecture)
                        else:
                            materia_failed_lectures.append(lecture)
                            failed_lectures.append(lecture)
                    
                    # Store lecture results for this materia
                    materia_lecture_results[materia] = {
                        "passed_lectures": materia_passed_lectures,
                        "failed_lectures": materia_failed_lectures,
                        "passed_lectures_count": len(materia_passed_lectures),
                        "failed_lectures_count": len(materia_failed_lectures)
                    }
                
                result.update({
                    "materias": categories,
                    "materia_lecture_results": materia_lecture_results,
                    "passed_lectures": passed_lectures,
                    "failed_lectures": failed_lectures,
                    "passed_lectures_count": len(passed_lectures),
                    "failed_lectures_count": len(failed_lectures)
                })
                
                # Now determine the CIEN level based on failed lectures count
                failed_lectures_threshold = config.get("failed_lectures_threshold", 30)
                if len(failed_lectures) <= failed_lectures_threshold:
                    result["level"] = "Nivel 2"
                else:
                    result["level"] = "Nivel 1"
            
            return result
            
        except Exception as e:
            logger.error(f"Error in category-based analysis: {str(e)}")
            raise
    
    def _analyze_percentage_based_generic(self, user_response: Dict[str, Any], question_bank: pd.DataFrame, assessment_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generic percentage-based analysis"""
        try:
            # HYST: Only 3 columns - question_number, correct_alternative, lecture
            required_cols = {'question_number', 'correct_alternative', 'lecture'}
            if not required_cols.issubset(set(question_bank.columns)):
                missing = required_cols - set(question_bank.columns)
                raise ValueError(f"Question bank missing required columns: {missing}")
            
            # HYST: Simple percentage-based analysis
            total_questions = len(question_bank)
            total_correct_questions = 0
                
                # Check each answer
            for _, question_row in question_bank.iterrows():
                try:
                    # Ensure question_number is a valid integer
                    question_num = question_row["question_number"]
                    if pd.isna(question_num):
                        continue  # Skip questions with NaN question numbers
                    
                    question_num = int(question_num)
                    correct_alternative = question_row["correct_alternative"]
                    
                    # Find user's answer for this question (1-based indexing)
                    if question_num <= len(user_response.get("answers", [])):
                        user_answer = user_response["answers"][question_num - 1].get(self.config["answer_column_name"], "")
                        if user_answer == correct_alternative:
                            total_correct_questions += 1
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error processing question {question_row.get('question_number', 'unknown')}: {e}")
                    continue
            
            # Calculate overall percentage
            overall_percentage = (total_correct_questions / total_questions * 100) if total_questions > 0 else 0
            
            # Determine level based on configuration
            level = self._determine_level_unified({0: {"percentage": overall_percentage}}, assessment_name)
            
            return {
                "user_id": user_response.get("user_id"),
                "title": assessment_name,
                "type": f"{assessment_name.lower()}_percentage_based",
                "total_questions": total_questions,
                "correct_questions": total_correct_questions,
                "level": level,
                "overall_percentage": overall_percentage
            }
            
        except Exception as e:
            logger.error(f"Error in percentage-based analysis: {str(e)}")
            raise

    def _determine_level_unified(self, results: Dict[Any, Dict[str, Any]], assessment_name: str) -> str:
        """
        Unified level determination function that handles all assessment types
        
        Args:
            results: Dictionary of results for the assessment
            assessment_name: Name of the assessment
            
        Returns:
            Level string based on assessment type and results
        """
        try:
            assessment_config = self.config["assessment_types"][assessment_name]
            assessment_type = assessment_config["type"]
            
            if assessment_type == "difficulty_based":
                # M1: Difficulty-based level determination
                thresholds = assessment_config["level_thresholds"]
                diff1_percentage = results[1]["percentage"]
                diff2_percentage = results[2]["percentage"]
                
                # Check for Nivel 4 conditions (internal)
                nivel_4_thresholds = thresholds["nivel_4"]
                if (diff1_percentage >= nivel_4_thresholds["diff1"] and 
                    diff2_percentage >= nivel_4_thresholds["diff2"]):
                    return "Nivel 3"  # Report as Nivel 3 but internally it's Nivel 4
                
                # Check for Nivel 3 conditions
                nivel_3_thresholds = thresholds["nivel_3"]
                if (diff1_percentage >= nivel_3_thresholds["diff1"] and 
                    diff2_percentage >= nivel_3_thresholds["diff2"]):
                    return "Nivel 3"
                
                # Check for Nivel 2 conditions
                nivel_2_thresholds = thresholds["nivel_2"]
                if (diff1_percentage >= nivel_2_thresholds["diff1"] and 
                    diff2_percentage < nivel_2_thresholds["diff2"]):
                    return "Nivel 2"
                
                return "Nivel 1"
                
            elif assessment_type == "skill_based":
                # CL: Skill-based level determination
                thresholds = assessment_config["level_thresholds"]
                interpretar_percentage = results["Interpretar"]["percentage"]
                evaluar_percentage = results["Evaluar"]["percentage"]
                
                # Check for Nivel 4 conditions (internal)
                nivel_4_thresholds = thresholds["nivel_4"]
                if (interpretar_percentage >= nivel_4_thresholds["interpretar"] and 
                    evaluar_percentage >= nivel_4_thresholds["evaluar"]):
                    return "Nivel 3"  # Report as Nivel 3 but internally it's Nivel 4
                
                # Check for Nivel 3 conditions
                nivel_3_thresholds = thresholds["nivel_3"]
                if (interpretar_percentage >= nivel_3_thresholds["interpretar"] and 
                    evaluar_percentage >= nivel_3_thresholds["evaluar"]):
                    return "Nivel 3"
                
                # Check for Nivel 2 conditions
                nivel_2_thresholds = thresholds["nivel_2"]
                if (interpretar_percentage >= nivel_2_thresholds["interpretar"] and 
                    evaluar_percentage < nivel_2_thresholds["evaluar"]):
                    return "Nivel 2"
                
                return "Nivel 1"
                
            elif assessment_type == "materia_based":
                # CIEN: Materia-based level determination
                # Use the same lecture analysis logic as other assessments
                # A lecture is passed only if ALL questions are correct
                failed_lectures_threshold = assessment_config["failed_lectures_threshold"]
                
                # Count total failed lectures using the results data
                total_failed_lectures = 0
                for materia, data in results.items():
                    # Check if all questions in this materia were correct
                    if data["correct"] < data["total"]:
                        # If not all questions were correct, count all lectures in this materia as failed
                        # This is a simplified approach - in practice, we'd need the lecture breakdown
                        # For now, we'll use the materia-level data and assume failed lectures
                        total_failed_lectures += 1
                
                # Level determination: <= threshold failed lectures = Nivel 2, > threshold = Nivel 1
                if total_failed_lectures <= failed_lectures_threshold:
                    return "Nivel 2"
                else:
                    return "Nivel 1"
                    
            elif assessment_type == "percentage_based":
                # HYST: Percentage-based level determination
                overall_percentage = results[0]["percentage"]
                
                # Use threshold from assessment_config for level determination
                level_thresholds = assessment_config.get("level_thresholds", {})
                nivel_2_threshold = level_thresholds.get("Avanzado", {}).get("overall_percentage", 80)
                if overall_percentage >= nivel_2_threshold:
                    return "Avanzado"
                else:
                    return "General"
                    
            else:
                raise ValueError(f"Unknown assessment type: {assessment_type}")
                
        except Exception as e:
            logger.error(f"Error in level determination: {str(e)}")
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
                try:
                    # Ensure question_number is a valid integer
                    question_num = question_row["question_number"]
                    if pd.isna(question_num):
                        continue  # Skip questions with NaN question numbers
                    
                    question_num = int(question_num)
                    correct_alternative = question_row["correct_alternative"]
                
                    # Find user's answer for this question
                    answers = self._extract_answers_from_response(user_response, len(question_bank))
                    if question_num <= len(answers):
                        user_answer = answers[question_num - 1].get(self.config["answer_column_name"], "")
                        if user_answer == correct_alternative:
                            correct_answers += 1
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error processing question {question_row.get('question_number', 'unknown')}: {e}")
                    continue
            
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

    def _get_internal_level(self, reported_level: str, assessment_name: str, result: Dict[str, Any]) -> str:
        """
        Get the internal level (including Nivel 4) based on assessment type and results
        
        Args:
            reported_level: The level reported to the user
            assessment_name: Name of the assessment
            result: Complete analysis result
            
        Returns:
            Internal level string (including "Nivel 4" when applicable)
        """
        try:
            assessment_config = self.config["assessment_types"][assessment_name]
            
            if assessment_name in ["M1"]:
                # For M1: Check if it's actually Nivel 4 internally
                difficulty_results = result["difficulty_results"]
                diff1_percentage = difficulty_results[1]["percentage"]
                diff2_percentage = difficulty_results[2]["percentage"]
                
                # Use config thresholds for Nivel 4 check
                nivel_4_thresholds = assessment_config["level_thresholds"]["nivel_4"]
                if (reported_level == "Nivel 3" and 
                    diff1_percentage >= nivel_4_thresholds["diff1"] and 
                    diff2_percentage >= nivel_4_thresholds["diff2"]):
                    return "Nivel 4"
                else:
                    return reported_level
                    
            elif assessment_name == "CL":
                # For CL: Check if it's actually Nivel 4 internally
                skill_results = result["skill_results"]
                interpretar_percentage = skill_results["Interpretar"]["percentage"]
                evaluar_percentage = skill_results["Evaluar"]["percentage"]
                
                # Use config thresholds for Nivel 4 check
                nivel_4_thresholds = assessment_config["level_thresholds"]["nivel_4"]
                if (reported_level == "Nivel 3" and 
                    interpretar_percentage >= nivel_4_thresholds["interpretar"] and 
                    evaluar_percentage >= nivel_4_thresholds["evaluar"]):
                    return "Nivel 4"
                else:
                    return reported_level
                    
            elif assessment_name in ["CIEN", "HYST"]:
                # For CIEN and HYST: No internal level 4, so return reported level
                return reported_level
                
            else:
                return reported_level
                
        except Exception as e:
            logger.error(f"Error determining internal level: {e}")
            return reported_level

    def analyze_assessment_from_csv(self, assessment_name: str, question_bank_path: str, processed_csv_path: str, output_path: str, return_df: bool = False) -> str | pd.DataFrame:
        """
        Step 3: Analyze assessment data from CSV files and generate analysis results
        
        Args:
            assessment_name: Name of the assessment (e.g., "M1")
            question_bank_path: Path to question bank CSV
            processed_csv_path: Path to processed responses CSV or DataFrame
            output_path: Path to save analysis results CSV
            return_df: If True, return DataFrame instead of file path
            
        Returns:
            Path to the generated analysis CSV or DataFrame if return_df=True
        """
        try:
            import pandas as pd
            import json
            from typing import Dict, Any, List
            
            # Get CSV settings from config
            csv_sep = self.config["csv_settings"]["separator"]
            lecture_sep = self.config["csv_settings"]["lecture_separator"]
            
            # Load question bank with configured separator using StorageClient
            from storage import StorageClient
            storage = StorageClient()
            question_bank = storage.read_csv(question_bank_path, sep=csv_sep)
            logger.info(f"Loaded question bank from {question_bank_path}")
            
            # Get total number of questions dynamically
            total_questions = len(question_bank)
            logger.info(f"Total questions in bank: {total_questions}")
            
            # Load processed responses with configured separator
            if isinstance(processed_csv_path, pd.DataFrame):
                responses_df = processed_csv_path
                logger.info(f"Using provided DataFrame with {len(responses_df)} responses")
            else:
                responses_df = storage.read_csv(processed_csv_path, sep=csv_sep)
                logger.info(f"Loaded {len(responses_df)} responses from {processed_csv_path}")
            
            # Initialize results list
            analysis_results = []
            
            # Process each student response
            for idx, row in responses_df.iterrows():
                try:
                    user_id = row.get('user_id', '')
                    email = row.get('email', '')
                    
                    # Extract answers from individual columns using config
                    answers = self._extract_answers_from_response(row, total_questions)
                    
                    # Create user response format
                    user_response = {
                        "user_id": user_id,
                        "answers": answers
                    }
                    
                    # Analyze based on assessment type using generic function
                    result = self.analyze_assessment(user_response, question_bank, assessment_name)
                    
                    # Extract lecture analysis for assessments that need it
                    passed_lectures = []
                    failed_lectures = []
                    
                    if assessment_name in ["M1", "HYST", "CIEN"]:
                        lectures = question_bank["lecture"].unique().tolist()
                        lecture_results = self._analyze_by_lecture(user_response, question_bank, lectures)
                        
                        for lecture, data in lecture_results.items():
                            if data["status"] == "Aprobado":
                                passed_lectures.append(lecture)
                            else:
                                failed_lectures.append(lecture)
                    
                    # Create analysis result row
                    analysis_row = {
                        "user_id": user_id,
                        "email": email,
                        "assessment_name": assessment_name,
                        "level": result["level"],
                        "internal_level": self._get_internal_level(result["level"], assessment_name, result),
                        "overall_percentage": self._format_percentage_for_excel(result['overall_percentage']),
                        "total_questions": result["total_questions"],
                        "correct_questions": result["correct_questions"],
                        "passed_lectures": lecture_sep.join([str(lecture) for lecture in passed_lectures]),
                        "failed_lectures": lecture_sep.join([str(lecture) for lecture in failed_lectures]),
                    }
                    
                    # Add assessment-specific columns based on configuration
                    assessment_config = self.config["assessment_types"][assessment_name]
                    
                    if assessment_config["type"] == "difficulty_based":
                        difficulty_results = result["difficulty_results"]
                        for diff, data in difficulty_results.items():
                            analysis_row[f"difficulty_{diff}_percentage"] = self._format_percentage_for_excel(data["percentage"])
                            analysis_row[f"difficulty_{diff}_correct"] = data["correct_answers"]
                            analysis_row[f"difficulty_{diff}_total"] = data["total_questions"]
                    
                    elif assessment_config["type"] == "skill_based":
                        skill_results = result["skill_results"]
                        for skill, data in skill_results.items():
                            analysis_row[f"skill_{skill.lower()}_percentage"] = self._format_percentage_for_excel(data["percentage"])
                            analysis_row[f"skill_{skill.lower()}_correct"] = data["correct_answers"]
                            analysis_row[f"skill_{skill.lower()}_total"] = data["total_questions"]
                    
                    elif assessment_config["type"] == "materia_based":
                        materia_results = result["materia_results"]
                        materias = result["materias"]
                        materia_lecture_results = result.get("materia_lecture_results", {})
                        
                        # Calculate global lecture counts and percentage
                        total_passed_lectures_count = 0
                        total_failed_lectures_count = 0
                        total_lectures = 0
                        
                        for materia in materias:
                            data = materia_results[materia]
                            safe_materia_name = str(materia).lower().replace(' ', '_')
                            analysis_row[f"materia_{safe_materia_name}_total"] = data["total"]
                            analysis_row[f"materia_{safe_materia_name}_correct"] = data["correct"]
                            analysis_row[f"materia_{safe_materia_name}_percentage"] = self._format_percentage_for_excel(data["percentage"])
                            
                            # Add passed and failed lectures for this materia
                            if materia in materia_lecture_results:
                                materia_lecture_data = materia_lecture_results[materia]
                                analysis_row[f"materia_{safe_materia_name}_passed_lectures"] = lecture_sep.join(materia_lecture_data["passed_lectures"])
                                analysis_row[f"materia_{safe_materia_name}_failed_lectures"] = lecture_sep.join(materia_lecture_data["failed_lectures"])
                                analysis_row[f"materia_{safe_materia_name}_passed_lectures_count"] = materia_lecture_data["passed_lectures_count"]
                                analysis_row[f"materia_{safe_materia_name}_failed_lectures_count"] = materia_lecture_data["failed_lectures_count"]
                                
                                # Accumulate global counts
                                total_passed_lectures_count += materia_lecture_data["passed_lectures_count"]
                                total_failed_lectures_count += materia_lecture_data["failed_lectures_count"]
                                total_lectures += (materia_lecture_data["passed_lectures_count"] + materia_lecture_data["failed_lectures_count"])
                            else:
                                analysis_row[f"materia_{safe_materia_name}_passed_lectures"] = ""
                                analysis_row[f"materia_{safe_materia_name}_failed_lectures"] = ""
                                analysis_row[f"materia_{safe_materia_name}_passed_lectures_count"] = 0
                                analysis_row[f"materia_{safe_materia_name}_failed_lectures_count"] = 0
                        
                        # Add global lecture columns
                        analysis_row["total_passed_lectures_count"] = total_passed_lectures_count
                        analysis_row["total_failed_lectures_count"] = total_failed_lectures_count
                        analysis_row["overall_lectures_percentage"] = self._format_percentage_for_excel((total_passed_lectures_count / total_lectures * 100) if total_lectures > 0 else 0)
                    
                    analysis_results.append(analysis_row)
                    
                except Exception as e:
                    logger.error(f"Error processing user {user_id}: {e}")
                    continue
            
            # Create DataFrame and save with configured separator and proper encoding
            analysis_df = pd.DataFrame(analysis_results)
            
            if return_df:
                logger.info(f"Analysis completed. Results returned as DataFrame")
                logger.info(f"Processed {len(analysis_results)} students")
                return analysis_df
            else:
                storage.write_csv(output_path, analysis_df, index=False, sep=csv_sep)
                
                logger.info(f"Analysis completed. Results saved to {output_path}")
                logger.info(f"Processed {len(analysis_results)} students")
                
                return output_path
            
        except Exception as e:
            logger.error(f"Error in analyze_assessment_from_csv: {e}")
            raise 