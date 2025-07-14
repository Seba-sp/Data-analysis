"""
Google Cloud Function for automated course data analysis pipeline
Runs daily at 8am Santiago time, processes all courses, uploads to Cloud Storage,
saves reports to Google Drive, and sends Slack notifications.
"""

import os
import json
import tempfile
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any
import pytz
import functions_framework

# Google Cloud imports
from google.cloud import storage
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Slack imports
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Local imports (these will be packaged with the function)
from descarga_procesa_datos import run_full_pipeline as run_download_pipeline
from analisis import run_analysis_pipeline as run_analysis_pipeline
from batch_process import load_course_config

# Configure logging for Cloud Functions
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables with defaults for local testing
PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'your-project-id')
BUCKET_NAME = os.environ.get('GCP_BUCKET_NAME', 'your-bucket-name')
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN', '')
SLACK_CHANNEL = os.environ.get('SLACK_CHANNEL', '#general')
GOOGLE_DRIVE_FOLDER_ID = os.environ.get('GOOGLE_DRIVE_FOLDER_ID', '')
IGNORED_USERS = os.environ.get('IGNORED_USERS', '').split(',') if os.environ.get('IGNORED_USERS') else []

# Initialize clients
storage_client = None
bucket = None

def initialize_clients():
    """Initialize Google Cloud clients"""
    global storage_client, bucket
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        logger.info(f"Initialized Cloud Storage client for bucket: {BUCKET_NAME}")
    except Exception as e:
        logger.error(f"Failed to initialize Cloud Storage client: {e}")
        raise

def get_slack_client():
    """Initialize Slack client"""
    if not SLACK_BOT_TOKEN:
        logger.warning("SLACK_BOT_TOKEN not configured")
        return None
    return WebClient(token=SLACK_BOT_TOKEN)

def get_drive_service():
    """Initialize Google Drive service"""
    import base64
    
    # Get the service account key (could be base64 encoded or raw JSON)
    service_account_key = os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY')
    
    if not service_account_key:
        logger.error("GOOGLE_SERVICE_ACCOUNT_KEY environment variable not set")
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_KEY not configured")
    
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
            scopes=['https://www.googleapis.com/auth/drive.file']
        )
        return build('drive', 'v3', credentials=credentials)
    except Exception as e:
        logger.error(f"Error parsing service account key: {e}")
        raise

def upload_to_cloud_storage(local_path: str, gcs_path: str) -> str:
    """Upload file to Google Cloud Storage"""
    if not storage_client or not bucket:
        initialize_clients()
    
    try:
        blob = bucket.blob(gcs_path)
        blob.upload_from_filename(local_path)
        logger.info(f"Uploaded {local_path} to gs://{BUCKET_NAME}/{gcs_path}")
        return f"gs://{BUCKET_NAME}/{gcs_path}"
    except Exception as e:
        logger.error(f"Error uploading to Cloud Storage: {e}")
        raise

def upload_directory_to_gcs(local_dir: str, gcs_prefix: str) -> List[str]:
    """Upload entire directory to Cloud Storage"""
    uploaded_files = []
    
    for root, dirs, files in os.walk(local_dir):
        for file in files:
            local_path = os.path.join(root, file)
            # Calculate relative path from local_dir
            rel_path = os.path.relpath(local_path, local_dir)
            gcs_path = f"{gcs_prefix}/{rel_path}".replace('\\', '/')
            
            try:
                gcs_url = upload_to_cloud_storage(local_path, gcs_path)
                uploaded_files.append(gcs_url)
            except Exception as e:
                logger.error(f"Failed to upload {local_path}: {e}")
    
    return uploaded_files

