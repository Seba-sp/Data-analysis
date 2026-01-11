"""
Storage abstraction for file I/O operations.
Handles reading, writing, saving, and deleting files with Spanish number formatting support.
"""
import os
import pandas as pd
from typing import Any, Optional
import json


class Storage:
    """Storage abstraction for all file I/O operations."""
    
    def __init__(self, base_path: str = "./data"):
        """
        Initialize storage with base path.
        
        Args:
            base_path: Base directory for file operations
        """
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
    
    def _get_full_path(self, file_path: str) -> str:
        """Get full path for a file."""
        if os.path.isabs(file_path):
            return file_path
        return os.path.join(self.base_path, file_path)
    
    def read_csv(self, file_path: str, **kwargs) -> pd.DataFrame:
        """
        Read CSV file with Spanish number formatting support.
        
        Args:
            file_path: Path to CSV file
            **kwargs: Additional arguments for pd.read_csv
            
        Returns:
            DataFrame with loaded data
        """
        full_path = self._get_full_path(file_path)
        
        # Default settings for Spanish number format
        default_kwargs = {
            'decimal': ',',
            'thousands': '.'
        }
        default_kwargs.update(kwargs)
        
        if not os.path.exists(full_path):
            # Return empty DataFrame if file doesn't exist
            return pd.DataFrame()
        
        return pd.read_csv(full_path, **default_kwargs)
    
    def write_csv(self, df: pd.DataFrame, file_path: str, **kwargs) -> str:
        """
        Write DataFrame to CSV with Spanish number formatting.
        
        Args:
            df: DataFrame to write
            file_path: Path to save CSV
            **kwargs: Additional arguments for pd.to_csv
            
        Returns:
            Full path to saved file
        """
        full_path = self._get_full_path(file_path)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Default settings for Spanish number format
        default_kwargs = {
            'index': False,
            'decimal': ',',
        }
        default_kwargs.update(kwargs)
        
        df.to_csv(full_path, **default_kwargs)
        return full_path
    
    def read_json(self, file_path: str) -> Any:
        """
        Read JSON file.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            Parsed JSON data
        """
        full_path = self._get_full_path(file_path)
        
        if not os.path.exists(full_path):
            return None
        
        with open(full_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def write_json(self, data: Any, file_path: str, indent: int = 2) -> str:
        """
        Write data to JSON file.
        
        Args:
            data: Data to write
            file_path: Path to save JSON
            indent: JSON indentation level
            
        Returns:
            Full path to saved file
        """
        full_path = self._get_full_path(file_path)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        
        return full_path
    
    def read_text(self, file_path: str, encoding: str = 'utf-8') -> str:
        """
        Read text file.
        
        Args:
            file_path: Path to text file
            encoding: File encoding
            
        Returns:
            File contents as string
        """
        full_path = self._get_full_path(file_path)
        
        if not os.path.exists(full_path):
            return ""
        
        with open(full_path, 'r', encoding=encoding) as f:
            return f.read()
    
    def write_text(self, content: str, file_path: str, encoding: str = 'utf-8') -> str:
        """
        Write text to file.
        
        Args:
            content: Text content to write
            file_path: Path to save file
            encoding: File encoding
            
        Returns:
            Full path to saved file
        """
        full_path = self._get_full_path(file_path)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w', encoding=encoding) as f:
            f.write(content)
        
        return full_path
    
    def save_text(self, content: str, filename: str, folder: str = '', encoding: str = 'utf-8') -> str:
        """
        Save text content to a file in a specific folder.
        
        Args:
            content: Text content to save
            filename: Name of the file
            folder: Subfolder within base_path (optional)
            encoding: File encoding
            
        Returns:
            Full path to saved file
        """
        if folder:
            file_path = os.path.join(folder, filename)
        else:
            file_path = filename
        
        return self.write_text(content, file_path, encoding)
    
    def delete(self, file_path: str) -> bool:
        """
        Delete a file.
        
        Args:
            file_path: Path to file to delete
            
        Returns:
            True if deleted, False if file didn't exist
        """
        full_path = self._get_full_path(file_path)
        
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
        return False
    
    def exists(self, file_path: str) -> bool:
        """
        Check if file exists.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file exists, False otherwise
        """
        full_path = self._get_full_path(file_path)
        return os.path.exists(full_path)
    
    def list_files(self, directory: str = "", pattern: Optional[str] = None) -> list[str]:
        """
        List files in directory.
        
        Args:
            directory: Directory to list (relative to base_path)
            pattern: Optional file pattern (e.g., "*.csv")
            
        Returns:
            List of file paths
        """
        full_path = self._get_full_path(directory)
        
        if not os.path.exists(full_path):
            return []
        
        files = []
        for item in os.listdir(full_path):
            item_path = os.path.join(full_path, item)
            if os.path.isfile(item_path):
                if pattern is None or item.endswith(pattern.replace("*", "")):
                    files.append(item)
        
        return files


# Global storage instance
storage = Storage()

