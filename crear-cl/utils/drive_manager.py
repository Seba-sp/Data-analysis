"""
Google Drive manager for file uploads and folder organization.
Handles authentication and file management in Google Drive.
"""
import os
import pickle
from typing import Optional, List, Dict
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from config import config


class DriveManager:
    """Manages Google Drive operations."""
    
    def __init__(self):
        """Initialize Drive manager (authentication happens on first use)."""
        self.service = None
        self.main_folder_id = None
        self._authenticated = False
    
    def _ensure_authenticated(self):
        """Ensure authentication has been done."""
        if not self._authenticated:
            self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Drive API."""
        if self._authenticated:
            return
        
        creds = None
        
        # Load existing credentials
        if os.path.exists(config.DRIVE_TOKEN_FILE):
            with open(config.DRIVE_TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(config.GOOGLE_DRIVE_CREDENTIALS):
                    raise FileNotFoundError(
                        f"Google Drive credentials file not found: {config.GOOGLE_DRIVE_CREDENTIALS}\n"
                        "Please download credentials.json from Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    config.GOOGLE_DRIVE_CREDENTIALS, 
                    config.DRIVE_SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials
            with open(config.DRIVE_TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('drive', 'v3', credentials=creds)
        self._authenticated = True
    
    def get_or_create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        """
        Get existing folder ID or create new folder.
        
        Args:
            folder_name: Name of the folder
            parent_id: Parent folder ID (None for root)
            
        Returns:
            Folder ID
        """
        self._ensure_authenticated()
        
        try:
            # Search for existing folder
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            files = results.get('files', [])
            
            if files:
                return files[0]['id']
            
            # Create new folder
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            return folder['id']
        
        except HttpError as error:
            print(f"Error creating/getting folder: {error}")
            raise
    
    def create_main_folder(self) -> str:
        """
        Create or get the main project folder.
        
        Returns:
            Main folder ID
        """
        if not self.main_folder_id:
            self.main_folder_id = self.get_or_create_folder(config.DRIVE_MAIN_FOLDER_NAME)
        return self.main_folder_id
    
    def create_article_folder(self, article_title: str) -> str:
        """
        Create folder for a specific article.
        
        Args:
            article_title: Title of the article
            
        Returns:
            Article folder ID
        """
        # Clean title for folder name
        clean_title = self._clean_filename(article_title)
        
        # Ensure main folder exists
        main_folder_id = self.create_main_folder()
        
        # Create article folder
        folder_id = self.get_or_create_folder(clean_title, main_folder_id)
        return folder_id
    
    def upload_file(self, file_path: str, folder_id: str, 
                   mime_type: Optional[str] = None) -> str:
        """
        Upload file to Google Drive folder.
        
        Args:
            file_path: Local path to file
            folder_id: Drive folder ID
            mime_type: MIME type of file (auto-detected if None)
            
        Returns:
            Uploaded file ID
        """
        self._ensure_authenticated()
        
        try:
            file_name = os.path.basename(file_path)
            
            file_metadata = {
                'name': file_name,
                'parents': [folder_id]
            }
            
            # Auto-detect MIME type if not provided
            if not mime_type:
                mime_type = self._get_mime_type(file_path)
            
            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            return file['id']
        
        except HttpError as error:
            print(f"Error uploading file: {error}")
            raise
    
    def upload_article_package(self, article: Dict,
                              questions_initial_path: str, 
                              questions_improved_path: str) -> Dict[str, str]:
        """
        Upload complete article package to Drive.
        
        Args:
            article: Article dictionary with metadata
            questions_initial_path: Path to initial questions Word doc
            questions_improved_path: Path to improved questions Word doc
            
        Returns:
            Dictionary with uploaded file IDs
        """
        # Create article folder
        article_folder_id = self.create_article_folder(article.get('title', 'Untitled'))
        
        # Upload files
        uploaded_ids = {}
        
        if os.path.exists(questions_initial_path):
            uploaded_ids['questions_initial'] = self.upload_file(
                questions_initial_path,
                article_folder_id,
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
        
        if os.path.exists(questions_improved_path):
            uploaded_ids['questions_improved'] = self.upload_file(
                questions_improved_path,
                article_folder_id,
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
        
        return uploaded_ids
    
    def upload_master_csv(self, csv_path: str) -> str:
        """
        Upload master CSV to main folder.
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            Uploaded file ID
        """
        main_folder_id = self.create_main_folder()
        
        # Check if master CSV already exists and delete it
        try:
            query = f"name='validated_articles.csv' and '{main_folder_id}' in parents and trashed=false"
            results = self.service.files().list(q=query, fields='files(id)').execute()
            files = results.get('files', [])
            
            for file in files:
                self.service.files().delete(fileId=file['id']).execute()
        except HttpError as error:
            print(f"Error deleting old CSV: {error}")
        
        # Upload new CSV
        return self.upload_file(csv_path, main_folder_id, 'text/csv')
    
    def _clean_filename(self, filename: str) -> str:
        """
        Clean filename for Drive compatibility.
        
        Args:
            filename: Original filename
            
        Returns:
            Cleaned filename
        """
        # Remove invalid characters
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        clean = filename
        for char in invalid_chars:
            clean = clean.replace(char, '_')
        
        # Limit length
        if len(clean) > 100:
            clean = clean[:100]
        
        return clean.strip()
    
    def _get_mime_type(self, file_path: str) -> str:
        """
        Get MIME type based on file extension.
        
        Args:
            file_path: Path to file
            
        Returns:
            MIME type string
        """
        extension = os.path.splitext(file_path)[1].lower()
        
        mime_types = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword',
            '.csv': 'text/csv',
            '.txt': 'text/plain',
            '.json': 'application/json'
        }
        
        return mime_types.get(extension, 'application/octet-stream')
    
    def list_folder_contents(self, folder_id: str) -> List[Dict]:
        """
        List contents of a folder.
        
        Args:
            folder_id: Drive folder ID
            
        Returns:
            List of file metadata dictionaries
        """
        self._ensure_authenticated()
        
        try:
            results = self.service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields='files(id, name, mimeType, createdTime)'
            ).execute()
            
            return results.get('files', [])
        
        except HttpError as error:
            print(f"Error listing folder contents: {error}")
            return []


# Global drive manager instance
drive_manager = DriveManager()