def upload_report_to_drive(file_path: str, filename: str) -> str:
    """Upload report file to Google Drive"""
    try:
        drive_service = get_drive_service()
        
        file_metadata = {
            'name': filename,
            'parents': [GOOGLE_DRIVE_FOLDER_ID]
        }
        
        media = MediaFileUpload(file_path, resumable=True)
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,webViewLink'
        ).execute()
        
        logger.info(f"Uploaded {filename} to Google Drive: {file.get('webViewLink')}")
        return file.get('webViewLink')
        
    except Exception as e:
        logger.error(f"Error uploading to Google Drive: {e}")
        raise

def send_slack_notification(course_results: List[Dict[str, Any]]):
    """Send Slack notification with results summary"""
    slack_client = get_slack_client()
    if not slack_client:
        logger.warning("Slack client not available, skipping notification")
        return
    
    try:
        # Create message blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📊 Reporte Diario de Análisis de Cursos"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Análisis completado:* {datetime.now(pytz.timezone('America/Santiago')).strftime('%Y-%m-%d %H:%M:%S %Z')}"
                }
            }
        ]
        
        # Add course results
        for result in course_results:
            course_name = result.get('course_name', result.get('course_id', 'Unknown'))
            status = result.get('status', 'Unknown')
            drive_links = result.get('drive_links', [])
            
            # Create course section
            course_text = f"*{course_name}*\n"
            course_text += f"Estado: {status}\n"
            
            if drive_links:
                course_text += "Archivos:\n"
                for link in drive_links:
                    course_text += f"• <{link}|Ver Archivo>\n"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": course_text
                }
            })
        
        # Add divider
        blocks.append({"type": "divider"})
        
        # Add footer
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "🤖 Automatizado por Google Cloud Function"
                }
            ]
        })
        
        # Create fallback text for accessibility
        fallback_text = f"📊 Reporte Diario de Análisis de Cursos\nAnálisis completado: {datetime.now(pytz.timezone('America/Santiago')).strftime('%Y-%m-%d %H:%M:%S %Z')}"
        for result in course_results:
            course_name = result.get('course_name', result.get('course_id', 'Unknown'))
            status = result.get('status', 'Unknown')
            fallback_text += f"\n{course_name}: {status}"
        
        # Send message
        slack_client.chat_postMessage(
            channel=SLACK_CHANNEL,
            text=fallback_text,  # Required for accessibility
            blocks=blocks
        )
        
        logger.info("Slack notification sent successfully")
        
    except SlackApiError as e:
        logger.error(f"Slack API error: {e.response['error']}")
    except Exception as e:
        logger.error(f"Error sending Slack notification: {e}")

def process_course(course_id: str, course_config: Dict[str, Any], up_to_date: bool = False) -> Dict[str, Any]:
    """Process a single course and return results"""
    result = {
        'course_id': course_id,
        'course_name': course_config.get('name', course_id),
        'status': 'success',
        'drive_links': [],
        'gcs_files': [],
        'up_to_date_filter': up_to_date
    }
    
    try:
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory for processing
            original_cwd = os.getcwd()
            os.chdir(temp_dir)
            
            # Create data directory structure
            os.makedirs('data/raw', exist_ok=True)
            os.makedirs('data/processed', exist_ok=True)
            os.makedirs('data/reports', exist_ok=True)
            os.makedirs('data/planification', exist_ok=True)
            
            # Copy configuration files
            # Note: In production, these should be stored in Cloud Storage or environment variables
            with open('cursos.yml', 'w') as f:
                import yaml
                yaml.dump({'courses': {course_id: course_config}}, f)
            
            # Copy planification file if it exists
            planification_source = f"data/planification/{course_id}.csv"
            if os.path.exists(planification_source):
                import shutil
                shutil.copy2(planification_source, f"data/planification/{course_id}.csv")
                logger.info(f"Copied planification file for {course_id}")
            
            # Run download pipeline (now handles Cloud Storage uploads directly)
            logger.info(f"Starting download pipeline for {course_id}")
            run_download_pipeline(course_id)
            
            # Run analysis pipeline with upload enabled and up-to-date filtering if requested
            logger.info(f"Starting analysis pipeline for {course_id}")
            if up_to_date:
                logger.info(f"Up-to-date filtering enabled for {course_id}")
            run_analysis_pipeline(course_id, upload_reports=True, filter_up_to_date=up_to_date)
            
            # Note: Raw data is now uploaded directly to Cloud Storage by the download pipeline
            # Processed data and reports are uploaded by the analysis pipeline
            # Track the Cloud Storage paths for reporting
            result['gcs_files'].extend([
                f"gs://{BUCKET_NAME}/raw/{course_id}/assessments.json",
                f"gs://{BUCKET_NAME}/raw/{course_id}/grades.json", 
                f"gs://{BUCKET_NAME}/raw/{course_id}/users.json"
            ])
            
            # Restore original working directory
            os.chdir(original_cwd)
            
    except Exception as e:
        logger.error(f"Error processing course {course_id}: {e}")
        result['status'] = 'error'
        result['error'] = str(e)
    
    return result

