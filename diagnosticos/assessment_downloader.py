#!/usr/bin/env python3
"""
Assessment Downloader - Downloads assessment responses from LearnWorlds API with incremental data support
and CSV processing
"""

import os
import json
import logging
import requests
import time
import pandas as pd
import argparse
from typing import List, Dict, Any, Optional
from pathlib import Path 
from datetime import datetime
from dotenv import load_dotenv
from storage import StorageClient

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class AssessmentDownloader:
    def __init__(self, data_dir: str = "data"):
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
    
        self.storage = StorageClient()
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        
        # Create directories
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Date filter for downloads (optional)
        self.min_date = os.getenv("MIN_DOWNLOAD_DATE")
        if self.min_date:
            try:
                # Parse the date string (expected format: YYYY-MM-DD)
                self.min_timestamp = int(datetime.strptime(self.min_date, "%Y-%m-%d").timestamp())
                logger.info(f"Date filter enabled: only downloading data from {self.min_date} onwards")
            except ValueError as e:
                logger.warning(f"Invalid MIN_DOWNLOAD_DATE format: {self.min_date}. Expected format: YYYY-MM-DD. Ignoring date filter.")
                self.min_timestamp = None
        else:
            self.min_timestamp = None
    
    def get_json_file_path(self, assessment_name: str) -> Path:
        """Get the JSON file path for an assessment"""
        return self.raw_dir / f"{assessment_name}.json"
    
    def get_csv_file_path(self, assessment_name: str) -> Path:
        """Get the CSV file path for an assessment"""
        return self.processed_dir / f"{assessment_name}.csv"
    
    def get_users_csv_file_path(self, form_name: str) -> Path:
        """Get the CSV file path for the USERS form (saves to analysis directory)"""
        analysis_dir = self.data_dir / "analysis"
        analysis_dir.mkdir(parents=True, exist_ok=True)
        return analysis_dir / f"{form_name}.csv"
    
    def get_incremental_json_file_path(self, assessment_name: str) -> Path:
        """Get the incremental JSON file path for an assessment (only new data)"""
        return self.raw_dir / f"incremental_{assessment_name}.json"
    
    def get_temp_csv_file_path(self, assessment_name: str) -> Path:
        """Get the temporary CSV file path for an assessment"""
        return self.processed_dir / f"temp_{assessment_name}.csv"
    
    def get_temp_analysis_file_path(self, assessment_name: str) -> Path:
        """Get the temporary analysis file path for an assessment"""
        analysis_dir = self.data_dir / "analysis"
        return analysis_dir / f"temp_{assessment_name}.csv"
    
    def get_latest_timestamp_from_json(self, json_file_path: str) -> Optional[int]:
        """Get the latest 'submitted' timestamp from an existing JSON file"""
        if not self.storage.exists(json_file_path):
            return None
        
        try:
            data = self.storage.read_json(json_file_path)
            
            # Handle case where read_json returns None
            if data is None or not data:
                return None
            
            # Get the first record (newest) since data is sorted by submitted timestamp
            latest_record = data[0]
            return latest_record.get('submittedTimestamp')
        except (json.JSONDecodeError, IndexError, KeyError):
            return None
    
    def _download_responses_incremental(self, object_id: str, object_name: str, object_type: str) -> List[Dict[str, Any]]:
        """
        Download responses incrementally for forms or assessments based on the latest timestamp.

        Args:
            object_id: The form or assessment ID to download responses for
            object_name: The form or assessment name for file organization
            object_type: Either "forms" or "assessments"

        Returns:
            List of response dictionaries
        """
        try:
            json_file_path = self.get_json_file_path(object_name)

            logger.info(f"Checking for existing responses data for {object_name}...")
            latest_timestamp = self.get_latest_timestamp_from_json(str(json_file_path))

            # If date filter is enabled, use the later of existing timestamp or minimum date
            if self.min_timestamp:
                if latest_timestamp is None:
                    # No existing data, use minimum date as starting point
                    effective_timestamp = self.min_timestamp
                    logger.info(f"No existing data found. Using date filter: {self.min_date} ({datetime.fromtimestamp(self.min_timestamp)})")
                else:
                    # Use the later of existing timestamp or minimum date
                    effective_timestamp = max(latest_timestamp, self.min_timestamp)
                    if effective_timestamp > latest_timestamp:
                        logger.info(f"Date filter {self.min_date} is newer than existing data. Using date filter as starting point.")
                    else:
                        logger.info(f"Existing data is newer than date filter. Using existing data as starting point.")
            else:
                effective_timestamp = latest_timestamp

            if effective_timestamp is None:
                logger.info("No existing responses data found and no date filter. Performing full download...")
                if object_type == "forms":
                    return self._download_form_responses_full(object_id, object_name)
                else:
                    return self._download_assessment_responses_full(object_id, object_name)

            logger.info(f"Effective timestamp: {datetime.fromtimestamp(effective_timestamp)}")
            logger.info("Downloading new responses only...")

            # Load existing data
            existing_data = []
            if self.storage.exists(str(json_file_path)):
                existing_data = self.storage.read_json(str(json_file_path))
                # Handle case where read_json returns None
                if existing_data is None:
                    existing_data = []

            new_data = []
            page = 1
            reached_existing = False

            while not reached_existing:
                url = f"https://{self.school_domain}/admin/api/v2/{object_type}/{object_id}/responses?page={page}"

                try:
                    response = requests.get(url, headers=self.headers, timeout=30)

                    if response.status_code == 200:
                        data = response.json()
                        responses = data.get('data', [])
                        meta = data.get('meta', {})

                        if not responses:
                            break

                        # Check if we've reached existing data or minimum date
                        for record in responses:
                            record_timestamp = record.get('submittedTimestamp')
                            
                            # Skip records older than effective timestamp
                            if record_timestamp and record_timestamp <= effective_timestamp:
                                reached_existing = True
                                break
                            new_data.append(record)

                        logger.info(f"Downloaded page {page} - {len(responses)} responses")

                        # Add delay to avoid rate limiting
                        time.sleep(1)

                        total_pages = meta.get('totalPages', 1)
                        if page >= total_pages:
                            break

                    elif response.status_code == 401:
                        logger.error("Authentication failed. Check your access token.")
                        raise Exception("Authentication failed")
                    elif response.status_code == 403:
                        logger.error("Access denied. Check your permissions.")
                        raise Exception("Access denied")
                    elif response.status_code == 404:
                        logger.error(f"{object_type[:-1].capitalize()} {object_id} not found.")
                        raise Exception(f"{object_type[:-1].capitalize()} {object_id} not found")
                    else:
                        logger.error(f"API request failed with status {response.status_code}")
                        raise Exception(f"API request failed with status {response.status_code}")

                except requests.exceptions.RequestException as e:
                    logger.error(f"Network error downloading page {page}: {e}")
                    raise Exception(f"Network error: {e}")

                page += 1

            if new_data:
                logger.info(f"Found {len(new_data)} new response records")
                # Combine new data with existing data and sort by submitted timestamp (newest first)
                combined_data = new_data + existing_data
                combined_data.sort(key=lambda x: x.get('submittedTimestamp', 0), reverse=True)
                return combined_data
            else:
                logger.info("No new responses found")
                return existing_data
                
        except Exception as e:
            logger.error(f"Error downloading {object_name} ({object_type}): {e}")
            raise Exception(f"Failed to download {object_name}: {e}")

    def download_form_responses_incremental(self, form_id: str, form_name: str) -> List[Dict[str, Any]]:
        """
        Download form responses incrementally based on the latest timestamp
        """
        return self._download_responses_incremental(form_id, form_name, "forms")

    def download_assessment_responses_incremental(self, assessment_id: str, assessment_name: str, return_df: bool = False) -> List[Dict[str, Any]] | pd.DataFrame:
        """
        Download assessment responses incrementally based on the latest timestamp
        
        Args:
            assessment_id: The assessment ID to download responses for
            assessment_name: The assessment name for file organization
            return_df: If True, return DataFrame instead of list
            
        Returns:
            List of response dictionaries or DataFrame if return_df=True
        """
        responses = self._download_responses_incremental(assessment_id, assessment_name, "assessments")
        
        if return_df:
            df = pd.DataFrame(responses)
            logger.info(f"Downloaded {len(df)} responses to memory for {assessment_name}")
            return df
        else:
            return responses
    
    def get_only_new_responses(self, assessment_id: str, assessment_name: str, return_df: bool = False) -> List[Dict[str, Any]] | pd.DataFrame:
        """
        Get only the new responses (not the combined ones) for incremental processing
        
        Args:
            assessment_id: The assessment ID to download responses for
            assessment_name: The assessment name for file organization
            return_df: If True, return DataFrame instead of list
            
        Returns:
            List of response dictionaries or DataFrame if return_df=True
        """
        try:
            json_file_path = self.get_json_file_path(assessment_name)
            
            logger.info(f"Checking for existing responses data for {assessment_name}...")
            latest_timestamp = self.get_latest_timestamp_from_json(str(json_file_path))
            
            # If date filter is enabled, use the later of existing timestamp or minimum date
            if self.min_timestamp:
                if latest_timestamp is None:
                    # No existing data, use minimum date as starting point
                    effective_timestamp = self.min_timestamp
                    logger.info(f"No existing data found. Using date filter: {self.min_date} ({datetime.fromtimestamp(self.min_timestamp)})")
                else:
                    # Use the later of existing timestamp or minimum date
                    effective_timestamp = max(latest_timestamp, self.min_timestamp)
                    if effective_timestamp > latest_timestamp:
                        logger.info(f"Date filter {self.min_date} is newer than existing data. Using date filter as starting point.")
                    else:
                        logger.info(f"Existing data is newer than date filter. Using existing data as starting point.")
            else:
                effective_timestamp = latest_timestamp
            
            if effective_timestamp is None:
                logger.info("No existing responses data found and no date filter. Performing full download...")
                return self.download_assessment_responses_incremental(assessment_id, assessment_name, return_df)
            
            logger.info(f"Effective timestamp: {datetime.fromtimestamp(effective_timestamp)}")
            logger.info("Downloading new responses only...")
            
            new_data = []
            page = 1
            reached_existing = False
            
            while not reached_existing:
                url = f"https://{self.school_domain}/admin/api/v2/assessments/{assessment_id}/responses?page={page}"
                
                try:
                    response = requests.get(url, headers=self.headers, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        responses = data.get('data', [])
                        meta = data.get('meta', {})
                        
                        if not responses:
                            break
                        
                        # Check if we've reached existing data or minimum date
                        for record in responses:
                            record_timestamp = record.get('submittedTimestamp')
                            
                            # Skip records older than effective timestamp
                            if record_timestamp and record_timestamp <= effective_timestamp:
                                reached_existing = True
                                break
                            new_data.append(record)
                        
                        logger.info(f"Downloaded page {page} - {len(responses)} responses")
                        
                        # Add delay to avoid rate limiting
                        time.sleep(1)
                        
                        total_pages = meta.get('totalPages', 1)
                        if page >= total_pages:
                            break
                        
                    elif response.status_code == 401:
                        logger.error("Authentication failed. Check your access token.")
                        raise Exception("Authentication failed")
                    elif response.status_code == 403:
                        logger.error("Access denied. Check your permissions.")
                        raise Exception("Access denied")
                    elif response.status_code == 404:
                        logger.error(f"Assessment {assessment_id} not found.")
                        raise Exception(f"Assessment {assessment_id} not found")
                    else:
                        logger.error(f"API request failed with status {response.status_code}")
                        raise Exception(f"API request failed with status {response.status_code}")
                        
                except requests.exceptions.RequestException as e:
                    logger.error(f"Network error downloading page {page}: {e}")
                    raise Exception(f"Network error: {e}")
                    
                page += 1
            
            if new_data:
                logger.info(f"Found {len(new_data)} new response records")
                if return_df:
                    df = pd.DataFrame(new_data)
                    logger.info(f"Downloaded {len(df)} new responses to memory for {assessment_name}")
                    return df
                else:
                    return new_data
            else:
                logger.info("No new responses found")
                if return_df:
                    return pd.DataFrame()
                else:
                    return []
                    
        except Exception as e:
            logger.error(f"Error downloading new responses for {assessment_name}: {e}")
            raise Exception(f"Failed to download new responses for {assessment_name}: {e}")
    
    def _download_responses_full(self, object_id: str, object_name: str, object_type: str) -> List[Dict[str, Any]]:
        """
        Download all responses (full download) for assessments or forms.

        Args:
            object_id: The ID to download responses for (assessment_id or form_id)
            object_name: The name for file organization
            object_type: "assessments" or "forms"

        Returns:
            List of response dictionaries
        """
        if self.min_timestamp:
            logger.info(f"Downloading all responses for {object_type[:-1]} {object_id} from {self.min_date} onwards")
        else:
            logger.info(f"Downloading all responses for {object_type[:-1]} {object_id}")

        all_responses = []
        page = 1
        total_pages = 1
        reached_min_date = False

        while page <= total_pages and not reached_min_date:
            url = f"https://{self.school_domain}/admin/api/v2/{object_type}/{object_id}/responses?page={page}"

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

                    # Filter responses by date if date filter is enabled
                    if self.min_timestamp:
                        filtered_responses = []
                        for record in responses:
                            record_timestamp = record.get('submittedTimestamp')
                            if record_timestamp and record_timestamp >= self.min_timestamp:
                                filtered_responses.append(record)
                            else:
                                # We've reached data older than our minimum date, stop downloading
                                reached_min_date = True
                                logger.info(f"Reached data older than {self.min_date}, stopping download")
                                break
                        
                        all_responses.extend(filtered_responses)
                        logger.info(f"Downloaded page {page}/{total_pages} - {len(responses)} responses, {len(filtered_responses)} after date filtering")
                        
                        if reached_min_date:
                            break
                    else:
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
                    logger.error(f"{object_type[:-1].capitalize()} {object_id} not found.")
                    break
                else:
                    logger.error(f"API request failed with status {response.status_code}")
                    break

            except requests.exceptions.RequestException as e:
                logger.error(f"Network error downloading page {page}: {e}")
                break

            page += 1

        # Sort by submitted timestamp (newest first)
        all_responses.sort(key=lambda x: x.get('submittedTimestamp', 0), reverse=True)
        logger.info(f"Downloaded {len(all_responses)} total responses for {object_type[:-1]} {object_id}")
        return all_responses

    def _download_assessment_responses_full(self, assessment_id: str, assessment_name: str) -> List[Dict[str, Any]]:
        """
        Download all assessment responses (full download)
        """
        return self._download_responses_full(assessment_id, assessment_name, "assessments")

    def _download_form_responses_full(self, form_id: str, form_name: str) -> List[Dict[str, Any]]:
        """
        Download all form responses (full download)
        """
        return self._download_responses_full(form_id, form_name, "forms")
    def save_responses_to_json(self, responses: List[Dict[str, Any]], assessment_name: str) -> str:
        """
        Save responses to JSON file
        
        Args:
            responses: List of response dictionaries
            assessment_name: The assessment name for file organization
            
        Returns:
            Path to the saved JSON file
        """
        json_file_path = self.get_json_file_path(assessment_name)
        
        # Save to storage
        json_content = json.dumps(responses, ensure_ascii=False, indent=2)
        self.storage.write_bytes(
            str(json_file_path), 
            json_content.encode("utf-8"), 
            content_type="application/json"
        )
        
        logger.info(f"Saved {len(responses)} responses to {json_file_path}")
        return str(json_file_path)
    
    def save_incremental_responses_to_json(self, responses: List[Dict[str, Any]], assessment_name: str) -> str:
        """
        Save incremental responses to JSON file (only new data)
        
        Args:
            responses: List of response dictionaries (only new data)
            assessment_name: The assessment name for file organization
            
        Returns:
            Path to the saved incremental JSON file
        """
        incremental_json_file_path = self.get_incremental_json_file_path(assessment_name)
        
        # Save to storage
        json_content = json.dumps(responses, ensure_ascii=False, indent=2)
        self.storage.write_bytes(
            str(incremental_json_file_path), 
            json_content.encode("utf-8"), 
            content_type="application/json"
        )
        
        logger.info(f"Saved {len(responses)} incremental responses to {incremental_json_file_path}")
        return str(incremental_json_file_path)
    
    def save_temp_responses_to_csv(self, responses: List[Dict[str, Any]], assessment_name: str) -> str:
        """
        Save filtered responses to temporary CSV file
        
        Args:
            responses: List of response dictionaries
            assessment_name: The assessment name for file organization
            
        Returns:
            Path to the saved temporary CSV file
        """
        # Filter responses
        filtered_responses = self.filter_responses(responses)
        
        # Convert to DataFrame
        df = pd.DataFrame(filtered_responses)
        
        # Save to temporary CSV
        temp_csv_file_path = self.get_temp_csv_file_path(assessment_name)
        self.storage.write_csv(str(temp_csv_file_path), df, sep=';', index=False)
        
        # Add answer columns
        self.add_answer_columns_to_csv(str(temp_csv_file_path), filtered_responses)
        
        logger.info(f"Saved {len(filtered_responses)} filtered responses to temporary {temp_csv_file_path}")
        return str(temp_csv_file_path)
    
    def merge_incremental_to_main_json(self, assessment_name: str, incremental_df: pd.DataFrame = None) -> bool:
        """
        Merge incremental JSON data into the main JSON file
        
        Args:
            assessment_name: The assessment name
            incremental_df: Optional DataFrame with incremental data (if provided, use this instead of file)
            
        Returns:
            True if merge successful, False otherwise
        """
        try:
            main_json_path = self.get_json_file_path(assessment_name)
            
            if incremental_df is not None:
                # Use provided DataFrame
                incremental_data = incremental_df.to_dict('records')
                logger.info(f"Using provided incremental DataFrame with {len(incremental_data)} records for {assessment_name}")
            else:
                # Use file-based approach
                incremental_json_path = self.get_incremental_json_file_path(assessment_name)
                
                # Check if incremental file exists
                if not self.storage.exists(str(incremental_json_path)):
                    logger.info(f"No incremental data to merge for {assessment_name}")
                    return True
                
                # Load incremental data
                incremental_data = self.storage.read_json(str(incremental_json_path))
                if not incremental_data:
                    logger.info(f"No incremental data to merge for {assessment_name}")
                    return True
            
            # Load existing main data
            existing_data = []
            if self.storage.exists(str(main_json_path)):
                existing_data = self.storage.read_json(str(main_json_path))
                if existing_data is None:
                    existing_data = []
            
            # Combine data
            combined_data = incremental_data + existing_data
            
            # Remove duplicates by response id if available
            seen = set()
            unique = []
            for r in combined_data:
                rid = r.get('id')
                if rid and rid not in seen:
                    seen.add(rid)
                    unique.append(r)
                elif not rid:
                    unique.append(r)
            
            # Sort by submitted timestamp, newest first
            unique.sort(key=lambda x: x.get('submittedTimestamp', 0), reverse=True)
            
            # Save combined data to main JSON
            self.save_responses_to_json(unique, assessment_name)
            logger.info(f"Merged {len(incremental_data)} incremental responses into main JSON for {assessment_name}")
            
            return True
        except Exception as e:
            logger.error(f"Error merging incremental data for {assessment_name}: {e}")
            return False
    
    def cleanup_temp_files(self, assessment_name: str) -> bool:
        """
        Clean up temporary files for an assessment
        
        Args:
            assessment_name: The assessment name
            
        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            deleted_files = []
            errors = []
            
            # Clean up incremental JSON
            incremental_json_path = self.get_incremental_json_file_path(assessment_name)
            if self.storage.exists(str(incremental_json_path)):
                if self.storage.delete(str(incremental_json_path)):
                    deleted_files.append("incremental JSON")
                else:
                    errors.append("failed to delete incremental JSON")
            
            # Clean up temporary CSV
            temp_csv_path = self.get_temp_csv_file_path(assessment_name)
            if self.storage.exists(str(temp_csv_path)):
                if self.storage.delete(str(temp_csv_path)):
                    deleted_files.append("temporary CSV")
                else:
                    errors.append("failed to delete temporary CSV")
            
            # Clean up temporary analysis files
            temp_analysis_path = self.get_temp_analysis_file_path(assessment_name)
            if self.storage.exists(str(temp_analysis_path)):
                if self.storage.delete(str(temp_analysis_path)):
                    deleted_files.append("temporary analysis")
                else:
                    errors.append("failed to delete temporary analysis")
            
            if deleted_files:
                logger.info(f"Cleaned up {', '.join(deleted_files)} files for {assessment_name}")
            else:
                logger.debug(f"No temporary files found for assessment: {assessment_name}")
            
            if errors:
                logger.warning(f"Some cleanup operations failed for {assessment_name}: {', '.join(errors)}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error cleaning up temp files for {assessment_name}: {e}")
            return False
    
    def load_responses_from_json(self, assessment_name: str) -> List[Dict[str, Any]]:
        """
        Load responses from JSON file
        
        Args:
            assessment_name: The assessment name for file organization
            
        Returns:
            List of response dictionaries
        """
        json_file_path = self.get_json_file_path(assessment_name)
        
        if not self.storage.exists(str(json_file_path)):
            logger.warning(f"No responses file found for {assessment_name}")
            return []
        
        try:
            responses = self.storage.read_json(str(json_file_path))
            # Handle case where read_json returns None
            if responses is None:
                logger.warning(f"Empty or corrupted JSON file for {assessment_name}")
                return []
            logger.info(f"Loaded {len(responses)} responses from {json_file_path}")
            return responses
        except Exception as e:
            logger.error(f"Error loading responses from {json_file_path}: {e}")
            return []
    
    def filter_responses(self, responses: List[Dict[str, Any]] | pd.DataFrame) -> List[Dict[str, Any]] | pd.DataFrame:
        """
        Filter responses to keep only valid ones
        
        Args:
            responses: List of response dictionaries or DataFrame
            
        Returns:
            Filtered list of responses or DataFrame
        """
        
        # Convert DataFrame to list if needed
        if isinstance(responses, pd.DataFrame):
            responses_list = responses.to_dict('records')
            return_df = True
        else:
            responses_list = responses
            return_df = False
        
        #For each user, keep only the newest response
        user_latest = {}
        for r in responses_list:
            user_id = r.get('userId') or r.get('user_id')
            created = r.get('submittedTimestamp', 0)
            if user_id is not None:
                if user_id not in user_latest or created > user_latest[user_id].get('submittedTimestamp', 0):
                    user_latest[user_id] = r
        
        filtered_list = list(user_latest.values())
        
        if return_df:
            filtered_df = pd.DataFrame(filtered_list)
            logger.info(f"Filtered {len(responses_list)} responses to {len(filtered_df)} valid responses")
            return filtered_df
        else:
            return filtered_list
    
    def add_answer_columns_to_csv(self, csv_path: str, responses: List[Dict[str, Any]] | pd.DataFrame) -> None:
        """
        Add answer columns to CSV file
        
        Args:
            csv_path: Path to CSV file
            responses: List of response dictionaries or DataFrame
        """
        # Convert DataFrame to list if needed
        if isinstance(responses, pd.DataFrame):
            responses_list = responses.to_dict('records')
            df = responses.copy()
        else:
            responses_list = responses
            # Load the existing CSV
            df = self.storage.read_csv(str(csv_path), sep=';')
        
        # Convert timestamps
        for col in ["created", "modified", "submittedTimestamp"]:
            if col in df.columns:
                try:
                    df[col] = pd.to_datetime(df[col], unit="s")
                except Exception:
                    pass
        
        # Prepare answer columns
        all_questions = set()
        answers_per_row = []
        for r in responses_list:
            answers = r.get("answers", [])
            ans_dict = {}
            for ans in answers:
                desc = ans.get("description")
                answer_val = ans.get("answer")
                if desc:
                    ans_dict[desc] = answer_val
                    all_questions.add(desc)
            answers_per_row.append(ans_dict)
        
        # Add columns for each question, ordered by number
        def question_sort_key(q):
            import re
            m = re.match(r"pregunta (\d+)", str(q).lower())
            return int(m.group(1)) if m else float('inf')
        
        ordered_questions = sorted([q for q in all_questions if q], key=question_sort_key)
        
        # Create new columns DataFrame to avoid fragmentation
        new_columns_data = {}
        for q in ordered_questions:
            new_columns_data[q] = [row.get(q) if isinstance(row, dict) else None for row in answers_per_row]
        
        # Create DataFrame with new columns and concatenate
        new_columns_df = pd.DataFrame(new_columns_data, index=df.index)
        df = pd.concat([df, new_columns_df], axis=1)
        
        # Save updated CSV
        self.storage.write_csv(str(csv_path), df, sep=';', index=False)
    
    def save_responses_to_csv(self, responses: List[Dict[str, Any]] | pd.DataFrame, assessment_name: str, return_df: bool = False) -> str | pd.DataFrame:
        """
        Save filtered responses to CSV file
        
        Args:
            responses: List of response dictionaries or DataFrame
            assessment_name: The assessment name for file organization
            return_df: If True, return DataFrame instead of file path
            
        Returns:
            Path to the saved CSV file or DataFrame if return_df=True
        """
        # Filter responses
        filtered_responses = self.filter_responses(responses)
        
        # Convert to DataFrame if needed
        if isinstance(filtered_responses, pd.DataFrame):
            df = filtered_responses
        else:
            df = pd.DataFrame(filtered_responses)
        
        if return_df:
            # Add answer columns to DataFrame directly
            # Convert DataFrame to list of dictionaries for processing
            responses = df.to_dict('records')
            
            # Prepare answer columns
            all_questions = set()
            answers_per_row = []
            for r in responses:
                answers = r.get("answers", [])
                ans_dict = {}
                for ans in answers:
                    desc = ans.get("description")
                    answer_val = ans.get("answer")
                    if desc:
                        ans_dict[desc] = answer_val
                        all_questions.add(desc)
                answers_per_row.append(ans_dict)
            
            # Add columns for each question, ordered by number
            def question_sort_key(q):
                import re
                m = re.match(r"pregunta (\d+)", str(q).lower())
                return int(m.group(1)) if m else float('inf')
            
            ordered_questions = sorted([q for q in all_questions if q], key=question_sort_key)
            
            # Create new columns DataFrame to avoid fragmentation
            new_columns_data = {}
            for q in ordered_questions:
                new_columns_data[q] = [row.get(q) if isinstance(row, dict) else None for row in answers_per_row]
            
            # Create DataFrame with new columns and concatenate
            new_columns_df = pd.DataFrame(new_columns_data, index=df.index)
            result_df = pd.concat([df, new_columns_df], axis=1)
            
            # Convert timestamps
            for col in ["created", "modified", "submittedTimestamp"]:
                if col in result_df.columns:
                    try:
                        result_df[col] = pd.to_datetime(result_df[col], unit="s")
                    except Exception:
                        pass
            
            logger.info(f"Processed {len(result_df)} filtered responses in memory for {assessment_name}")
            return result_df
        else:
            # Save to CSV
            csv_file_path = self.get_csv_file_path(assessment_name)
            self.storage.write_csv(str(csv_file_path), df, sep=';', index=False)
            
            # Add answer columns
            self.add_answer_columns_to_csv(str(csv_file_path), filtered_responses)
            
            logger.info(f"Saved {len(filtered_responses)} filtered responses to {csv_file_path}")
            return str(csv_file_path)
    
    def save_form_responses_to_csv(self, responses: List[Dict[str, Any]], form_name: str) -> str:
        """
        Save form responses to CSV file with special processing for multi-choice questions
        
        Args:
            responses: List of form response dictionaries
            form_name: Name of the form for file naming
            
        Returns:
            Path to the saved CSV file
        """
        # Use special path for USERS form (saves to analysis directory)
        if form_name == "USERS":
            csv_path = self.get_users_csv_file_path(form_name)
        else:
            csv_path = self.get_csv_file_path(form_name)
        
        # Process each response to extract answers
        processed_responses = []
        
        for response in responses:
            processed_response = {
                'id': response.get('id'),
                'user_id': response.get('user_id'),
                'email': response.get('email'),
                'grade': response.get('grade'),
                'passed': response.get('passed'),
                'created': response.get('created'),
                'modified': response.get('modified'),
                'submittedTimestamp': response.get('submittedTimestamp')
            }
            
            # Process answers
            answers = response.get('answers', [])
            for answer in answers:
                description = answer.get('description', '')
                answer_value = answer.get('answer', '')
                block_type = answer.get('blockType', '')
                
                # Special handling for the multi-choice question about tests to prepare
                if (description == "¿Qué pruebas vas a preparar con M30M este semestre?" and 
                    block_type == "mcma"):
                    
                    # Define the 5 possible test options
                    test_options = ["Matemática M1", "Matemática M2", "Competencia lectora", "Ciencias", "Historia"]
                    
                    # Check which options are present in the answer
                    # Handle case where answer_value might be None
                    answer_str = str(answer_value) if answer_value is not None else ""
                    for option in test_options:
                        column_name = f"preparar_{option.replace(' ', '_').lower()}"
                        processed_response[column_name] = 1 if option in answer_str else 0
                else:
                    # For other questions, use the description as column name
                    # Clean the description to make it a valid column name
                    column_name = description.replace('¿', '').replace('?', '').replace(' ', '_').lower()
                    column_name = ''.join(c for c in column_name if c.isalnum() or c == '_')
                    
                    # Handle duplicate column names by adding a suffix
                    if column_name in processed_response:
                        column_name = f"{column_name}_2"
                    
                    processed_response[column_name] = answer_value
            
            processed_responses.append(processed_response)
        
        # Convert to DataFrame
        df = pd.DataFrame(processed_responses)
        
        # Convert timestamps to readable datetime format
        for col in ["created", "modified", "submittedTimestamp"]:
            if col in df.columns:
                try:
                    df[col] = pd.to_datetime(df[col], unit="s")
                except Exception:
                    pass
        
        # Add sum column for test preparation
        preparar_columns = [col for col in df.columns if col.startswith('preparar_')]
        if preparar_columns:
            df['cantidad_pruebas_a_preparar'] = df[preparar_columns].sum(axis=1)
        
        # Normalize commune column
        if 'en_qué_comuna_vives' in df.columns:
            df['en_qué_comuna_vives_normalizada'] = df['en_qué_comuna_vives'].apply(self._normalize_commune)
        
        # Process email columns
        df = self._process_email_columns(df)
        
        # Save to CSV
        self.storage.write_csv(str(csv_path), df, sep=';', index=False)
        
        # Save to Excel
        excel_path = str(csv_path).replace('.csv', '.xlsx')
        df.to_excel(excel_path, index=False, engine='openpyxl')
        
        logger.info(f"Saved {len(df)} form responses to {csv_path} and {excel_path}")
        return str(csv_path)
    
    def _normalize_commune(self, commune: str) -> str:
        """
        Normalize commune names by removing accents, converting to lowercase,
        and handling common misspellings
        
        Args:
            commune: The commune name to normalize
            
        Returns:
            Normalized commune name
        """
        if not commune or pd.isna(commune):
            return commune
        
        # Convert to string and lowercase
        commune = str(commune).lower().strip()
        
        # Replace special characters with their basic equivalents
        special_char_mappings = {
            'á': 'a',
            'é': 'e',
            'í': 'i',
            'ó': 'o',
            'ú': 'u',
            'ñ': 'n', 
        }
        
        # Apply special character mappings
        for special_char, replacement in special_char_mappings.items():
            commune = commune.replace(special_char, replacement)
        
        # Remove any remaining diacritics using unicodedata
        import unicodedata
        commune = unicodedata.normalize('NFD', commune)
        commune = ''.join(c for c in commune if not unicodedata.combining(c))
        
        # Handle common misspellings and variations
        commune_mappings = {
            'valdiviq': 'valdivia',
            'florida': 'la florida',
            'penanolen': 'penalolen',
            'lo barnerchea': 'lo barnechea',
            'santiago': 'santiago centro',
            'vina': 'vina del mar',
        }
        
        # Apply mappings
        if commune in commune_mappings:
            return commune_mappings[commune]
        
        return commune
    
    def delete_assessment_data(self, assessment_name: str) -> bool:
        """
        Delete all data for a specific assessment
        
        Args:
            assessment_name: The assessment name to delete data for
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            json_file_path = self.get_json_file_path(assessment_name)
            csv_file_path = self.get_csv_file_path(assessment_name)
            
            deleted_files = []
            
            if self.storage.exists(str(json_file_path)):
                self.storage.delete(str(json_file_path))
                deleted_files.append("JSON")
            
            if self.storage.exists(str(csv_file_path)):
                self.storage.delete(str(csv_file_path))
                deleted_files.append("CSV")
            
            if deleted_files:
                logger.info(f"Deleted {', '.join(deleted_files)} files for assessment: {assessment_name}")
            else:
                logger.info(f"No data found for assessment: {assessment_name}")
            
            return True
        except Exception as e:
            logger.error(f"Error deleting data for assessment {assessment_name}: {e}")
            return False
    
    def _download_and_process_common(
        self,
        object_id: str,
        object_name: str,
        download_func,
        save_json_name: str,
        download_only: bool = False,
        process_only: bool = False,
        filter_func=None,
        save_csv_func=None,
        incremental_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        Common logic for downloading and processing forms/assessments.

        Args:
            object_id: The form or assessment ID
            object_name: The name for file organization
            download_func: Function to download responses incrementally
            save_json_name: Name to use for saving JSON (form_name or assessment_name)
            download_only: If True, only download JSON, do not process to CSV
            process_only: If True, only process existing JSON to CSV, do not download
            filter_func: Optional function to filter responses (for assessments)
            save_csv_func: Optional function to save responses to CSV (for assessments)
            incremental_mode: If True, use incremental processing with temporary files

        Returns:
            Dictionary with results
        """
        result = {
            'name': object_name,
            'id': object_id,
            'json_path': None,
            'response_count': 0,
            'incremental_count': 0
        }
        if save_csv_func:
            result['csv_path'] = None
            result['filtered_count'] = 0

        json_file_path = self.get_json_file_path(object_name)

        # Download step
        if not process_only:
            logger.info(f"Downloading responses for: {object_name}")
            latest_timestamp = self.get_latest_timestamp_from_json(str(json_file_path))
            downloaded_responses = download_func(object_id, object_name)

            # Determine if there are actually new responses
            new_responses = []
            if latest_timestamp and self.storage.exists(str(json_file_path)):
                existing = self.storage.read_json(str(json_file_path))
                # Handle case where existing might be None
                if existing is None:
                    existing = []
                
                # Find responses that are newer than the latest timestamp
                for response in downloaded_responses:
                    response_timestamp = response.get('submittedTimestamp', 0)
                    if response_timestamp > latest_timestamp:
                        new_responses.append(response)
                
                # Combine new data with existing data
                combined = downloaded_responses + existing

                # Remove duplicates by response id if available
                seen = set()
                unique = []
                for r in combined:
                    rid = r.get('id')
                    if rid and rid not in seen:
                        seen.add(rid)
                        unique.append(r)
                    elif not rid:
                        unique.append(r)

                # Sort by submitted timestamp, newest first
                unique.sort(key=lambda x: x.get('submittedTimestamp', 0), reverse=True)
                responses = unique
            else:
                # No existing data, so all downloaded responses are new
                new_responses = downloaded_responses
                responses = downloaded_responses

            # Save incremental data if in incremental mode and there are actually new responses
            if incremental_mode and new_responses:
                self.save_incremental_responses_to_json(new_responses, object_name)
                result['incremental_count'] = len(new_responses)
                logger.info(f"Saved {len(new_responses)} incremental responses for {object_name}")
            elif incremental_mode:
                logger.info(f"No new responses found for {object_name}, skipping incremental file creation")

            # Save raw JSON (only in non-incremental mode to maintain current behavior)
            if not incremental_mode:
                self.save_responses_to_json(responses, object_name)
                result['json_path'] = str(json_file_path)
                result['response_count'] = len(responses)
                logger.info(f"Saved raw JSON for {object_name} to {json_file_path}")
            else:
                # In incremental mode, we don't save to main JSON yet
                result['response_count'] = len(responses)
                logger.info(f"Downloaded {len(responses)} total responses for {object_name} (incremental mode - not saved to main JSON yet)")

        # Processing step (for assessments only)
        if save_csv_func and not download_only:
            logger.info(f"Processing responses for: {object_name}")
            
            if incremental_mode:
                # Use incremental JSON for processing
                incremental_json_path = self.get_incremental_json_file_path(object_name)
                if not self.storage.exists(str(incremental_json_path)):
                    logger.info(f"No incremental data to process for {object_name} (no new responses found)")
                    return result
                
                # Load incremental responses
                incremental_responses = self.storage.read_json(str(incremental_json_path))
                if not incremental_responses:
                    logger.info(f"No incremental data to process for {object_name}")
                    return result
                
                # Use temporary CSV function
                csv_path = self.save_temp_responses_to_csv(incremental_responses, object_name)
                result['csv_path'] = csv_path
                
                # Count filtered responses
                filtered_responses = filter_func(incremental_responses) if filter_func else incremental_responses
                result['filtered_count'] = len(filtered_responses)
            else:
                # Use existing logic for backward compatibility
                if not self.storage.exists(str(json_file_path)):
                    logger.warning(f"Raw JSON file not found: {json_file_path}. Skipping processing.")
                    return result

                responses = self.load_responses_from_json(object_name)
                csv_path = save_csv_func(responses, object_name)
                result['csv_path'] = csv_path

                # Count filtered responses
                filtered_responses = filter_func(responses) if filter_func else responses
                result['filtered_count'] = len(filtered_responses)

        return result

    def download_and_process_form(self, form_id: str, form_name: str, download_only: bool = False, process_only: bool = False, incremental_mode: bool = False) -> Dict[str, Any]:
        """
        Download and process form responses to CSV
        """
        return self._download_and_process_common(
            object_id=form_id,
            object_name=form_name,
            download_func=self.download_form_responses_incremental,
            save_json_name=form_name,
            download_only=download_only,
            process_only=process_only,
            filter_func=None,
            save_csv_func=self.save_form_responses_to_csv,
            incremental_mode=incremental_mode,
        )

    def download_and_process_assessment(
        self,
        assessment_id: str,
        assessment_name: str,
        download_only: bool = False,
        process_only: bool = False,
        incremental_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Download and/or process assessment responses
        """
        return self._download_and_process_common(
            object_id=assessment_id,
            object_name=assessment_name,
            download_func=self.download_assessment_responses_incremental,
            save_json_name=assessment_name,
            download_only=download_only,
            process_only=process_only,
            filter_func=self.filter_responses,
            save_csv_func=self.save_responses_to_csv,
            incremental_mode=incremental_mode,
        )
    
    def download_all_assessments(self, assessment_list: List[Dict[str, str]], 
                                reset_data: bool = False, download_only: bool = False, 
                                process_only: bool = False, incremental_mode: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Download and/or process responses for all assessments in the list
        
        Args:
            assessment_list: List of assessment dictionaries with 'name' and 'assessment_id'
            reset_data: If True, delete existing data before downloading
            download_only: If True, only download JSON, do not process to CSV
            process_only: If True, only process existing JSON to CSV, do not download
            incremental_mode: If True, use incremental processing with temporary files
        
        Returns:
            Dictionary mapping assessment names to their results
        """
        all_results = {}
        
        for assessment in assessment_list:
            name = assessment['name']
            assessment_id = assessment['assessment_id']
            
            logger.info(f"Processing assessment: {name}")
            
            # Reset data if requested
            if reset_data:
                self.delete_assessment_data(name)
            
            try:
                result = self.download_and_process_assessment(
                    assessment_id, name, download_only, process_only, incremental_mode
                )
                all_results[name] = result
                logger.info(f"Completed processing for {name}: {result['response_count']} responses, {result.get('incremental_count', 0)} incremental, {result['filtered_count']} filtered")
            except Exception as e:
                logger.error(f"Error processing {name}: {e}")
                all_results[name] = {
                    'assessment_name': name,
                    'assessment_id': assessment_id,
                    'error': str(e)
                }
        
        return all_results
    
    def get_assessment_info(self, assessment_name: str) -> Dict[str, Any]:
        """
        Get information about downloaded assessment data
        
        Args:
            assessment_name: The assessment name
            
        Returns:
            Dictionary with assessment information
        """
        json_file_path = self.get_json_file_path(assessment_name)
        csv_file_path = self.get_csv_file_path(assessment_name)
        
        info = {
            'name': assessment_name,
            'json_exists': self.storage.exists(str(json_file_path)),
            'csv_exists': self.storage.exists(str(csv_file_path)),
            'json_path': str(json_file_path),
            'csv_path': str(csv_file_path),
            'last_modified': None,
            'response_count': 0,
            'filtered_count': 0
        }
        
        if info['json_exists']:
            try:
                responses = self.storage.read_json(str(json_file_path))
                info['response_count'] = len(responses)
                
                if responses:
                    # Get latest timestamp
                    latest_record = responses[0]
                    latest_timestamp = latest_record.get('submittedTimestamp')
                    if latest_timestamp:
                        info['last_modified'] = datetime.fromtimestamp(latest_timestamp).isoformat()
                        
            except Exception as e:
                logger.error(f"Error getting JSON info for {assessment_name}: {e}")
        
        if info['csv_exists']:
            try:
                df = self.storage.read_csv(str(csv_file_path), sep=';')
                info['filtered_count'] = len(df)
            except Exception as e:
                logger.error(f"Error getting CSV info for {assessment_name}: {e}")
        
        return info

    def _compare_emails(self, email1: str, email2: str) -> str:
        """
        Compare two emails and return the action to take:
        - 'same': emails are identical
        - 'similar': emails have 1 character difference (typo)
        - 'different': emails are different
        
        Args:
            email1: First email (from 'email' column)
            email2: Second email (from 'ingresa_tu_correo' column)
            
        Returns:
            Action to take: 'same', 'similar', or 'different'
        """
        if not email1 or not email2 or pd.isna(email1) or pd.isna(email2):
            return 'different'
        
        email1 = str(email1).strip().lower()
        email2 = str(email2).strip().lower()
        
        # If they're identical
        if email1 == email2:
            return 'same'
        
        # Check for 1 character difference using Levenshtein distance
        def levenshtein_distance(s1, s2):
            if len(s1) < len(s2):
                return levenshtein_distance(s2, s1)
            
            if len(s2) == 0:
                return len(s1)
            
            previous_row = list(range(len(s2) + 1))
            for i, c1 in enumerate(s1):
                current_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = previous_row[j + 1] + 1
                    deletions = current_row[j] + 1
                    substitutions = previous_row[j] + (c1 != c2)
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row
            
            return previous_row[-1]
        
        distance = levenshtein_distance(email1, email2)
        
        if distance == 1:
            return 'similar'
        else:
            return 'different'
    
    def _process_email_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process email columns in the form DataFrame:
        - If emails are identical: remove the second email column
        - If emails have 1 character difference: remove the second email column
        - If emails are different: keep both columns
        
        Args:
            df: DataFrame with 'email' and 'ingresa_tu_correo' columns
            
        Returns:
            DataFrame with processed email columns
        """
        if 'email' not in df.columns or 'ingresa_tu_correo' not in df.columns:
            return df
        
        # Create a copy to avoid modifying the original
        df_processed = df.copy()
        
        # Add a column to track the comparison result
        df_processed['email_comparison'] = df_processed.apply(
            lambda row: self._compare_emails(row['email'], row['ingresa_tu_correo']), 
            axis=1
        )
        
        # Remove the second email column for same/similar cases
        same_similar_mask = df_processed['email_comparison'].isin(['same', 'similar'])
        df_processed.loc[same_similar_mask, 'ingresa_tu_correo'] = None
        
        # Log statistics
        same_count = (df_processed['email_comparison'] == 'same').sum()
        similar_count = (df_processed['email_comparison'] == 'similar').sum()
        different_count = (df_processed['email_comparison'] == 'different').sum()
        
        logger.info(f"Email processing results: {same_count} same, {similar_count} similar (1 char diff), {different_count} different")
        
        # Remove the comparison column as it was just for processing
        df_processed = df_processed.drop('email_comparison', axis=1)
        
        return df_processed

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Download and process assessment responses')
    parser.add_argument('--reset-data', action='store_true', help='Reset all downloaded data and download from scratch')
    parser.add_argument('--download-only', action='store_true', help='Only download JSON data, do not process to CSV')
    parser.add_argument('--process-only', action='store_true', help='Only process existing JSON to CSV, do not download')
    parser.add_argument('--info', help='Get information about downloaded data for a specific assessment')
    parser.add_argument('--delete-data', help='Delete all data for a specific assessment')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--incremental', action='store_true', help='Use incremental processing mode (process only new data)')
    parser.add_argument('--full', action='store_true', help='Force full download (ignore incremental mode)')
    return parser.parse_args()

def load_assessment_list_from_env() -> List[Dict[str, str]]:
    """Load assessment list from environment variables"""
    try:
        assessments = []
        
        # Load assessment IDs from environment variables
        m1_id = os.getenv("M1_ASSESSMENT_ID")
        cl_id = os.getenv("CL_ASSESSMENT_ID")
        cien_id = os.getenv("CIEN_ASSESSMENT_ID")
        hyst_id = os.getenv("HYST_ASSESSMENT_ID")
        
        if m1_id:
            assessments.append({'name': 'M1', 'assessment_id': m1_id})
        if cl_id:
            assessments.append({'name': 'CL', 'assessment_id': cl_id})
        if cien_id:
            assessments.append({'name': 'CIEN', 'assessment_id': cien_id})
        if hyst_id:
            assessments.append({'name': 'HYST', 'assessment_id': hyst_id})
        
        logger.info(f"Loaded {len(assessments)} assessments from environment variables")
        return assessments
    except Exception as e:
        logger.error(f"Error loading assessment list from environment: {e}")
        raise



def main():
    """Main function for standalone execution"""
    # Parse arguments
    args = parse_arguments()
    
    # Configure logging
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize downloader
    downloader = AssessmentDownloader()
    
    # Handle info command
    if args.info:
        info = downloader.get_assessment_info(args.info)
        print(f"\nAssessment Info for '{args.info}':")
        print(f"  JSON exists: {info['json_exists']}")
        print(f"  CSV exists: {info['csv_exists']}")
        print(f"  JSON path: {info['json_path']}")
        print(f"  CSV path: {info['csv_path']}")
        print(f"  Response count: {info['response_count']}")
        print(f"  Filtered count: {info['filtered_count']}")
        print(f"  Last modified: {info['last_modified']}")
        return
    
    # Handle delete command
    if args.delete_data:
        success = downloader.delete_assessment_data(args.delete_data)
        if success:
            print(f"Successfully deleted data for assessment: {args.delete_data}")
        else:
            print(f"Failed to delete data for assessment: {args.delete_data}")
        return
    
    # Determine incremental mode
    incremental_mode = args.incremental and not args.full
    
    # Handle form download (USERS environment variable)
    users_form_id = os.getenv("USERS")
    if users_form_id:
        try:
            if args.process_only:
                logger.info("Processing USERS form (process-only mode)")
                result = downloader.download_and_process_form(users_form_id, "USERS", download_only=False, process_only=True, incremental_mode=incremental_mode)
            else:
                logger.info("Downloading USERS form")
                result = downloader.download_and_process_form(users_form_id, "USERS", args.download_only, process_only=False, incremental_mode=incremental_mode)
            
            print(f"\n=== Form Download Results ===")
            print(f"USERS: {result['response_count']} responses")
            if incremental_mode and result.get('incremental_count', 0) > 0:
                print(f"  New responses: {result['incremental_count']}")
            if result['json_path']:
                print(f"  JSON: {result['json_path']}")
            if result.get('csv_path'):
                print(f"  CSV: {result['csv_path']}")
        except Exception as e:
            logger.error(f"Error processing USERS form: {e}")
            print(f"❌ Failed to process USERS form: {e}")
    else:
        logger.info("USERS environment variable not found, skipping form download")
    
    # Load assessment list from environment variables
    try:
        assessments = load_assessment_list_from_env()
        if not assessments:
            logger.warning("No assessment IDs found in environment variables")
            print("⚠️  No assessments to process")
            return
    except Exception as e:
        logger.error(f"Error loading assessment list from environment: {e}")
        print(f"❌ Failed to load assessment list: {e}")
        return
    
    # Download and process assessments
    try:
        results = downloader.download_all_assessments(
            assessments, 
            reset_data=args.reset_data,
            download_only=args.download_only,
            process_only=args.process_only,
            incremental_mode=incremental_mode
        )
        
        # Print results
        if incremental_mode:
            print("\n=== Incremental Download/Processing Results ===")
        else:
            print("\n=== Download/Processing Results ===")
        successful_count = 0
        failed_count = 0
        total_incremental = 0
        
        for name, result in results.items():
            if 'error' in result:
                print(f"❌ {name}: ERROR - {result['error']}")
                failed_count += 1
            else:
                if incremental_mode:
                    incremental_count = result.get('incremental_count', 0)
                    total_incremental += incremental_count
                    print(f"✅ {name}: {result['response_count']} total responses, {incremental_count} new, {result['filtered_count']} filtered")
                else:
                    print(f"✅ {name}: {result['response_count']} responses, {result['filtered_count']} filtered")
                if result['json_path']:
                    print(f"  JSON: {result['json_path']}")
                if result['csv_path']:
                    print(f"  CSV: {result['csv_path']}")
                successful_count += 1
        
        print(f"\n📊 Summary: {successful_count} successful, {failed_count} failed")
        if incremental_mode:
            print(f"📈 New responses: {total_incremental}")
        print(f"📁 JSON files saved in: {downloader.raw_dir}")
        print(f"📁 CSV files saved in: {downloader.processed_dir}")
        
    except Exception as e:
        logger.error(f"Error in assessment processing: {e}")
        print(f"❌ Failed to process assessments: {e}")

if __name__ == "__main__":
    main()
    