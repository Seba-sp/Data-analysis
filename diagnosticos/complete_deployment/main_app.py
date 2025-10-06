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
from email_sender import EmailSender
from drive_service import DriveService

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
        self.email_sender = EmailSender()
        self.drive_service = DriveService()
        self.processed_emails_file = "processed_emails.csv"
        
        # Assessment types
        self.assessment_types = ["M1", "CL", "CIEN", "HYST"]
        
        # Log drive service status
        if self.drive_service.drive_service:
            logger.info("Google Drive service initialized successfully")
        else:
            logger.warning("Google Drive service not available - reports will not be saved to Drive")
    
    def _get_assessment_list(self) -> List[Dict[str, str]]:
        """Get list of assessments from environment variables"""
        assessments = []
        assessment_ids = {
            'M1': os.getenv("M1_ASSESSMENT_ID"),
            'CL': os.getenv("CL_ASSESSMENT_ID"),
            'CIEN': os.getenv("CIEN_ASSESSMENT_ID"),
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
    
    def _get_file_path(self, base_path: str, assessment_type: str) -> str:
        """Generate file path for assessment data"""
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
            
            assessment_types = self._get_assessment_types_to_process(assessment_type)
            
            for assessment_name in assessment_types:
                try:
                    if downloaded_data and assessment_name in downloaded_data:
                        # Use provided downloaded data
                        downloaded_df = downloaded_data[assessment_name]
                        logger.info(f"Processing {assessment_name} from provided data: {len(downloaded_df)} responses")
                        
                        processed_df = self.downloader.save_responses_to_csv(
                            downloaded_df, assessment_name, return_df=True
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
                                responses, assessment_name, return_df=True
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
            incremental_mode: If True, use in-memory processing for analysis
            processed_data: Optional dictionary with processed DataFrames
            
        Returns:
            Dict with analysis results
        """
        results = {"success": True, "error": None}
        
        try:
            self._log_operation_start("analysis", incremental_mode, assessment_type)
            
            # Define file paths
            question_bank_path = f"data/questions/{assessment_type}.csv"
            output_path = self._get_file_path("data/analysis", assessment_type)
            
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
                processed_csv_path = self._get_file_path("data/processed", assessment_type)
                
                if incremental_mode:
                    # In incremental mode, we should always use processed_data if available
                    results["success"] = False
                    results["error"] = f"No processed data provided for {assessment_type} in incremental mode"
                    return results
                elif not self.storage.exists(processed_csv_path):
                    error_msg = f"Processed CSV file not found: {processed_csv_path}"
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
    
    def cleanup_incremental_files(self, assessment_type: str = None) -> Dict[str, Any]:
        """
        Clean up incremental files for assessments
        
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
            logger.info(f"Cleaning up incremental files for {len(assessment_types)} assessment(s)")
            
            for assessment_type in assessment_types:
                try:
                    success = self.downloader.cleanup_incremental_files(assessment_type)
                    if success:
                        results["files_cleaned"] += 1
                    else:
                        results["errors"].append(f"Failed to cleanup incremental files for {assessment_type}")
                except Exception as e:
                    error_msg = f"Error cleaning up incremental files for {assessment_type}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            # Consider cleanup successful if at least some files were cleaned and no critical errors
            results["success"] = results["files_cleaned"] > 0 or not results["errors"]
            logger.info(f"Cleanup complete. {results['files_cleaned']} assessments cleaned")
            return results
            
        except Exception as e:
            logger.error(f"Error in cleanup_incremental_files: {str(e)}")
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
                pdf_files = [
                    filename for filename in os.listdir("reports")
                    if filename.endswith('.pdf') and filename.startswith('informe_')
                ]
                
                # Filter by assessment type if specified
                if assessment_type:
                    pdf_files = [f for f in pdf_files if f.endswith(f'_{assessment_type}.pdf')]
                
                # Count reports by assessment type
                for filename in pdf_files:
                    parts = filename.replace('.pdf', '').split('_')
                    if len(parts) >= 3:
                        file_assessment_type = parts[-1]
                        results["reports_by_type"][file_assessment_type] = results["reports_by_type"].get(file_assessment_type, 0) + 1
                        results["total_reports"] += 1
                        results["existing_files"].append(filename)
                
                logger.info(f"Found {results['total_reports']} existing PDF reports")
                for assessment_type, count in results["reports_by_type"].items():
                    logger.info(f"  - {assessment_type}: {count} reports")
            
            return results
            
        except Exception as e:
            logger.error(f"Error checking existing reports: {str(e)}")
            return results

    def generate_all_reports(self, skip_existing: bool = True, incremental_mode: bool = False, 
                            assessment_type: str = None, analysis_data: Dict[str, pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Generate reports for all assessments or specific assessment
        
        Args:
            skip_existing: If True, skip generation of reports that already exist
            incremental_mode: If True, use incremental processing mode
            assessment_type: Optional specific assessment type to generate reports for
            analysis_data: Optional dictionary with analysis DataFrames
            
        Returns:
            Dict with report generation results including all generated PDFs for incremental mode
        """
        results = {
            "success": True,
            "assessments_processed": 0,
            "reports_generated": 0,
            "reports_skipped": 0,
            "errors": [],
            "all_generated_pdfs": {}  # Collect all PDFs from all assessments
        }
        
        try:
            self._log_operation_start("report generation", incremental_mode, assessment_type)
            
            assessment_types = self._get_assessment_types_to_process(assessment_type)
            
            # Check existing reports if skip_existing is True
            existing_reports = {}
            if skip_existing:
                existing_reports = self.check_existing_reports(assessment_type)
                logger.info(f"Found {existing_reports['total_reports']} existing reports")
            
            for assessment_type in assessment_types:
                try:
                    report_result = self.generate_reports(
                        assessment_type, skip_existing=skip_existing, existing_reports=existing_reports, 
                        incremental_mode=incremental_mode, analysis_data=analysis_data
                    )
                    if not report_result["success"]:
                        results["errors"].append(f"Failed to generate reports for {assessment_type}: {report_result['error']}")
                        continue
                    
                    results["assessments_processed"] += 1
                    results["reports_generated"] += report_result["reports_generated"]
                    results["reports_skipped"] += report_result.get("reports_skipped", 0)
                    
                    # Collect PDFs from this assessment
                    if "generated_pdfs" in report_result:
                        results["all_generated_pdfs"].update(report_result["generated_pdfs"])
                    
                    logger.info(f"Successfully generated reports for {assessment_type}")
                    
                except Exception as e:
                    error_msg = f"Error generating reports for {assessment_type}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            results["success"] = not bool(results["errors"])
            self._log_operation_complete("report generation", incremental_mode, results["assessments_processed"], 
                                       f", {results['reports_generated']} reports generated, {results['reports_skipped']} reports skipped")
            return results
            
        except Exception as e:
            logger.error(f"Error in generate_all_reports: {str(e)}")
            return {
                "success": False, "assessments_processed": 0, "reports_generated": 0, 
                "reports_skipped": 0, "errors": [str(e)]
            }
    
    def generate_reports(self, assessment_type: str, skip_existing: bool = True, 
                        existing_reports: Dict[str, Any] = None, incremental_mode: bool = False, 
                        analysis_data: Dict[str, pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Generate reports for a specific assessment type
        
        Args:
            assessment_type: Type of assessment (M1, CL, CIEN, HYST)
            skip_existing: If True, skip generation of reports that already exist
            existing_reports: Dictionary with existing reports information
            incremental_mode: If True, use in-memory analysis data
            analysis_data: Optional dictionary with analysis DataFrames
            
        Returns:
            Dict with report generation results including in-memory PDFs for incremental mode
        """
        results = {
            "success": True,
            "reports_generated": 0,
            "reports_skipped": 0,
            "error": None,
            "generated_pdfs": {}  # Store PDFs in memory for incremental mode
        }
        
        try:
            self._log_operation_start("report generation", incremental_mode, assessment_type)
            
            # Determine analysis data source
            if analysis_data and assessment_type in analysis_data:
                analysis_df = analysis_data[assessment_type]
                logger.info(f"Using provided analysis data for {assessment_type}: {len(analysis_df)} records")
            else:
                analysis_file = self._get_file_path("data/analysis", assessment_type)
                
                if incremental_mode:
                    # In incremental mode, we should always use analysis_data if available
                    results["success"] = False
                    results["error"] = f"No analysis data provided for {assessment_type} in incremental mode"
                    return results
                elif not self.storage.exists(analysis_file):
                    error_msg = f"Analysis file not found: {analysis_file}. Please analyze the assessment first."
                    results["success"] = False
                    results["error"] = error_msg
                    return results
                
                analysis_df = self.storage.read_csv(analysis_file, sep=';')
                if analysis_df.empty:
                    error_msg = f"No analysis data found for {assessment_type}"
                    results["success"] = False
                    results["error"] = error_msg
                    return results
                
                logger.info(f"Found {len(analysis_df)} records in analysis file for {assessment_type}")
            
            # Ensure reports directory exists
            self.storage.ensure_directory("reports")
            
            # Get existing files for this assessment type if not provided
            if existing_reports is None and skip_existing:
                existing_reports = self.check_existing_reports(assessment_type)
            
            # Create a set of existing filenames for fast lookup
            existing_files = set(existing_reports.get("existing_files", [])) if existing_reports else set()
            
            # Generate reports for each student
            for _, row in analysis_df.iterrows():
                try:
                    user_info = {
                        "username": row.get("email", "unknown"),
                        "email": row.get("email", "unknown")
                    }
                    
                    username = user_info.get("username", "unknown")
                    filename = f"informe_{username}_{assessment_type}.pdf"
                    
                    # Check if report already exists
                    if skip_existing and filename in existing_files:
                        results["reports_skipped"] += 1
                        logger.debug(f"Skipping existing report: {filename}")
                        continue
                    
                    # Generate PDF report
                    pdf_content = self.report_generator.generate_pdf(
                        assessment_type, row.to_dict(), user_info, incremental_mode, analysis_df
                    )
                    
                    if pdf_content:
                        if incremental_mode:
                            # Store PDF in memory for email sending
                            user_email = user_info.get("email", "unknown")
                            results["generated_pdfs"][user_email] = {
                                "pdf_content": pdf_content,
                                "filename": filename,
                                "assessment_type": assessment_type
                            }
                            results["reports_generated"] += 1
                            logger.info(f"Generated in-memory report: {filename}")
                        else:
                            # Save PDF to storage (normal mode)
                            pdf_path = f"reports/{filename}"
                            if self.storage.write_bytes(pdf_path, pdf_content, "application/pdf"):
                                results["reports_generated"] += 1
                                logger.info(f"Generated report: {filename}")
                            else:
                                logger.error(f"Failed to save report: {filename}")
                    
                except Exception as e:
                    logger.error(f"Error generating report for student: {str(e)}")
            
            logger.info(f"Generated {results['reports_generated']} reports, skipped {results['reports_skipped']} existing reports for {assessment_type}")
            return results
            
        except Exception as e:
            logger.error(f"Error generating reports for assessment {assessment_type}: {str(e)}")
            results["success"] = False
            results["error"] = str(e)
            return results
    
    def _extract_email_from_filename(self, filename: str) -> str:
        """
        Extract email address from filename
        Filename format: informe_email_assessment.pdf
        
        Args:
            filename: The filename to extract email from
            
        Returns:
            Email address or empty string if not found
        """
        try:
            if filename.startswith('informe_') and filename.endswith('.pdf'):
                # Remove 'informe_' prefix and '.pdf' suffix
                parts = filename.replace('informe_', '').replace('.pdf', '').split('_')
                if len(parts) >= 2:
                    # Everything except the last part (assessment type) is the email
                    return '_'.join(parts[:-1])
        except Exception as e:
            logger.warning(f"Error extracting email from filename {filename}: {str(e)}")
        return ""
    
    def _extract_assessment_type_from_filename(self, filename: str) -> str:
        """
        Extract assessment type from filename
        Filename format: informe_email_assessment.pdf
        
        Args:
            filename: The filename to extract assessment type from
            
        Returns:
            Assessment type or empty string if not found
        """
        try:
            if filename.startswith('informe_') and filename.endswith('.pdf'):
                # Remove 'informe_' prefix and '.pdf' suffix
                parts = filename.replace('informe_', '').replace('.pdf', '').split('_')
                if len(parts) >= 2:
                    # Last part is the assessment type
                    return parts[-1]
        except Exception as e:
            logger.warning(f"Error extracting assessment type from filename {filename}: {str(e)}")
        return ""
    
    def _save_report_to_drive(self, pdf_content: bytes, filename: str, email: str) -> Optional[Dict[str, str]]:
        """
        Save report to Google Drive
        
        Args:
            pdf_content: PDF content as bytes
            filename: Original filename
            email: Email address of recipient
            
        Returns:
            Dict with file_id and link if successful, None otherwise
        """
        try:
            if not self.drive_service.drive_service:
                logger.warning("Google Drive service not available, skipping drive upload")
                return None
            
            # Extract assessment type for folder organization
            assessment_type = self._extract_assessment_type_from_filename(filename)
            if not assessment_type:
                logger.warning(f"Could not extract assessment type from filename: {filename}")
                return None
            
            # Create organized folder structure and upload
            result = self.drive_service.upload_bytes(
                content=pdf_content,
                filename=filename,
                folder_id=self.drive_service.base_folder_id,
                mime_type='application/pdf'
            )
            
            if result:
                # Get shareable link
                link = self.drive_service.get_file_link(result)
                logger.info(f"Report saved to Google Drive: {filename} (ID: {result})")
                return {
                    'file_id': result,
                    'link': link
                }
            else:
                logger.error(f"Failed to upload report to Google Drive: {filename}")
                return None
                
        except Exception as e:
            logger.error(f"Error saving report to Google Drive {filename}: {str(e)}")
            return None
    
    def _load_processed_emails(self) -> set:
        """
        Load list of already processed email-assessment combinations from CSV file
        
        Returns:
            Set of (email, assessment_type) tuples that have already been processed
        """
        processed_combinations = set()
        try:
            if self.storage.exists(self.processed_emails_file):
                df = self.storage.read_csv(self.processed_emails_file)
                if 'email' in df.columns and 'assessment_type' in df.columns:
                    # Create tuples of (email, assessment_type) for each processed combination
                    for _, row in df.iterrows():
                        email = row['email'].lower()
                        assessment_type = row['assessment_type']
                        processed_combinations.add((email, assessment_type))
                logger.info(f"Loaded {len(processed_combinations)} previously processed email-assessment combinations")
        except Exception as e:
            logger.warning(f"Error loading processed emails: {str(e)}")
        return processed_combinations
    
    def _save_processed_email(self, email: str, filename: str, assessment_type: str, drive_file_id: str = None, drive_link: str = None):
        """
        Save processed email to CSV file
        
        Args:
            email: Email address that was processed
            filename: Report filename that was sent
            assessment_type: Type of assessment
            drive_file_id: Google Drive file ID (optional)
            drive_link: Google Drive shareable link (optional)
        """
        try:
            # Create new row
            new_row = {
                'email': email,
                'filename': filename,
                'assessment_type': assessment_type,
                'processed_date': pd.Timestamp.now().isoformat(),
                'drive_file_id': drive_file_id or '',
                'drive_link': drive_link or ''
            }
            
            # Load existing data or create new DataFrame
            if self.storage.exists(self.processed_emails_file):
                df = self.storage.read_csv(self.processed_emails_file)
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            else:
                df = pd.DataFrame([new_row])
            
            # Save back to CSV using StorageClient
            self.storage.write_csv(self.processed_emails_file, df, index=False)
            logger.info(f"Saved processed email: {email}")
            
        except Exception as e:
            logger.error(f"Error saving processed email {email}: {str(e)}")
    
    def send_reports_via_email(self, generated_pdfs: Dict[str, Dict[str, Any]], test_mode: bool = False, disable_drive: bool = False) -> Dict[str, Any]:
        """
        Send generated PDF reports via email
        
        Args:
            generated_pdfs: Dictionary with email -> PDF data mapping
            test_mode: If True, send all emails to TEST_EMAIL environment variable
            disable_drive: If True, skip Google Drive uploads
            
        Returns:
            Dict with email sending results
        """
        results = {
            "success": True,
            "emails_sent": 0,
            "emails_skipped": 0,
            "reports_saved_to_drive": 0,
            "errors": []
        }
        
        try:
            # Load already processed email-assessment combinations
            processed_combinations = self._load_processed_emails()
            
            # If test mode is enabled, use the test email from environment
            if test_mode:
                test_email = os.getenv("TEST_EMAIL")
                if not test_email:
                    results["success"] = False
                    results["errors"].append("TEST_EMAIL environment variable not set for test mode")
                    return results
                logger.info(f"TEST MODE: All emails will be sent to {test_email}")
            
            if not generated_pdfs:
                results["success"] = False
                results["errors"].append("No generated PDFs provided")
                return results
            
            logger.info(f"Found {len(generated_pdfs)} PDF reports to send via email")
            
            # Send emails
            for email, pdf_data in generated_pdfs.items():
                try:
                    pdf_content = pdf_data["pdf_content"]
                    filename = pdf_data["filename"]
                    assessment_type = pdf_data["assessment_type"]
                    
                    # Check if this specific email-assessment combination was already processed
                    email_assessment_key = (email.lower(), assessment_type)
                    if email_assessment_key in processed_combinations:
                        logger.info(f"Skipping already processed email-assessment combination: {email} - {assessment_type}")
                        results["emails_skipped"] += 1
                        continue
                    
                    # Extract username from email
                    username = email
                    
                    # Use test email if in test mode, otherwise use original email
                    recipient_email = test_email if test_mode else email
                    
                    email_sent = self.email_sender.send_comprehensive_report_email(
                        recipient_email, pdf_content, username, filename
                    )
                    
                    if email_sent:
                        results["emails_sent"] += 1
                        
                        # Save report to Google Drive (unless disabled)
                        drive_result = None
                        if not disable_drive:
                            drive_result = self._save_report_to_drive(pdf_content, filename, email)
                            if drive_result:
                                results["reports_saved_to_drive"] += 1
                                logger.info(f"Report saved to Google Drive: {filename}")
                        else:
                            logger.info(f"Drive upload disabled, skipping: {filename}")
                        
                        # Save to processed emails (only if not in test mode)
                        if not test_mode:
                            # Get drive info for tracking
                            drive_file_id = drive_result.get('file_id') if drive_result else None
                            drive_link = drive_result.get('link') if drive_result else None
                            
                            self._save_processed_email(
                                email, 
                                filename, 
                                assessment_type,
                                drive_file_id,
                                drive_link
                            )
                        
                        if test_mode:
                            logger.info(f"TEST MODE: Email sent successfully to {recipient_email} (original: {email})")
                        else:
                            logger.info(f"Email sent successfully to: {email}")
                    else:
                        results["errors"].append(f"Failed to send email to: {email}")
                    
                except Exception as e:
                    error_msg = f"Error sending email to {email}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            if results["errors"]:
                results["success"] = False
            
            logger.info(f"Email sending complete. {results['emails_sent']} emails sent, {results['emails_skipped']} skipped, {results['reports_saved_to_drive']} reports saved to Drive")
            return results
            
        except Exception as e:
            logger.error(f"Error in send_reports_via_email: {str(e)}")
            return {
                "success": False,
                "emails_sent": 0,
                "emails_skipped": 0,
                "reports_saved_to_drive": 0,
                "errors": [str(e)]
            }


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Diagnosticos - Assessment Processing and Reporting")
    parser.add_argument("--download", action="store_true", help="Download assessment data")
    parser.add_argument("--process", action="store_true", help="Process assessments (convert JSON to CSV)")
    parser.add_argument("--analyze", action="store_true", help="Analyze assessments (generate analysis CSV)")
    parser.add_argument("--reports", action="store_true", help="Generate PDF reports")
    parser.add_argument("--send-emails", action="store_true", help="Send generated reports via email")
    parser.add_argument("--check-reports", action="store_true", help="Check existing PDF reports in reports folder")
    parser.add_argument("--force-reports", action="store_true", help="Force generation of all reports (don't skip existing)")
    parser.add_argument("--assessment", choices=["M1", "CL", "CIEN", "HYST"], help="Process specific assessment type")
    parser.add_argument("--incremental", action="store_true", help="Process only incremental data (for batch processing)")
    parser.add_argument("--full", action="store_true", help="Force full download (ignore incremental mode)")
    parser.add_argument("--cleanup", action="store_true", help="Clean up incremental files after processing")
    parser.add_argument("--test-email", action="store_true", help="Send all emails to TEST_EMAIL environment variable (for testing)")
    parser.add_argument("--disable-drive", action="store_true", help="Disable Google Drive uploads (for testing)")
    
    args = parser.parse_args()
    
    app = DiagnosticosApp()
    
    try:
        # Determine if we should use incremental mode
        incremental_mode = args.incremental and not args.full
        
        # Initialize in-memory data storage
        data_storage = {
            "downloaded_data": {},
            "processed_data": {},
            "analysis_data": {},
            "generated_pdfs": {}
        }
        
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
            # Check if we have analysis data to generate reports from
            if incremental_mode and not data_storage["analysis_data"]:
                logger.info("Skipping report generation in incremental mode - no analysis data available (no new data was processed).")
            else:
                logger.info(f"Generating reports{' in incremental mode' if incremental_mode else ''}...")
                skip_existing = not args.force_reports
                
                reports_result = app.generate_all_reports(
                    skip_existing=skip_existing, 
                    incremental_mode=incremental_mode, 
                    assessment_type=args.assessment, 
                    analysis_data=data_storage["analysis_data"]
                )
                
                if reports_result["success"]:
                    mode = "incremental" if incremental_mode else "full"
                    logger.info(f"{mode.capitalize()} report generation completed successfully. "
                              f"{reports_result.get('reports_generated', 0)} reports generated, "
                              f"{reports_result.get('reports_skipped', 0)} reports skipped")
                    
                    # Store generated PDFs for email sending
                    if incremental_mode and "all_generated_pdfs" in reports_result:
                        data_storage["generated_pdfs"] = reports_result["all_generated_pdfs"]
                        logger.info(f"Stored {len(data_storage['generated_pdfs'])} PDFs in memory for email sending")
                else:
                    logger.error(f"Report generation failed: {reports_result.get('error', 'Unknown error')}")
                    for error in reports_result.get('errors', []):
                        logger.error(f"  - {error}")
        
        # Handle email sending
        if args.send_emails:
            if incremental_mode and data_storage["generated_pdfs"]:
                # Send emails for in-memory PDFs (incremental mode)
                logger.info("Sending emails for generated reports...")
                email_result = app.send_reports_via_email(
                    data_storage["generated_pdfs"], 
                    test_mode=args.test_email, 
                    disable_drive=args.disable_drive
                )
                
                if email_result["success"]:
                    logger.info(f"Email sending completed successfully. "
                              f"{email_result.get('emails_sent', 0)} emails sent, "
                              f"{email_result.get('emails_skipped', 0)} skipped, "
                              f"{email_result.get('reports_saved_to_drive', 0)} reports saved to Drive")
                else:
                    logger.error(f"Email sending failed: {email_result.get('errors', [])}")
                    
            elif not incremental_mode:
                # For non-incremental mode, we would load from file system
                logger.info("Email sending in non-incremental mode is not yet implemented in main.py")
                logger.info("Use send_emails.py for file-based email sending")
            else:
                logger.info("No generated PDFs available for email sending in incremental mode")
        
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
                
                logger.info("Cleaning up incremental files after all processing...")
                cleanup_result = app.cleanup_incremental_files(assessment_type=args.assessment)
                if cleanup_result["success"]:
                    logger.info(f"Cleanup completed successfully. {cleanup_result.get('files_cleaned', 0)} assessments cleaned")
                else:
                    logger.warning(f"Cleanup had issues: {cleanup_result.get('errors', [])}")
        elif incremental_mode:
            # If we're in incremental mode but no operations were executed (due to errors), log this
            logger.info("Incremental mode enabled but no operations completed successfully. Skipping merge and cleanup.")
        
        # Handle standalone cleanup
        if args.cleanup and not any([args.download, args.process, args.analyze, args.reports, args.check_reports]):
            logger.info("Cleaning up incremental files...")
            cleanup_result = app.cleanup_incremental_files()
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
