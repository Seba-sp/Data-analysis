import os
import pandas as pd
from fpdf import FPDF
import argparse
from pathlib import Path
import yaml
import re
from datetime import datetime
import json
import base64
from typing import Dict, List, Any
from dotenv import load_dotenv
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

def parse_arguments():
    parser = argparse.ArgumentParser(description='Analyze course data and generate reports')
    parser.add_argument('--course', '-c', required=True, help='Course ID to analyze')
    parser.add_argument('--upload', '-u', action='store_true', help='Upload reports to Google Drive and send Slack notification')
    parser.add_argument('--no-upload', action='store_true', help='Skip upload and notification (default behavior)')
    return parser.parse_args()

def load_course_config(config_path: str = "cursos.yml"):
    """Load course configuration from YAML file"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_ignored_users(course_id: str, config_path: str = "cursos.yml"):
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

def send_slack_notification(course_id: str, course_name: str, drive_links: List[str], channel: str = None):
    """Send Slack notification with report links"""
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
                    "text": f"📊 Reporte de Análisis de Curso - {course_name}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Curso:* {course_name}\n*ID del Curso:* {course_id}\n*Análisis completado:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
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
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• <{link}|Ver Archivo>"
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
        
        # Create fallback text for accessibility
        fallback_text = f"📊 Reporte de Análisis de Curso - {course_name}\nCurso: {course_name}\nID del Curso: {course_id}\nAnálisis completado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
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

def upload_reports_and_notify(course_id: str, course_name: str, reports_dir: Path, processed_dir: Path):
    """Upload today's reports and CSV files to Google Drive (per-course folder), send Slack notification for reports only"""
    from datetime import datetime
    drive_service = get_drive_service()
    parent_folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
    drive_id = os.getenv('GOOGLE_DRIVE_ID') if os.getenv('GOOGLE_DRIVE_ID') else None
    course_folder_id = find_or_create_folder(drive_service, parent_folder_id, course_id, drive_id)
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
            send_slack_notification(course_id, course_name, report_links)
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

