import os
import pandas as pd
from fpdf import FPDF
import argparse
from pathlib import Path
import yaml
import re
from datetime import datetime, timedelta
import json
import base64
from typing import List
from dotenv import load_dotenv
import unicodedata
import numpy as np
import tempfile
load_dotenv()

# Google Drive imports
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False
    print("Warning: Google Drive libraries not available. Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")

# Slack imports
try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
    SLACK_AVAILABLE = True
except ImportError:
    SLACK_AVAILABLE = False
    print("Warning: Slack libraries not available. Install with: pip install slack-sdk")

from storage import StorageClient

GRADE_ZERO_THRESHOLD = float(os.getenv('GRADE_ZERO_THRESHOLD', 0))
TIME_MAX_THRESHOLD_MINUTES = float(os.getenv('TIME_MAX_THRESHOLD_MINUTES', 100))

def parse_arguments():
    parser = argparse.ArgumentParser(description='Analyze course data and generate reports')
    parser.add_argument('--category', '-g', required=False, help='Category of the course (e.g., Matematicas, Ciencias, etc.)')
    parser.add_argument('--course', '-c', required=False, help='Course ID to analyze')
    parser.add_argument('--no-upload', action='store_true', help='Do not upload reports to Google Drive or send Slack notification')
    return parser.parse_args()

def load_course_config(config_path: str = "cursos.yml"):
    """Load course configuration from YAML file"""
    storage = StorageClient()
    if storage.backend == 'gcp' and storage.exists(config_path):
        # Try to load from GCS first
        content = storage.read_bytes(config_path).decode('utf-8')
        return yaml.safe_load(content)
    else:
        # Fall back to local file
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

def get_ignored_users(course_id: str):
    """Get ignored users from environment variable"""
    import os
    ignored_users_str = os.getenv('IGNORED_USERS', '')
    if ignored_users_str:
        return [email.strip() for email in ignored_users_str.split(',') if email.strip()]
    return []

def clean_excel_sheet_name(name: str) -> str:
    """Clean sheet name to be compatible with Excel"""
    # Remove or replace characters not allowed in Excel sheet names
    # Excel doesn't allow: [ ] * ? / \ : 
    cleaned = re.sub(r'[\[\]*?/\\:]', '', name)
    # Excel sheet names cannot be longer than 31 characters
    return cleaned[:31]

def calculate_completion_time(created, submitted):
    """Calculate completion time in minutes between created and submitted timestamps"""
    try:
        if pd.isna(created) or pd.isna(submitted):
            return None
        
        # Convert to datetime if they're strings
        if isinstance(created, str):
            created = pd.to_datetime(created)
        if isinstance(submitted, str):
            submitted = pd.to_datetime(submitted)
        
        # Calculate difference in minutes
        time_diff = submitted - created
        return time_diff.total_seconds() / 60
    except:
        return None

def get_drive_service():
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
        print(f"Error parsing service account key: {e}")
        raise

