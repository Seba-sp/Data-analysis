#!/usr/bin/env python3
"""
Assessment Analyzer - Analyzes assessment responses using percentage-based analysis
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
        # Default configuration template for any assessment
        default_assessment_config = {
            "type": "percentage_based",
            "columns": ["question_number", "correct_alternative", "lecture"],
            "level_thresholds": {
                "nivel_1": {"overall_percentage": 49},
                "nivel_2": {"overall_percentage": 49},
                "nivel_3": {"overall_percentage": 100}
            },
            "reported_levels": ["General", "Avanzado", "Excelente"],
            "internal_levels": ["General", "Avanzado", "Excelente"]
        }
        
        return {
            "assessment_types": {
                # Default template - will be used for any assessment not explicitly configured
                "_default": default_assessment_config
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
            assessment_name: Name of the assessment (uses default config if not explicitly configured)
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Get assessment config, use default if not found
            if assessment_name not in self.config["assessment_types"]:
                # Use default configuration for any assessment
                assessment_config = self.config["assessment_types"].get("_default", {})
                logger.info(f"Using default configuration for assessment: {assessment_name}")
            else:
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
            if assessment_type == "percentage_based":
                return self._analyze_percentage_based_generic(user_response, question_bank, assessment_name, assessment_config)
            else:
                raise ValueError(f"Unknown assessment type: {assessment_type}")
            
        except Exception as e:
            logger.error(f"Error analyzing {assessment_name} assessment: {str(e)}")
            raise
    
    def _analyze_percentage_based_generic(self, user_response: Dict[str, Any], question_bank: pd.DataFrame, assessment_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generic percentage-based analysis for all assessments"""
        try:
            # Required columns: question_number, correct_alternative, lecture
            required_cols = {'question_number', 'correct_alternative', 'lecture'}
            if not required_cols.issubset(set(question_bank.columns)):
                missing = required_cols - set(question_bank.columns)
                raise ValueError(f"Question bank missing required columns: {missing}")
            
            # Simple percentage-based analysis
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
        Level determination function for all assessment types (percentage-based)
        
        Args:
            results: Dictionary of results for the assessment
            assessment_name: Name of the assessment
            
        Returns:
            Level string based on assessment type and results
        """
        try:
            # Get assessment config, use default if not found
            if assessment_name not in self.config["assessment_types"]:
                assessment_config = self.config["assessment_types"].get("_default", {})
            else:
                assessment_config = self.config["assessment_types"][assessment_name]
            
            assessment_type = assessment_config.get("type", "percentage_based")
            
            if assessment_type == "percentage_based":
                # Percentage-based level determination for all assessments
                overall_percentage = results[0]["percentage"]
                
                # Use threshold from assessment_config for level determination
                level_thresholds = assessment_config.get("level_thresholds", {})
                
                # Check for Nivel 3 (Excelente) - 100%
                nivel_3_threshold = level_thresholds.get("nivel_3", {}).get("overall_percentage", 100)
                if overall_percentage >= nivel_3_threshold:
                    return "Excelente"
                
                # Check for Nivel 2 (Avanzado) - 49%
                nivel_2_threshold = level_thresholds.get("nivel_2", {}).get("overall_percentage", 49)
                if overall_percentage >= nivel_2_threshold:
                    return "Avanzado"
                
                # Default to Nivel 1 (General)
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
        Get the internal level for all assessment types
        
        Args:
            reported_level: The level reported to the user
            assessment_name: Name of the assessment
            result: Complete analysis result
            
        Returns:
            Internal level string (same as reported level for all assessments)
        """
        try:
            # For all assessments: No internal level distinction, so return reported level
            return reported_level
                
        except Exception as e:
            logger.error(f"Error determining internal level: {e}")
            return reported_level

    def analyze_assessment_from_csv(self, assessment_name: str, question_bank_path: str, processed_csv_path: str, output_path: str, return_df: bool = False) -> str | pd.DataFrame:
        """
        Step 3: Analyze assessment data from CSV files and generate analysis results
        
        Args:
            assessment_name: Name of the assessment (e.g., "HYST", "M1", etc.)
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
                    
                    # Extract lecture analysis for all assessments
                    passed_lectures = []
                    failed_lectures = []
                    
                    # Check if lecture column exists in question bank
                    if "lecture" in question_bank.columns:
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