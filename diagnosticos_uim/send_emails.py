#!/usr/bin/env python3
"""
Independent email sender for diagnosticos project
Automatically sends reports to all people with reports in the reports folder
Tracks processed emails to avoid duplicates
Saves reports to Google Drive when sent via email
"""

import os
import logging
import argparse
import csv
import pandas as pd
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from email_sender import EmailSender
from storage import StorageClient
from drive_service import DriveService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EmailSenderApp:
    def __init__(self):
        """Initialize the email sender application"""
        self.storage = StorageClient()
        self.email_sender = EmailSender()
        self.drive_service = DriveService()
        self.processed_file = "processed_emails.csv"
        
        # Log drive service status
        if self.drive_service.drive_service:
            logger.info("Google Drive service initialized successfully")
        else:
            logger.warning("Google Drive service not available - reports will not be saved to Drive")
    
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
            if filename.startswith('informe_uim') and filename.endswith('.pdf'):
                # Remove 'informe_uim' prefix and '.pdf' suffix
                parts = filename.replace('informe_uim_', '').replace('.pdf', '').split('_')
                if len(parts) >= 2:
                    # Everything except the last part (assessment type) is the email
                    return '_'.join(parts[:-1])
        except Exception as e:
            logger.warning(f"Error extracting email from filename {filename}: {str(e)}")
        return ""
    
    def _extract_username_from_filename(self, filename: str) -> str:
        """
        Extract username (email) from filename for personalization
        Filename format: informe_email_assessment.pdf
        
        Args:
            filename: The filename to extract username from
            
        Returns:
            Username (email address) or empty string if not found
        """
        return self._extract_email_from_filename(filename)
    
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
            if filename.startswith('informe_uim_') and filename.endswith('.pdf'):
                # Remove 'informe_uim_' prefix and '.pdf' suffix
                parts = filename.replace('informe_uim_', '').replace('.pdf', '').split('_')
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
            if self.storage.exists(self.processed_file):
                df = self.storage.read_csv(self.processed_file)
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
            if self.storage.exists(self.processed_file):
                df = self.storage.read_csv(self.processed_file)
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            else:
                df = pd.DataFrame([new_row])
            
            # Save back to CSV using StorageClient
            self.storage.write_csv(self.processed_file, df, index=False)
            logger.info(f"Saved processed email: {email}")
            
        except Exception as e:
            logger.error(f"Error saving processed email {email}: {str(e)}")
    
    def send_all_reports_email(self, assessment_type: str = None, test_mode: bool = False, disable_drive: bool = False) -> Dict[str, Any]:
        """
        Send reports via email to all people with reports in the reports folder
        Also saves reports to Google Drive
        
        Args:
            assessment_type: Optional assessment type filter
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
            
            # Get list of PDF files
            reports_dir = "reports"
            if not self.storage.exists(reports_dir):
                results["success"] = False
                results["errors"].append("Reports directory not found")
                return results
            
            pdf_files = [f for f in self.storage.list_files(reports_dir) if f.endswith('.pdf')]
            
            if assessment_type:
                pdf_files = [f for f in pdf_files if assessment_type in f]
            
            if not pdf_files:
                results["success"] = False
                results["errors"].append("No PDF reports found")
                return results
            
            logger.info(f"Found {len(pdf_files)} PDF reports to process")
            
            # Group reports by email and assessment type
            email_reports = {}
            for f in pdf_files:
                # Extract just the filename from the full path
                filename = os.path.basename(f) if os.path.sep in f else f
                email = self._extract_email_from_filename(filename)
                assessment_type_from_file = self._extract_assessment_type_from_filename(filename)
                
                if email and assessment_type_from_file:
                    key = (email, assessment_type_from_file)
                    if key not in email_reports:
                        email_reports[key] = []
                    email_reports[key].append(f)
            
            logger.info(f"Found {len(email_reports)} unique email-assessment combinations")
            
            # Send emails
            for (email, assessment_type_from_file), reports in email_reports.items():
                try:
                    # Check if this specific email-assessment combination was already processed
                    email_assessment_key = (email.lower(), assessment_type_from_file)
                    if email_assessment_key in processed_combinations:
                        logger.info(f"Skipping already processed email-assessment combination: {email} - {assessment_type_from_file}")
                        results["emails_skipped"] += 1
                        continue
                    
                    # Send email with the first report (or you could send all reports)
                    report_file = reports[0]
                    # Use the full path directly since list_files returns full paths
                    pdf_content = self.storage.read_bytes(report_file)
                    
                    # Extract username from filename (email part only)
                    filename = os.path.basename(report_file) if os.path.sep in report_file else report_file
                    username = self._extract_username_from_filename(filename)
                    
                    # Use test email if in test mode, otherwise use original email
                    recipient_email = test_email if test_mode else email
                    
                    # Use just the filename for the email attachment, not the full path
                    attachment_filename = os.path.basename(report_file) if os.path.sep in report_file else report_file
                    
                    email_sent = self.email_sender.send_comprehensive_report_email(
                        recipient_email, pdf_content, username, attachment_filename
                    )
                    
                    if email_sent:
                        results["emails_sent"] += 1
                        
                        # Save report to Google Drive (unless disabled)
                        drive_result = None
                        if not disable_drive:
                            drive_result = self._save_report_to_drive(pdf_content, attachment_filename, email)
                            if drive_result:
                                results["reports_saved_to_drive"] += 1
                                logger.info(f"Report saved to Google Drive: {attachment_filename}")
                        else:
                            logger.info(f"Drive upload disabled, skipping: {attachment_filename}")
                        
                        # Save to processed emails (only if not in test mode)
                        if not test_mode:
                            # Get drive info for tracking
                            drive_file_id = drive_result.get('file_id') if drive_result else None
                            drive_link = drive_result.get('link') if drive_result else None
                            
                            self._save_processed_email(
                                email, 
                                report_file, 
                                assessment_type_from_file,
                                drive_file_id,
                                drive_link
                            )
                        
                        if test_mode:
                            logger.info(f"TEST MODE: Email sent successfully to {recipient_email} (original: {email}) for {assessment_type_from_file}")
                        else:
                            logger.info(f"Email sent successfully to: {email} for {assessment_type_from_file}")
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
            logger.error(f"Error in send_all_reports_email: {str(e)}")
            return {
                "success": False,
                "emails_sent": 0,
                "emails_skipped": 0,
                "reports_saved_to_drive": 0,
                "errors": [str(e)]
            }
    
    def list_available_reports(self, assessment_type: str = None) -> List[str]:
        """
        List available PDF reports
        
        Args:
            assessment_type: Optional assessment type filter
            
        Returns:
            List of available report filenames
        """
        try:
            reports_dir = "reports"
            if not self.storage.exists(reports_dir):
                logger.warning("Reports directory not found")
                return []
            
            pdf_files = [f for f in self.storage.list_files(reports_dir) if f.endswith('.pdf')]
            
            if assessment_type:
                pdf_files = [f for f in pdf_files if assessment_type in f]
            
            return pdf_files
            
        except Exception as e:
            logger.error(f"Error listing reports: {str(e)}")
            return []
    
    def list_reports_with_emails(self, assessment_type: str = None) -> List[Dict[str, str]]:
        """
        List available PDF reports with extracted email addresses
        
        Args:
            assessment_type: Optional assessment type filter
            
        Returns:
            List of dictionaries with filename and email
        """
        try:
            reports_dir = "reports"
            if not self.storage.exists(reports_dir):
                logger.warning("Reports directory not found")
                return []
            
            pdf_files = [f for f in self.storage.list_files(reports_dir) if f.endswith('.pdf')]
            
            if assessment_type:
                pdf_files = [f for f in pdf_files if assessment_type in f]
            
            reports_info = []
            for f in pdf_files:
                # Extract just the filename from the full path
                filename = os.path.basename(f) if os.path.sep in f else f
                email = self._extract_email_from_filename(filename)
                reports_info.append({
                    "filename": f,
                    "email": email,
                    "assessment": filename.split('_')[-1].replace('.pdf', '') if filename.endswith('.pdf') else ""
                })
            
            return reports_info
            
        except Exception as e:
            logger.error(f"Error listing reports: {str(e)}")
            return []
    
    def reset_processed_emails(self):
        """
        Reset the processed emails CSV file (for testing purposes)
        """
        try:
            if self.storage.exists(self.processed_file):
                os.remove(self.processed_file)
                logger.info("Processed emails file reset")
            else:
                logger.info("No processed emails file found to reset")
        except Exception as e:
            logger.error(f"Error resetting processed emails: {str(e)}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Email Sender - Send diagnostic reports via email")
    parser.add_argument("--assessment", choices=["M1", "F30M", "Q30M", "B30M", "HYST"], help="Filter by assessment type")
    parser.add_argument("--list-reports", action="store_true", help="List available reports and exit")
    parser.add_argument("--test-email", action="store_true", help="Send all emails to TEST_EMAIL environment variable (for testing)")
    parser.add_argument("--reset-processed", action="store_true", help="Reset processed emails tracking (for testing)")
    parser.add_argument("--disable-drive", action="store_true", help="Disable Google Drive uploads (for testing)")
    
    args = parser.parse_args()
    
    app = EmailSenderApp()
    
    try:
        if args.reset_processed:
            app.reset_processed_emails()
            return
        
        if args.list_reports:
            logger.info("Listing available reports...")
            reports_info = app.list_reports_with_emails(args.assessment)
            if reports_info:
                print(f"\nAvailable reports ({len(reports_info)}):")
                for report in reports_info:
                    print(f"  - {report['filename']}")
                    print(f"    Email: {report['email']}")
                    print(f"    Assessment: {report['assessment']}")
                    print()
            else:
                print("No reports found")
            return
        
        logger.info("Sending reports via email to all people with reports...")
        result = app.send_all_reports_email(args.assessment, args.test_email, args.disable_drive)
        
        if result["success"]:
            logger.info(f"Email sending completed successfully. {result['emails_sent']} emails sent, {result['emails_skipped']} skipped, {result['reports_saved_to_drive']} reports saved to Drive")
            if result['reports_saved_to_drive'] > 0:
                logger.info(f"✓ {result['reports_saved_to_drive']} reports successfully uploaded to Google Drive")
        else:
            logger.error(f"Email sending failed: {result['errors']}")
    
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()