def find_or_create_folder(drive_service, parent_folder_id, folder_name, drive_id=None):
    query = f"mimeType='application/vnd.google-apps.folder' and trashed=false and name='{folder_name}' and '{parent_folder_id}' in parents"
    results = drive_service.files().list(
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
    folder = drive_service.files().create(**create_args).execute()
    print(f"[DEBUG] Carpeta creada en Drive: {folder['name']} (ID: {folder['id']})")
    return folder['id']

def find_file_in_folder(drive_service, folder_id, filename, drive_id=None):
    query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
    results = drive_service.files().list(
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

def upload_file_to_drive(file_path: str, filename: str, folder_id: str = None, drive_id: str = None) -> str:
    """Upload or replace file in Google Drive and return the web view link"""
    if not GOOGLE_DRIVE_AVAILABLE:
        print("Warning: Google Drive not available, skipping upload")
        return None
    try:
        drive_service = get_drive_service()
        if not folder_id:
            folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
            if not folder_id:
                raise ValueError("GOOGLE_DRIVE_FOLDER_ID environment variable not set")
        if not drive_id:
            drive_id = os.getenv('GOOGLE_DRIVE_ID') if os.getenv('GOOGLE_DRIVE_ID') else None
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        media = MediaFileUpload(file_path, resumable=True)
        existing_file_id = find_file_in_folder(drive_service, folder_id, filename, drive_id)
        if existing_file_id:
            print(f"[DEBUG] Archivo ya existe en Drive, actualizando: {filename} (ID: {existing_file_id})")
            update_args = dict(
                fileId=existing_file_id,
                media_body=media,
                fields='id,webViewLink',
                supportsAllDrives=True
            )
            if drive_id:
                update_args['driveId'] = drive_id
            uploaded = drive_service.files().update(**update_args).execute()
        else:
            upload_args = dict(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink',
                supportsAllDrives=True
            )
            if drive_id:
                upload_args['driveId'] = drive_id
            uploaded = drive_service.files().create(**upload_args).execute()
        print(f"Uploaded {filename} to Google Drive: {uploaded.get('webViewLink')}")
        return uploaded.get('webViewLink')
    except Exception as e:
        print(f"Error uploading to Google Drive: {e}")
        return None

def get_slack_client():
    """Initialize Slack client"""
    if not SLACK_AVAILABLE:
        raise ImportError("Slack libraries not available")
    
    slack_token = os.getenv('SLACK_BOT_TOKEN')
    if not slack_token:
        raise ValueError("SLACK_BOT_TOKEN environment variable not set")
    
    return WebClient(token=slack_token)

def send_slack_notification(category: str, course_id: str, course_name: str, drive_links: List[str], channel: str = None):
    """Send Slack notification with report links, including file type."""
    if not SLACK_AVAILABLE:
        print("Warning: Slack not available, skipping notification")
        return
    
    try:
        slack_client = get_slack_client()
        
        # Use provided channel or get from environment
        if not channel:
            channel = os.getenv('SLACK_CHANNEL')
            if not channel:
                raise ValueError("SLACK_CHANNEL environment variable not set")
        
        # Create message blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📊 Reporte de Análisis de Curso - {course_name} ({category})"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Categoría:* {category}\n*Curso:* {course_name}\n*ID del Curso:* {course_id}\n*Análisis completado:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            }
        ]
        
        # Add file links
        if drive_links:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*📁 Archivos Generados:*"
                }
            })
            
            for link in drive_links:
                # Determine file type from link or filename
                file_type = "Archivo"
                if "file" in link.lower():
                    file_type = "PDF"
                elif "spreadsheets" in link.lower():
                    file_type = "Excel"
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• <{link}|Ver Archivo ({file_type})>"
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
                    "text": "🤖 Automatizado por el Pipeline de Análisis de Cursos"
                }
            ]
        })
        fallback_text = f"📊 Reporte de Análisis de Curso - {course_name} ({category})\nCategoría: {category}\nCurso: {course_name}\nID del Curso: {course_id}\nAnálisis completado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        if drive_links:
            fallback_text += f"\nArchivos generados: {len(drive_links)} archivos"
        
        # Send message
        slack_client.chat_postMessage(
            channel=channel,
            text=fallback_text,  # Required for accessibility
            blocks=blocks
        )
        
        print(f"Notificación de Slack enviada a {channel}")
        
    except SlackApiError as e:
        print(f"Error de API de Slack: {e.response['error']}")
    except Exception as e:
        print(f"Error enviando notificación de Slack: {e}")

def upload_reports_and_notify(category: str, course_id: str, course_name: str, reports_dir: Path, processed_dir: Path):
    """Upload today's reports and CSV files to Google Drive (per-course folder), send Slack notification for reports only"""
    from datetime import datetime
    drive_service = get_drive_service()
    parent_folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
    drive_id = os.getenv('GOOGLE_DRIVE_ID') if os.getenv('GOOGLE_DRIVE_ID') else None
    
    # Create nested folder structure: category/course
    category_folder_id = find_or_create_folder(drive_service, parent_folder_id, category, drive_id)
    course_folder_id = find_or_create_folder(drive_service, category_folder_id, course_id, drive_id)
    
    today = datetime.now().date()
    report_links = []
    all_uploaded_files = []
    
    # Upload report files (PDF and Excel) - included in Slack notification
    if reports_dir.exists():
        for file in reports_dir.glob("*"):
            if file.suffix in ['.xlsx', '.pdf']:
                mtime = datetime.fromtimestamp(file.stat().st_mtime).date()
                ctime = datetime.fromtimestamp(file.stat().st_ctime).date()
                if mtime != today and ctime != today:
                    continue
                try:
                    drive_link = upload_file_to_drive(str(file), file.name, course_folder_id, drive_id)
                    if drive_link:
                        report_links.append(drive_link)
                        all_uploaded_files.append(drive_link)
                        print(f"✅ Reporte subido: {file.name}")
                except Exception as e:
                    print(f"❌ Error subiendo reporte {file.name}: {e}")
    
    # Upload processed CSV files - NOT included in Slack notification
    csv_count = 0
    if processed_dir.exists():
        for file in processed_dir.glob("*.csv"):
            mtime = datetime.fromtimestamp(file.stat().st_mtime).date()
            ctime = datetime.fromtimestamp(file.stat().st_ctime).date()
            if mtime != today and ctime != today:
                continue
            try:
                drive_link = upload_file_to_drive(str(file), file.name, course_folder_id, drive_id)
                if drive_link:
                    all_uploaded_files.append(drive_link)
                    csv_count += 1
                    print(f"📁 CSV subido: {file.name}")
            except Exception as e:
                print(f"❌ Error subiendo CSV {file.name}: {e}")
    
    # Send Slack notification only for report files
    if report_links:
        try:
            send_slack_notification(category, course_id, course_name, report_links)
        except Exception as e:
            print(f"❌ Error enviando notificación de Slack: {e}")
    else:
        print("⚠️  No se subieron reportes, omitiendo notificación de Slack")
    
    # Print summary
    if csv_count > 0:
        print(f"📊 Resumen: {len(report_links)} reportes y {csv_count} archivos CSV subidos")
    else:
        print(f"📊 Resumen: {len(report_links)} reportes subidos")
    
    return all_uploaded_files

