#!/usr/bin/env python3
"""
Simplified Assessment Analyzer
Analyzes assessment results and generates a comprehensive analysis file
"""

import os
import logging
import pandas as pd
from typing import Dict, List, Any
from storage import StorageClient

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class AssessmentAnalyzer:
    def __init__(self):
        """Initialize the assessment analyzer"""
        self.storage = StorageClient()
        self.assessment_types = ["M1", "M2", "CL", "CIENB", "CIENF", "CIENQ", "CIENT", "HYST"]
        self.processed_dir = "data/processed"
        self.questions_dir = "data/questions"
        self.conversion_file = "data/questions/CONVERSION.xlsx"
        self.output_file = "data/analysis/analysis.csv"
        
    def get_unique_identifiers(self) -> List[Dict[str, str]]:
        """Get all unique user identifiers (email + username pairs) from all processed assessments"""
        user_identifiers = {}  # Use dict to store email -> username mapping
        
        for assessment_type in self.assessment_types:
            processed_file = os.path.join(self.processed_dir, f"{assessment_type}.csv")
            
            if self.storage.exists(processed_file):
                try:
                    # Read CSV with semicolon separator since that's what the files use
                    df = self.storage.read_csv(processed_file, sep=';')
                    logger.info(f"Loaded {len(df)} responses from {assessment_type}")
                    logger.info(f"Columns in {assessment_type}: {list(df.columns)}")
                    
                    if 'email' in df.columns:
                        # Use email as primary identifier, store associated username
                        for _, row in df.iterrows():
                            email = row.get('email')
                            username = row.get('username', '')
                            
                            if pd.notna(email) and email.strip():
                                # Use email as key, store username if available
                                if email not in user_identifiers:
                                    user_identifiers[email] = username if pd.notna(username) else email
                                else:
                                    # If username is available and current stored value is email, update it
                                    if pd.notna(username) and user_identifiers[email] == email:
                                        user_identifiers[email] = username
                        
                        logger.info(f"Found {len([e for e in df['email'].dropna().unique()])} unique emails in {assessment_type}")
                    elif 'username' in df.columns:
                        # Fallback to username if no email column
                        for _, row in df.iterrows():
                            username = row.get('username')
                            if pd.notna(username) and username.strip():
                                # Use username as both key and value when no email available
                                user_identifiers[username] = username
                        logger.info(f"Found {len(df['username'].dropna().unique())} unique usernames in {assessment_type}")
                    else:
                        logger.warning(f"No username or email column found in {assessment_type}")
                except Exception as e:
                    logger.error(f"Error reading {assessment_type}: {e}")
            else:
                logger.warning(f"Processed file not found: {processed_file}")
        
        # Convert to list of dictionaries with email and username
        unique_users = []
        for email, username in user_identifiers.items():
            unique_users.append({'email': email, 'username': username})
        
        # Sort by email for consistency
        unique_users.sort(key=lambda x: x['email'])
        logger.info(f"Found {len(unique_users)} total unique users")
        return unique_users
    
    def load_conversion_data(self) -> Dict[str, pd.DataFrame]:
        """Load conversion data from CONVERSION.xlsx"""
        conversion_data = {}
        
        try:
            # Load the Excel file
            if self.storage.exists(self.conversion_file):
                # For Excel files, we need to use pandas directly since storage doesn't handle Excel
                excel_path = self.storage._local_path(self.conversion_file) if self.storage.backend == 'local' else self.conversion_file
                
                # Load each sheet
                for assessment_type in self.assessment_types:
                    sheet_name = assessment_type
                    if assessment_type in ["CIENB", "CIENF", "CIENQ", "CIENT"]:
                        sheet_name = "CIEN"
                    
                    try:
                        df = pd.read_excel(excel_path, sheet_name=sheet_name)
                        conversion_data[assessment_type] = df
                        logger.info(f"Loaded conversion data for {assessment_type} from sheet {sheet_name}")
                    except Exception as e:
                        logger.warning(f"Could not load sheet {sheet_name} for {assessment_type}: {e}")
                        conversion_data[assessment_type] = pd.DataFrame(columns=["Correctas", "Puntaje PAES"])
            else:
                logger.warning(f"Conversion file not found: {self.conversion_file}")
                # Create empty DataFrames for each assessment type
                for assessment_type in self.assessment_types:
                    conversion_data[assessment_type] = pd.DataFrame(columns=["Correctas", "Puntaje PAES"])
        except Exception as e:
            logger.error(f"Error loading conversion data: {e}")
            # Create empty DataFrames for each assessment type
            for assessment_type in self.assessment_types:
                conversion_data[assessment_type] = pd.DataFrame(columns=["Correctas", "Puntaje PAES"])
        
        return conversion_data
    
    def calculate_assessment_score(self, assessment_type: str, user_answers: pd.Series, questions_df: pd.DataFrame) -> int:
        """Calculate raw score for a user in a specific assessment"""
        try:
            logger.info(f"Calculating score for {assessment_type}")
            logger.info(f"User answers columns: {list(user_answers.index)}")
            logger.info(f"Questions DataFrame columns: {list(questions_df.columns)}")
            logger.info(f"Questions DataFrame shape: {questions_df.shape}")
            
            # Filter questions that are not pilot (Piloto = 0 or empty)
            valid_questions = questions_df[
                (questions_df['Piloto'] == 0) | 
                (questions_df['Piloto'].isna()) | 
                (questions_df['Piloto'] == '')
            ].copy()
            
            logger.info(f"Valid questions (non-pilot) count: {len(valid_questions)}")
            
            if valid_questions.empty:
                logger.warning(f"No valid questions found for {assessment_type}")
                return 0
            
            score = 0
            correct_count = 0
            total_checked = 0
            
            for _, question_row in valid_questions.iterrows():
                # Get the actual question identifier from the Pregunta column
                question_identifier = question_row['Pregunta']  # e.g., "Pregunta 1", "Pregunta 2", etc.
                
                logger.debug(f"Checking question: {question_identifier}")
                logger.debug(f"Correct answer: {question_row['Alternativa correcta']}")
                
                if question_identifier in user_answers.index:
                    user_answer = user_answers[question_identifier]
                    correct_answer = question_row['Alternativa correcta']
                    total_checked += 1
                    
                    logger.debug(f"User answer: {user_answer}")
                    
                    if pd.notna(user_answer) and pd.notna(correct_answer):
                        # Clean and compare answers
                        user_clean = str(user_answer).strip().upper()
                        correct_clean = str(correct_answer).strip().upper()
                        
                        if user_clean == correct_clean:
                            score += 1
                            correct_count += 1
                        
                else:
                    logger.debug(f"Question {question_identifier} not found in user answers")
            
            logger.info(f"{assessment_type} scoring complete: {correct_count}/{total_checked} correct, final score: {score}")
            return score
            
        except Exception as e:
            logger.error(f"Error calculating score for {assessment_type}: {e}")
            return 0
    
    def convert_score(self, raw_score: int, conversion_df: pd.DataFrame) -> float:
        """Convert raw score to PAES score using conversion table"""
        try:
            if conversion_df.empty:
                return 0.0
            
            # Find the row where Correctas matches the raw score
            matching_row = conversion_df[conversion_df['Correctas'] == raw_score]
            
            if not matching_row.empty:
                converted_score = matching_row.iloc[0]['Puntaje PAES']
                return float(converted_score)
            else:
                # If exact match not found, find closest lower score
                lower_scores = conversion_df[conversion_df['Correctas'] <= raw_score]
                if not lower_scores.empty:
                    closest_score = lower_scores['Correctas'].max()
                    matching_row = conversion_df[conversion_df['Correctas'] == closest_score]
                    converted_score = matching_row.iloc[0]['Puntaje PAES']
                    return float(converted_score)
                else:
                    return 0.0
                    
        except Exception as e:
            logger.error(f"Error converting score {raw_score}: {e}")
            return 0.0
    
    def analyze_all_assessments(self) -> pd.DataFrame:
        """Analyze all assessments and generate comprehensive analysis"""
        logger.info("Starting comprehensive assessment analysis...")
        
        # Get unique user identifiers (email + username pairs)
        users = self.get_unique_identifiers()
        if not users:
            logger.error("No users found")
            return pd.DataFrame()
        
        # Load conversion data
        conversion_data = self.load_conversion_data()
        
        # Initialize results DataFrame
        results_data = []
        
        for user in users:
            email = user['email']
            username = user['username']
            user_row = {'username': username, 'email': email}
            
            # Process each assessment type
            for assessment_type in self.assessment_types:
                processed_file = os.path.join(self.processed_dir, f"{assessment_type}.csv")
                questions_file = os.path.join(self.questions_dir, f"{assessment_type}.csv")
                
                # Initialize assessment columns
                user_row[f"{assessment_type}"] = 0  # Participation
                user_row[f"{assessment_type}_score"] = 0  # Raw score
                user_row[f"{assessment_type}_converted"] = 0  # Converted score (will be converted to float)
                
                # Check if user participated in this assessment
                if self.storage.exists(processed_file) and self.storage.exists(questions_file):
                    try:
                        # Load processed responses with semicolon separator
                        responses_df = self.storage.read_csv(processed_file, sep=';')
                        
                        # Find user's responses - prioritize email matching, fallback to username
                        user_responses = pd.DataFrame()
                        if 'email' in responses_df.columns:
                            user_responses = responses_df[responses_df['email'] == email]
                        elif 'username' in responses_df.columns:
                            user_responses = responses_df[responses_df['username'] == username]
                        
                        if not user_responses.empty:
                            # User participated
                            user_row[f"{assessment_type}"] = 1
                            
                            # Load questions
                            questions_df = self.storage.read_csv(questions_file, sep=';')
                            
                            # Calculate score
                            raw_score = self.calculate_assessment_score(
                                assessment_type, 
                                user_responses.iloc[0], 
                                questions_df
                            )
                            user_row[f"{assessment_type}_score"] = raw_score
                            
                            # Convert score
                            converted_score = self.convert_score(
                                raw_score, 
                                conversion_data[assessment_type]
                            )
                            user_row[f"{assessment_type}_converted"] = converted_score
                            
                            logger.info(f"User {email} ({username}) - {assessment_type}: {raw_score} correct, {converted_score} converted")
                    
                    except Exception as e:
                        logger.error(f"Error processing {assessment_type} for user {email} ({username}): {e}")
            
            results_data.append(user_row)
        
        # Create final DataFrame
        results_df = pd.DataFrame(results_data)
        
        # Convert score columns to float with 0 decimal places
        for assessment_type in self.assessment_types:
            converted_col = f"{assessment_type}_converted"
            if converted_col in results_df.columns:
                results_df[converted_col] = results_df[converted_col].astype(float).round(0).astype(int)
        
        # Ensure output directory exists
        self.storage.ensure_directory("data/analysis")
        
        # Save results
        self.storage.write_csv(self.output_file, results_df, index=False)
        
        logger.info(f"Analysis complete. Results saved to {self.output_file}")
        logger.info(f"Processed {len(results_df)} users with {len(self.assessment_types)} assessment types")
        
        return results_df

def main():
    """Main function for testing"""
    analyzer = AssessmentAnalyzer()
    results = analyzer.analyze_all_assessments()
    
    if not results.empty:
        print(f"\nAnalysis complete!")
        print(f"Users processed: {len(results)}")
        print(f"Assessment types: {len(analyzer.assessment_types)}")
        print(f"Output file: {analyzer.output_file}")
        
        # Show sample results
        print("\nSample results:")
        print(results.head())
    else:
        print("Analysis failed - no results generated")

if __name__ == "__main__":
    main() 