#!/usr/bin/env python3
"""
Multi-Assessment Processor
Downloads multiple assessments, joins responses by user, and generates combined reports
Designed to run as a Cloud Run job for automated processing
"""

import os
import sys
import yaml
import logging
import tempfile
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
from dotenv import load_dotenv

# Import existing services
from descarga_responses import get_assessment_responses, filter_responses, save_and_update_responses
from drive_service import DriveService
from slack_service import SlackService
from storage import StorageClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MultiAssessmentProcessor:
    def __init__(self, config_path: str, upload_to_drive: bool = True, send_slack: bool = True):
        """
        Initialize the multi-assessment processor
        
        Args:
            config_path: Path to the YAML configuration file
            upload_to_drive: Whether to upload files to Google Drive
            send_slack: Whether to send Slack notifications
        """
        self.config = self._load_config(config_path)
        self.storage = StorageClient()
        self.drive_service = DriveService() if upload_to_drive else None
        self.slack_service = SlackService() if send_slack else None
        
        # Setup directories
        self.course_id = self.config['course']['id']
        self.raw_dir = Path(f"data/responses/raw/{self.course_id}")
        self.processed_dir = Path(f"data/responses/processed/{self.course_id}")
        self.reports_dir = Path(f"data/responses/reports/{self.course_id}")
        
        # Create directories
        for directory in [self.raw_dir, self.processed_dir, self.reports_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Set default configuration values
        self.output_format = os.getenv('OUTPUT_FORMAT', 'xlsx')
        self.drive_folder_name = os.getenv('DRIVE_FOLDER_NAME', 'Assessment Reports')
        self.drive_subfolder = os.getenv('DRIVE_SUBFOLDER', 'Combined Reports')
        self.slack_channel = os.getenv('SLACK_CHANNEL', '#assessment-reports')
        self.notify_on_success = os.getenv('NOTIFY_ON_SUCCESS', 'true').lower() == 'true'
        self.notify_on_error = os.getenv('NOTIFY_ON_ERROR', 'true').lower() == 'true'
        
        # Processing options
        self.download_new = os.getenv('DOWNLOAD_NEW', 'true').lower() == 'true'
        self.process_individual = os.getenv('PROCESS_INDIVIDUAL', 'true').lower() == 'true'
        self.process_grouped = os.getenv('PROCESS_GROUPED', 'true').lower() == 'true'
        
        # Feature flags
        self.should_upload_to_drive = upload_to_drive
        self.should_send_slack = send_slack
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_path}: {e}")
            raise
    
    def download_assessment(self, assessment_name: str, assessment_id: str) -> bool:
        """
        Download responses for a single assessment
        
        Args:
            assessment_name: Name of the assessment
            assessment_id: ID of the assessment
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Downloading responses for assessment: {assessment_name}")
            
            # Check if we should download new responses
            if not self.download_new:
                logger.info(f"Skipping download for {assessment_name} (download_new=False)")
                return True
            
            # Get existing responses to check for incremental updates
            json_path = self.raw_dir / f"{assessment_name.replace('/', '_')}.json"
            latest_timestamp = None
            
            if self.storage.exists(str(json_path)):
                try:
                    existing_data = self.storage.read_json(str(json_path))
                    if existing_data:
                        latest_timestamp = existing_data[0].get('created')
                        logger.info(f"Found existing data for {assessment_name}, latest timestamp: {latest_timestamp}")
                except Exception as e:
                    logger.warning(f"Could not read existing data for {assessment_name}: {e}")
            
            # Download new responses
            new_responses = get_assessment_responses(assessment_id, latest_timestamp)
            logger.info(f"Downloaded {len(new_responses)} new responses for {assessment_name}")
            
            # Combine with existing if incremental
            if latest_timestamp and self.storage.exists(str(json_path)):
                existing = self.storage.read_json(str(json_path))
                combined = new_responses + existing
                
                # Remove duplicates by response id
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
            self.storage.write_json(str(json_path), responses)
            logger.info(f"Saved raw JSON for {assessment_name} to {json_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to download assessment {assessment_name}: {e}")
            return False
    
    def process_assessment(self, assessment_name: str) -> bool:
        """
        Process a single assessment (filter and convert to CSV)
        
        Args:
            assessment_name: Name of the assessment
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Processing assessment: {assessment_name}")
            
            json_path = self.raw_dir / f"{assessment_name.replace('/', '_')}.json"
            if not self.storage.exists(str(json_path)):
                logger.error(f"Raw JSON file not found: {json_path}")
                return False
            
            # Load responses
            responses = self.storage.read_json(str(json_path))

            # Filter responses
            filtered_responses = filter_responses(responses)

            # Save processed CSV
            save_and_update_responses(self.processed_dir, assessment_name, filtered_responses)
            
            logger.info(f"Processed assessment {assessment_name} successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process assessment {assessment_name}: {e}")
            return False
    
    def join_assessments_by_user(self, group_name: str, assessment_names: List[str]) -> Optional[str]:
        """
        Join multiple assessments by user ID
        
        Args:
            group_name: Name for the combined assessment group
            assessment_names: List of assessment names to join
            
        Returns:
            Path to the combined file if successful, None otherwise
        """
        try:
            logger.info(f"Joining assessments for group {group_name}: {assessment_names}")
            
            # Load all assessment CSVs
            dfs = []
            for assessment_name in assessment_names:
                csv_path = self.processed_dir / f"{assessment_name.replace('/', '_')}.csv"
                if not self.storage.exists(str(csv_path)):
                    logger.error(f"Processed CSV not found: {csv_path}")
                    return None
                
                df = self.storage.read_csv(str(csv_path), sep=';')
                # Add assessment identifier
                df['assessment_name'] = assessment_name
                dfs.append(df)
            
            if not dfs:
                logger.error("No valid assessment data found")
                return None
            
            # Join by user ID (userId or user_id column)
            user_id_col = None
            for col in ['userId', 'user_id', 'user']:
                if col in dfs[0].columns:
                    user_id_col = col
                    break
            
            if not user_id_col:
                logger.error("No user ID column found in assessment data")
                return None
            
            # Combine all dataframes
            combined_df = pd.concat(dfs, ignore_index=True)
            
            # Pivot to get one row per user with columns for each assessment
            try:
                pivot_df = combined_df.pivot_table(
                    index=user_id_col,
                    columns='assessment_name',
                    aggfunc='first'
                )
                
                # Flatten column names
                pivot_df.columns = [f"{col[1]}_{col[0]}" if col[1] != 'assessment_name' else col[0] 
                                  for col in pivot_df.columns]
            except Exception as e:
                logger.error(f"Pivot table operation failed: {e}")
                # Fallback: use groupby instead
                pivot_df = combined_df.groupby(user_id_col).first().reset_index()
            
            # Reset index to make user_id a column
            pivot_df = pivot_df.reset_index()
            
            # Filter to only include users who answered all assessments in the group
            # Check which users have data for all assessments
            users_with_all_assessments = []
            for user_id in pivot_df[user_id_col]:
                has_all_assessments = True
                for assessment_name in assessment_names:
                    # Check if user has any data for this assessment
                    assessment_cols = [col for col in pivot_df.columns if col.startswith(f"{assessment_name}_")]
                    if assessment_cols:
                        # Check if user has any non-null values for this assessment
                        user_data = pivot_df[pivot_df[user_id_col] == user_id][assessment_cols]
                        if user_data.empty or user_data.isnull().all().all():
                            has_all_assessments = False
                            break
                    else:
                        has_all_assessments = False
                        break
                
                if has_all_assessments:
                    users_with_all_assessments.append(user_id)
            
            # Filter the dataframe to only include users with all assessments
            pivot_df = pivot_df[pivot_df[user_id_col].isin(users_with_all_assessments)]
            
            logger.info(f"Filtered to {len(users_with_all_assessments)} users who answered all {len(assessment_names)} assessments")
            logger.info(f"Original users: {len(combined_df[user_id_col].unique())}, Filtered users: {len(users_with_all_assessments)}")
            
            # Reorder columns: user info first, then by assessment and question number
            pivot_df = self._reorder_columns(pivot_df, assessment_names)
            
            # Save combined file
            if self.output_format.lower() == 'xlsx':
                output_path = self.reports_dir / f"{group_name}_combined.xlsx"
                self.storage.write_excel(str(output_path), pivot_df, index=False)
            else:
                output_path = self.reports_dir / f"{group_name}_combined.csv"
                self.storage.write_csv(str(output_path), pivot_df, sep=';', index=False)
            
            logger.info(f"Combined assessment data saved to {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Failed to join assessments for group {group_name}: {e}")
            return None
    
    def _reorder_columns(self, df: pd.DataFrame, assessment_names: List[str]) -> pd.DataFrame:
        """
        Reorder columns to put user info first, then assessment questions ordered by test and question number
        
        Args:
            df: DataFrame to reorder
            assessment_names: List of assessment names in order
            
        Returns:
            DataFrame with reordered columns
        """
        import re
        
        # Separate user info columns from question columns
        user_cols = []
        question_cols = []
        
        # Define user info column names (these are the same across all assessments)
        user_info_names = ['id', 'user_id', 'email', 'grade', 'passed', 'created', 'modified', 
                          'submittedTimestamp', 'answers', 'generalFeedback']
        
        for col in df.columns:
            # Check if this is a question column (numeric or "Pregunta X")
            is_question_col = False
            
            for assessment_name in assessment_names:
                if col.startswith(f"{assessment_name}_"):
                    # Extract the part after assessment name
                    suffix = col[len(f"{assessment_name}_"):]
                    
                    # Check if it's a question (numeric or "Pregunta X")
                    if (suffix.isdigit() or  # Numeric question like "1", "2", "3"
                        suffix.lower().startswith('pregunta')):  # "Pregunta 1", "Pregunta 2", etc.
                        is_question_col = True
                        break
            
            if is_question_col:
                question_cols.append(col)
            else:
                user_cols.append(col)
        
        # Sort question columns by assessment order and question number
        def question_sort_key(col):
            # Extract assessment name and question from column
            for i, assessment_name in enumerate(assessment_names):
                if col.startswith(f"{assessment_name}_"):
                    question_part = col[len(f"{assessment_name}_"):]
                    
                    # Handle numeric questions (like "1", "2", "3")
                    if question_part.isdigit():
                        question_num = int(question_part)
                        return (i, question_num)
                    
                    # Handle "Pregunta X" format
                    match = re.search(r'pregunta\s*(\d+)', question_part.lower())
                    if match:
                        question_num = int(match.group(1))
                        return (i, question_num)
                    
                    # If no question number found, put at the end of this assessment
                    return (i, 999)
            # If no assessment found, put at the very end
            return (999, 999)
        
        # Sort question columns
        question_cols.sort(key=question_sort_key)
        
        # Sort user columns according to the specified order in user_info_names
        # First, separate base user columns from prefixed user columns
        base_user_cols = []
        prefixed_user_cols = []
        
        for col in user_cols:
            # Check if it's a base user column (not prefixed with assessment name)
            is_prefixed = any(col.startswith(f"{assessment_name}_") for assessment_name in assessment_names)
            if is_prefixed:
                prefixed_user_cols.append(col)
            else:
                base_user_cols.append(col)
        
        # Sort base user columns according to user_info_names order
        sorted_base_user_cols = []
        for info_name in user_info_names:
            for col in base_user_cols:
                if col == info_name:
                    sorted_base_user_cols.append(col)
                    break
        
        # Add any remaining base user columns that weren't in user_info_names
        for col in base_user_cols:
            if col not in sorted_base_user_cols:
                sorted_base_user_cols.append(col)
        
        # Sort prefixed user columns by assessment order and then by user_info_names order
        def prefixed_sort_key(col):
            # First, get assessment index
            assessment_index = next((i for i, name in enumerate(assessment_names) if col.startswith(f"{name}_")), 999)
            
            # Extract the suffix (the part after assessment name)
            for assessment_name in assessment_names:
                if col.startswith(f"{assessment_name}_"):
                    suffix = col[len(f"{assessment_name}_"):]
                    # Find the position of this suffix in user_info_names
                    try:
                        suffix_index = user_info_names.index(suffix)
                        return (assessment_index, suffix_index)
                    except ValueError:
                        # If suffix not in user_info_names, put it at the end
                        return (assessment_index, 999)
            
            return (999, 999)
        
        prefixed_user_cols.sort(key=prefixed_sort_key)
        
        # Combine: sorted base user columns + prefixed user columns + question columns
        ordered_cols = sorted_base_user_cols + prefixed_user_cols + question_cols
        
        logger.info(f"Column ordering: {len(sorted_base_user_cols)} base user cols, {len(prefixed_user_cols)} prefixed user cols, {len(question_cols)} question cols")
        logger.info(f"Base user cols order: {sorted_base_user_cols}")
        logger.info(f"First few question cols: {question_cols[:5]}")
        
        return df[ordered_cols]
    
    def upload_to_drive(self, file_path: str, group_name: str) -> Optional[str]:
        """
        Upload combined file to Google Drive
        
        Args:
            file_path: Path to the file to upload
            group_name: Name of the assessment group
            
        Returns:
            Drive file ID if successful, None otherwise
        """
        try:
            if not self.should_upload_to_drive:
                logger.info("Skipping Drive upload (upload_to_drive=False)")
                return None
                
            if not self.drive_service:
                logger.warning("Google Drive service not available")
                return None
            
            # Create folder structure
            base_folder_name = self.drive_folder_name
            subfolder_name = self.drive_subfolder
            
            # Find or create base folder
            base_folder_id = self.drive_service.find_or_create_folder(
                self.drive_service.base_folder_id, 
                base_folder_name
            )
            
            if not base_folder_id:
                logger.error(f"Could not create base folder: {base_folder_name}")
                return None
            
            # Find or create subfolder
            subfolder_id = self.drive_service.find_or_create_folder(
                base_folder_id, 
                subfolder_name
            )
            
            if not subfolder_id:
                logger.error(f"Could not create subfolder: {subfolder_name}")
                return None
            
            # Upload file
            file_name = f"{group_name}_combined_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{self.output_format}"
            
            if self.storage.backend == 'local':
                file_id = self.drive_service.upload_file(
                    file_path, 
                    file_name, 
                    subfolder_id
                )
            else:
                # For GCS, we need to download first
                with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                    file_data = self.storage.read_bytes(file_path)
                    tmp_file.write(file_data)
                    tmp_file.flush()
                    
                    file_id = self.drive_service.upload_file(
                        tmp_file.name, 
                        file_name, 
                        subfolder_id
                    )
                    
                    # Clean up temp file
                    os.unlink(tmp_file.name)
            
            if file_id:
                logger.info(f"File uploaded to Drive with ID: {file_id}")
                return file_id
            else:
                logger.error("Failed to upload file to Drive")
                return None
                
        except Exception as e:
            logger.error(f"Failed to upload file to Drive: {e}")
            return None
    
    def send_slack_notification(self, group_name: str, file_path: str, drive_file_id: Optional[str] = None, success: bool = True):
        """
        Send Slack notification about the processing results
        
        Args:
            group_name: Name of the assessment group
            file_path: Path to the generated file
            drive_file_id: Google Drive file ID if uploaded
            success: Whether the processing was successful
        """
        try:
            if not self.should_send_slack:
                logger.info("Skipping Slack notification (send_slack=False)")
                return
                
            if not self.slack_service:
                logger.warning("Slack service not available")
                return
            
            channel = self.slack_channel
            
            if success:
                if self.notify_on_success:
                    message = f"✅ Assessment processing completed successfully!\n"
                    message += f"• Group: {group_name}\n"
                    message += f"• File: {Path(file_path).name}\n"
                    
                    if drive_file_id:
                        drive_link = f"https://drive.google.com/file/d/{drive_file_id}/view"
                        message += f"• Drive: {drive_link}\n"
                    
                    message += f"• Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    
                    self.slack_service.send_message(message, channel)
            else:
                if self.notify_on_error:
                    message = f"❌ Assessment processing failed!\n"
                    message += f"• Group: {group_name}\n"
                    message += f"• Error: Check logs for details\n"
                    message += f"• Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    
                    self.slack_service.send_message(message, channel)
                    
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
    
    def process_individual_assessments(self) -> bool:
        """Process individual assessments"""
        if not self.process_individual:
            logger.info("Skipping individual assessments (process_individual=False)")
            return True
        
        individual_assessments = self.config['course']['assessments']['individual']
        success_count = 0
        
        for assessment in individual_assessments:
            assessment_name = assessment['name']
            assessment_id = assessment['id']
            
            # Download
            if self.download_assessment(assessment_name, assessment_id):
                # Process
                if self.process_assessment(assessment_name):
                    success_count += 1
                    logger.info(f"Successfully processed individual assessment: {assessment_name}")
                else:
                    logger.error(f"Failed to process assessment: {assessment_name}")
            else:
                logger.error(f"Failed to download assessment: {assessment_name}")
        
        logger.info(f"Processed {success_count}/{len(individual_assessments)} individual assessments")
        return success_count == len(individual_assessments)
    
    def process_grouped_assessments(self) -> bool:
        """Process grouped assessments"""
        if not self.process_grouped:
            logger.info("Skipping grouped assessments (process_grouped=False)")
            return True
        
        grouped_assessments = self.config['course']['assessments']['grouped']
        success_count = 0
        
        for group_key, group_config in grouped_assessments.items():
            group_name = group_config['name']
            assessments = group_config['assessments']
            assessment_names = [a['name'] for a in assessments]
            assessment_ids = [a['id'] for a in assessments]
            
            logger.info(f"Processing grouped assessment: {group_name}")
            
            # Download all assessments in the group
            download_success = True
            for assessment_name, assessment_id in zip(assessment_names, assessment_ids):
                if not self.download_assessment(assessment_name, assessment_id):
                    download_success = False
                    break
            
            if not download_success:
                logger.error(f"Failed to download assessments for group: {group_name}")
                continue
            
            # Process all assessments in the group
            process_success = True
            for assessment_name in assessment_names:
                if not self.process_assessment(assessment_name):
                    process_success = False
                    break
            
            if not process_success:
                logger.error(f"Failed to process assessments for group: {group_name}")
                continue
            
            # Join assessments by user
            combined_file_path = self.join_assessments_by_user(group_name, assessment_names)
            
            if combined_file_path:
                # Upload to Drive
                drive_file_id = self.upload_to_drive(combined_file_path, group_name)
                
                # Send Slack notification
                self.send_slack_notification(group_name, combined_file_path, drive_file_id, success=True)
                
                success_count += 1
                logger.info(f"Successfully processed grouped assessment: {group_name}")
            else:
                logger.error(f"Failed to join assessments for group: {group_name}")
                self.send_slack_notification(group_name, "", None, success=False)
        
        logger.info(f"Processed {success_count}/{len(grouped_assessments)} grouped assessments")
        return success_count == len(grouped_assessments)
    
    def run(self) -> bool:
        """
        Run the complete multi-assessment processing workflow
        
        Returns:
            True if all processing was successful, False otherwise
        """
        try:
            logger.info("Starting multi-assessment processing workflow")
            
            # Process individual assessments
            individual_success = self.process_individual_assessments()
            
            # Process grouped assessments
            grouped_success = self.process_grouped_assessments()
            
            overall_success = individual_success and grouped_success
            
            if overall_success:
                logger.info("Multi-assessment processing completed successfully")
            else:
                logger.error("Multi-assessment processing completed with errors")
            
            return overall_success
            
        except Exception as e:
            logger.error(f"Multi-assessment processing failed: {e}")
            return False

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Process multiple assessments with user joining')
    parser.add_argument('--no-upload', action='store_true', help='Skip uploading files to Google Drive')
    parser.add_argument('--no-slack', action='store_true', help='Skip sending Slack notifications')
    
    args = parser.parse_args()
    
    config_path = "assessments_config.yml"
    
    if not os.path.exists(config_path):
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)
    
    # Run the processor
    upload_to_drive = not args.no_upload
    send_slack = not args.no_slack
    
    processor = MultiAssessmentProcessor(config_path, upload_to_drive=upload_to_drive, send_slack=send_slack)
    success = processor.run()
    
    if success:
        logger.info("Processing completed successfully")
        sys.exit(0)
    else:
        logger.error("Processing completed with errors")
        sys.exit(1)

if __name__ == "__main__":
    main()
