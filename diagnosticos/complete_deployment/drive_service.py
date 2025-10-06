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
            
            # Add drive ID to query if provided
            if drive_id:
                query += f" and '{drive_id}' in parents"
            
            results = self.drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            files = results.get('files', [])
            
            if files:
                # Folder already exists, return its ID
                folder_id = files[0]['id']
                logger.info(f"Found existing folder: {folder_name} (ID: {folder_id})")
                return folder_id
            else:
                # Create new folder
                folder_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [parent_folder_id]
                }
                
                # Add to shared drive if specified
                if drive_id:
                    folder_metadata['parents'] = [drive_id]
                
                folder = self.drive_service.files().create(
                    body=folder_metadata,
                    supportsAllDrives=True,
                    fields='id'
                ).execute()
                
                folder_id = folder.get('id')
                logger.info(f"Created new folder: {folder_name} (ID: {folder_id})")
                return folder_id
                
        except Exception as e:
            logger.error(f"Error finding/creating folder {folder_name}: {e}")
            return None
    
    def upload_file(self, file_path: Union[str, Path], folder_id: str, filename: Optional[str] = None, 
                   mime_type: Optional[str] = None) -> Optional[str]:
        """
        Upload a file to Google Drive
        
        Args:
            file_path: Path to the file to upload
            folder_id: ID of the folder to upload to
            filename: Optional custom filename
            mime_type: Optional MIME type
            
        Returns:
            File ID if successful, None otherwise
        """
        if not self.drive_service:
            logger.warning("Google Drive service not available")
            return None
        
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return None
            
            # Determine filename
            if filename is None:
                filename = file_path.name
            
            # Determine MIME type
            if mime_type is None:
                mime_type = self._get_mime_type(file_path)
            
            # Create file metadata
            file_metadata = {
                'name': filename,
                'parents': [folder_id]
            }
            
            # Upload file
            media = MediaFileUpload(str(file_path), mimetype=mime_type, resumable=True)
            
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                supportsAllDrives=True,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            logger.info(f"Uploaded file: {filename} (ID: {file_id})")
            return file_id
            
        except Exception as e:
            logger.error(f"Error uploading file {file_path}: {e}")
            return None
    
    def upload_bytes(self, content: bytes, filename: str, folder_id: str, 
                    mime_type: Optional[str] = None) -> Optional[str]:
        """
        Upload bytes content to Google Drive
        
        Args:
            content: File content as bytes
            filename: Name for the file
            folder_id: ID of the folder to upload to
            mime_type: Optional MIME type
            
        Returns:
            File ID if successful, None otherwise
        """
        if not self.drive_service:
            logger.warning("Google Drive service not available")
            return None
        
        try:
            # Determine MIME type
            if mime_type is None:
                mime_type = self._get_mime_type_from_filename(filename)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            try:
                # Upload the temporary file
                return self.upload_file(temp_file_path, folder_id, filename, mime_type)
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            logger.error(f"Error uploading bytes as {filename}: {e}")
            return None
    
    def _get_mime_type(self, file_path: Path) -> str:
        """Get MIME type from file extension"""
        return self._get_mime_type_from_filename(file_path.name)
    
    def _get_mime_type_from_filename(self, filename: str) -> str:
        """Get MIME type from filename"""
        extension = Path(filename).suffix.lower()
        
        mime_types = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.xls': 'application/vnd.ms-excel',
            '.csv': 'text/csv',
            '.txt': 'text/plain',
            '.json': 'application/json',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.html': 'text/html',
            '.htm': 'text/html'
        }
        
        return mime_types.get(extension, 'application/octet-stream')
    
    def get_file_link(self, file_id: str) -> Optional[str]:
        """
        Get a shareable link for a file
        
        Args:
            file_id: ID of the file
            
        Returns:
            Shareable link if successful, None otherwise
        """
        if not self.drive_service:
            logger.warning("Google Drive service not available")
            return None
        
        try:
            # Create a shareable link
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            
            self.drive_service.permissions().create(
                fileId=file_id,
                body=permission,
                supportsAllDrives=True
            ).execute()
            
            # Get the file to get the webViewLink
            file = self.drive_service.files().get(
                fileId=file_id,
                fields='webViewLink',
                supportsAllDrives=True
            ).execute()
            
            return file.get('webViewLink')
            
        except Exception as e:
            logger.error(f"Error getting file link for {file_id}: {e}")
            return None
    
    def upload_to_organized_folder(self, file_path: Union[str, Path], assessment_title: str, 
                                 filename: Optional[str] = None) -> Optional[Dict[str, str]]:
        """
        Upload file to an organized folder structure
        
        Args:
            file_path: Path to the file to upload
            assessment_title: Assessment title for folder organization
            filename: Optional custom filename
            
        Returns:
            Dict with file_id and link if successful, None otherwise
        """
        if not self.base_folder_id:
            logger.warning("No base folder ID configured")
            return None
        
        try:
            # Create assessment folder
            assessment_folder_id = self.find_or_create_folder(
                self.base_folder_id, 
                assessment_title,
                self.drive_id
            )
            
            if not assessment_folder_id:
                logger.error(f"Failed to create/find folder for {assessment_title}")
                return None
            
            # Upload file
            file_id = self.upload_file(file_path, assessment_folder_id, filename)
            
            if not file_id:
                logger.error(f"Failed to upload file {file_path}")
                return None
            
            # Get shareable link
            link = self.get_file_link(file_id)
            
            return {
                'file_id': file_id,
                'link': link
            }
            
        except Exception as e:
            logger.error(f"Error uploading to organized folder: {e}")
            return None
