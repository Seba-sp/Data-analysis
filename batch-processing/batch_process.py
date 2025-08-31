import yaml
import argparse
from pathlib import Path
from descarga_procesa_datos import run_full_pipeline as run_download_pipeline
from analisis import run_analysis_pipeline as run_analysis_pipeline
from storage import StorageClient
import os
from datetime import datetime

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

def load_base_courses(base_courses_path: str = "base_courses.yml"):
    """Load base course mapping from YAML file"""
    storage = StorageClient()
    if storage.backend == 'gcp' and storage.exists(base_courses_path):
        # Try to load from GCS first
        content = storage.read_bytes(base_courses_path).decode('utf-8')
        return yaml.safe_load(content).get('base_courses', {})
    else:
        # Fall back to local file
        with open(base_courses_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f).get('base_courses', {})

def parse_arguments():
    parser = argparse.ArgumentParser(description='Batch process multiple courses')
    parser.add_argument('--config', '-f', default='cursos.yml', help='Path to course configuration file')
    parser.add_argument('--category', '-g', required=False, help='Category of the course (e.g., Matematicas, Ciencias, etc.)')
    parser.add_argument('--course', '-c', required=False, help='Course ID to process')
    parser.add_argument('--download-only', action='store_true', help='Only download data, skip analysis and upload')
    parser.add_argument('--analysis-only', action='store_true', help='Only run analysis, skip download and upload')
    parser.add_argument('--no-upload', action='store_true', help='Do not upload reports to Google Drive or send Slack notification')
    return parser.parse_args()

# --- Google Drive upload logic ---
from drive_service import DriveService
import datetime

def upload_files_for_course(category, course_id, folder_id=None, drive_id=None):
    """
    Uploads today's files in data/reports/{category}/{course_id}/ to a subfolder in Google Drive.
    If a file with the same name exists, it is replaced (updated).
    Returns a dict of {filename: webViewLink}
    """
    storage = StorageClient()
    if storage.backend == 'gcp':
        print(f"[DEBUG] STORAGE_BACKEND is 'gcp': skipping upload_files_for_course (handled in analysis.py)")
        return {}
    if folder_id is None:
        folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
    if drive_id is None:
        drive_id = os.environ.get('GOOGLE_DRIVE_ID') if os.environ.get('GOOGLE_DRIVE_ID') else None
    print(f"[DEBUG] Subiendo archivos para el curso: {category}/{course_id}")
    print(f"[DEBUG] Usando carpeta de Drive con ID: {folder_id}")
    
    # Initialize DriveService
    drive_service = DriveService()
    
    # Find or create subfolder for the course
    course_folder_id = drive_service.find_or_create_folder(folder_id, f"{category}_{course_id}", drive_id)
    print(f"[DEBUG] Carpeta de curso en Drive: {course_folder_id}")
    results = {}
    today = datetime.now().date()
    # Only upload report files (PDF, Excel) from reports directory
    subdir = 'reports'
    dir_path = Path('data') / subdir / category / course_id
    print(f"[DEBUG] Buscando archivos en: {dir_path}")
    if not dir_path.exists():
        print(f"[DEBUG] Directorio no existe: {dir_path}")
    else:
        for file_path in dir_path.iterdir():
            if file_path.is_file() and file_path.suffix in ['.xlsx', '.pdf']:
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime).date()
                ctime = datetime.fromtimestamp(file_path.stat().st_ctime).date()
                if mtime != today and ctime != today:
                    continue
                try:
                    file_size = file_path.stat().st_size
                    print(f"[DEBUG] Subiendo archivo: {file_path.name} (tamaño: {file_size} bytes)")
                    
                    # Use DriveService to upload the file
                    drive_link = drive_service.upload_file(str(file_path), file_path.name, course_folder_id, drive_id)
                    if drive_link:
                        results[file_path.name] = drive_link
                        print(f"[DEBUG] Archivo subido: {file_path.name} → {drive_link}")
                    else:
                        print(f"[ERROR] Falló la subida de {file_path.name}")
                        
                except Exception as e:
                    print(f"[ERROR] Falló la subida de {file_path.name}: {e}")
                    import traceback
                    traceback.print_exc()
    print(f"[DEBUG] Subida finalizada para el curso: {category}/{course_id}")
    return results

from slack_service import SlackService

def send_slack_notification_for_upload(category, course_id, course_config, uploaded_links):
    """Send a Slack notification listing uploaded files for a course, including the category."""
    slack_service = SlackService()
    if not slack_service.is_available():
        print("[DEBUG] Slack service no disponible, omitiendo notificación Slack.")
        return
    
    course_name = course_config.get('name', course_id)
    success = slack_service.send_file_upload_notification(category, course_id, course_name, uploaded_links)
    
    if success:
        print(f"[DEBUG] Notificación de Slack enviada para {category}/{course_id}")
    else:
        print(f"[ERROR] Falló el envío de notificación Slack para {category}/{course_id}")

def run_batch_pipeline(config_path: str, category: str = None, course_id: str = None, download_only: bool = False, analysis_only: bool = False, no_upload: bool = False):
    """Run pipeline for one or more courses/categories"""
    import os
    base_courses = load_base_courses()
    config = load_course_config(config_path)
    courses = config.get('courses', {})
    def process_one(cat, cid):
        base_course = base_courses.get(cat, None)
        course_config = None
        if cat in courses and cid in courses[cat]:
            course_config = courses[cat][cid]
        if not course_config:
            print(f"No course found for category '{cat}' and course '{cid}'")
            return
        print(f"Processing course: {cat}/{cid}")
        print(f"Name: {course_config.get('name', 'Unknown')}")
        print(f"Base course for up-to-date intersection: {base_course if base_course else 'None'}")
        try:
            if not analysis_only and not download_only:
                print(f"Downloading data for {cat}/{cid}...")
                run_download_pipeline(cat, cid)
                print(f"Download completed for {cat}/{cid}")
            if not download_only:
                print(f"Analyzing data for {cat}/{cid}...")
                run_analysis_pipeline(cat, cid, upload_reports=not no_upload)
                print(f"Analysis completed for {cat}/{cid}")
            if not no_upload:
                print(f"Uploading reports/CSVs para {cat}/{cid}...")
                uploaded_links = upload_files_for_course(cat, cid)
                print(f"Upload completed for {cat}/{cid}")
                send_slack_notification_for_upload(cat, cid, course_config, uploaded_links)
        except Exception as e:
            print(f"Error processing course {cat}/{cid}: {str(e)}")
            return
        print(f"Batch processing completed for {cat}/{cid}!")
    # Logic for batch
    if category and course_id:
        process_one(category, course_id)
    elif category:
        if category in courses:
            for cid in courses[category]:
                process_one(category, cid)
        else:
            print(f"Category {category} not found.")
    else:
        for cat in courses:
            for cid in courses[cat]:
                process_one(cat, cid)

if __name__ == "__main__":
    args = parse_arguments()
    run_batch_pipeline(
        config_path=args.config,
        category=args.category,
        course_id=args.course,
        download_only=args.download_only,
        analysis_only=args.analysis_only,
        no_upload=args.no_upload
    ) 