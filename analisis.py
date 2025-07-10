import os
import pandas as pd
from fpdf import FPDF
import argparse
from pathlib import Path
import yaml
import re
from datetime import datetime

def parse_arguments():
    parser = argparse.ArgumentParser(description='Analyze course data and generate reports')
    parser.add_argument('--course', '-c', required=True, help='Course ID to analyze')
    return parser.parse_args()

def load_course_config(config_path: str = "cursos.yml"):
    """Load course configuration from YAML file"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_ignored_users(course_id: str, config_path: str = "cursos.yml"):
    """Get ignored users for a specific course from configuration"""
    config = load_course_config(config_path)
    courses = config.get('courses', {})
    course_config = courses.get(course_id, {})
    return course_config.get('ignored_users', [])

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

def run_analysis_pipeline(course_id: str):
    """Main analysis pipeline function"""
    print(f"Analyzing course: {course_id}")
    
    # Get ignored users from configuration
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
            user_response_summary.append({
                'user_id': user_id,
                'email': user_email,
                'username': username,
                'assessment': assess_name,
                'responded': has_responded,
                'grade': grade,
                'completion_time_minutes': completion_time
            })
    user_response_df = pd.DataFrame(user_response_summary)

    # --- Lists for report ---
    no_response_users = users_df.copy()
    no_response_users['responded_any'] = no_response_users['id'].apply(lambda uid: user_response_df[user_response_df['user_id'] == uid]['responded'].any())
    no_response_list = no_response_users[~no_response_users['responded_any']][['email', 'username']].values.tolist()

    responded_list = user_response_df[user_response_df['responded']][['email', 'username', 'assessment', 'grade', 'completion_time_minutes']].values.tolist()

    from collections import defaultdict
    responded_by_assessment = defaultdict(list)
    for email, username, assessment, grade, completion_time in responded_list:
        responded_by_assessment[assessment].append([email, username, assessment, grade, completion_time])

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
            df_response = pd.DataFrame(rows, columns=["correo", "usuario", "evaluación", "nota", "tiempo_minutos"])
            df_response.to_excel(writer, sheet_name=clean_sheet_name, index=False)
    
    print(f"Excel file generated: {excel_path}")

if __name__ == "__main__":
    args = parse_arguments()
    run_analysis_pipeline(args.course) 