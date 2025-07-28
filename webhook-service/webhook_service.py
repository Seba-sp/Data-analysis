#!/usr/bin/env python3
"""
Webhook service for processing individual student assessment completions
Handles signature validation, assessment analysis, and report generation
"""

import os
import hmac
import hashlib
import json
import logging
import re
from typing import Dict, Any, Optional
import requests
import pandas as pd
from pathlib import Path
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
            
            # Extract signature value (remove v1= prefix)
            if not signature_header.startswith("v1="):
                logger.warning("Invalid signature format")
                return False
            
            received_signature = signature_header[3:]  # Remove "v1=" prefix
            
            # Calculate expected signature
            payload = request.get_data()
            expected_signature = hmac.new(
                self.webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            if hmac.compare_digest(received_signature, expected_signature):
                logger.info("Webhook signature validated successfully")
                return True
            else:
                logger.warning("Signature validation failed")
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
            
            # Validate required fields
            if not all([user.get("id"), user.get("email"), assessment.get("title")]):
                return {
                    "success": False,
                    "error": "Missing required fields in webhook payload"
                }
            
            # Check if already processed
            if self._is_already_processed(user["id"], assessment.get("title")):
                return {
                    "success": True,
                    "message": "Report already sent for this user and assessment",
                    "user_id": user["id"]
                }
            
            # Get assessment responses from API
            assessment_id = self._extract_assessment_id(assessment.get("url", ""))
            if not assessment_id:
                return {
                    "success": False,
                    "error": "Could not extract assessment ID from URL"
                }
            
            user_responses = self._get_user_responses(assessment_id, user["id"])
            if not user_responses:
                return {
                    "success": False,
                    "error": "No responses found for user"
                }
            
            # Load question bank
            question_bank = self._load_question_bank(assessment["title"])
            if question_bank.empty:
                return {
                    "success": False,
                    "error": f"Question bank not found for assessment: {assessment['title']}"
                }
            
            # Analyze assessment results
            analysis_result = self.analyzer.analyze_user_assessment(
                user_responses, question_bank
            )
            
            # Generate report
            report_path = self.report_generator.generate_individual_report(
                user, assessment, analysis_result
            )
            
            # Send email
            email_sent = self.email_sender.send_report_email(
                user["email"], report_path, user.get("username", user["email"])
            )
            
            if not email_sent:
                return {
                    "success": False,
                    "error": "Failed to send email"
                }
            
            # Mark as processed
            self._mark_as_processed(user["id"], assessment.get("title"))
            
            return {
                "success": True,
                "message": "Report generated and sent successfully",
                "user_id": user["id"],
                "report_path": str(report_path)
            }
            
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
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
                logger.error(f"API request failed: {response.status_code}")
                return None
            
            data = response.json().get('data', [])
            # Filter for specific user
            user_responses = [r for r in data if str(r.get("user_id")) == str(user_id)]
            
            return user_responses[0] if user_responses else None
            
        except Exception as e:
            logger.error(f"Error fetching user responses: {str(e)}")
            return None
    
    def _load_question_bank(self, assessment_title: str) -> pd.DataFrame:
        """Load question bank for assessment"""
        try:
            # Try to find question bank in storage
            question_bank_path = f"data/responses/questions/{assessment_title}_questions.csv"
            
            if self.storage.exists(question_bank_path):
                return self.storage.read_csv(question_bank_path)
            else:
                logger.warning(f"Question bank not found: {question_bank_path}")
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
    
    def _mark_as_processed(self, user_id: str, assessment_title: str):
        """Mark user assessment as processed"""
        try:
            processed_file = "data/webhook_reports/processed.csv"
            
            # Create directory if it doesn't exist
            self.storage.ensure_directory("data/webhook_reports/")
            
            # Read existing data or create new
            if self.storage.exists(processed_file):
                df = self.storage.read_csv(processed_file)
            else:
                df = pd.DataFrame(columns=["user_id", "assessment_title", "processed_at"])
            
            # Add new record
            new_record = pd.DataFrame([{
                "user_id": user_id,
                "assessment_title": assessment_title,
                "processed_at": pd.Timestamp.now()
            }])
            
            df = pd.concat([df, new_record], ignore_index=True)
            
            # Save back to storage
            self.storage.write_csv(df, processed_file)
            
        except Exception as e:
            logger.error(f"Error marking as processed: {str(e)}") 