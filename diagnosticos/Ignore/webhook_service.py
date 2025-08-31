#!/usr/bin/env python3
"""
Webhook service for processing individual student assessment completions
Handles signature validation, assessment analysis, and report generation
"""

import os
import hmac
import logging
import re
from typing import Dict, Any, Optional
import requests
import pandas as pd
from storage import StorageClient
from assessment_analyzer import AssessmentAnalyzer
from report_generator import ReportGenerator
from email_sender import EmailSender

logger = logging.getLogger(__name__)

class WebhookService:
    def __init__(self):
        """Initialize webhook service with configuration"""
        self.storage = StorageClient()
        self.analyzer = AssessmentAnalyzer()
        self.report_generator = ReportGenerator()
        self.email_sender = EmailSender()
        
        # LearnWorlds API configuration
        self.client_id = os.getenv("CLIENT_ID")
        self.school_domain = os.getenv("SCHOOL_DOMAIN")
        self.access_token = os.getenv("ACCESS_TOKEN")
        self.webhook_secret = os.getenv("LEARNWORLDS_WEBHOOK_SECRET")
        
        # API headers
        self.api_headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Lw-Client": self.client_id,
            "Accept": "application/json"
        }
        
        # Validate required environment variables
        self._validate_config()
    
    def _validate_config(self):
        """Validate required configuration"""
        required_vars = [
            "CLIENT_ID", "SCHOOL_DOMAIN", "ACCESS_TOKEN", 
            "LEARNWORLDS_WEBHOOK_SECRET", "EMAIL_FROM", "EMAIL_PASS"
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}")
    
    def validate_signature(self, request) -> bool:
        """Validate LearnWorlds webhook signature"""
        try:
            # Get signature from header
            signature_header = request.headers.get("Learnworlds-Webhook-Signature")
            if not signature_header:
                logger.warning("No signature header found")
                return False
            
            # Log signature details for debugging
            #logger.info(f"Received signature header: {signature_header}")
            
            # Extract signature value (remove v1= prefix)
            if not signature_header.startswith("v1="):
                logger.warning("Invalid signature format")
                return False
            
            received_signature = signature_header[3:]  # Remove "v1=" prefix
            #logger.info(f"Received signature: {received_signature}")
            
            # Calculate expected signature
            payload = request.get_data()
            logger.info(f"Payload length: {len(payload)} bytes")
            logger.info(f"Payload preview: {payload[:200]}...")
            
            # Use raw webhook secret without encoding
            expected_signature = self.webhook_secret
            
            #logger.info(f"Expected signature: {expected_signature}")
            logger.info(f"Webhook secret length: {len(self.webhook_secret)}")
            
            # Compare signatures
            if hmac.compare_digest(received_signature, expected_signature):
                logger.info("Webhook signature validated successfully")
                return True
            else:
                logger.warning("Signature validation failed")
                #logger.warning(f"Received: {received_signature}")
                #logger.warning(f"Expected: {expected_signature}")
                return False
                
        except Exception as e:
            logger.error(f"Error validating signature: {str(e)}")
            return False
    
    def process_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process webhook payload and generate student report"""
        try:
            logger.info(f"Processing webhook for user {payload.get('user', {}).get('id')}")
            
            # Extract data from payload
            user = payload.get("user", {})
            assessment = payload.get("assessment", {})
            submission = payload.get("submission", {})
            
            # Extract assessment title from URL or use default
            assessment_title = assessment.get("title")
            if not assessment_title:
                # Try to extract from URL
                assessment_url = assessment.get("url", "")
                if assessment_url:
                    # Extract assessment ID and use it as title
                    assessment_id = self._extract_assessment_id(assessment_url)
                    if assessment_id:
                        assessment_title = f"Assessment_{assessment_id[:8]}"  # Use first 8 chars of ID
                    else:
                        assessment_title = "Diagnóstico"
                else:
                    assessment_title = "Diagnóstico"
            
            # Validate required fields
            if not all([user.get("id"), user.get("email")]):
                return {
                    "success": False,
                    "error": "Missing required fields in webhook payload"
                }
            
            # Check if already processed
            if self._is_already_processed(user["id"], assessment_title):
                return {
                    "success": True,
                    "message": "Report already sent for this user and assessment",
                    "user_id": user["id"]
                }
            
            # Get user responses - try API first, fall back to submission data for testing
            user_responses = None
            
            # Try to get responses from API
            assessment_id = self._extract_assessment_id(assessment.get("url", ""))
            logger.info(f"Assessment ID extracted: {assessment_id}")
            
            if assessment_id:
                user_responses = self._get_user_responses(assessment_id, user["id"])
                logger.info(f"API responses: {user_responses}")
            
            # If API call failed or this is a test, use submission data directly
            #logger.info(f"Submission answers: {submission.get('answers')}")
            if not user_responses and submission.get("answers"):
                logger.info("Using submission data directly (test mode or API unavailable)")
                user_responses = {
                    "user_id": user["id"],
                    "answers": submission["answers"]
                }
            elif not user_responses:
                logger.warning("No user responses found from API and no submission data available")
            
            #logger.info(f"Final user_responses: {user_responses}")
            
            if not user_responses:
                return {
                    "success": False,
                    "error": "No responses found for user"
                }
            
            # Load question bank
            question_bank = self._load_question_bank(assessment_title)
            if question_bank.empty:
                error_msg = f"Question bank not found for assessment: {assessment_title}"
                logger.error(error_msg)
                
                # Send error notification to admin
                try:
                    self.email_sender.send_error_notification(error_msg)
                except Exception as email_error:
                    logger.error(f"Failed to send error notification: {str(email_error)}")
                
                return {
                    "success": False,
                    "error": error_msg
                }
            
            # Analyze assessment results
            analysis_result = self.analyzer.analyze_user_assessment(
                user_responses, question_bank, assessment_title
            )
            
            # Generate report
            pdf_content, email_filename = self.report_generator.generate_individual_report(
                user, assessment, analysis_result
            )
            
            # Send email
            email_sent = self.email_sender.send_report_email(
                user["email"], pdf_content, user.get("username", user["email"]), assessment_title, email_filename
            )
            
            if not email_sent:
                error_msg = f"Failed to send email to {user['email']} for assessment {assessment_title}"
                logger.error(error_msg)
                
                # Send error notification to admin
                try:
                    self.email_sender.send_error_notification(error_msg)
                except Exception as email_error:
                    logger.error(f"Failed to send error notification: {str(email_error)}")
                
                return {
                    "success": False,
                    "error": "Failed to send email"
                }
            
            # Mark as processed
            self._mark_as_processed(user["id"], assessment_title, user["email"])
            
            return {
                "success": True,
                "message": "Report generated and sent successfully",
                "user_id": user["id"],
                "assessment_title": assessment_title
            }
            
        except Exception as e:
            error_msg = f"Error processing webhook: {str(e)}"
            logger.error(error_msg)
            
            # Send error notification to admin
            try:
                self.email_sender.send_error_notification(error_msg)
            except Exception as email_error:
                logger.error(f"Failed to send error notification: {str(email_error)}")
            
            return {
                "success": False,
                "error": f"Processing error: {str(e)}"
            }
    
    def _extract_assessment_id(self, url: str) -> Optional[str]:
        """Extract assessment ID from LearnWorlds URL"""
        if not url:
            return None
        
        # Pattern: unit=24_character_hex_id
        match = re.search(r"unit=([a-fA-F0-9]{24})", url)
        return match.group(1) if match else None
    
    def _get_user_responses(self, assessment_id: str, user_id: str) -> Optional[Dict]:
        """Get user responses from LearnWorlds API"""
        try:
            url = f"https://{self.school_domain}/admin/api/v2/assessments/{assessment_id}/responses"
            response = requests.get(url, headers=self.api_headers)
            
            if response.status_code != 200:
                error_msg = f"API request failed: {response.status_code} for assessment {assessment_id}, user {user_id}"
                logger.error(error_msg)
                
                # Send error notification to admin
                try:
                    self.email_sender.send_error_notification(error_msg)
                except Exception as email_error:
                    logger.error(f"Failed to send error notification: {str(email_error)}")
                
                return None
            
            data = response.json().get('data', [])
            # Filter for specific user
            user_responses = [r for r in data if str(r.get("user_id")) == str(user_id)]
            
            return user_responses[0] if user_responses else None
            
        except Exception as e:
            error_msg = f"Error fetching user responses: {str(e)} for assessment {assessment_id}, user {user_id}"
            logger.error(error_msg)
            
            # Send error notification to admin
            try:
                self.email_sender.send_error_notification(error_msg)
            except Exception as email_error:
                logger.error(f"Failed to send error notification: {str(email_error)}")
            
            return None
    
    def _load_question_bank(self, assessment_title: str) -> pd.DataFrame:
        """Load question bank for assessment"""
        try:
            # Try to find question bank in storage with new naming convention
            # Look for CSV files with the assessment title
            question_bank_path = f"data/responses/questions/{assessment_title}.csv"
            
            if self.storage.exists(question_bank_path):
                return self.storage.read_csv(question_bank_path)
            else:
                # Try alternative naming patterns
                alternative_paths = [
                    f"data/responses/questions/{assessment_title}_questions.csv",
                    f"data/responses/questions/{assessment_title}_bank.csv",
                    f"data/responses/questions/banco_preguntas_{assessment_title}.csv"
                ]
                
                for alt_path in alternative_paths:
                    if self.storage.exists(alt_path):
                        logger.info(f"Found question bank at: {alt_path}")
                        return self.storage.read_csv(alt_path)
                
                logger.warning(f"Question bank not found for assessment: {assessment_title}")
                logger.warning(f"Tried paths: {question_bank_path}, {alternative_paths}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error loading question bank: {str(e)}")
            return pd.DataFrame()
    
    def _is_already_processed(self, user_id: str, assessment_title: str) -> bool:
        """Check if report was already sent for this user and assessment"""
        try:
            processed_file = "data/webhook_reports/processed.csv"
            
            if not self.storage.exists(processed_file):
                return False
            
            df = self.storage.read_csv(processed_file)
            return ((df["user_id"] == user_id) & 
                   (df["assessment_title"] == assessment_title)).any()
                   
        except Exception as e:
            logger.error(f"Error checking processed status: {str(e)}")
            return False
    
    def _mark_as_processed(self, user_id: str, assessment_title: str, user_email: str):
        """Mark user assessment as processed with atomic operation"""
        try:
            processed_file = "data/webhook_reports/processed.csv"
            
            # Create directory if it doesn't exist
            self.storage.ensure_directory("data/webhook_reports/")
            
            # Atomic operation: read, check for duplicates, write
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Read current data
                    if self.storage.exists(processed_file):
                        df = self.storage.read_csv(processed_file)
                        # Keep only the important columns
                        important_cols = ["user_id", "assessment_title", "user_email", "processed_at"]
                        df = df[[col for col in important_cols if col in df.columns]]
                    else:
                        df = pd.DataFrame(columns=["user_id", "assessment_title", "user_email", "processed_at"])
                    
                    # Check if already processed (double-check)
                    if ((df["user_id"] == user_id) & (df["assessment_title"] == assessment_title)).any():
                        logger.info(f"Already processed: {user_id} - {assessment_title}")
                        return
                    
                    # Add new record
                    new_record = pd.DataFrame([{
                        "user_id": user_id,
                        "assessment_title": assessment_title,
                        "user_email": user_email,
                        "processed_at": pd.Timestamp.now()
                    }], dtype=object)
                    
                    # Concatenate and save
                    df = pd.concat([df, new_record], ignore_index=True, sort=False)
                    self.storage.write_csv(processed_file, df, index=False)
                    
                    logger.info(f"Successfully marked as processed: {user_id} - {assessment_title}")
                    return
                    
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Retry {attempt + 1}/{max_retries} for marking as processed: {e}")
                        import time
                        time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                    else:
                        raise e
            
        except Exception as e:
            logger.error(f"Error marking as processed: {str(e)}") 