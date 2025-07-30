#!/usr/bin/env python3
"""
Assessment Downloader - Downloads assessment responses from LearnWorlds API
"""

import os
import logging
import requests
import time
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class AssessmentDownloader:
    def __init__(self):
        """Initialize the assessment downloader"""
        self.client_id = os.getenv("CLIENT_ID")
        self.school_domain = os.getenv("SCHOOL_DOMAIN")
        self.access_token = os.getenv("ACCESS_TOKEN")
        
        if not all([self.client_id, self.school_domain, self.access_token]):
            raise ValueError("Missing required environment variables: CLIENT_ID, SCHOOL_DOMAIN, ACCESS_TOKEN")
        
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Lw-Client": self.client_id,
            "Accept": "application/json"
        }
    
    def download_assessment_responses(self, assessment_id: str) -> List[Dict[str, Any]]:
        """
        Download all responses for a specific assessment
        
        Args:
            assessment_id: The assessment ID to download responses for
            
        Returns:
            List of response dictionaries
        """
        try:
            logger.info(f"Downloading responses for assessment {assessment_id}")
            
            all_responses = []
            page = 1
            total_pages = 1
            
            while page <= total_pages:
                url = f"https://{self.school_domain}/admin/api/v2/assessments/{assessment_id}/responses?page={page}"
                
                try:
                    response = requests.get(url, headers=self.headers, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        responses = data.get('data', [])
                        meta = data.get('meta', {})
                        
                        # Update total pages on first request
                        if page == 1:
                            total_pages = meta.get('totalPages', 1)
                            logger.info(f"Total pages to download: {total_pages}")
                        
                        all_responses.extend(responses)
                        logger.info(f"Downloaded page {page}/{total_pages} - {len(responses)} responses")
                        
                        # Add delay to avoid rate limiting
                        time.sleep(1)
                        
                    elif response.status_code == 401:
                        logger.error("Authentication failed. Check your access token.")
                        break
                    elif response.status_code == 403:
                        logger.error("Access denied. Check your permissions.")
                        break
                    elif response.status_code == 404:
                        logger.error(f"Assessment {assessment_id} not found.")
                        break
                    else:
                        logger.error(f"API request failed with status {response.status_code}")
                        break
                        
                except requests.exceptions.RequestException as e:
                    logger.error(f"Network error downloading page {page}: {e}")
                    break
                
                page += 1
            
            logger.info(f"Downloaded {len(all_responses)} total responses for assessment {assessment_id}")
            return all_responses
            
        except Exception as e:
            logger.error(f"Error downloading assessment responses: {e}")
            raise
    
    def get_assessment_info(self, assessment_id: str) -> Dict[str, Any]:
        """
        Get basic information about an assessment
        
        Args:
            assessment_id: The assessment ID
            
        Returns:
            Dictionary with assessment information
        """
        try:
            url = f"https://{self.school_domain}/admin/api/v2/assessments/{assessment_id}"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return response.json().get('data', {})
            else:
                logger.error(f"Failed to get assessment info: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting assessment info: {e}")
            return {}
    
    def validate_assessment_id(self, assessment_id: str) -> bool:
        """
        Validate if an assessment ID exists and is accessible
        
        Args:
            assessment_id: The assessment ID to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            assessment_info = self.get_assessment_info(assessment_id)
            return bool(assessment_info.get('id'))
        except Exception as e:
            logger.error(f"Error validating assessment ID {assessment_id}: {e}")
            return False
    
    def get_user_responses(self, assessment_id: str, user_id: str) -> List[Dict[str, Any]]:
        """
        Get responses for a specific user in an assessment
        
        Args:
            assessment_id: The assessment ID
            user_id: The user ID
            
        Returns:
            List of response dictionaries for the user
        """
        try:
            all_responses = self.download_assessment_responses(assessment_id)
            user_responses = [
                response for response in all_responses 
                if str(response.get('user_id')) == str(user_id)
            ]
            
            logger.info(f"Found {len(user_responses)} responses for user {user_id} in assessment {assessment_id}")
            return user_responses
            
        except Exception as e:
            logger.error(f"Error getting user responses: {e}")
            return []
    
    def test_connection(self) -> bool:
        """
        Test the API connection
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to get a simple endpoint to test connection
            url = f"https://{self.school_domain}/admin/api/v2/assessments"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                logger.info("API connection test successful")
                return True
            else:
                logger.error(f"API connection test failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"API connection test error: {e}")
            return False 