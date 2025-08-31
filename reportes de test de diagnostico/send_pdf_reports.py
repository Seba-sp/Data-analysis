#!/usr/bin/env python3
"""
PDF Report Email Sender

Sends PDF reports from a specific folder to students and tracks sent emails
to avoid duplicates. Reads student information from the Excel file and
sends personalized emails with PDF attachments.

Usage:
    python send_pdf_reports.py --folder "reports/S3" --dry_run
    python send_pdf_reports.py --folder "reports/S3" --execute
"""

import os
import argparse
import pandas as pd
import glob
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Import the existing email sender
from email_sender import EmailSender

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PDFReportSender:
    def __init__(self, analysis_excel_path: str = "data/analysis/analisis de datos.xlsx"):
        """
        Initialize the PDF report sender
        
        Args:
            analysis_excel_path: Path to the Excel file containing student data
        """
        self.analysis_excel_path = analysis_excel_path
        self._df_reporte = None
        self.email_sender = None
        self.sent_emails_file = "sent_emails_tracker.xlsx"
        
        # Try to initialize email sender, but don't fail if credentials are missing
        try:
            self.email_sender = EmailSender()
        except ValueError as e:
            logger.warning(f"Email sender not initialized: {e}")
            logger.info("Email sending will be disabled. Set EMAIL_FROM and EMAIL_PASS environment variables to enable.")
        
    def _load_reporte_sheet(self) -> pd.DataFrame:
        """Load the Reporte sheet from the Excel file"""
        if self._df_reporte is not None:
            return self._df_reporte
            
        try:
            logger.info(f"Loading analysis workbook: {self.analysis_excel_path}")
            excel_file = pd.ExcelFile(self.analysis_excel_path)
            self._df_reporte = excel_file.parse(sheet_name="Reporte")
            logger.info(f"Loaded {len(self._df_reporte)} rows from Reporte sheet")
            return self._df_reporte
        except Exception as e:
            logger.error(f"Error loading Excel file: {e}")
            raise
    
    def _find_col_case_insensitive(self, df: pd.DataFrame, targets: List[str]) -> Optional[str]:
        """Find a column name case-insensitively"""
        if df is None or df.empty:
            return None
        lower_to_actual = {c.strip().lower(): c for c in df.columns}
        for t in targets:
            key = t.strip().lower()
            if key in lower_to_actual:
                return lower_to_actual[key]
        return None
    
    def _load_sent_emails_tracker(self) -> pd.DataFrame:
        """Load the sent emails tracker Excel file"""
        if os.path.exists(self.sent_emails_file):
            try:
                df = pd.read_excel(self.sent_emails_file)
                logger.info(f"Loaded {len(df)} records from sent emails tracker")
                return df
            except Exception as e:
                logger.warning(f"Error loading sent emails tracker: {e}")
                return pd.DataFrame(columns=['email', 'pdf_filename', 'sent_date', 'folder'])
        else:
            logger.info("Sent emails tracker file not found, creating new one")
            return pd.DataFrame(columns=['email', 'pdf_filename', 'sent_date', 'folder'])
    
    def _save_sent_emails_tracker(self, df: pd.DataFrame) -> None:
        """Save the sent emails tracker to Excel file"""
        try:
            df.to_excel(self.sent_emails_file, index=False)
            logger.info(f"Saved {len(df)} records to sent emails tracker")
        except Exception as e:
            logger.error(f"Error saving sent emails tracker: {e}")
    
    def _extract_email_from_filename(self, filename: str) -> Optional[str]:
        """Extract email address from PDF filename"""
        # Remove file extension
        name_without_ext = os.path.splitext(filename)[0]
        
        # Handle different naming patterns
        if "_segmento_" in name_without_ext:
            # Pattern: email_segmento_manana.pdf or email_segmento_tarde.pdf
            email = name_without_ext.split("_segmento_")[0]
        elif "_S" in name_without_ext and ("_manana" in name_without_ext or "_tarde" in name_without_ext):
            # Pattern: email_S7_manana.pdf or email_S8_tarde.pdf
            # Find the last underscore before _S
            parts = name_without_ext.split("_S")
            if len(parts) >= 2:
                email = parts[0]
            else:
                email = name_without_ext
        else:
            # Pattern: email.pdf (for Cuarto medio)
            email = name_without_ext
        
        return email if "@" in email else None
    
    def _get_student_info(self, email: str) -> Optional[Dict]:
        """Get student information from the Reporte sheet"""
        df = self._load_reporte_sheet()
        
        email_col = self._find_col_case_insensitive(df, ["email", "correo"])
        name_col = self._find_col_case_insensitive(df, ["nombre_y_apellido", "nombre", "name"])
        
        if not email_col:
            logger.error("Email column not found in Reporte sheet")
            return None
        
        # Find student by email
        student_row = df[df[email_col].astype(str).str.lower() == email.lower()]
        
        if student_row.empty:
            logger.warning(f"Student not found for email: {email}")
            return None
        
        student = student_row.iloc[0]
        
        # Get student name
        student_name = "Estudiante"
        if name_col and not pd.isna(student[name_col]):
            student_name = str(student[name_col]).strip()
        else:
            # Use email prefix as name if no name column
            student_name = email.split("@")[0]
        
        return {
            'email': email,
            'name': student_name,
            'row_data': student
        }
    
    def _is_email_already_sent(self, email: str, folder: str, sent_emails_df: pd.DataFrame) -> bool:
        """Check if email was already sent for this folder"""
        if sent_emails_df.empty:
            return False
        
        # Check if this email was already sent for this folder (regardless of specific files)
        mask = (
            (sent_emails_df['email'].str.lower() == email.lower()) &
            (sent_emails_df['folder'] == folder)
        )
        
        return mask.any()
    
    def _send_pdf_email(self, email: str, pdf_paths: List[str], student_name: str, dry_run: bool = True) -> bool:
        """Send PDF report email to student with multiple attachments"""
        try:
            if dry_run:
                pdf_filenames = [os.path.basename(pdf_path) for pdf_path in pdf_paths]
                logger.info(f"DRY RUN: Would send email to {email} with attachments: {', '.join(pdf_filenames)}")
                return True
            
            # Check if email sender is available
            if self.email_sender is None:
                logger.error("Email sender not available. Set EMAIL_FROM and EMAIL_PASS environment variables.")
                return False
            
            # Create email message
            msg = MIMEMultipart()
            msg["Subject"] = f"Plan de Estudio Personalizado"
            msg["From"] = self.email_sender.email_from
            msg["To"] = email
            
            # Email body
            body = f"""Hola,

Te hago entrega de tu plan de estudio personalizado!

Sigue al pie de la letra los pasos indicados dentro de tu reporte para llegar al máximo en este camino a la PAES 2025.

¡Un abrazo gigante y vamos con TODO!

Equipo Preu M30M
"""
            
            msg.attach(MIMEText(body, "plain", "utf-8"))
            
            # Attach all PDF files
            for pdf_path in pdf_paths:
                pdf_filename = os.path.basename(pdf_path)
                try:
                    with open(pdf_path, 'rb') as f:
                        pdf_content = f.read()
                    
                    pdf_attachment = MIMEBase("application", "pdf")
                    pdf_attachment.set_payload(pdf_content)
                    encoders.encode_base64(pdf_attachment)
                    pdf_attachment.add_header(
                        "Content-Disposition",
                        f"attachment; filename= {pdf_filename}"
                    )
                    msg.attach(pdf_attachment)
                    logger.info(f"PDF attached: {pdf_filename}")
                except Exception as e:
                    logger.error(f"Error reading PDF file {pdf_path}: {e}")
                    return False
            
            # Send email
            with smtplib.SMTP(self.email_sender.smtp_server, self.email_sender.smtp_port) as server:
                server.starttls()
                server.login(self.email_sender.email_from, self.email_sender.email_pass)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {email} with {len(pdf_paths)} attachments")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email to {email}: {e}")
            return False
    
    def send_reports_from_folder(self, folder_path: str, dry_run: bool = True, use_fixed_email: bool = False) -> Dict[str, int]:
        """
        Send PDF reports from a specific folder to students
        
        Args:
            folder_path: Path to the folder containing PDF reports
            dry_run: If True, only show what would be sent without actually sending
            use_fixed_email: If True, send all PDFs to FIXED_EMAIL environment variable instead of individual students
            
        Returns:
            Dictionary with statistics about the operation
        """
        logger.info(f"Starting PDF report sending process for folder: {folder_path}")
        
        if not os.path.exists(folder_path):
            logger.error(f"Folder does not exist: {folder_path}")
            return {'error': 'Folder not found'}
        
        # Load sent emails tracker
        sent_emails_df = self._load_sent_emails_tracker()
        
        # Find all PDF files in the folder
        pdf_files = glob.glob(os.path.join(folder_path, "*.pdf"))
        
        if not pdf_files:
            logger.warning(f"No PDF files found in folder: {folder_path}")
            return {'error': 'No PDF files found'}
        
        logger.info(f"Found {len(pdf_files)} PDF files in folder")
        
        # Statistics
        stats = {
            'total_files': len(pdf_files),
            'emails_sent': 0,
            'emails_skipped': 0,
            'errors': 0,
            'new_records': []
        }
        
        print(f"\n{'='*60}")
        print(f"PDF REPORT SENDING SUMMARY")
        print(f"{'='*60}")
        
        # Check for fixed email environment variable if use_fixed_email is True
        fixed_email = None
        if use_fixed_email:
            fixed_email = os.getenv('FIXED_EMAIL')
            if not fixed_email:
                logger.error("FIXED_EMAIL environment variable not set but --fixed_email 1 was specified")
                return {'error': 'FIXED_EMAIL environment variable not set'}
        
        print(f"Folder: {folder_path}")
        print(f"Total PDF files: {len(pdf_files)}")
        print(f"Dry run: {'Yes' if dry_run else 'No'}")
        if fixed_email:
            print(f"Fixed email: {fixed_email} (all PDFs will be sent here)")
        print(f"{'='*60}")
        
        # Group PDF files by email address
        email_to_pdfs = {}
        for pdf_path in pdf_files:
            pdf_filename = os.path.basename(pdf_path)
            
            # Extract email from filename
            email = self._extract_email_from_filename(pdf_filename)
            
            if not email:
                logger.warning(f"Could not extract email from filename: {pdf_filename}")
                stats['errors'] += 1
                continue
            
            # Group by email
            if email not in email_to_pdfs:
                email_to_pdfs[email] = []
            email_to_pdfs[email].append(pdf_path)
        
        if fixed_email:
            # Send all PDFs to the fixed email address
            all_pdfs = []
            for pdf_paths in email_to_pdfs.values():
                all_pdfs.extend(pdf_paths)
            
            if all_pdfs:
                # Check if email was already sent for this folder
                if self._is_email_already_sent(fixed_email, folder_path, sent_emails_df):
                    logger.info(f"Skipping {fixed_email} - email already sent for this folder")
                    stats['emails_skipped'] += 1
                else:
                    # Send all PDFs to fixed email
                    success = self._send_pdf_email(
                        email=fixed_email,
                        pdf_paths=all_pdfs,
                        student_name="Administrador",
                        dry_run=dry_run
                    )
                    
                    if success:
                        stats['emails_sent'] += 1
                        
                        # Add to new records for tracking
                        stats['new_records'].append({
                            'email': fixed_email,
                            'pdf_filename': f"{len(all_pdfs)} files (all students)",
                            'sent_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'folder': folder_path
                        })
                        
                        if not dry_run:
                            print(f"✓ Sent all {len(all_pdfs)} PDFs to {fixed_email}")
                    else:
                        stats['errors'] += 1
                        print(f"✗ Failed to send to {fixed_email}")
        else:
            # Process each email (one email per student with all their PDFs)
            for email, pdf_paths in email_to_pdfs.items():
                # Check if email was already sent for this folder
                if self._is_email_already_sent(email, folder_path, sent_emails_df):
                    logger.info(f"Skipping {email} - email already sent for this folder")
                    stats['emails_skipped'] += 1
                    continue
                
                # Get student information
                student_info = self._get_student_info(email)
                
                if not student_info:
                    logger.warning(f"Student info not found for email: {email}")
                    stats['errors'] += 1
                    continue
                
                # Send email with all PDFs for this student
                success = self._send_pdf_email(
                    email=email,
                    pdf_paths=pdf_paths,
                    student_name=student_info['name'],
                    dry_run=dry_run
                )
                
                if success:
                    stats['emails_sent'] += 1
                    
                    # Add to new records for tracking (one record per email, not per PDF)
                    stats['new_records'].append({
                        'email': email,
                        'pdf_filename': f"{len(pdf_paths)} files",  # Indicate multiple files
                        'sent_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'folder': folder_path
                    })
                    
                    if not dry_run:
                        pdf_filenames = [os.path.basename(pdf_path) for pdf_path in pdf_paths]
                        print(f"✓ Sent to {email} ({student_info['name']}) - {len(pdf_paths)} files: {', '.join(pdf_filenames)}")
                else:
                    stats['errors'] += 1
                    pdf_filenames = [os.path.basename(pdf_path) for pdf_path in pdf_paths]
                    print(f"✗ Failed to send to {email} - {len(pdf_paths)} files: {', '.join(pdf_filenames)}")
        
        # Update sent emails tracker if not dry run
        if not dry_run and stats['new_records']:
            new_records_df = pd.DataFrame(stats['new_records'])
            updated_df = pd.concat([sent_emails_df, new_records_df], ignore_index=True)
            self._save_sent_emails_tracker(updated_df)
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"FINAL SUMMARY")
        print(f"{'='*60}")
        print(f"Total files processed: {stats['total_files']}")
        print(f"Emails sent: {stats['emails_sent']}")
        print(f"Emails skipped (already sent): {stats['emails_skipped']}")
        print(f"Errors: {stats['errors']}")
        print(f"{'='*60}")
        
        if dry_run:
            print("\nDRY RUN COMPLETED - No emails were actually sent")
            print("Use --execute to actually send the emails")
        else:
            print(f"\nEmails sent successfully! Tracker updated with {len(stats['new_records'])} new records")
        
        return stats


def main():
    parser = argparse.ArgumentParser(description="Send PDF reports from a folder to students")
    parser.add_argument("--folder", type=str, required=True,
                       help="Folder path containing PDF reports (e.g., 'reports/S3')")
    parser.add_argument("--excel_path", type=str, default="data/analysis/analisis de datos.xlsx",
                       help="Path to the analysis Excel file")
    parser.add_argument("--dry_run", action="store_true", default=True,
                       help="Show what would be sent without actually sending (default)")
    parser.add_argument("--execute", action="store_true",
                       help="Actually send the emails (overrides --dry_run)")
    parser.add_argument("--fixed_email", type=int, choices=[0, 1],
                       help="1 to send all PDFs to FIXED_EMAIL environment variable, 0 to send to individual students (default)")
    
    args = parser.parse_args()
    
    # Set dry_run based on arguments
    dry_run = not args.execute
    
    # Create sender and run
    sender = PDFReportSender(args.excel_path)
    use_fixed_email = args.fixed_email == 1 if args.fixed_email is not None else False
    stats = sender.send_reports_from_folder(args.folder, dry_run=dry_run, use_fixed_email=use_fixed_email)
    
    if 'error' in stats:
        print(f"Error: {stats['error']}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
