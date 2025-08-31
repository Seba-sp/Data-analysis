#!/usr/bin/env python3
"""
Google Drive service for uploading files and managing folders
Project-agnostic service that can be used across multiple projects
Handles uploading files to Google Drive with organized folder structure
Supports shared drives, multiple file types, and flexible folder hierarchies
"""

import os
import json
import base64
import logging
import tempfile
from typing import Optional, List, Dict, Union
from pathlib import Path

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
    def __init__(self, base_folder_id: Optional[str] = None, drive_id: Optional[str] = None):
        """
        Initialize Google Drive service
        
        Args:
            base_folder_id: Base folder ID for uploads (defaults to GOOGLE_DRIVE_FOLDER_ID env var)
            drive_id: Shared drive ID (defaults to GOOGLE_DRIVE_ID env var)
        """
        self.drive_service = None
        self.base_folder_id = base_folder_id or os.getenv('GOOGLE_DRIVE_FOLDER_ID')
        self.drive_id = drive_id or os.getenv('GOOGLE_DRIVE_ID')
        
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
    
    def find_or_create_folder(self, parent_folder_id: str, folder_name: str, drive_id: Optional[str] = None) -> Optional[str]:
        """
        Find or create a folder in Google Drive
        
        Args:
            parent_folder_id: ID of the parent folder
            folder_name: Name of the folder to find or create
            drive_id: Shared drive ID (optional)
            
        Returns:
            Folder ID if successful, None otherwise
        """
        if not self.drive_service:
            logger.warning("Google Drive service not available")
            return None
            
        try:
            query = f"mimeType='application/vnd.google-apps.folder' and trashed=false and name='{folder_name}' and '{parent_folder_id}' in parents"
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                corpora='drive' if drive_id else None,
                driveId=drive_id
            ).execute()
            
            files = results.get('files', [])
            if files:
                logger.info(f"Found existing folder: {folder_name}")
                return files[0]['id']
            
            # Create the folder if not found
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_folder_id]
            }
            
            create_args = dict(
                body=folder_metadata,
                fields='id, name',
                supportsAllDrives=True
            )
            if drive_id:
                create_args['driveId'] = drive_id
                
            folder = self.drive_service.files().create(**create_args).execute()
            logger.info(f"Created folder in Drive: {folder['name']} (ID: {folder['id']})")
            return folder['id']
            
        except Exception as e:
            logger.error(f"Error finding/creating folder '{folder_name}': {e}")
            return None
    
    def find_file_in_folder(self, folder_id: str, filename: str, drive_id: Optional[str] = None) -> Optional[str]:
        """
        Find a file in a Google Drive folder
        
        Args:
            folder_id: ID of the folder to search in
            filename: Name of the file to find
            drive_id: Shared drive ID (optional)
            
        Returns:
            File ID if found, None otherwise
        """
        if not self.drive_service:
            return None
            
        try:
            query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                corpora='drive' if drive_id else None,
                driveId=drive_id
            ).execute()
            
            files = results.get('files', [])
            if files:
                return files[0]['id']
            return None
            
        except Exception as e:
            logger.error(f"Error finding file '{filename}' in folder: {e}")
            return None
    
    def upload_file(self, file_path: Union[str, Path], filename: Optional[str] = None, 
                   folder_id: Optional[str] = None, drive_id: Optional[str] = None) -> Optional[str]:
        """
        Upload a file to Google Drive
        
        Args:
            file_path: Path to the file to upload
            filename: Name for the file in Drive (defaults to original filename)
            folder_id: Folder ID to upload to (defaults to base_folder_id)
            drive_id: Shared drive ID (optional)
            
        Returns:
            Web view link if successful, None otherwise
        """
        if not self.drive_service:
            logger.warning("Google Drive not available, skipping upload")
            return None
            
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return None
                
            filename = filename or file_path.name
            folder_id = folder_id or self.base_folder_id
            
            if not folder_id:
                raise ValueError("No folder ID specified for upload")
            
            file_metadata = {
                'name': filename,
                'parents': [folder_id]
            }
            
            media = MediaFileUpload(str(file_path), resumable=True)
            
            # Check if file already exists
            existing_file_id = self.find_file_in_folder(folder_id, filename, drive_id)
            
            if existing_file_id:
                logger.info(f"File already exists in Drive, updating: {filename}")
                update_args = dict(
                    fileId=existing_file_id,
                    media_body=media,
                    fields='id,webViewLink',
                    supportsAllDrives=True
                )
                if drive_id:
                    update_args['driveId'] = drive_id
                uploaded = self.drive_service.files().update(**update_args).execute()
            else:
                logger.info(f"Creating new file in Drive: {filename}")
                upload_args = dict(
                    body=file_metadata,
                    media_body=media,
                    fields='id,webViewLink',
                    supportsAllDrives=True
                )
                if drive_id:
                    upload_args['driveId'] = drive_id
                uploaded = self.drive_service.files().create(**upload_args).execute()
            
            web_link = uploaded.get('webViewLink')
            logger.info(f"Uploaded {filename} to Google Drive: {web_link}")
            return web_link
            
        except Exception as e:
            logger.error(f"Error uploading file {file_path}: {e}")
            return None
    
    def upload_file_content(self, content: Union[bytes, str], filename: str, 
                          folder_id: Optional[str] = None, drive_id: Optional[str] = None) -> Optional[str]:
        """
        Upload file content (bytes or string) to Google Drive
        
        Args:
            content: File content as bytes or string
            filename: Name for the file in Drive
            folder_id: Folder ID to upload to (defaults to base_folder_id)
            drive_id: Shared drive ID (optional)
            
        Returns:
            Web view link if successful, None otherwise
        """
        if not self.drive_service:
            logger.warning("Google Drive not available, skipping upload")
            return None
            
        try:
            folder_id = folder_id or self.base_folder_id
            
            if not folder_id:
                raise ValueError("No folder ID specified for upload")
            
            # Convert string content to bytes if needed
            if isinstance(content, str):
                content = content.encode('utf-8')
            
            # Create temporary file
            temp_file_path = None
            try:
                temp_fd, temp_file_path = tempfile.mkstemp(suffix=Path(filename).suffix, prefix='drive_upload_')
                os.close(temp_fd)
                
                # Write content to temporary file
                with open(temp_file_path, 'wb') as temp_file:
                    temp_file.write(content)
                
                # Upload the temporary file
                return self.upload_file(temp_file_path, filename, folder_id, drive_id)
                
            finally:
                # Clean up temporary file
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.unlink(temp_file_path)
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to clean up temporary file {temp_file_path}: {cleanup_error}")
                        
        except Exception as e:
            logger.error(f"Error uploading file content {filename}: {e}")
            return None
    
    def create_nested_folder_structure(self, parent_id: str, folder_names: List[str], 
                                     drive_id: Optional[str] = None) -> Optional[str]:
        """
        Create a nested folder structure
        
        Args:
            parent_id: ID of the parent folder
            folder_names: List of folder names to create (in order)
            drive_id: Shared drive ID (optional)
            
        Returns:
            ID of the last created folder, None if failed
        """
        current_folder_id = parent_id
        
        for folder_name in folder_names:
            current_folder_id = self.find_or_create_folder(current_folder_id, folder_name, drive_id)
            if not current_folder_id:
                logger.error(f"Failed to create folder structure at: {folder_name}")
                return None
                
        return current_folder_id
    
    def list_files_in_folder(self, folder_id: str, drive_id: Optional[str] = None) -> List[Dict]:
        """
        List all files in a folder
        
        Args:
            folder_id: ID of the folder to list
            drive_id: Shared drive ID (optional)
            
        Returns:
            List of file dictionaries with 'id' and 'name' keys
        """
        if not self.drive_service:
            return []
            
        try:
            query = f"'{folder_id}' in parents and trashed=false"
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name, mimeType)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                corpora='drive' if drive_id else None,
                driveId=drive_id
            ).execute()
            
            return results.get('files', [])
            
        except Exception as e:
            logger.error(f"Error listing files in folder: {e}")
            return []
    
    def delete_file(self, file_id: str, drive_id: Optional[str] = None) -> bool:
        """
        Delete a file from Google Drive
        
        Args:
            file_id: ID of the file to delete
            drive_id: Shared drive ID (optional)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.drive_service:
            return False
            
        try:
            delete_args = dict(
                fileId=file_id,
                supportsAllDrives=True
            )
            if drive_id:
                delete_args['driveId'] = drive_id
                
            self.drive_service.files().delete(**delete_args).execute()
            logger.info(f"Deleted file with ID: {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {e}")
            return False
    
    # Legacy method for backward compatibility
    def upload_pdf_to_drive(self, pdf_content: bytes, filename: str, assessment_title: str) -> Optional[str]:
        """
        Legacy method for uploading PDFs (maintains backward compatibility)
        
        Args:
            pdf_content: PDF content as bytes
            filename: Name for the file in Drive
            assessment_title: Assessment title for folder structure
            
        Returns:
            Web view link if successful, None otherwise
        """
        if not self.drive_service or not self.base_folder_id:
            logger.info("Google Drive not available, skipping upload")
            return None
            
        try:
            # Create nested folder structure: base_folder/webhook_reports/assessment_title
            webhook_reports_folder_id = self.find_or_create_folder(self.base_folder_id, "webhook_reports")
            if not webhook_reports_folder_id:
                logger.error("Failed to create/find webhook_reports folder")
                return None
            
            assessment_folder_id = self.find_or_create_folder(webhook_reports_folder_id, assessment_title)
            if not assessment_folder_id:
                logger.error(f"Failed to create/find assessment folder: {assessment_title}")
                return None
            
            # Upload using the new method
            return self.upload_file_content(pdf_content, filename, assessment_folder_id)
            
        except Exception as e:
            logger.error(f"Error uploading PDF to Drive: {e}")
            return None