def run_analysis_pipeline(course_id: str, upload_reports: bool = False):
    """Main analysis pipeline function"""
    print(f"Analyzing course: {course_id}")
    
    # Get ignored users from environment variable
    ignore_emails = get_ignored_users(course_id)
    print(f"Ignored users for {course_id}: {ignore_emails}")
    
    # Setup paths
    root = Path("data")
    processed_dir = root / "processed" / course_id
    reports_dir = root / "reports" / course_id
    metrics_dir = root / "metrics" / "kpi"
    
    # Ensure reports directory exists
    reports_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)
    
    # Load processed DataFrames from CSV
    sep = ";"
    df_assessments = pd.read_csv(processed_dir / "assessments.csv", sep=sep)
    df_users = pd.read_csv(processed_dir / "users.csv", sep=sep)
    df_grades = pd.read_csv(processed_dir / "grades.csv", sep=sep)

    # Create ignored users DataFrame
    ignored_users = df_users[df_users['email'].str.lower().isin([e.lower() for e in ignore_emails])].copy()
    print(f"Usuarios ignorados: {len(ignored_users)}")

    # Remove ignored users from all DataFrames
    df_users = df_users[~df_users['email'].str.lower().isin([e.lower() for e in ignore_emails])]
    df_grades = df_grades[~df_grades['user_id'].isin(ignored_users['id'])]

    print(f"Usuarios restantes después de limpieza: {len(df_users)}")
    print(f"Calificaciones restantes después de limpieza: {len(df_grades)}")

    # Calculate completion time for each grade
    df_grades['completion_time_minutes'] = df_grades.apply(
        lambda row: calculate_completion_time(row['created'], row['submittedTimestamp']), 
        axis=1
    )

    # Merge grades with assessment names using a fast pandas merge on 'assessment_id'
    df_grades = df_grades.merge(df_assessments, on="assessment_id", how="left")

    # 1. Get all users enrolled in the course
    users_df = df_users.copy()
    if 'username' not in users_df.columns:
        users_df['username'] = users_df['email'].apply(lambda x: x.split('@')[0] if pd.notnull(x) else None)

    # 2. For each assessment, check which users have a grade (as a proxy for response)
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

    # --- Lists for report ---
    no_response_users = users_df.copy()
    no_response_users['responded_any'] = no_response_users['id'].apply(lambda uid: user_response_df[user_response_df['user_id'] == uid]['responded'].any())
    no_response_list = no_response_users[~no_response_users['responded_any']][['email', 'username']].values.tolist()

    responded_list = user_response_df[user_response_df['responded']][['email', 'username', 'assessment', 'grade', 'completion_time_minutes', 'created_timestamp', 'submitted_timestamp']].values.tolist()

    from collections import defaultdict
    responded_by_assessment = defaultdict(list)
    for email, username, assessment, grade, completion_time, created_timestamp, submitted_timestamp in responded_list:
        responded_by_assessment[assessment].append([email, username, assessment, grade, completion_time, created_timestamp, submitted_timestamp])

    # --- Metrics ---
    metrics = []
    for assess_name in df_assessments['assessment_name']:
        grades = user_response_df[(user_response_df['assessment'] == assess_name) & (user_response_df['grade'].notnull())]['grade']
        completion_times = user_response_df[(user_response_df['assessment'] == assess_name) & 
                                          (user_response_df['completion_time_minutes'].notnull())]['completion_time_minutes']
        
        if not grades.empty:
            metrics.append({
                'assessment': assess_name,
                'min': grades.min(),
                'q25': grades.quantile(0.25),
                'q50': grades.quantile(0.5),
                'q75': grades.quantile(0.75),
                'q100': grades.max(),
                'mean': grades.mean(),
                'count': grades.count(),
                'avg_completion_time_minutes': completion_times.mean() if not completion_times.empty else None
            })
        else:
            metrics.append({
                'assessment': assess_name,
                'min': None,
                'q25': None,
                'q50': None,
                'q75': None,
                'q100': None,
                'mean': None,
                'count': 0,
                'avg_completion_time_minutes': None
            })
    metrics_df = pd.DataFrame(metrics)

    # Save metrics to CSV
    metrics_df.to_csv(metrics_dir / f"{course_id}.csv", index=False)
    print(f"Metrics saved to: {metrics_dir / f'{course_id}.csv'}")

    # --- PDF REPORT GENERATION (simplified to show only metrics) ---
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Métricas de notas y tiempos - Curso: {course_id}", ln=True, align="C")

    # Metrics Table
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, "Métricas de notas y tiempos por evaluación", ln=True, align="C")
    pdf.set_font("Arial", 'B', 9)
    metric_cols_es = ["Evaluación", "Mínimo", "Q25", "Q50", "Q75", "Máximo", "Promedio", "Cantidad", "Tiempo Prom (min)"]
    col_widths = [35, 15, 15, 15, 15, 15, 18, 15, 20]
    pdf.set_fill_color(220, 220, 220)  # Light gray background for header
    for i, col in enumerate(metric_cols_es):
        pdf.cell(col_widths[i], 8, col, border=1, fill=True)
    pdf.ln()
    pdf.set_fill_color(255, 255, 255)  # Reset to white for data rows
    pdf.set_font("Arial", size=8)
    for _, row in metrics_df.iterrows():
        values = [
            row["assessment"],
            row["min"],
            row["q25"],
            row["q50"],
            row["q75"],
            row["q100"],
            f"{row['mean']:.2f}" if pd.notnull(row['mean']) else str(row['mean']),
            row["count"],
            f"{row['avg_completion_time_minutes']:.1f}" if pd.notnull(row['avg_completion_time_minutes']) else str(row['avg_completion_time_minutes'])
        ]
        for i, value in enumerate(values):
            pdf.cell(col_widths[i], 8, str(value), border=1)
        pdf.ln()
    pdf.ln(5)

    # Attendance Metrics
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

    fecha_actual = datetime.now().strftime("%Y-%m-%d")
    pdf_path = reports_dir / f"reporte_{course_id}_{fecha_actual}.pdf"
    pdf.output(str(pdf_path))
    print(f"PDF report generated: {pdf_path}")

    # --- Export lists to Excel (grouped by assessment for responded) ---
    excel_path = reports_dir / f"reporte_{course_id}_{fecha_actual}.xlsx"
    with pd.ExcelWriter(excel_path) as writer:
        # Sheet for users with no response
        pd.DataFrame(no_response_list, columns=["correo", "usuario"]).to_excel(
            writer, sheet_name="Sin Respuesta", index=False
        )
        
        # Sheets for each assessment with responses
        for assessment, rows in responded_by_assessment.items():
            # Clean the assessment name for Excel sheet name
            clean_sheet_name = clean_excel_sheet_name(assessment)
            df_response = pd.DataFrame(rows, columns=["correo", "usuario", "evaluación", "nota", "tiempo_minutos", "fecha_creación", "fecha_envío"])
            df_response.to_excel(writer, sheet_name=clean_sheet_name, index=False)
    
    print(f"Excel file generated: {excel_path}")

    # --- Upload reports to Google Drive and send Slack notification ---
    if upload_reports:
        try:
            # Get course name from configuration
            config = load_course_config()
            courses = config.get('courses', {})
            course_config = courses.get(course_id, {})
            course_name = course_config.get('name', course_id)
            
            # Upload reports and send notification
            drive_links = upload_reports_and_notify(course_id, course_name, reports_dir, processed_dir)
            
            if drive_links:
                print(f"✅ Se subieron {len(drive_links)} archivos a Google Drive")
                print(f"✅ Notificación de Slack enviada con enlaces a reportes")
            else:
                print("⚠️  No se subieron archivos (verificar variables de entorno y permisos)")
                
        except Exception as e:
            print(f"❌ Error durante la subida/notificación: {e}")
            print("   Esta es funcionalidad opcional - el análisis se completó exitosamente")
    else:
        print("📁 Reportes generados localmente (usar --upload para subir a Google Drive y enviar notificación de Slack)")

if __name__ == "__main__":
    args = parse_arguments()
    
    # Determine if upload should be enabled
    upload_enabled = args.upload
    if args.no_upload:
        upload_enabled = False
    
    run_analysis_pipeline(args.course, upload_enabled) 