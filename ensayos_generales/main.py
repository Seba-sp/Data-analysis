#!/usr/bin/env python3
"""
Main application for diagnosticos project
Handles data download, processing, and report generation
"""

import os
import logging
import argparse
import pandas as pd
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

from assessment_downloader import AssessmentDownloader
from assessment_analyzer import AssessmentAnalyzer
from report_generator import ReportGenerator
from storage import StorageClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)





class DiagnosticosApp:
    def __init__(self):
        """Initialize the diagnosticos application"""
        self.storage = StorageClient()
        self.downloader = AssessmentDownloader()
        self.analyzer = AssessmentAnalyzer()
        self.report_generator = ReportGenerator()
        
        # Assessment types
        self.assessment_types = ["M1", "M2", "CL", "CIENB", "CIENF", "CIENQ", "CIENT", "HYST"]
        
        # File naming configuration
        self.report_filename_prefix = "resultados_"
        self.report_filename_suffix = ".pdf"
        self.assessment_name_suffix = ""  # Can be set to assessment type if needed
    
    def _generate_report_filename(self, email: str = None, username: str = None, assessment_type: str = None) -> str:
        """
        Generate a standardized report filename
        
        Args:
            email: Student's email address (preferred for filename)
            username: Student's username (fallback if no email)
            assessment_type: Optional assessment type to append to filename
            
        Returns:
            Generated filename string
        """
        # Use email if available, otherwise use username
        identifier = email if email and email.strip() else username
        
        if not identifier:
            raise ValueError("Either email or username must be provided")
        
        # Clean the identifier (remove any invalid filename characters)
        import re
        clean_identifier = re.sub(r'[<>:"/\\|?*]', '_', str(identifier).strip())
        
        # Build filename components
        filename_parts = [self.report_filename_prefix, clean_identifier]
        
        # Add assessment type suffix if specified
        if assessment_type and self.assessment_name_suffix:
            filename_parts.append(self.assessment_name_suffix)
        elif assessment_type:
            filename_parts.append(f"_{assessment_type}")
        
        # Add file extension
        filename_parts.append(self.report_filename_suffix)
        
        return ''.join(filename_parts)
    
    def _get_assessment_list(self) -> List[Dict[str, str]]:
        """Get list of assessments from environment variables"""
        assessments = []
        assessment_ids = {
            'M1': os.getenv("M1_ASSESSMENT_ID"),
            'M2': os.getenv("M2_ASSESSMENT_ID"),
            'CL': os.getenv("CL_ASSESSMENT_ID"),
            'CIENB': os.getenv("CIENB_ASSESSMENT_ID"),
            'CIENF': os.getenv("CIENF_ASSESSMENT_ID"),
            'CIENQ': os.getenv("CIENQ_ASSESSMENT_ID"),
            'CIENT': os.getenv("CIENT_ASSESSMENT_ID"),
            'HYST': os.getenv("HYST_ASSESSMENT_ID")
        }
        
        for name, assessment_id in assessment_ids.items():
            if assessment_id:
                assessments.append({'name': name, 'assessment_id': assessment_id})
        
        return assessments
    
    def _filter_assessments(self, assessments: List[Dict[str, str]], assessment_type: Optional[str] = None) -> List[Dict[str, str]]:
        """Filter assessments by type if specified"""
        if assessment_type:
            return [a for a in assessments if a['name'] == assessment_type]
        return assessments
    
    def _get_assessment_types_to_process(self, assessment_type: Optional[str] = None) -> List[str]:
        """Get list of assessment types to process"""
        if assessment_type:
            return [assessment_type]
        return self.assessment_types
    
    def _log_operation_start(self, operation: str, incremental_mode: bool, assessment_type: Optional[str] = None):
        """Log the start of an operation"""
        mode = "incremental" if incremental_mode else "full"
        if assessment_type:
            logger.info(f"Starting {mode} {operation} for {assessment_type}")
        else:
            logger.info(f"Starting {mode} {operation} of all assessments")
    
    def _log_operation_complete(self, operation: str, incremental_mode: bool, count: int, additional_info: str = ""):
        """Log the completion of an operation"""
        mode = "incremental" if incremental_mode else "full"
        logger.info(f"{mode.capitalize()} {operation} complete. {count} assessments processed{additional_info}")
    
    def _get_file_path(self, base_path: str, assessment_type: str, incremental_mode: bool, temp_prefix: str = "temp_") -> str:
        """Generate file path with optional temp prefix for incremental mode"""
        if incremental_mode:
            return f"{base_path}/{temp_prefix}{assessment_type}.csv"
        return f"{base_path}/{assessment_type}.csv"
    

    
    def download_all_assessments(self, incremental_mode: bool = False, assessment_type: str = None) -> Dict[str, Any]:
        """
        Download all assessments or specific assessment
        
        Args:
            incremental_mode: If True, use incremental processing mode
            assessment_type: Optional specific assessment type to download
            
        Returns:
            Dict with download results
        """
        results = {
            "success": True,
            "assessments_downloaded": 0,
            "incremental_count": 0,
            "errors": [],
            "downloaded_data": {}
        }
        
        try:
            self._log_operation_start("download", incremental_mode, assessment_type)
            
            # Get and filter assessments
            assessments = self._get_assessment_list()
            if not assessments:
                return {"success": False, "error": "No assessment IDs found in environment variables"}
            
            assessments = self._filter_assessments(assessments, assessment_type)
            
            # Download assessments
            for assessment in assessments:
                name = assessment['name']
                assessment_id = assessment['assessment_id']
                
                try:
                    downloaded_df = self.downloader.get_only_new_responses(
                        assessment_id, name, return_df=True
                    )
                    
                    if not downloaded_df.empty:
                        results["downloaded_data"][name] = downloaded_df
                        results["assessments_downloaded"] += 1
                        results["incremental_count"] += len(downloaded_df)
                        logger.info(f"Successfully downloaded {name}: {len(downloaded_df)} new responses")
                    else:
                        logger.info(f"No new responses found for {name}")
                    
                except Exception as e:
                    error_msg = f"Failed to download {name}: {str(e)}"
                    results["errors"].append(error_msg)
                    logger.error(error_msg)
            
            results["success"] = not bool(results["errors"])
            self._log_operation_complete("download", incremental_mode, results["assessments_downloaded"], 
                                       f", {results['incremental_count']} total responses")
            return results
            
        except Exception as e:
            logger.error(f"Error in download_all_assessments: {str(e)}")
            return {"success": False, "assessments_downloaded": 0, "incremental_count": 0, 
                   "errors": [str(e)], "downloaded_data": {}}
    
    def process_all_assessments(self, incremental_mode: bool = False, assessment_type: str = None, 
                               downloaded_data: Dict[str, pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Process all assessments or specific assessment (convert JSON to CSV and analyze)
        
        Args:
            incremental_mode: If True, use incremental processing mode
            assessment_type: Optional specific assessment type to process
            downloaded_data: Optional dictionary with downloaded DataFrames
            
        Returns:
            Dict with processing results
        """
        results = {
            "success": True,
            "assessments_processed": 0,
            "errors": [],
            "processed_data": {}
        }
        
        try:
            self._log_operation_start("processing", incremental_mode, assessment_type)
            
            # Ensure users are available for username lookup
            try:
                users = self.downloader.load_users_from_json()
                if not users:
                    logger.warning("No users found. Downloading users first...")
                    users = self.downloader.download_users()
                    if not users:
                        logger.error("Failed to download users. Processing will continue without usernames.")
                else:
                    logger.info(f"Loaded {len(users)} users for username lookup")
            except Exception as e:
                logger.warning(f"Error loading users: {str(e)}. Processing will continue without usernames.")
            
            assessment_types = self._get_assessment_types_to_process(assessment_type)
            
            for assessment_name in assessment_types:
                try:
                    if downloaded_data and assessment_name in downloaded_data:
                        # Use provided downloaded data
                        downloaded_df = downloaded_data[assessment_name]
                        logger.info(f"Processing {assessment_name} from provided data: {len(downloaded_df)} responses")
                        
                        processed_df = self.downloader.save_responses_to_csv(
                            downloaded_df, assessment_name, return_df=True, include_usernames=True
                        )
                        
                        results["processed_data"][assessment_name] = processed_df
                        results["assessments_processed"] += 1
                        logger.info(f"Successfully processed {assessment_name}: {len(processed_df)} filtered responses")
                        
                    else:
                        # Use file-based approach
                        logger.info(f"Processing {assessment_name} from files")
                        responses = self.downloader.load_responses_from_json(assessment_name)
                        
                        if responses:
                            processed_df = self.downloader.save_responses_to_csv(
                                responses, assessment_name, return_df=True, include_usernames=True
                            )
                            results["processed_data"][assessment_name] = processed_df
                            results["assessments_processed"] += 1
                            logger.info(f"Successfully processed {assessment_name}: {len(processed_df)} filtered responses")
                        else:
                            results["errors"].append(f"No data found for {assessment_name}")
                            
                except Exception as e:
                    error_msg = f"Failed to process {assessment_name}: {str(e)}"
                    results["errors"].append(error_msg)
                    logger.error(error_msg)
            
            results["success"] = not bool(results["errors"])
            self._log_operation_complete("processing", incremental_mode, results["assessments_processed"])
            return results
            
        except Exception as e:
            logger.error(f"Error in process_all_assessments: {str(e)}")
            return {"success": False, "assessments_processed": 0, "errors": [str(e)], "processed_data": {}}
    
    def analyze_all_assessments(self, incremental_mode: bool = False, assessment_type: str = None, 
                               processed_data: Dict[str, pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Analyze all assessments or specific assessment (generate analysis CSV files)
        
        Args:
            incremental_mode: If True, use incremental processing mode
            assessment_type: Optional specific assessment type to analyze
            processed_data: Optional dictionary with processed DataFrames
            
        Returns:
            Dict with analysis results
        """
        results = {
            "success": True,
            "assessments_analyzed": 0,
            "errors": [],
            "analysis_data": {}
        }
        
        try:
            self._log_operation_start("analysis", incremental_mode, assessment_type)
            
            assessment_types = self._get_assessment_types_to_process(assessment_type)
            
            for assessment_type in assessment_types:
                try:
                    analysis_result = self.analyze_assessment(assessment_type, incremental_mode, processed_data)
                    if not analysis_result["success"]:
                        results["errors"].append(f"Failed to analyze {assessment_type}: {analysis_result['error']}")
                        continue
                    
                    results["assessments_analyzed"] += 1
                    if "analysis_df" in analysis_result:
                        results["analysis_data"][assessment_type] = analysis_result["analysis_df"]
                    logger.info(f"Successfully analyzed {assessment_type}")
                    
                except Exception as e:
                    error_msg = f"Error analyzing {assessment_type}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            results["success"] = not bool(results["errors"])
            self._log_operation_complete("analysis", incremental_mode, results["assessments_analyzed"])
            return results
            
        except Exception as e:
            logger.error(f"Error in analyze_all_assessments: {str(e)}")
            return {"success": False, "assessments_analyzed": 0, "errors": [str(e)], "analysis_data": {}}
    
    def analyze_assessment(self, assessment_type: str, incremental_mode: bool = False, 
                          processed_data: Dict[str, pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Analyze a specific assessment type
        
        Args:
            assessment_type: Type of assessment (M1, CL, CIEN, HYST)
            incremental_mode: If True, use temporary files for analysis
            processed_data: Optional dictionary with processed DataFrames
            
        Returns:
            Dict with analysis results
        """
        results = {"success": True, "error": None}
        
        try:
            self._log_operation_start("analysis", incremental_mode, assessment_type)
            
            # Define file paths
            question_bank_path = f"data/questions/{assessment_type}.csv"
            output_path = self._get_file_path("data/analysis", assessment_type, incremental_mode)
            
            # Check if question bank file exists
            if not self.storage.exists(question_bank_path):
                results["success"] = False
                results["error"] = f"Question bank file not found: {question_bank_path}"
                return results
            
            # Determine input data source
            if processed_data and assessment_type in processed_data:
                processed_csv_path = processed_data[assessment_type]
                logger.info(f"Using provided processed data for {assessment_type}: {len(processed_csv_path)} records")
            else:
                processed_csv_path = self._get_file_path("data/processed", assessment_type, incremental_mode)
                
                if not self.storage.exists(processed_csv_path):
                    error_msg = f"{'Temporary' if incremental_mode else 'Processed'} CSV file not found: {processed_csv_path}"
                    if incremental_mode:
                        error_msg += ". This may indicate no new data was found to process."
                    results["success"] = False
                    results["error"] = error_msg
                    return results
            
            # Ensure analysis directory exists
            self.storage.ensure_directory("data/analysis")
            
            # Analyze assessment
            if processed_data and assessment_type in processed_data:
                analysis_df = self.analyzer.analyze_assessment_from_csv(
                    assessment_type, question_bank_path, processed_csv_path, output_path, return_df=True
                )
                results["analysis_df"] = analysis_df
                logger.info(f"Analysis completed for {assessment_type}. Generated DataFrame with {len(analysis_df)} records")
            else:
                output_file = self.analyzer.analyze_assessment_from_csv(
                    assessment_type, question_bank_path, processed_csv_path, output_path
                )
                logger.info(f"Analysis completed for {assessment_type}. Output: {output_file}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error analyzing assessment {assessment_type}: {str(e)}")
            results["success"] = False
            results["error"] = str(e)
            return results
    
    def merge_incremental_data(self, assessment_type: str = None, 
                              downloaded_data: Dict[str, pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Merge incremental data into main JSON files
        
        Args:
            assessment_type: Optional specific assessment type to merge
            downloaded_data: Optional dictionary with downloaded DataFrames
            
        Returns:
            Dict with merge results
        """
        results = {
            "success": True,
            "assessments_merged": 0,
            "errors": []
        }
        
        try:
            assessment_types = self._get_assessment_types_to_process(assessment_type)
            logger.info(f"Merging incremental data for {len(assessment_types)} assessment(s)")
            
            for assessment_type in assessment_types:
                try:
                    if downloaded_data and assessment_type in downloaded_data:
                        success = self.downloader.merge_incremental_to_main_json(assessment_type, downloaded_data[assessment_type])
                    else:
                        success = self.downloader.merge_incremental_to_main_json(assessment_type)
                    
                    if success:
                        results["assessments_merged"] += 1
                    else:
                        results["errors"].append(f"Failed to merge incremental data for {assessment_type}")
                except Exception as e:
                    error_msg = f"Error merging incremental data for {assessment_type}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            results["success"] = not bool(results["errors"])
            logger.info(f"Merge complete. {results['assessments_merged']} assessments merged")
            return results
            
        except Exception as e:
            logger.error(f"Error in merge_incremental_data: {str(e)}")
            return {"success": False, "assessments_merged": 0, "errors": [str(e)]}
    
    def cleanup_temp_files(self, assessment_type: str = None) -> Dict[str, Any]:
        """
        Clean up temporary files for assessments
        
        Args:
            assessment_type: Optional specific assessment type to clean up
            
        Returns:
            Dict with cleanup results
        """
        results = {
            "success": True,
            "files_cleaned": 0,
            "errors": []
        }
        
        try:
            assessment_types = self._get_assessment_types_to_process(assessment_type)
            logger.info(f"Cleaning up temporary files for {len(assessment_types)} assessment(s)")
            
            for assessment_type in assessment_types:
                try:
                    success = self.downloader.cleanup_temp_files(assessment_type)
                    if success:
                        results["files_cleaned"] += 1
                    else:
                        results["errors"].append(f"Failed to cleanup temp files for {assessment_type}")
                except Exception as e:
                    error_msg = f"Error cleaning up temp files for {assessment_type}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            # Consider cleanup successful if at least some files were cleaned and no critical errors
            results["success"] = results["files_cleaned"] > 0 and not results["errors"]
            logger.info(f"Cleanup complete. {results['files_cleaned']} assessments cleaned")
            return results
            
        except Exception as e:
            logger.error(f"Error in cleanup_temp_files: {str(e)}")
            return {"success": False, "files_cleaned": 0, "errors": [str(e)]}
    
    def check_existing_reports(self, assessment_type: str = None) -> Dict[str, Any]:
        """
        Check for existing PDF reports in the reports folder
        
        Args:
            assessment_type: Optional specific assessment type to check
            
        Returns:
            Dict with information about existing reports
        """
        results = {
            "total_reports": 0,
            "reports_by_type": {},
            "existing_files": []
        }
        
        try:
            self.storage.ensure_directory("reports")
            
            if self.storage.exists("reports"):
                all_files = self.storage.list_files("reports")
                pdf_files = [
                    filename for filename in all_files
                    if filename.endswith(self.report_filename_suffix) and os.path.basename(filename).startswith(self.report_filename_prefix)
                ]
                
                # Since the new naming pattern uses the configured prefix and suffix,
                # we don't filter by assessment type anymore as each report contains all assessments
                # Just add all PDF files to the existing files list
                for filename in pdf_files:
                    # Extract just the filename from the full path
                    basename = os.path.basename(filename)
                    results["total_reports"] += 1
                    results["existing_files"].append(basename)
                
                # For compatibility, we'll count all reports as "comprehensive" type
                if results["total_reports"] > 0:
                    results["reports_by_type"]["comprehensive"] = results["total_reports"]
                
                logger.info(f"Found {results['total_reports']} existing PDF reports")
                for assessment_type, count in results["reports_by_type"].items():
                    logger.info(f"  - {assessment_type}: {count} reports")
            
            return results
            
        except Exception as e:
            logger.error(f"Error checking existing reports: {str(e)}")
            return results


    



    def generate_reports(self, skip_existing: bool = True) -> Dict[str, Any]:
        """
        Generate comprehensive reports for all students using the new simplified system
        
        Args:
            skip_existing: If True, skip generation of reports that already exist
            
        Returns:
            Dict with report generation results
        """
        results = {
            "success": True,
            "reports_generated": 0,
            "reports_skipped": 0,
            "errors": []
        }
        
        try:
            logger.info("Starting comprehensive report generation for all students")
            
            # Load analysis data to get all usernames
            analysis_file = "data/analysis/analysis.csv"
            
            if not self.storage.exists(analysis_file):
                error_msg = f"No analysis data found at {analysis_file}"
                results["success"] = False
                results["error"] = error_msg
                return results
            
            # Use pandas directly to read the CSV file
            try:
                import pandas as pd
                analysis_df = pd.read_csv(analysis_file, sep=',')
                if analysis_df.empty:
                    error_msg = f"No analysis data found in {analysis_file}"
                    results["success"] = False
                    results["error"] = error_msg
                    return results
                logger.info(f"Successfully loaded analysis data with pandas. DataFrame shape: {analysis_df.shape}")
                logger.info(f"Columns: {list(analysis_df.columns)}")
            except Exception as e:
                error_msg = f"Failed to read analysis file: {str(e)}"
                results["success"] = False
                results["error"] = error_msg
                return results
            
            logger.info(f"Found {len(analysis_df)} students in analysis file")
            logger.info(f"Analysis file columns: {list(analysis_df.columns)}")
            logger.info(f"First few rows sample:")
            for i, row in analysis_df.head(3).iterrows():
                logger.info(f"Row {i}: {dict(row)}")
            
            # Ensure reports directory exists
            self.storage.ensure_directory("reports")
            
            # Check existing reports if skip_existing is True
            existing_reports = {}
            if skip_existing:
                existing_reports = self.check_existing_reports()
                logger.info(f"Found {existing_reports['total_reports']} existing reports")
                if existing_reports['existing_files']:
                    logger.info(f"Existing report files: {existing_reports['existing_files'][:5]}{'...' if len(existing_reports['existing_files']) > 5 else ''}")
            else:
                logger.info("Force mode enabled - will regenerate all reports")
            
            existing_files = set(existing_reports.get("existing_files", [])) if existing_reports else set()
            
            # Generate reports for each student
            for _, row in analysis_df.iterrows():
                try:
                    # Try to find the username from various possible column names
                    username = None
                    username_columns = ['username', 'email', 'user', 'student', 'estudiante']
                    
                    for col in username_columns:
                        if col in row and pd.notna(row[col]) and str(row[col]).strip():
                            username = str(row[col]).strip()
                            break
                    
                    if not username:
                        logger.warning(f"Skipping row with no valid username: {dict(row)}")
                        continue
                    
                    # Get email from analysis data for filename
                    email = None
                    if 'email' in row and pd.notna(row['email']) and str(row['email']).strip():
                        email = str(row['email']).strip()
                    
                    # Generate standardized filename
                    filename = self._generate_report_filename(email=email, username=username)
                    
                    # Check if report already exists
                    if skip_existing and filename in existing_files:
                        results["reports_skipped"] += 1
                        logger.info(f"Skipping existing report: {filename}")
                        continue
                    
                    # Generate comprehensive PDF report using the new simplified generator
                    pdf_content = self.report_generator.generate_report(username)
                    
                    if pdf_content:
                        pdf_path = f"reports/{filename}"
                        if self.storage.write_bytes(pdf_path, pdf_content):
                            results["reports_generated"] += 1
                            logger.info(f"Generated comprehensive report: {filename}")
                        else:
                            logger.error(f"Failed to save report: {filename}")
                            results["errors"].append(f"Failed to save report for {username}")
                    
                except Exception as e:
                    logger.error(f"Error generating report for student {username if 'username' in locals() else 'unknown'}: {str(e)}")
                    results["errors"].append(f"Error for {username if 'username' in locals() else 'unknown'}: {str(e)}")
            
            results["success"] = not bool(results["errors"])
            logger.info(f"Comprehensive report generation complete. {results['reports_generated']} reports generated, {results['reports_skipped']} reports skipped")
            if results["errors"]:
                logger.warning(f"Encountered {len(results['errors'])} errors during report generation")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in comprehensive report generation: {str(e)}")
            return {
                "success": False, "reports_generated": 0, "reports_skipped": 0, "errors": [str(e)]
            }


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Diagnosticos - Assessment Processing and Reporting")
    parser.add_argument("--download", action="store_true", help="Download assessment data")
    parser.add_argument("--process", action="store_true", help="Process assessments (convert JSON to CSV)")
    parser.add_argument("--analyze", action="store_true", help="Analyze assessments (generate analysis CSV)")
    parser.add_argument("--reports", action="store_true", help="Generate comprehensive reports for all students using new system")
    parser.add_argument("--check-reports", action="store_true", help="Check existing PDF reports in reports folder")
    parser.add_argument("--force-reports", action="store_true", help="Force generation of all reports (don't skip existing)")
    parser.add_argument("--assessment", choices=["M1", "M2", "CL", "CIENB", "CIENF", "CIENQ", "CIENT", "HYST"], help="Process specific assessment type")
    parser.add_argument("--incremental", action="store_true", help="Process only incremental data (for batch processing)")
    parser.add_argument("--full", action="store_true", help="Force full download (ignore incremental mode)")
    parser.add_argument("--cleanup", action="store_true", help="Clean up temporary files after processing")
    parser.add_argument("--download-users", action="store_true", help="Download users from LearnWorlds API")
    
    args = parser.parse_args()
    
    app = DiagnosticosApp()
    
    try:
        # Determine if we should use incremental mode
        incremental_mode = args.incremental and not args.full
        
        # Initialize in-memory data storage
        data_storage = {
            "downloaded_data": {},
            "processed_data": {},
            "analysis_data": {}
        }
        
        # Handle download-users command
        if args.download_users:
            logger.info("Downloading users from LearnWorlds API...")
            try:
                users = app.downloader.download_users()
                if users:
                    logger.info(f"Successfully downloaded {len(users)} users")
                    print(f"✅ Successfully downloaded {len(users)} users")
                    print(f"📁 Users saved to: data/raw/users.json")
                else:
                    logger.error("Failed to download users")
                    print("❌ Failed to download users")
                return
            except Exception as e:
                logger.error(f"Error downloading users: {str(e)}")
                print(f"❌ Failed to download users: {str(e)}")
                return
        
        # Define operations to perform
        operations = [
            ("download", args.download, app.download_all_assessments, "downloaded_data"),
            ("process", args.process, app.process_all_assessments, "processed_data"),
            ("analyze", args.analyze, app.analyze_all_assessments, "analysis_data"),
        ]
        
        # Execute operations
        for operation_name, should_execute, operation_func, data_key in operations:
            if should_execute:
                logger.info(f"{operation_name.capitalize()}ing assessment data{' in incremental mode' if incremental_mode else ''}...")
                
                # Prepare arguments for operation
                operation_args = {
                    "incremental_mode": incremental_mode,
                    "assessment_type": args.assessment
                }
                
                # Add data from previous operations if available
                if operation_name == "process" and data_storage["downloaded_data"]:
                    operation_args["downloaded_data"] = data_storage["downloaded_data"]
                elif operation_name == "analyze" and data_storage["processed_data"]:
                    operation_args["processed_data"] = data_storage["processed_data"]
                
                # Execute operation
                result = operation_func(**operation_args)
                
                if result["success"]:
                    # Map the correct data keys
                    if operation_name == "download":
                        data_storage[data_key] = result.get("downloaded_data", {})
                        count = result.get("assessments_downloaded", 0)
                        
                        # Check if no new data was found in incremental mode
                        if incremental_mode and count == 0:
                            logger.info("No new data found in incremental mode. Stopping processing.")
                            # Clear any subsequent operations that depend on new data
                            if args.process or args.analyze or args.reports:
                                logger.info("Skipping subsequent operations (process, analyze, reports) as no new data is available.")
                            break
                            
                    elif operation_name == "process":
                        data_storage[data_key] = result.get("processed_data", {})
                        count = result.get("assessments_processed", 0)
                    elif operation_name == "analyze":
                        data_storage[data_key] = result.get("analysis_data", {})
                        count = result.get("assessments_analyzed", 0)
                    else:
                        count = 0
                    
                    mode = "incremental" if incremental_mode else "full"
                    logger.info(f"{operation_name.capitalize()} completed successfully. {count} assessments processed")
                else:
                    logger.error(f"{operation_name.capitalize()} failed: {result.get('error', 'Unknown error')}")
                    for error in result.get('errors', []):
                        logger.error(f"  - {error}")
                    
                    # Stop processing if any operation fails in incremental mode
                    if incremental_mode:
                        logger.error(f"Stopping processing due to {operation_name} failure in incremental mode.")
                        break
        
        # Handle report checking
        if args.check_reports:
            logger.info("Checking existing reports...")
            result = app.check_existing_reports(args.assessment)
            
            logger.info(f"Found {result['total_reports']} total PDF reports")
            for assessment_type, count in result["reports_by_type"].items():
                logger.info(f"  - {assessment_type}: {count} reports")
            
            if result["existing_files"]:
                logger.info("Sample existing files:")
                for filename in result["existing_files"][:5]:
                    logger.info(f"  - {filename}")
                if len(result["existing_files"]) > 5:
                    logger.info(f"  ... and {len(result['existing_files']) - 5} more files")
        
        # Handle report generation
        if args.reports:
            logger.info("Generating comprehensive reports for all students...")
            skip_existing = not args.force_reports
            
            reports_result = app.generate_reports(skip_existing=skip_existing)
            
            if reports_result["success"]:
                logger.info(f"Report generation completed successfully. "
                          f"{reports_result.get('reports_generated', 0)} reports generated, "
                          f"{reports_result.get('reports_skipped', 0)} reports skipped")
                print(f"✅ Reports generated successfully!")
                print(f"📊 {reports_result.get('reports_generated', 0)} new reports generated")
                print(f"⏭️  {reports_result.get('reports_skipped', 0)} existing reports skipped")
            else:
                logger.error(f"Report generation failed: {reports_result.get('error', 'Unknown error')}")
                for error in reports_result.get('errors', []):
                    logger.error(f"  - {error}")
                print(f"❌ Report generation failed: {reports_result.get('error', 'Unknown error')}")
        

        
        # Handle incremental cleanup and merge
        if incremental_mode and any([args.download, args.process, args.analyze, args.reports]):
            # Check if we actually have new data to merge
            has_new_data = bool(data_storage["downloaded_data"])
            
            if not has_new_data:
                logger.info("No new data to merge. Skipping merge and cleanup operations.")
            else:
                should_merge = True
                if args.reports and 'reports_result' in locals():
                    total_reports_generated = reports_result.get('reports_generated', 0)
                    if total_reports_generated == 0:
                        logger.warning("No reports were generated. Skipping merge to avoid data loss.")
                        should_merge = False
                
                if should_merge:
                    logger.info("Merging incremental data into main JSON files...")
                    merge_result = app.merge_incremental_data(
                        assessment_type=args.assessment, 
                        downloaded_data=data_storage["downloaded_data"]
                    )
                    if merge_result["success"]:
                        logger.info(f"Merge completed successfully. {merge_result.get('assessments_merged', 0)} assessments merged")
                    else:
                        logger.warning(f"Merge had issues: {merge_result.get('errors', [])}")
                else:
                    logger.info("Skipping merge due to report generation issues")
                
                logger.info("Cleaning up temporary files after all processing...")
                cleanup_result = app.cleanup_temp_files(assessment_type=args.assessment)
                if cleanup_result["success"]:
                    logger.info(f"Cleanup completed successfully. {cleanup_result.get('files_cleaned', 0)} assessments cleaned")
                else:
                    logger.warning(f"Cleanup had issues: {cleanup_result.get('errors', [])}")
        elif incremental_mode:
            # If we're in incremental mode but no operations were executed (due to errors), log this
            logger.info("Incremental mode enabled but no operations completed successfully. Skipping merge and cleanup.")
        
        # Handle standalone cleanup
        if args.cleanup and not any([args.download, args.process, args.analyze, args.reports, args.check_reports]):
            logger.info("Cleaning up temporary files...")
            cleanup_result = app.cleanup_temp_files()
            if cleanup_result["success"]:
                logger.info(f"Cleanup completed successfully. {cleanup_result.get('files_cleaned', 0)} assessments cleaned")
            else:
                logger.error(f"Cleanup failed: {cleanup_result.get('errors', [])}")
        elif not any([args.download, args.process, args.analyze, args.reports, args.check_reports, args.cleanup]):
            parser.print_help()
    
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()
