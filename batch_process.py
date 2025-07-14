#!/usr/bin/env python3
"""
Batch processing script for multiple courses
Reads course configuration from cursos.yml and processes each course
"""

import yaml
import argparse
from pathlib import Path
from descarga_procesa_datos import run_full_pipeline as run_download_pipeline
from analisis import run_analysis_pipeline as run_analysis_pipeline

def load_course_config(config_path: str = "cursos.yml"):
    """Load course configuration from YAML file"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def parse_arguments():
    parser = argparse.ArgumentParser(description='Batch process multiple courses')
    parser.add_argument('--config', '-f', default='cursos.yml', help='Path to course configuration file')
    parser.add_argument('--courses', '-c', nargs='+', help='Specific course IDs to process (overrides config)')
    parser.add_argument('--download-only', action='store_true', help='Only download data, skip analysis')
    parser.add_argument('--analysis-only', action='store_true', help='Only run analysis, skip download')
    parser.add_argument('--upload-only', action='store_true', help='Only upload reports/CSVs to Google Drive, skip download and analysis')
    return parser.parse_args()

# --- Google Drive upload logic ---
def get_drive_service():
    import os, base64, json
    from googleapiclient.discovery import build
    from google.oauth2 import service_account
    service_account_key = os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY')
    if not service_account_key:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_KEY environment variable not set")
    try:
        decoded_key = base64.b64decode(service_account_key).decode('utf-8')
        key_data = json.loads(decoded_key)
    except Exception:
        key_data = json.loads(service_account_key)
    credentials = service_account.Credentials.from_service_account_info(
        key_data,
        scopes=['https://www.googleapis.com/auth/drive']
    )
    return build('drive', 'v3', credentials=credentials)

def find_or_create_folder(drive_service, parent_folder_id, folder_name, drive_id=None):
    # Search for the folder by name under the parent
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
    folder = drive_service.files().create(**create_args).execute()
    print(f"[DEBUG] Carpeta creada en Drive: {folder['name']} (ID: {folder['id']})")
    return folder['id']

import datetime

def find_file_in_folder(drive_service, folder_id, filename, drive_id=None):
    # Search for a file by name in a specific folder
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

def upload_files_for_course(course_id, folder_id=None, drive_id=None):
    """
    Uploads today's files in data/reports/{course_id}/ and data/processed/{course_id}/ to a subfolder in Google Drive.
    If a file with the same name exists, it is replaced (updated).
    Returns a dict of {filename: webViewLink}
    """
    import os
    import traceback
    from pathlib import Path
    from googleapiclient.http import MediaFileUpload
    from datetime import datetime
    if folder_id is None:
        folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
    if drive_id is None:
        drive_id = os.environ.get('GOOGLE_DRIVE_ID') if os.environ.get('GOOGLE_DRIVE_ID') else None
    print(f"[DEBUG] Subiendo archivos para el curso: {course_id}")
    print(f"[DEBUG] Usando carpeta de Drive con ID: {folder_id}")
    drive_service = get_drive_service()
    # Find or create subfolder for the course
    course_folder_id = find_or_create_folder(drive_service, folder_id, course_id, drive_id)
    print(f"[DEBUG] Carpeta de curso en Drive: {course_folder_id}")
    results = {}
    today = datetime.now().date()
    for subdir in ['reports', 'processed']:
        dir_path = Path('data') / subdir / course_id
        print(f"[DEBUG] Buscando archivos en: {dir_path}")
        if not dir_path.exists():
            print(f"[DEBUG] Directorio no existe: {dir_path}")
            continue
        for file_path in dir_path.iterdir():
            if file_path.is_file():
                # Only upload files created or modified today
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime).date()
                ctime = datetime.fromtimestamp(file_path.stat().st_ctime).date()
                if mtime != today and ctime != today:
                    continue
                try:
                    file_size = file_path.stat().st_size
                    print(f"[DEBUG] Subiendo archivo: {file_path.name} (tamaño: {file_size} bytes)")
                    file_metadata = {
                        'name': file_path.name,
                        'parents': [course_folder_id]
                    }
                    media = MediaFileUpload(str(file_path), resumable=True)
                    # Check if file exists in Drive folder
                    existing_file_id = find_file_in_folder(drive_service, course_folder_id, file_path.name, drive_id)
                    if existing_file_id:
                        print(f"[DEBUG] Archivo ya existe en Drive, actualizando: {file_path.name} (ID: {existing_file_id})")
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
                    results[file_path.name] = uploaded.get('webViewLink')
                    print(f"[DEBUG] Archivo subido: {file_path.name} → {uploaded.get('webViewLink')}")
                except Exception as e:
                    print(f"[ERROR] Falló la subida de {file_path.name}: {e}")
                    traceback.print_exc()
    print(f"[DEBUG] Subida finalizada para el curso: {course_id}")
    return results

def send_slack_notification_for_upload(course_id, course_config, uploaded_links):
    """Send a Slack notification listing uploaded files for a course."""
    import os
    slack_channel = os.environ.get('SLACK_CHANNEL')
    if not slack_channel:
        print("[DEBUG] SLACK_CHANNEL no configurado, omitiendo notificación Slack.")
        return
    slack_client = get_slack_client()
    if not slack_client:
        print("[DEBUG] Slack client no disponible, omitiendo notificación Slack.")
        return
    if not uploaded_links:
        print("[DEBUG] No hay archivos subidos para notificar a Slack.")
        return
    course_name = course_config.get('name', course_id)
    text = f"Se han subido los siguientes archivos para el curso *{course_name}* ({course_id}):\n"
    for fname, link in uploaded_links.items():
        text += f"• <{link}|{fname}>\n"
    try:
        slack_client.chat_postMessage(
            channel=slack_channel,
            text=text
        )
        print(f"[DEBUG] Notificación de Slack enviada para {course_id}")
    except Exception as e:
        print(f"[ERROR] Falló el envío de notificación Slack para {course_id}: {e}")

def get_slack_client():
    """Initialize Slack client"""
    import os
    from slack_sdk import WebClient
    slack_token = os.environ.get('SLACK_BOT_TOKEN')
    if not slack_token:
        print("[DEBUG] SLACK_BOT_TOKEN no configurado")
        return None
    return WebClient(token=slack_token)

def run_batch_pipeline(config_path: str, specific_courses: list = None, 
                      download_only: bool = False, analysis_only: bool = False, upload_only: bool = False):
    """Run pipeline for multiple courses"""
    
    # Load configuration
    config = load_course_config(config_path)
    courses = config.get('courses', {})
    
    # Determine which courses to process
    if specific_courses:
        courses_to_process = {course_id: courses[course_id] 
                            for course_id in specific_courses 
                            if course_id in courses}
    else:
        courses_to_process = courses
    
    if not courses_to_process:
        print("No courses found to process")
        return
    
    print(f"Processing {len(courses_to_process)} courses:")
    for course_id in courses_to_process:
        print(f"  - {course_id}: {courses_to_process[course_id].get('name', 'Unknown')}")
    
    # Process each course
    for course_id, course_config in courses_to_process.items():
        print(f"\n{'='*50}")
        print(f"Processing course: {course_id}")
        print(f"Name: {course_config.get('name', 'Unknown')}")
        print(f"{'='*50}")
        
        try:
            if upload_only:
                print(f"Uploading reports/CSVs para {course_id}...")
                uploaded_links = upload_files_for_course(course_id)
                print(f"Upload completed for {course_id}")
                send_slack_notification_for_upload(course_id, course_config, uploaded_links)
                continue
            # Download phase
            if not analysis_only:
                print(f"Downloading data for {course_id}...")
                run_download_pipeline(course_id)
                print(f"Download completed for {course_id}")
            
            # Analysis phase
            if not download_only:
                print(f"Analyzing data for {course_id}...")
                run_analysis_pipeline(course_id)
                print(f"Analysis completed for {course_id}")
                
        except Exception as e:
            print(f"Error processing course {course_id}: {str(e)}")
            continue
    
    print(f"\n{'='*50}")
    print("Batch processing completed!")

if __name__ == "__main__":
    args = parse_arguments()
    run_batch_pipeline(
        config_path=args.config,
        specific_courses=args.courses,
        download_only=args.download_only,
        analysis_only=args.analysis_only,
        upload_only=args.upload_only
    ) 