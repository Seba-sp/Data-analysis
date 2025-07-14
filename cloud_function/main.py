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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
PROJECT_ID = os.environ.get('GCP_PROJECT_ID')
BUCKET_NAME = os.environ.get('GCP_BUCKET_NAME')
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_CHANNEL = os.environ.get('SLACK_CHANNEL')
GOOGLE_DRIVE_FOLDER_ID = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
IGNORED_USERS = os.environ.get('IGNORED_USERS', '').split(',') if os.environ.get('IGNORED_USERS') else []

# Initialize clients
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)

def get_slack_client():
    """Initialize Slack client"""
    return WebClient(token=SLACK_BOT_TOKEN)

def get_drive_service():
    """Initialize Google Drive service"""
    import base64
    
    # Get the service account key (could be base64 encoded or raw JSON)
    service_account_key = os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY')
    
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
    try:
        slack_client = get_slack_client()
        
        # Create message blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📊 Daily Course Analysis Report"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Analysis completed at:* {datetime.now(pytz.timezone('America/Santiago')).strftime('%Y-%m-%d %H:%M:%S %Z')}"
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
            course_text += f"Status: {status}\n"
            
            if drive_links:
                course_text += "Files:\n"
                for link in drive_links:
                    course_text += f"• <{link}|View File>\n"
            
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
                    "text": "🤖 Automated by Google Cloud Function"
                }
            ]
        })
        
        # Send message
        slack_client.chat_postMessage(
            channel=SLACK_CHANNEL,
            blocks=blocks
        )
        
        logger.info("Slack notification sent successfully")
        
    except SlackApiError as e:
        logger.error(f"Slack API error: {e.response['error']}")
    except Exception as e:
        logger.error(f"Error sending Slack notification: {e}")

def process_course(course_id: str, course_config: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single course and return results"""
    result = {
        'course_id': course_id,
        'course_name': course_config.get('name', course_id),
        'status': 'success',
        'drive_links': [],
        'gcs_files': []
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
            
            # Copy configuration files and update with environment variables
            # Note: In production, these should be stored in Cloud Storage or environment variables
            with open('cursos.yml', 'w') as f:
                import yaml
                # Update course config with environment variable ignored users
                updated_config = course_config.copy()
                if IGNORED_USERS:
                    updated_config['ignored_users'] = IGNORED_USERS
                yaml.dump({'courses': {course_id: updated_config}}, f)
            
            # Run download pipeline
            logger.info(f"Starting download pipeline for {course_id}")
            run_download_pipeline(course_id)
            
            # Run analysis pipeline
            logger.info(f"Starting analysis pipeline for {course_id}")
            run_analysis_pipeline(course_id)
            
            # Upload raw data to Cloud Storage (single file, not dated)
            raw_dir = f'data/raw/{course_id}'
            if os.path.exists(raw_dir):
                gcs_prefix = f'raw/{course_id}'
                result['gcs_files'].extend(upload_directory_to_gcs(raw_dir, gcs_prefix))
            
            # Upload processed data to Cloud Storage (single file, not dated)
            processed_dir = f'data/processed/{course_id}'
            if os.path.exists(processed_dir):
                gcs_prefix = f'processed/{course_id}'
                result['gcs_files'].extend(upload_directory_to_gcs(processed_dir, gcs_prefix))
            
            # Upload reports to Google Drive
            reports_dir = f'data/reports/{course_id}'
            if os.path.exists(reports_dir):
                for file in os.listdir(reports_dir):
                    if file.endswith(('.xlsx', '.pdf')):
                        file_path = os.path.join(reports_dir, file)
                        timestamp = datetime.now().strftime("%Y-%m-%d")
                        filename = f"{course_id}_{file.replace('.', f'_{timestamp}.')}"
                        
                        try:
                            drive_link = upload_report_to_drive(file_path, filename)
                            result['drive_links'].append(drive_link)
                        except Exception as e:
                            logger.error(f"Failed to upload report {file}: {e}")
            
            # Upload processed CSV files to Google Drive
            processed_dir = f'data/processed/{course_id}'
            if os.path.exists(processed_dir):
                for file in os.listdir(processed_dir):
                    if file.endswith('.csv'):
                        file_path = os.path.join(processed_dir, file)
                        timestamp = datetime.now().strftime("%Y-%m-%d")
                        filename = f"{course_id}_{file.replace('.csv', f'_{timestamp}.csv')}"
                        
                        try:
                            drive_link = upload_report_to_drive(file_path, filename)
                            result['drive_links'].append(drive_link)
                        except Exception as e:
                            logger.error(f"Failed to upload CSV {file}: {e}")
            
            # Restore original working directory
            os.chdir(original_cwd)
            
    except Exception as e:
        logger.error(f"Error processing course {course_id}: {e}")
        result['status'] = 'error'
        result['error'] = str(e)
    
    return result

def course_analysis_pipeline(request):
    """Main Cloud Function entry point"""
    try:
        logger.info("Starting daily course analysis pipeline")
        
        # Load course configuration
        config = load_course_config()
        courses = config.get('courses', {})
        
        if not courses:
            logger.error("No courses found in configuration")
            return {'error': 'No courses configured'}, 400
        
        logger.info(f"Processing {len(courses)} courses")
        
        # Process each course
        course_results = []
        for course_id, course_config in courses.items():
            logger.info(f"Processing course: {course_id}")
            result = process_course(course_id, course_config)
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
            'results': course_results
        }
        
        logger.info(f"Pipeline completed. {len(successful_courses)} successful, {len(failed_courses)} failed")
        
        return summary, 200
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        return {'error': str(e)}, 500

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