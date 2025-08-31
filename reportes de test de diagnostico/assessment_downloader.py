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
    
    def get_latest_timestamp_from_json(self, json_file_path: str) -> Optional[int]:
        """Get the latest 'created' timestamp from an existing JSON file"""
        if not self.storage.exists(json_file_path):
            return None
        
        try:
            data = self.storage.read_json(json_file_path)
            
            # Handle case where read_json returns None
            if data is None or not data:
                return None
            
            # Get the first record (newest) since data is sorted by created timestamp
            latest_record = data[0]
            return latest_record.get('created')
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

            if latest_timestamp is None:
                logger.info("No existing responses data found. Performing full download...")
                if object_type == "forms":
                    return self._download_form_responses_full(object_id, object_name)
                else:
                    return self._download_assessment_responses_full(object_id, object_name)

            logger.info(f"Latest response timestamp: {datetime.fromtimestamp(latest_timestamp)}")
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

                        # Check if we've reached existing data
                        for record in responses:
                            record_timestamp = record.get('created')
                            if record_timestamp and record_timestamp <= latest_timestamp:
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
                # Combine new data with existing data and sort by created timestamp (newest first)
                combined_data = new_data + existing_data
                combined_data.sort(key=lambda x: x.get('created', 0), reverse=True)
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

    def download_assessment_responses_incremental(self, assessment_id: str, assessment_name: str) -> List[Dict[str, Any]]:
        """
        Download assessment responses incrementally based on the latest timestamp
        """
        return self._download_responses_incremental(assessment_id, assessment_name, "assessments")
    
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
        logger.info(f"Downloading all responses for {object_type[:-1]} {object_id}")

        all_responses = []
        page = 1
        total_pages = 1

        while page <= total_pages:
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

        # Sort by created timestamp (newest first)
        all_responses.sort(key=lambda x: x.get('created', 0), reverse=True)
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
    
    def filter_responses(self, responses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter responses to keep only valid ones
        
        Args:
            responses: List of response dictionaries
            
        Returns:
            Filtered list of responses
        """
        
        #For each user, keep only the newest response
        user_latest = {}
        for r in responses:
            user_id = r.get('userId') or r.get('user_id')
            created = r.get('created', 0)
            if user_id is not None:
                if user_id not in user_latest or created > user_latest[user_id].get('created', 0):
                    user_latest[user_id] = r
        
        return list(user_latest.values())
    
    def add_answer_columns_to_csv(self, csv_path: str, responses: List[Dict[str, Any]]) -> None:
        """
        Add answer columns to CSV file
        
        Args:
            csv_path: Path to CSV file
            responses: List of response dictionaries
        """
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
        df = pd.concat([df, new_columns_df], axis=1)
        
        # Save updated CSV
        self.storage.write_csv(str(csv_path), df, sep=';', index=False)
    
    def save_responses_to_csv(self, responses: List[Dict[str, Any]], assessment_name: str) -> str:
        """
        Save filtered responses to CSV file
        
        Args:
            responses: List of response dictionaries
            assessment_name: The assessment name for file organization
            
        Returns:
            Path to the saved CSV file
        """
        # Filter responses
        filtered_responses = self.filter_responses(responses)
        
        # Convert to DataFrame
        df = pd.DataFrame(filtered_responses)
        
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

        Returns:
            Dictionary with results
        """
        result = {
            'name': object_name,
            'id': object_id,
            'json_path': None,
            'response_count': 0
        }
        if save_csv_func:
            result['csv_path'] = None
            result['filtered_count'] = 0

        json_file_path = self.get_json_file_path(object_name)

        # Download step
        if not process_only:
            logger.info(f"Downloading responses for: {object_name}")
            latest_timestamp = self.get_latest_timestamp_from_json(str(json_file_path))
            new_responses = download_func(object_id, object_name)

            # If incremental, combine with existing
            if latest_timestamp and self.storage.exists(str(json_file_path)):
                existing = self.storage.read_json(str(json_file_path))
                # Handle case where existing might be None
                if existing is None:
                    existing = []
                combined = new_responses + existing

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

                # Sort by created timestamp, newest first
                unique.sort(key=lambda x: x.get('created', 0), reverse=True)
                responses = unique
            else:
                responses = new_responses

            # Save raw JSON
            self.save_responses_to_json(responses, object_name)
            result['json_path'] = str(json_file_path)
            result['response_count'] = len(responses)
            logger.info(f"Saved raw JSON for {object_name} to {json_file_path}")

        # Processing step (for assessments only)
        if save_csv_func and not download_only:
            logger.info(f"Processing responses for: {object_name}")
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

    def download_and_process_form(self, form_id: str, form_name: str, download_only: bool = False, process_only: bool = False) -> Dict[str, Any]:
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
        )

    def download_and_process_assessment(
        self,
        assessment_id: str,
        assessment_name: str,
        download_only: bool = False,
        process_only: bool = False
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
        )
    
    def download_all_assessments(self, assessment_list: List[Dict[str, str]], 
                                reset_data: bool = False, download_only: bool = False, 
                                process_only: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Download and/or process responses for all assessments in the list
        
        Args:
            assessment_list: List of assessment dictionaries with 'name' and 'assessment_id'
            reset_data: If True, delete existing data before downloading
            download_only: If True, only download JSON, do not process to CSV
            process_only: If True, only process existing JSON to CSV, do not download
        
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
                    assessment_id, name, download_only, process_only
                )
                all_results[name] = result
                logger.info(f"Completed processing for {name}: {result['response_count']} responses, {result['filtered_count']} filtered")
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
                    latest_timestamp = latest_record.get('created')
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
    
    # Handle form download (USERS environment variable)
    users_form_id = os.getenv("USERS")
    if users_form_id:
        try:
            if args.process_only:
                logger.info("Processing USERS form (process-only mode)")
                result = downloader.download_and_process_form(users_form_id, "USERS", download_only=False, process_only=True)
            else:
                logger.info("Downloading USERS form")
                result = downloader.download_and_process_form(users_form_id, "USERS", args.download_only, process_only=False)
            
            print(f"\n=== Form Download Results ===")
            print(f"USERS: {result['response_count']} responses")
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
            process_only=args.process_only
        )
        
        # Print results
        print("\n=== Download/Processing Results ===")
        successful_count = 0
        failed_count = 0
        
        for name, result in results.items():
            if 'error' in result:
                print(f"❌ {name}: ERROR - {result['error']}")
                failed_count += 1
            else:
                print(f"✅ {name}: {result['response_count']} responses, {result['filtered_count']} filtered")
                if result['json_path']:
                    print(f"  JSON: {result['json_path']}")
                if result['csv_path']:
                    print(f"  CSV: {result['csv_path']}")
                successful_count += 1
        
        print(f"\n📊 Summary: {successful_count} successful, {failed_count} failed")
        print(f"📁 JSON files saved in: {downloader.raw_dir}")
        print(f"📁 CSV files saved in: {downloader.processed_dir}")
        
    except Exception as e:
        logger.error(f"Error in assessment processing: {e}")
        print(f"❌ Failed to process assessments: {e}")

if __name__ == "__main__":
    main()
    