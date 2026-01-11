"""
State management system to track article processing status.
Maintains a CSV file with processing state for all articles.
"""
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict
from storage import storage
from config import config


class StateManager:
    """Manages processing state for articles."""
    
    def __init__(self, state_file: str = None):
        """
        Initialize state manager.
        
        Args:
            state_file: Path to state CSV file (defaults to config setting)
        """
        self.state_file = state_file or config.STATE_FILE
        self._initialize_state_file()
    
    def _initialize_state_file(self):
        """Initialize state file if it doesn't exist."""
        if not storage.exists(self.state_file):
            # Create empty state DataFrame with required columns
            df = pd.DataFrame(columns=[
                'article_id',
                'title',
                'url',
                'source',
                'date',
                'license_status',
                'license_type',
                'processing_status',
                'questions_generated',
                'questions_improved',
                'uploaded_to_drive',
                'created_date',
                'processed_date',
                'error_message'
            ])
            storage.write_csv(df, self.state_file)
    
    def load_state(self) -> pd.DataFrame:
        """
        Load current state from CSV.
        
        Returns:
            DataFrame with current processing state
        """
        return storage.read_csv(self.state_file)
    
    def save_state(self, df: pd.DataFrame):
        """
        Save state DataFrame to CSV.
        
        Args:
            df: State DataFrame to save
        """
        storage.write_csv(df, self.state_file)
    
    def add_articles(self, articles: List[Dict]) -> List[str]:
        """
        Add new articles to state tracking.
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            List of article IDs added
        """
        df = self.load_state()
        article_ids = []
        
        for article in articles:
            article_id = self._generate_article_id(article)
            article_ids.append(article_id)
            
            # Check if article already exists (only if we have the column)
            if not df.empty and 'article_id' in df.columns and article_id in df['article_id'].values:
                continue
            
            # Add new article
            new_row = {
                'article_id': article_id,
                'title': article.get('title', ''),
                'url': article.get('url', ''),
                'source': article.get('source', ''),
                'date': article.get('date', ''),
                'license_status': '',
                'license_type': '',
                'processing_status': 'pending',
                'questions_generated': False,
                'questions_improved': False,
                'uploaded_to_drive': False,
                'created_date': datetime.now().isoformat(),
                'processed_date': '',
                'error_message': ''
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        
        self.save_state(df)
        return article_ids
    
    def update_license_validation(self, article_id: str, license_status: str, 
                                  license_type: str, validation_reason: str = ""):
        """
        Update license validation results for an article.
        
        Args:
            article_id: Article identifier
            license_status: Validation status (cc_valid, cc_invalid, no_license)
            license_type: Type of Creative Commons license
            validation_reason: Reason for validation result
        """
        df = self.load_state()
        
        # Handle empty DataFrame or missing columns
        if df.empty or 'article_id' not in df.columns:
            return
        
        mask = df['article_id'] == article_id
        
        if mask.any():
            # Use explicit str dtype to avoid FutureWarning
            df.loc[mask, 'license_status'] = str(license_status)
            df.loc[mask, 'license_type'] = str(license_type)
            
            # Update processing status based on license
            if license_status == 'cc_valid':
                df.loc[mask, 'processing_status'] = str('validated')
            else:
                df.loc[mask, 'processing_status'] = str('rejected')
                df.loc[mask, 'error_message'] = str(validation_reason)
            
            self.save_state(df)
    
    def mark_questions_generated(self, article_id: str):
        """
        Mark that initial questions have been generated for an article.
        
        Args:
            article_id: Article identifier
        """
        df = self.load_state()
        
        # Handle empty DataFrame or missing columns
        if df.empty or 'article_id' not in df.columns:
            return
        
        mask = df['article_id'] == article_id
        
        if mask.any():
            df.loc[mask, 'questions_generated'] = True
            df.loc[mask, 'processing_status'] = 'questions_generated'
            self.save_state(df)
    
    def mark_questions_improved(self, article_id: str):
        """
        Mark that questions have been improved for an article.
        
        Args:
            article_id: Article identifier
        """
        df = self.load_state()
        
        # Handle empty DataFrame or missing columns
        if df.empty or 'article_id' not in df.columns:
            return
        
        mask = df['article_id'] == article_id
        
        if mask.any():
            df.loc[mask, 'questions_improved'] = True
            df.loc[mask, 'processing_status'] = 'questions_improved'
            self.save_state(df)
    
    def mark_article_processed(self, article_id: str, uploaded: bool = True):
        """
        Mark an article as fully processed and uploaded.
        
        Args:
            article_id: Article identifier
            uploaded: Whether files were uploaded to Drive
        """
        df = self.load_state()
        
        # Handle empty DataFrame or missing columns
        if df.empty or 'article_id' not in df.columns:
            return
        
        mask = df['article_id'] == article_id
        
        if mask.any():
            df.loc[mask, 'processing_status'] = str('completed')
            df.loc[mask, 'uploaded_to_drive'] = bool(uploaded)
            df.loc[mask, 'processed_date'] = str(datetime.now().isoformat())
            self.save_state(df)
    
    def mark_error(self, article_id: str, error_message: str):
        """
        Mark an article as having an error during processing.
        
        Args:
            article_id: Article identifier
            error_message: Error description
        """
        df = self.load_state()
        
        # Handle empty DataFrame or missing columns
        if df.empty or 'article_id' not in df.columns:
            return
        
        mask = df['article_id'] == article_id
        
        if mask.any():
            df.loc[mask, 'processing_status'] = 'error'
            df.loc[mask, 'error_message'] = error_message
            self.save_state(df)
    
    def get_validated_articles(self) -> List[Dict]:
        """
        Get all validated articles that need processing.
        
        Returns:
            List of validated article dictionaries
        """
        df = self.load_state()
        
        # Handle empty DataFrame or missing columns
        if df.empty or 'license_status' not in df.columns:
            return []
        
        validated = df[df['license_status'] == 'cc_valid']
        return validated.to_dict('records')
    
    def get_pending_articles(self) -> List[Dict]:
        """
        Get articles pending question generation.
        
        Returns:
            List of article dictionaries
        """
        df = self.load_state()
        
        # Handle empty DataFrame or missing columns
        if df.empty or 'license_status' not in df.columns or 'processing_status' not in df.columns:
            return []
        
        pending = df[
            (df['license_status'] == 'cc_valid') & 
            (df['processing_status'].isin(['validated', 'questions_generated']))
        ]
        return pending.to_dict('records')
    
    def get_article_by_id(self, article_id: str) -> Optional[Dict]:
        """
        Get article information by ID.
        
        Args:
            article_id: Article identifier
            
        Returns:
            Article dictionary or None if not found
        """
        df = self.load_state()
        
        # Handle empty DataFrame or missing columns
        if df.empty or 'article_id' not in df.columns:
            return
        
        mask = df['article_id'] == article_id
        
        if mask.any():
            return df[mask].iloc[0].to_dict()
        return None
    
    def get_statistics(self) -> Dict:
        """
        Get processing statistics.
        
        Returns:
            Dictionary with statistics
        """
        df = self.load_state()
        
        # Handle empty DataFrame or missing columns
        if df.empty or 'license_status' not in df.columns or 'processing_status' not in df.columns:
            return {
                'total_articles': 0,
                'validated': 0,
                'rejected': 0,
                'completed': 0,
                'pending': 0,
                'in_progress': 0,
                'errors': 0
            }
        
        return {
            'total_articles': len(df),
            'validated': len(df[df['license_status'] == 'cc_valid']),
            'rejected': len(df[df['license_status'] != 'cc_valid']),
            'completed': len(df[df['processing_status'] == 'completed']),
            'pending': len(df[df['processing_status'] == 'pending']),
            'in_progress': len(df[df['processing_status'].isin(['validated', 'questions_generated'])]),
            'errors': len(df[df['processing_status'] == 'error'])
        }
    
    def get_processed_urls(self) -> List[str]:
        """
        Get list of all processed article URLs for duplicate prevention.
        
        Returns:
            List of URLs that have been processed
        """
        df = self.load_state()
        
        # Handle empty DataFrame or missing url column
        if df.empty or 'url' not in df.columns:
            return []
        
        # Get all URLs that are not empty
        urls = df[df['url'].notna() & (df['url'] != '')]['url'].tolist()
        return urls
    
    def is_duplicate(self, url: str) -> bool:
        """
        Check if a URL has already been processed.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL exists in state, False otherwise
        """
        if not url:
            return False
        
        df = self.load_state()
        
        # Handle empty DataFrame or missing url column
        if df.empty or 'url' not in df.columns:
            return False
        
        return url in df['url'].values
    
    def get_processed_count(self) -> int:
        """
        Get total count of processed articles.
        
        Returns:
            Number of articles that have been processed
        """
        df = self.load_state()
        return len(df)
    
    def _generate_article_id(self, article: Dict) -> str:
        """
        Generate unique article ID from article data.
        
        Args:
            article: Article dictionary
            
        Returns:
            Unique article identifier
        """
        # Use URL as base for ID, or create from title and source
        if 'url' in article and article['url']:
            # Clean URL to create ID
            import hashlib
            return hashlib.md5(article['url'].encode()).hexdigest()[:12]
        else:
            # Fallback to title + source hash
            import hashlib
            data = f"{article.get('title', '')}_{article.get('source', '')}"
            return hashlib.md5(data.encode()).hexdigest()[:12]
    
    def get_last_id(self) -> Optional[str]:
        """Get the last article ID used (for continuing numbering)."""
        df = self.load_state()
        
        # Handle empty DataFrame or missing columns
        if df.empty or 'article_id' not in df.columns:
            return None
        
        # Extract article IDs and find the highest number
        article_ids = df['article_id'].dropna().tolist()
        if not article_ids:
            return None
        
        # Find the highest numeric ID (e.g., C030 -> 30)
        import re
        max_num = 0
        max_id = None
        
        for aid in article_ids:
            match = re.search(r'C(\d+)', str(aid))
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num
                    max_id = aid
        
        return max_id


# Global state manager instance
state_manager = StateManager()