def load_planification_data(category: str, course_id: str) -> pd.DataFrame:
    """Load planification data for a course, robust to encoding issues, using StorageClient"""
    planification_path = Path("data") / "planification" / category / f"{course_id}.csv"
    storage = StorageClient()
    if not storage.exists(planification_path):
        print(f"Warning: Planification file not found at {planification_path}")
        return pd.DataFrame()
    try:
        try:
            df_plan = storage.read_csv(planification_path, sep=';', encoding='utf-8')
        except UnicodeDecodeError:
            print("[DEBUG] UTF-8 decode failed, trying latin1")
            df_plan = storage.read_csv(planification_path, sep=';', encoding='latin1')
        # Normalize all string columns except 'date' to remove encoding artifacts
        for col in df_plan.select_dtypes(include=["object"]).columns:
            if col != 'date':
                df_plan[col] = df_plan[col].apply(normalize_str)
        # Convert date column to datetime
        if 'date' in df_plan.columns:
            df_plan['date'] = pd.to_datetime(df_plan['date'], format='%d-%m-%Y', errors='coerce')
        print(f"Loaded planification data: {len(df_plan)} assessments")
        return df_plan
    except Exception as e:
        print(f"Error loading planification data: {e}")
        return pd.DataFrame()

def get_assessments_due_until_today(planification_df: pd.DataFrame) -> List[str]:
    """Get list of assessment names that should have been completed until yesterday"""
    if planification_df.empty:
        return []
    
    # Get yesterday's date (since data is downloaded in the morning)
    yesterday = datetime.now().date() - timedelta(days=1)
    
    # Filter assessments due until yesterday
    due_assessments = planification_df[planification_df['date'].dt.date <= yesterday]
    
    assessment_names = due_assessments['assessment_name'].tolist()
    print(f"Assessments due until {yesterday}: {len(assessment_names)} assessments")
    
    return assessment_names

def filter_up_to_date_students(user_response_df: pd.DataFrame, due_assessments: List[str]) -> pd.DataFrame:
    """Filter students who have completed all assessments due until today (using normalized assessment names if available)"""
    if not due_assessments:
        print("No assessments due, returning all students")
        return user_response_df
    # Use normalized column if present
    assessment_col = 'assessment_normalized' if 'assessment_normalized' in user_response_df.columns else 'assessment'
    # Get unique user IDs
    all_user_ids = user_response_df['user_id'].unique()
    up_to_date_users = []
    for user_id in all_user_ids:
        user_data = user_response_df[user_response_df['user_id'] == user_id]
        # Check if user has completed all due assessments (normalized)
        user_completed_assessments = user_data[user_data['responded']][assessment_col].tolist()
        all_completed = all(assessment in user_completed_assessments for assessment in due_assessments)
        missing = [assessment for assessment in due_assessments if assessment not in user_completed_assessments]
        
        if all_completed:
            up_to_date_users.append(user_id)
    print(f"Students up to date: {len(up_to_date_users)} out of {len(all_user_ids)}")
    # Filter user_response_df to only include up-to-date students
    filtered_df = user_response_df[user_response_df['user_id'].isin(up_to_date_users)]
    return filtered_df

def normalize_str(s):
    if pd.isnull(s):
        return s
    return ''.join(c for c in unicodedata.normalize('NFKD', str(s)) if not unicodedata.combining(c))