@functions_framework.http
def course_analysis_pipeline(request):
    """
    Main Cloud Function entry point for HTTP triggers
    
    Args:
        request: Flask request object
        
    Returns:
        Flask response object with JSON data
    """
    # Set CORS headers for web requests
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    
    headers = {'Access-Control-Allow-Origin': '*'}
    
    try:
        logger.info("Starting daily course analysis pipeline")
        
        # Initialize clients
        initialize_clients()
        
        # Load course configuration
        config = load_course_config()
        courses = config.get('courses', {})
        
        if not courses:
            logger.error("No courses found in configuration")
            return (json.dumps({'error': 'No courses configured'}), 400, headers)
        
        # Check if up-to-date filtering is requested
        request_data = request.get_json() if request.is_json else {}
        up_to_date = request_data.get('up_to_date', False)
        
        if up_to_date:
            logger.info("Up-to-date filtering enabled for all courses")
        
        logger.info(f"Processing {len(courses)} courses")
        
        # Process each course
        course_results = []
        for course_id, course_config in courses.items():
            logger.info(f"Processing course: {course_id}")
            result = process_course(course_id, course_config, up_to_date=up_to_date)
            course_results.append(result)
            
            if result['status'] == 'success':
                logger.info(f"Successfully processed {course_id}")
            else:
                logger.error(f"Failed to process {course_id}: {result.get('error', 'Unknown error')}")
        
        # Send Slack notification
        send_slack_notification(course_results)
        
        # Return summary
        successful_courses = [r for r in course_results if r['status'] == 'success']
        failed_courses = [r for r in course_results if r['status'] == 'error']
        
        summary = {
            'total_courses': len(courses),
            'successful': len(successful_courses),
            'failed': len(failed_courses),
            'up_to_date_filter': up_to_date,
            'results': course_results
        }
        
        logger.info(f"Pipeline completed. {len(successful_courses)} successful, {len(failed_courses)} failed")
        
        return (json.dumps(summary, indent=2), 200, headers)
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        return (json.dumps({'error': str(e)}, indent=2), 500, headers)

# For local testing
if __name__ == "__main__":
    # Simulate Cloud Function environment
    os.environ.setdefault('GCP_PROJECT_ID', 'your-project-id')
    os.environ.setdefault('GCP_BUCKET_NAME', 'your-bucket-name')
    os.environ.setdefault('SLACK_BOT_TOKEN', 'your-slack-token')
    os.environ.setdefault('SLACK_CHANNEL', '#your-channel')
    os.environ.setdefault('GOOGLE_DRIVE_FOLDER_ID', 'your-folder-id')
    
    # Mock request object
    class MockRequest:
        def __init__(self):
            self.method = 'POST'
            self.headers = {}
            self.get_json = lambda: {}
    
    result = course_analysis_pipeline(MockRequest())
    print(json.dumps(result, indent=2)) 