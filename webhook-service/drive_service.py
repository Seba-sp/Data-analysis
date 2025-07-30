#!/usr/bin/env python3
"""
Google Drive service for uploading PDF reports
Handles uploading generated PDFs to Google Drive with organized folder structure
"""

import os
import json
import base64
import logging
from typing import Optional

# Try to import Google Drive libraries
try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2 import service_account
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False
    logging.warning("Google Drive libraries not available. Install with: pip install google-api-python-client google-auth")

logger = logging.getLogger(__name__)

class DriveService:
    def __init__(self):
        self.drive_service = None
        self.base_folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
        self.drive_id = os.getenv('GOOGLE_SHARED_DRIVE_ID')
        
        # Only try to initialize if we have the required environment variables
        if self.base_folder_id:
            try:
                self.drive_service = self._get_drive_service()
                logger.info("Google Drive service initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Google Drive service: {e}")
                self.drive_service = None
        else:
            logger.info("Google Drive not configured (GOOGLE_DRIVE_FOLDER_ID not set)")
            self.drive_service = None
    
    def _get_drive_service(self):
        """Initialize Google Drive service"""
        if not GOOGLE_DRIVE_AVAILABLE:
            raise ImportError("Google Drive libraries not available")
        
        # Get the service account key from environment variable
        service_account_key = os.getenv('GOOGLE_SERVICE_ACCOUNT_KEY')
        
        if not service_account_key:
            raise ValueError("GOOGLE_SERVICE_ACCOUNT_KEY environment variable not set")
        
        try:
            # Try to decode as base64 first
            try:
                decoded_key = base64.b64decode(service_account_key).decode('utf-8')
                key_data = json.loads(decoded_key)
            except:
                # If base64 fails, try as raw JSON
                key_data = json.loads(service_account_key)
            
            credentials = service_account.Credentials.from_service_account_info(
                key_data,
                scopes=['https://www.googleapis.com/auth/drive']
            )
            return build('drive', 'v3', credentials=credentials)
        except Exception as e:
            logger.error(f"Error parsing service account key: {e}")
            raise
    
    def _find_or_create_folder(self, parent_folder_id: str, folder_name: str) -> str:
        """Find or create a folder in Google Drive"""
        if not self.drive_service:
            return None
            
        query = f"mimeType='application/vnd.google-apps.folder' and trashed=false and name='{folder_name}' and '{parent_folder_id}' in parents"
        results = self.drive_service.files().list(
            q=query,
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        files = results.get('files', [])
        if files:
            return files[0]['id']
        
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id]
        }
        
        folder = self.drive_service.files().create(
            body=folder_metadata,
            fields='id, name',
            supportsAllDrives=True
        ).execute()
        
        logger.info(f"Created folder in Drive: {folder['name']} (ID: {folder['id']})")
        return folder['id']
    
    def _find_file_in_folder(self, folder_id: str, filename: str) -> Optional[str]:
        """Find a file in a Google Drive folder"""
        if not self.drive_service:
            return None
            
        query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
        results = self.drive_service.files().list(
            q=query,
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        files = results.get('files', [])
        if files:
            return files[0]['id']
        return None
    
    def upload_pdf_to_drive(self, pdf_content: bytes, filename: str, assessment_title: str) -> Optional[str]:
        if not self.drive_service or not self.base_folder_id:
            logger.info("Google Drive not available, skipping upload")
            return None
        try:
            # First, create or find the webhook_reports folder
            webhook_reports_folder_id = self._find_or_create_folder(self.base_folder_id, "webhook_reports")
            if not webhook_reports_folder_id:
                logger.error("Failed to create/find webhook_reports folder")
                return None
            
            # Then, create or find the assessment folder inside webhook_reports
            assessment_folder_id = self._find_or_create_folder(webhook_reports_folder_id, assessment_title)
            if not assessment_folder_id:
                logger.error(f"Failed to create/find assessment folder: {assessment_title}")
                return None
            
            # Use a unique temporary file path to avoid conflicts
            import tempfile
            import os
            temp_file_path = None
            
            try:
                # Create temporary file with unique name
                temp_fd, temp_file_path = tempfile.mkstemp(suffix='.pdf', prefix='drive_upload_')
                os.close(temp_fd)  # Close the file descriptor
                
                # Write PDF content to temporary file
                with open(temp_file_path, 'wb') as temp_file:
                    temp_file.write(pdf_content)
                
                file_metadata = {'name': filename, 'parents': [assessment_folder_id]}
                media = MediaFileUpload(temp_file_path, resumable=True)
                
                existing_file_id = self._find_file_in_folder(assessment_folder_id, filename)
                if existing_file_id:
                    logger.info(f"File already exists in Drive, updating: {filename}")
                    uploaded = self.drive_service.files().update(
                        fileId=existing_file_id,
                        media_body=media,
                        fields='id,webViewLink',
                        supportsAllDrives=True
                    ).execute()
                else:
                    logger.info(f"Creating new file in Drive: {filename}")
                    uploaded = self.drive_service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields='id,webViewLink',
                        supportsAllDrives=True
                    ).execute()
                
                web_link = uploaded.get('webViewLink')
                logger.info(f"Uploaded {filename} to Google Drive: {web_link}")
                return web_link
                
            finally:
                # Clean up temporary file
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.unlink(temp_file_path)
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to clean up temporary file {temp_file_path}: {cleanup_error}")
                        
        except Exception as e:
            logger.error(f"Error uploading to Google Drive: {e}")
            return None