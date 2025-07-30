#!/usr/bin/env python3
"""
Assessment Analysis Project - Main Script
Downloads assessment responses, analyzes them, and generates PDF reports
"""

import os
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any
from dotenv import load_dotenv

from assessment_downloader import AssessmentDownloader
from assessment_analyzer import AssessmentAnalyzer
from report_generator import ReportGenerator
from email_sender import EmailSender
from storage import StorageClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AssessmentAnalysisProject:
    def __init__(self):
        """Initialize the assessment analysis project"""
        self.downloader = AssessmentDownloader()
        self.analyzer = AssessmentAnalyzer()
        self.report_generator = ReportGenerator()
        self.email_sender = EmailSender()
        self.storage = StorageClient()
        
        # Assessment configurations
        self.assessments = {
            "M1": {"type": "lecture_based", "has_materia": False},
            "CL": {"type": "percentage_based", "has_materia": False},
            "CIEN": {"type": "lecture_based", "has_materia": True},
            "HYST": {"type": "lecture_based", "has_materia": False}
        }
    
    def load_assessment_list(self, file_path: str) -> List[Dict[str, str]]:
        """Load assessment list from text file"""
        try:
            assessments = []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and ',' in line:
                        name, assessment_id = line.split(',', 1)
                        assessments.append({
                            'name': name.strip(),
                            'assessment_id': assessment_id.strip()
                        })
            logger.info(f"Loaded {len(assessments)} assessments from {file_path}")
            return assessments
        except Exception as e:
            logger.error(f"Error loading assessment list: {e}")
            raise
    
    def download_all_responses(self, assessments: List[Dict[str, str]]) -> Dict[str, List[Dict]]:
        """Download responses for all assessments"""
        all_responses = {}
        
        for assessment in assessments:
            name = assessment['name']
            assessment_id = assessment['assessment_id']
            
            logger.info(f"Downloading responses for {name} (ID: {assessment_id})")
            
            try:
                responses = self.downloader.download_assessment_responses(assessment_id)
                all_responses[name] = responses
                logger.info(f"Downloaded {len(responses)} responses for {name}")
            except Exception as e:
                logger.error(f"Error downloading responses for {name}: {e}")
                all_responses[name] = []
        
        return all_responses
    
    def load_question_banks(self) -> Dict[str, Any]:
        """Load question banks for all assessments"""
        question_banks = {}
        
        for assessment_name in self.assessments.keys():
            try:
                csv_path = f"data/questions/{assessment_name}.csv"
                if self.storage.exists(csv_path):
                    df = self.storage.read_csv(csv_path)
                    question_banks[assessment_name] = df
                    logger.info(f"Loaded question bank for {assessment_name}: {len(df)} questions")
                else:
                    logger.warning(f"Question bank not found for {assessment_name}: {csv_path}")
                    question_banks[assessment_name] = None
            except Exception as e:
                logger.error(f"Error loading question bank for {assessment_name}: {e}")
                question_banks[assessment_name] = None
        
        return question_banks
    
    def analyze_user_responses(self, user_id: str, user_email: str, username: str, 
                             all_responses: Dict[str, List[Dict]], 
                             question_banks: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze responses for a specific user across all assessments"""
        user_results = {}
        
        for assessment_name, responses in all_responses.items():
            logger.info(f"Analyzing {assessment_name} for user {user_id}")
            
            # Find user's response for this assessment
            user_response = None
            for response in responses:
                if str(response.get('user_id')) == str(user_id):
                    user_response = response
                    break
            
            if not user_response:
                logger.warning(f"No response found for user {user_id} in {assessment_name}")
                continue
            
            question_bank = question_banks.get(assessment_name)
            if question_bank is None:
                logger.warning(f"No question bank available for {assessment_name}")
                continue
            
            try:
                # Analyze based on assessment type
                assessment_config = self.assessments[assessment_name]
                
                if assessment_config["type"] == "lecture_based":
                    if assessment_config["has_materia"]:
                        # CIEN assessment with Materia column
                        result = self.analyzer.analyze_lecture_based_with_materia(
                            user_response, question_bank, assessment_name
                        )
                    else:
                        # Standard lecture-based assessment
                        result = self.analyzer.analyze_lecture_based(
                            user_response, question_bank, assessment_name
                        )
                elif assessment_config["type"] == "percentage_based":
                    # CL assessment - percentage based
                    result = self.analyzer.analyze_percentage_based(
                        user_response, question_bank, assessment_name
                    )
                
                user_results[assessment_name] = result
                logger.info(f"Analysis completed for {assessment_name}")
                
            except Exception as e:
                logger.error(f"Error analyzing {assessment_name} for user {user_id}: {e}")
                continue
        
        return user_results
    
    def generate_comprehensive_report(self, user_id: str, user_email: str, username: str,
                                   user_results: Dict[str, Any]) -> bytes:
        """Generate comprehensive PDF report with all assessment results"""
        try:
            pdf_content = self.report_generator.generate_comprehensive_report(
                user_id, user_email, username, user_results
            )
            logger.info(f"Generated comprehensive report for user {user_id}")
            return pdf_content
        except Exception as e:
            logger.error(f"Error generating comprehensive report: {e}")
            raise
    
    def save_report_to_drive(self, pdf_content: bytes, user_id: str, username: str) -> str:
        """Save report to Google Drive in 'planes de estudios' folder"""
        try:
            filename = f"plan_estudio_{username}_{user_id}.pdf"
            drive_link = self.report_generator.save_to_drive(
                pdf_content, filename, "planes de estudios"
            )
            logger.info(f"Report saved to Drive: {drive_link}")
            return drive_link
        except Exception as e:
            logger.error(f"Error saving report to Drive: {e}")
            raise
    
    def send_report_email(self, user_email: str, pdf_content: bytes, username: str, 
                         user_id: str, drive_link: str = None) -> bool:
        """Send report email to user"""
        try:
            filename = f"plan_estudio_{username}_{user_id}.pdf"
            success = self.email_sender.send_comprehensive_report_email(
                user_email, pdf_content, username, filename, drive_link
            )
            
            if success:
                logger.info(f"Report email sent successfully to {user_email}")
            else:
                logger.error(f"Failed to send report email to {user_email}")
            
            return success
        except Exception as e:
            logger.error(f"Error sending report email: {e}")
            return False
    
    def process_user(self, user_id: str, user_email: str, username: str,
                    all_responses: Dict[str, List[Dict]], 
                    question_banks: Dict[str, Any]) -> bool:
        """Process a single user's assessment data"""
        try:
            logger.info(f"Processing user: {user_id} ({username})")
            
            # Analyze user responses
            user_results = self.analyze_user_responses(
                user_id, user_email, username, all_responses, question_banks
            )
            
            if not user_results:
                logger.warning(f"No valid results for user {user_id}")
                return False
            
            # Generate comprehensive report
            pdf_content = self.generate_comprehensive_report(
                user_id, user_email, username, user_results
            )
            
            # Save to Drive
            drive_link = self.save_report_to_drive(pdf_content, user_id, username)
            
            # Send email
            email_sent = self.send_report_email(
                user_email, pdf_content, username, user_id, drive_link
            )
            
            return email_sent
            
        except Exception as e:
            logger.error(f"Error processing user {user_id}: {e}")
            return False
    
    def run(self, assessment_list_file: str, fixed_email: str = None):
        """Main execution method"""
        try:
            logger.info("Starting Assessment Analysis Project")
            
            # Load assessment list
            assessments = self.load_assessment_list(assessment_list_file)
            
            # Download all responses
            all_responses = self.download_all_responses(assessments)
            
            # Load question banks
            question_banks = self.load_question_banks()
            
            # Get unique users from all responses
            all_users = set()
            for responses in all_responses.values():
                for response in responses:
                    user_id = response.get('user_id')
                    if user_id:
                        all_users.add(str(user_id))
            
            logger.info(f"Found {len(all_users)} unique users")
            
            # Process each user
            processed_count = 0
            for user_id in all_users:
                # Get user info from first response
                user_info = self._get_user_info(user_id, all_responses)
                if not user_info:
                    continue
                
                # Use fixed email if provided, otherwise use user's email
                email_to_use = fixed_email if fixed_email else user_info['email']
                
                success = self.process_user(
                    user_id, email_to_use, user_info['username'],
                    all_responses, question_banks
                )
                
                if success:
                    processed_count += 1
            
            logger.info(f"Processing completed. {processed_count} users processed successfully.")
            
        except Exception as e:
            logger.error(f"Error in main execution: {e}")
            raise
    
    def _get_user_info(self, user_id: str, all_responses: Dict[str, List[Dict]]) -> Dict[str, str]:
        """Extract user information from responses"""
        for responses in all_responses.values():
            for response in responses:
                if str(response.get('user_id')) == str(user_id):
                    return {
                        'email': response.get('user', {}).get('email', 'unknown@email.com'),
                        'username': response.get('user', {}).get('username', f'user_{user_id}')
                    }
        return None

def main():
    parser = argparse.ArgumentParser(description='Assessment Analysis Project')
    parser.add_argument('assessment_list', help='Path to assessment list file')
    parser.add_argument('--fixed-email', help='Fixed email address to send all reports to')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate assessment list file
    if not os.path.exists(args.assessment_list):
        logger.error(f"Assessment list file not found: {args.assessment_list}")
        return
    
    # Run the project
    project = AssessmentAnalysisProject()
    project.run(args.assessment_list, args.fixed_email)

if __name__ == "__main__":
    main() 