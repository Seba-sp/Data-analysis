"""
Configuration module for the multi-agent news processing pipeline.
Loads API keys, credentials, and system settings.
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()


class Config:
    """Configuration class for pipeline settings."""
    
    # API Keys
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    
    # Google Drive Configuration
    GOOGLE_DRIVE_CREDENTIALS = os.getenv('GOOGLE_DRIVE_CREDENTIALS', 'credentials.json')
    DRIVE_TOKEN_FILE = 'token.json'
    DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    # Drive Folder Structure
    DRIVE_MAIN_FOLDER_NAME = os.getenv('DRIVE_MAIN_FOLDER_NAME', 'NewsArticlesProcessing')
    
    # Processing Configuration (Batch Mode)
    CHECK_INTERVAL_SECONDS = int(os.getenv('CHECK_INTERVAL_SECONDS', '3600'))  # Legacy, not used in batch mode
    ARTICLES_PER_BATCH = 10
    DEFAULT_BATCHES = 1
    
    # PDF Context for Agent 3
    AGENT3_CONTEXT_DIR = 'agent-3-context'
    
    # File Paths
    BASE_DATA_PATH = './data'
    STATE_FILE = 'processing_state.csv'
    PROMPTS_DIR = './prompts'
    
    # Gemini Model Configuration
    # Agent 1 Mode: 'agent' (Deep Research) or 'model' (Fast with Google Search)
    AGENT1_MODE = os.getenv('AGENT1_MODE', 'agent')  # 'agent' or 'model'
    
    # Agent 1 configurations
    AGENT1_DEEP_RESEARCH = 'deep-research-pro-preview-12-2025'  # Agent mode
    AGENT1_MODEL = os.getenv('AGENT1_MODEL', 'gemini-3-pro-preview')  # Model mode
    
    # Agents 2, 3, 4 use standard model
    GEMINI_MODEL_AGENTS234 = os.getenv('GEMINI_MODEL_AGENTS234', 'gemini-2.0-flash-exp')
    
    # Legacy config for backwards compatibility
    GEMINI_MODEL_AGENT1 = AGENT1_DEEP_RESEARCH
    GEMINI_MODEL = GEMINI_MODEL_AGENTS234
    
    TEMPERATURE = 1
    MAX_OUTPUT_TOKENS = 100000
    
    # Document Generation Settings
    PDF_FONT_SIZE = 12
    WORD_FONT_NAME = 'Arial'
    WORD_FONT_SIZE = 11
    
    # Spanish Number Format Settings
    DECIMAL_SEPARATOR = ','
    THOUSANDS_SEPARATOR = '.'
    
    @classmethod
    def validate(cls) -> list[str]:
        """
        Validate configuration settings.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        if not cls.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY is not set in environment variables")
        
        if not os.path.exists(cls.GOOGLE_DRIVE_CREDENTIALS):
            errors.append(f"Google Drive credentials file not found: {cls.GOOGLE_DRIVE_CREDENTIALS}")
        
        # Create necessary directories
        os.makedirs(cls.BASE_DATA_PATH, exist_ok=True)
        os.makedirs(cls.PROMPTS_DIR, exist_ok=True)
        
        return errors
    
    @classmethod
    def get_prompt_path(cls, prompt_name: str) -> str:
        """
        Get absolute path to a prompt file.
        
        Args:
            prompt_name: Name of the prompt file (e.g., 'agent1_prompt.txt')
            
        Returns:
            Absolute path to prompt file
        """
        # Get the directory where this config.py file is located (project root)
        project_root = Path(__file__).parent.absolute()
        prompts_dir = project_root / 'prompts'
        prompt_path = prompts_dir / prompt_name
        return str(prompt_path)


# Global config instance
config = Config()