def run_analysis_pipeline(category: str, course_id: str, upload_reports: bool = False):
    storage = StorageClient()
    ignore_emails = get_ignored_users(course_id)
    root = Path("data")
    processed_dir = root / "processed" / category / course_id
    reports_dir = root / "reports" / category / course_id
    metrics_dir = root / "metrics" / "kpi" / category / course_id
    reports_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)
    sep = ";"
    # Use storage for reading CSVs
    df_assessments = storage.read_csv(str(processed_dir / "assessments.csv"), sep=sep)
    df_users = storage.read_csv(str(processed_dir / "users.csv"), sep=sep)
    df_grades = storage.read_csv(str(processed_dir / "grades.csv"), sep=sep)
    ignored_users = df_users[df_users['email'].str.lower().isin([e.lower() for e in ignore_emails])].copy()
    df_users = df_users[~df_users['email'].str.lower().isin([e.lower() for e in ignore_emails])]
    df_grades = df_grades[~df_grades['user_id'].isin(ignored_users['id'])]
    df_grades['completion_time_minutes'] = df_grades.apply(
        lambda row: calculate_completion_time(row['created'], row['submittedTimestamp']), axis=1)
    df_grades = df_grades.merge(df_assessments, on="assessment_id", how="left")
    users_df = df_users.copy()
    if 'username' not in users_df.columns:
        users_df['username'] = users_df['email'].apply(lambda x: x.split('@')[0] if pd.notnull(x) else None)
    user_response_summary = []
    for assess_name in df_assessments['assessment_name']:
        for _, user in users_df.iterrows():
            user_id = user['id'] if 'id' in user else user['user_id']
            user_email = user['email'] if 'email' in user else user.get('email', None)
            username = user['username'] if 'username' in user else (user_email.split('@')[0] if user_email else None)
            grade_row = df_grades[(df_grades['user_id'] == user_id) & (df_grades['assessment_name'] == assess_name)]
            has_responded = not grade_row.empty
            grade = grade_row['grade'].iloc[0] if not grade_row.empty else None
            completion_time = grade_row['completion_time_minutes'].iloc[0] if not grade_row.empty else None
            created_timestamp = grade_row['created'].iloc[0] if not grade_row.empty else None
            submitted_timestamp = grade_row['submittedTimestamp'].iloc[0] if not grade_row.empty else None
            user_response_summary.append({
                'user_id': user_id,
                'email': user_email,
                'username': username,
                'assessment': assess_name,
                'responded': has_responded,
                'grade': grade,
                'completion_time_minutes': completion_time,
                'created_timestamp': created_timestamp,
                'submitted_timestamp': submitted_timestamp
            })
    user_response_df = pd.DataFrame(user_response_summary)

    # --- Regular report data ---
    no_response_users = users_df.copy()
    no_response_users['responded_any'] = no_response_users['id'].apply(lambda uid: user_response_df[user_response_df['user_id'] == uid]['responded'].any())
    no_response_list = no_response_users[~no_response_users['responded_any']][['email', 'username']].values.tolist()
    responded_list = user_response_df[user_response_df['responded']][['email', 'username', 'assessment', 'grade', 'completion_time_minutes', 'created_timestamp', 'submitted_timestamp']].values.tolist()
    from collections import defaultdict
    responded_by_assessment = defaultdict(list)
    for email, username, assessment, grade, completion_time, created_timestamp, submitted_timestamp in responded_list:
        responded_by_assessment[assessment].append([email, username, assessment, grade, completion_time, created_timestamp, submitted_timestamp])

    # After user_response_df is created and before metrics are calculated, filter out users with grade 0 and time > threshold
    if 'grade' in user_response_df.columns and 'completion_time_minutes' in user_response_df.columns:
        mask = ~((user_response_df['grade'] == GRADE_ZERO_THRESHOLD) & (user_response_df['completion_time_minutes'] > TIME_MAX_THRESHOLD_MINUTES))
        user_response_df = user_response_df[mask]

    metrics = []
    for assess_name in df_assessments['assessment_name']:
        grades = user_response_df[(user_response_df['assessment'] == assess_name) & (user_response_df['grade'].notnull())]['grade']
        completion_times = user_response_df[(user_response_df['assessment'] == assess_name) & (user_response_df['completion_time_minutes'].notnull())]['completion_time_minutes']
        if not grades.empty:
            metrics.append({
                'assessment': assess_name,
                'median': grades.median(),
                'mean': grades.mean(),
                'count': grades.count(),
                'q75': grades.quantile(0.75),
                'q100': grades.max(),
                'avg_completion_time_minutes': completion_times.mean() if not completion_times.empty else None
            })
        else:
            metrics.append({
                'assessment': assess_name,
                'median': None,
                'mean': None,
                'count': 0,
                'q75': None,
                'q100': None,
                'avg_completion_time_minutes': None
            })
    metrics_df = pd.DataFrame(metrics)

    # --- Up-to-date section (debug: print heads of all relevant DataFrames, error handling) ---
    planification_path = Path("data/planification") / category / f"{course_id}.csv"
    include_up_to_date = storage.exists(planification_path)
    up_to_date_section = None
    if include_up_to_date:
        try:
            planification_df = load_planification_data(category, course_id)
            due_assessments = get_assessments_due_until_today(planification_df)
            # Normalize assessment names in due_assessments and in user_response_df
            due_assessments_normalized = [normalize_str(a) for a in due_assessments]
            if 'assessment' in user_response_df.columns:
                user_response_df['assessment_normalized'] = user_response_df['assessment'].apply(normalize_str)
            # Print due assessments and which ones match actual assessments in the target course
            if 'assessment' in user_response_df.columns:
                actual_assessments_target = set(user_response_df['assessment_normalized'].unique())
                matching_assessments_target = set(due_assessments_normalized) & actual_assessments_target
            # 1. Up-to-date students in the target course (using only assessments that exist in target course)
            up_to_date_df = filter_up_to_date_students(user_response_df, list(matching_assessments_target))
            # 2. Up-to-date students in the base course, using only assessments that exist in base course
            base_course = os.getenv("UP_TO_DATE_BASE_COURSE", "lecciones-m0m")
            base_up_to_date_df = None
            if base_course:
                # NOTE: This assumes base course is in the same category. If not, you may need to update this logic.
                base_processed_dir = Path("data/processed") / category / base_course
                base_user_response_path = base_processed_dir / "users.csv"
                base_grades_path = base_processed_dir / "grades.csv"
                base_assessments_path = base_processed_dir / "assessments.csv"
                
                # Check if base course data exists using StorageClient
                if (storage.exists(base_user_response_path) and 
                    storage.exists(base_grades_path) and 
                    storage.exists(base_assessments_path)):
                    
                    try:
                        # Load base course data using StorageClient
                        base_df_users = storage.read_csv(str(base_user_response_path), sep=sep)
                        base_df_grades = storage.read_csv(str(base_grades_path), sep=sep)
                        base_df_assessments = storage.read_csv(str(base_assessments_path), sep=sep)
                        
                        # Filter ignored users from base course
                        base_ignored_users = base_df_users[base_df_users['email'].str.lower().isin([e.lower() for e in ignore_emails])].copy()
                        base_df_users = base_df_users[~base_df_users['email'].str.lower().isin([e.lower() for e in ignore_emails])]
                        base_df_grades = base_df_grades[~base_df_grades['user_id'].isin(base_ignored_users['id'])]
                        
                        # Calculate completion time for base course
                        base_df_grades['completion_time_minutes'] = base_df_grades.apply(
                            lambda row: calculate_completion_time(row['created'], row['submittedTimestamp']), axis=1)
                        base_df_grades = base_df_grades.merge(base_df_assessments, on="assessment_id", how="left")
                        
                        # Create user response summary for base course
                        base_user_response_summary = []
                        for assess_name in base_df_assessments['assessment_name']:
                            for _, user in base_df_users.iterrows():
                                user_id = user['id'] if 'id' in user else user['user_id']
                                user_email = user['email'] if 'email' in user else user.get('email', None)
                                username = user['username'] if 'username' in user else (user_email.split('@')[0] if user_email else None)
                                grade_row = base_df_grades[(base_df_grades['user_id'] == user_id) & (base_df_grades['assessment_name'] == assess_name)]
                                has_responded = not grade_row.empty
                                grade = grade_row['grade'].iloc[0] if not grade_row.empty else None
                                completion_time = grade_row['completion_time_minutes'].iloc[0] if not grade_row.empty else None
                                created_timestamp = grade_row['created'].iloc[0] if not grade_row.empty else None
                                submitted_timestamp = grade_row['submittedTimestamp'].iloc[0] if not grade_row.empty else None
                                base_user_response_summary.append({
                                    'user_id': user_id,
                                    'email': user_email,
                                    'username': username,
                                    'assessment': assess_name,
                                    'responded': has_responded,
                                    'grade': grade,
                                    'completion_time_minutes': completion_time,
                                    'created_timestamp': created_timestamp,
                                    'submitted_timestamp': submitted_timestamp
                                })
                        
                        base_user_response_df = pd.DataFrame(base_user_response_summary)
                        
                        # Filter out users with grade 0 and time > threshold for base course
                        if 'grade' in base_user_response_df.columns and 'completion_time_minutes' in base_user_response_df.columns:
                            mask = ~((base_user_response_df['grade'] == GRADE_ZERO_THRESHOLD) & (base_user_response_df['completion_time_minutes'] > TIME_MAX_THRESHOLD_MINUTES))
                            base_user_response_df = base_user_response_df[mask]
                        
                        # Normalize assessment names in base course
                        if 'assessment' in base_user_response_df.columns:
                            base_user_response_df['assessment_normalized'] = base_user_response_df['assessment'].apply(normalize_str)
                        
                        # Get base course assessments that match due assessments
                        if 'assessment_normalized' in base_user_response_df.columns:
                            actual_assessments_base = set(base_user_response_df['assessment_normalized'].unique())
                            matching_assessments_base = set(due_assessments_normalized) & actual_assessments_base
                            
                            # Filter up-to-date students in base course
                            base_up_to_date_df = filter_up_to_date_students(base_user_response_df, list(matching_assessments_base))
                            
                            print(f"Base course '{base_course}' up-to-date students: {len(base_up_to_date_df['user_id'].unique())}")
                        else:
                            print(f"Warning: Could not process base course '{base_course}' - missing assessment data")
                            base_up_to_date_df = None
                            
                    except Exception as e:
                        print(f"Error processing base course '{base_course}': {e}")
                        base_up_to_date_df = None
                else:
                    print(f"Base course '{base_course}' data not found in storage, skipping base course analysis")
                    base_up_to_date_df = None
            # 3. Intersect both groups (by email, case-insensitive)
            if base_up_to_date_df is not None:
                emails_target = set(up_to_date_df['email'].str.lower())
                emails_base = set(base_up_to_date_df['email'].str.lower())
                intersect_emails = emails_target & emails_base
                up_to_date_df = up_to_date_df[up_to_date_df['email'].str.lower().isin(intersect_emails)]
            # In the up-to-date section, after up_to_date_df is created and before metrics are calculated, apply the same grade/time filter
            if up_to_date_df is not None and 'grade' in up_to_date_df.columns and 'completion_time_minutes' in up_to_date_df.columns:
                mask = ~((up_to_date_df['grade'] == GRADE_ZERO_THRESHOLD) & (up_to_date_df['completion_time_minutes'] > TIME_MAX_THRESHOLD_MINUTES))
                up_to_date_df = up_to_date_df[mask]
            # Prepare up-to-date metrics and attendance (unchanged)
            up_to_date_metrics = []
            for assess_name in df_assessments['assessment_name']:
                grades = up_to_date_df[(up_to_date_df['assessment'] == assess_name) & (up_to_date_df['grade'].notnull())]['grade']
                completion_times = up_to_date_df[(up_to_date_df['assessment'] == assess_name) & (up_to_date_df['completion_time_minutes'].notnull())]['completion_time_minutes']
                if not grades.empty:
                    up_to_date_metrics.append({
                        'assessment': assess_name,
                        'median': grades.median(),
                        'mean': grades.mean(),
                        'count': grades.count(),
                        'q75': grades.quantile(0.75),
                        'q100': grades.max(),
                        'avg_completion_time_minutes': completion_times.mean() if not completion_times.empty else None
                    })
                else:
                    up_to_date_metrics.append({
                        'assessment': assess_name,
                        'median': None,
                        'mean': None,
                        'count': 0,
                        'q75': None,
                        'q100': None,
                        'avg_completion_time_minutes': None
                    })
            up_to_date_metrics_df = pd.DataFrame(up_to_date_metrics)
            up_to_date_total_users = len(up_to_date_df['user_id'].unique()) if 'user_id' in up_to_date_df.columns else 0
            up_to_date_responded_user_ids = set(up_to_date_df[up_to_date_df['responded']]['user_id']) if 'user_id' in up_to_date_df.columns and 'responded' in up_to_date_df.columns else set()
            up_to_date_unique_responded = len(up_to_date_responded_user_ids)
            up_to_date_attendance_pct = (up_to_date_unique_responded / up_to_date_total_users * 100) if up_to_date_total_users > 0 else 0
            up_to_date_section = {
                'metrics_df': up_to_date_metrics_df,
                'total_users': up_to_date_total_users,
                'unique_responded': up_to_date_unique_responded,
                'attendance_pct': up_to_date_attendance_pct,
                'df': up_to_date_df
            }
        except Exception as e:
            print(f"[ERROR] Exception in up-to-date section: {e}")
            print("[ERROR] Skipping up-to-date section for this course.")

    # --- PDF REPORT GENERATION ---
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Métricas de notas y tiempos - Curso: {category}/{course_id}", ln=True, align="C")
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, "Métricas de notas y tiempos por evaluación", ln=True, align="C")
    pdf.set_font("Arial", 'B', 9)
    metric_cols_es = ["Evaluación", "Mediana", "Promedio", "Cantidad", "Q75", "Máximo", "Tiempo Prom (min)"]
    col_widths = [35, 15, 18, 15, 15, 15, 20]
    pdf.set_fill_color(220, 220, 220)
    for i, col in enumerate(metric_cols_es):
        pdf.cell(col_widths[i], 8, col, border=1, fill=True)
    pdf.ln()
    pdf.set_fill_color(255, 255, 255)
    pdf.set_font("Arial", size=8)
    for _, row in metrics_df.iterrows():
        values = [
            row["assessment"],
            row["median"],
            row["mean"],
            row["count"],
            row["q75"],
            row["q100"],
            row["avg_completion_time_minutes"]
        ]
        for i, value in enumerate(values):
            # Replace nan/None with '-'
            if pd.isnull(value) or value is None:
                value = "-"
            elif isinstance(value, float):
                if np.isnan(value):
                    value = "-"
                elif i == 6:  # avg_completion_time_minutes column
                    value = f"{value:.2f}"
                elif i == 2:  # mean column
                    value = f"{value:.2f}"
            pdf.cell(col_widths[i], 8, str(value), border=1)
        pdf.ln()
    pdf.ln(5)
    total_users = len(users_df)
    responded_user_ids = set(user_response_df[user_response_df['responded']]['user_id'])
    unique_responded = len(responded_user_ids)
    attendance_pct = (unique_responded / total_users * 100) if total_users > 0 else 0
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, "Métricas de asistencia", ln=True, align="C")
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 8, f"Total de alumnos: {total_users}", ln=True)
    pdf.cell(0, 8, f"Alumnos que respondieron al menos una evaluación: {unique_responded}", ln=True)
    pdf.cell(0, 8, f"Porcentaje de asistencia: {attendance_pct:.2f}%", ln=True)
    pdf.ln(5)
    # --- Up-to-date PDF section ---
    if up_to_date_section is not None:
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, "---", ln=True, align="C")
        pdf.cell(0, 10, "Métricas SOLO estudiantes al día", ln=True, align="C")
        pdf.set_font("Arial", 'B', 9)
        for i, col in enumerate(metric_cols_es):
            pdf.cell(col_widths[i], 8, col, border=1, fill=True)
        pdf.ln()
        pdf.set_fill_color(255, 255, 255)
        pdf.set_font("Arial", size=8)
        for _, row in up_to_date_section['metrics_df'].iterrows():
            values = [
                row["assessment"],
                row["median"],
                row["mean"],
                row["count"],
                row["q75"],
                row["q100"],
                row["avg_completion_time_minutes"]
            ]
            for i, value in enumerate(values):
                # Replace nan/None with '-'
                if pd.isnull(value) or value is None:
                    value = "-"
                elif isinstance(value, float):
                    if np.isnan(value):
                        value = "-"
                    elif i == 6:  # avg_completion_time_minutes column
                        value = f"{value:.2f}"
                    elif i == 2:  # mean column
                        value = f"{value:.2f}"
                pdf.cell(col_widths[i], 8, str(value), border=1)
            pdf.ln()
        pdf.ln(5)
    fecha_actual = datetime.now().strftime("%Y-%m-%d")
    pdf_filename = f"reporte_{category}_{course_id}_{fecha_actual}.pdf"
    excel_filename = f"reporte_{category}_{course_id}_{fecha_actual}.xlsx"
    pdf_path = None
    excel_path = None
    if storage.backend == 'local':
        pdf_path = reports_dir / pdf_filename
        pdf.output(str(pdf_path))
        excel_path = reports_dir / excel_filename
        with pd.ExcelWriter(excel_path) as writer:
            pd.DataFrame(no_response_list, columns=["correo", "usuario"]).to_excel(
                writer, sheet_name="Sin Respuesta", index=False)
            for assessment, rows in responded_by_assessment.items():
                clean_sheet_name = clean_excel_sheet_name(assessment)
                df_response = pd.DataFrame(rows, columns=["correo", "usuario", "evaluación", "nota", "tiempo_minutos", "fecha_creación", "fecha_envío"])
                df_response.to_excel(writer, sheet_name=clean_sheet_name, index=False)
            # Add up-to-date sheet if needed
            if up_to_date_section is not None:
                up_to_date_df = up_to_date_section['df']
                up_to_date_users = up_to_date_df[up_to_date_df['responded']][['email', 'username', 'assessment', 'grade', 'completion_time_minutes', 'created_timestamp', 'submitted_timestamp']]
                up_to_date_users = up_to_date_users.rename(columns={
                    'email': 'correo', 'username': 'usuario', 'assessment': 'evaluación', 'grade': 'nota',
                    'completion_time_minutes': 'tiempo_minutos', 'created_timestamp': 'fecha_creación', 'submitted_timestamp': 'fecha_envío'
                })
                up_to_date_users.to_excel(writer, sheet_name="UpToDate", index=False)
    else:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
            pdf.output(tmp_pdf.name)
            pdf_path = tmp_pdf.name
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_xlsx:
            with pd.ExcelWriter(tmp_xlsx.name) as writer:
                pd.DataFrame(no_response_list, columns=["correo", "usuario"]).to_excel(
                    writer, sheet_name="Sin Respuesta", index=False)
                for assessment, rows in responded_by_assessment.items():
                    clean_sheet_name = clean_excel_sheet_name(assessment)
                    df_response = pd.DataFrame(rows, columns=["correo", "usuario", "evaluación", "nota", "tiempo_minutos", "fecha_creación", "fecha_envío"])
                    df_response.to_excel(writer, sheet_name=clean_sheet_name, index=False)
                # Add up-to-date sheet if needed
                if up_to_date_section is not None:
                    up_to_date_df = up_to_date_section['df']
                    up_to_date_users = up_to_date_df[up_to_date_df['responded']][['email', 'username', 'assessment', 'grade', 'completion_time_minutes', 'created_timestamp', 'submitted_timestamp']]
                    up_to_date_users = up_to_date_users.rename(columns={
                        'email': 'correo', 'username': 'usuario', 'assessment': 'evaluación', 'grade': 'nota',
                        'completion_time_minutes': 'tiempo_minutos', 'created_timestamp': 'fecha_creación', 'submitted_timestamp': 'fecha_envío'
                    })
                    up_to_date_users.to_excel(writer, sheet_name="UpToDate", index=False)
            excel_path = tmp_xlsx.name
    print(f"PDF report generated: {pdf_filename}")
    print(f"Excel file generated: {excel_filename}")

    # --- Upload reports to Google Drive and send Slack notification ---
    if upload_reports:
        try:
            config = load_course_config()
            courses = config.get('courses', {})
            # Find course config by category and course_id
            course_config = None
            if category in courses:
                course_config = courses[category].get(course_id, {})
            if not course_config:
                course_config = courses.get(course_id, {})
            course_name = course_config.get('name', course_id)
            
            # Create nested folder structure: category/course
            drive_service = get_drive_service()
            parent_folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
            drive_id = os.getenv('GOOGLE_DRIVE_ID') if os.getenv('GOOGLE_DRIVE_ID') else None
            
            # Create nested folder structure: category/course
            category_folder_id = find_or_create_folder(drive_service, parent_folder_id, category, drive_id)
            course_folder_id = find_or_create_folder(drive_service, category_folder_id, course_id, drive_id)
            
            # Upload from the correct path (temp file for GCP, local file for local)
            drive_links = []
            from pathlib import Path as _Path
            for file_path, file_name in [(pdf_path, pdf_filename), (excel_path, excel_filename)]:
                if file_path and _Path(file_path).exists():
                    drive_link = upload_file_to_drive(file_path, file_name, course_folder_id, drive_id)
                    if drive_link:
                        drive_links.append(drive_link)
            if drive_links:
                send_slack_notification(category, course_id, course_name, drive_links)
                print(f"✅ Se subieron {len(drive_links)} archivos a Google Drive")
                print(f"✅ Notificación de Slack enviada con enlaces a reportes")
            else:
                print("⚠️  No se subieron archivos (verificar variables de entorno y permisos)")
        except Exception as e:
            print(f"❌ Error durante la subida/notificación: {e}")
            print("   Esta es funcionalidad opcional - el análisis se completó exitosamente")
    else:
        print("📁 Reportes generados localmente (usar --upload para subir a Google Drive y enviar notificación de Slack)")

def batch_analysis(category=None, course=None, upload_reports=False, no_upload=False):
    config = load_course_config()
    courses = config.get('courses', {})
    if category and course:
        # Single course in a category
        if category in courses and course in courses[category]:
            run_analysis_pipeline(category, course, upload_reports=upload_reports and not no_upload)
        else:
            print(f"Course {course} not found in category {category}.")
    elif category:
        # All courses in a category
        if category in courses:
            for course_id in courses[category]:
                print(f"\nProcessing {category}/{course_id}")
                run_analysis_pipeline(category, course_id, upload_reports=upload_reports and not no_upload)
        else:
            print(f"Category {category} not found.")
    else:
        # All categories and all courses
        for cat in courses:
            for course_id in courses[cat]:
                print(f"\nProcessing {cat}/{course_id}")
                run_analysis_pipeline(cat, course_id, upload_reports=upload_reports and not no_upload)

if __name__ == "__main__":
    args = parse_arguments()
    upload_enabled = not args.no_upload
    batch_analysis(category=args.category, course=args.course, upload_reports=upload_enabled, no_upload=args.no_upload) 