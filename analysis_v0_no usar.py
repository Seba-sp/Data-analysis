import requests
import pandas as pd
import os
from dotenv import load_dotenv
from fpdf import FPDF
from collections import defaultdict

load_dotenv()  # Loads from .env by default

# --- CONFIG ---
course_id = "test-de-diagnostico-m30m"
client_id = os.getenv("CLIENT_ID")
school_domain = os.getenv("SCHOOL_DOMAIN")
access_token = os.getenv("ACCESS_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {access_token}",
    "Lw-Client": client_id,
    "Accept": "application/json"
}

def get_assessments(course_id, pages=None):
    """
    Fetch all assessments for a course, paginating if necessary.
    If pages is None, fetch all pages. If pages is an int, fetch up to that many pages.
    """
    assessment_dict = {}
    page = 1
    fetched = 0
    while True:
        url = f"https://{school_domain}/admin/api/v2/courses/{course_id}/contents?page={page}"
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            print(f"Failed to fetch assessments: {response.status_code}")
            break
        resp_json = response.json()
        for section in resp_json.get("sections", []):
            for unit in section.get("learningUnits", []):
                if unit.get("type") == "assessmentV2":
                    key = unit.get("title") or f"{section['title']} - sin título"
                    assessment_dict[key] = unit["id"]
        total_pages = resp_json.get("meta", {}).get("totalPages", 1)
        fetched += 1
        if (pages is not None and fetched >= pages) or page >= total_pages:
            break
        page += 1
    return assessment_dict

def get_course_grades(course_id, pages=None):
    """
    Fetch all course grades, paginating if necessary.
    If pages is None, fetch all pages. If pages is an int, fetch up to that many pages.
    """
    all_data = []
    page = 1
    fetched = 0
    while True:
        url = f"https://{school_domain}/admin/api/v2/courses/{course_id}/grades?page={page}"
        response = requests.get(url, headers=HEADERS)
        data = response.json()
        if response.status_code != 200:
            print(f"Failed to fetch response for course {course_id}: {response.status_code}")
            break
        all_data.extend(data.get("data", []))
        total_pages = data.get("meta", {}).get("totalPages", 1)
        fetched += 1
        if (pages is not None and fetched >= pages) or page >= total_pages:
            break
        page += 1
    if not all_data:
        return pd.DataFrame([])
    df = pd.json_normalize(all_data)
    if "learningUnit.id" in df.columns:
        df["assessment_id"] = df["learningUnit.id"]
    for col in ["created", "modified", "submittedTimestamp"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], unit="s").dt.floor("s")
    return df

def get_assessment_responses(assessment_id, pages=None):
    """
    Fetch all responses for an assessment, paginating if necessary.
    If pages is None, fetch all pages. If pages is an int, fetch up to that many pages.
    """
    if not assessment_id:
        print("No assessment_id provided.")
        return pd.DataFrame([])
    rows = []
    page = 1
    fetched = 0
    while True:
        url = f"https://{school_domain}/admin/api/v2/assessments/{assessment_id}/responses?page={page}"
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            print(f"Failed to fetch responses for assessment {assessment_id}: {response.status_code}")
            break
        data = response.json().get('data', [])
        for entry in data:
            base = {
                "id": entry["id"],
                "user_id": entry["user_id"],
                "email": entry["email"],
                "grade": entry["grade"],
                "passed": entry["passed"],
                "created": entry["created"],
                "modified": entry["modified"],
                "submittedTimestamp": entry["submittedTimestamp"]
            }
            for i, ans in enumerate(entry["answers"], start=1):
                base[f"Pregunta {i} - Respuesta"] = ans["answer"]
                base[f"Pregunta {i} - Correcta"] = ans["points"] == ans["blockMaxScore"]
            rows.append(base)
        resp_json = response.json()
        total_pages = resp_json.get("meta", {}).get("totalPages", 1)
        fetched += 1
        if (pages is not None and fetched >= pages) or page >= total_pages:
            break
        page += 1
    df = pd.DataFrame(rows)
    for col in ["created", "modified", "submittedTimestamp"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], unit="s").dt.floor("s")
    return df

def get_course_users(course_id, pages=None):
    """
    Fetch all users for a course, paginating if necessary.
    If pages is None, fetch all pages. If pages is an int, fetch up to that many pages.
    """
    users = []
    page = 1
    fetched = 0
    while True:
        url = f"https://{school_domain}/admin/api/v2/courses/{course_id}/users?page={page}"
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            print(f"❌ Failed to fetch users for course {course_id}: {response.status_code}")
            break
        data = response.json()
        users.extend(data.get("data", []))
        total_pages = data.get("meta", {}).get("totalPages", 1)
        fetched += 1
        if (pages is not None and fetched >= pages) or page >= total_pages:
            break
        page += 1
    df = pd.json_normalize(users)
    return df

# --- DATA FETCHING ---

assessments = get_assessments(course_id)
grades_df = get_course_grades(course_id)

# Example: Get responses for all assessments
responses_dfs = {}
for name, aid in assessments.items():
    responses_dfs[name] = get_assessment_responses(aid)

# --- ANALYSIS EXAMPLES ---

# Merge grades with assessment names
grades_df["assessment_name"] = grades_df["assessment_id"].map({v: k for k, v in assessments.items()})

# --- USER/RESPONSE/GRADE ANALYSIS ---

# 1. Get all users enrolled in the course
users_df = get_course_users(course_id)

# 1.1. Add username extraction (if available)
if 'username' not in users_df.columns:
    users_df['username'] = users_df['email'].apply(lambda x: x.split('@')[0] if pd.notnull(x) else None)

# 2. For each assessment, check which users responded
user_response_summary = []
for assess_name, df in responses_dfs.items():
    responded_users = set(df['user_id'])
    for _, user in users_df.iterrows():
        user_id = user['id'] if 'id' in user else user['user_id']
        user_email = user['email'] if 'email' in user else user.get('email', None)
        username = user['username'] if 'username' in user else (user_email.split('@')[0] if user_email else None)
        has_responded = user_id in responded_users
        # Get grade if available
        grade_row = grades_df[(grades_df['user_id'] == user_id) & (grades_df['assessment_name'] == assess_name)]
        grade = grade_row['grade'].iloc[0] if not grade_row.empty else None
        user_response_summary.append({
            'user_id': user_id,
            'email': user_email,
            'username': username,
            'assessment': assess_name,
            'responded': has_responded,
            'grade': grade
        })
user_response_df = pd.DataFrame(user_response_summary)

# --- Remove responses for user 'seba test' ---
user_response_df = user_response_df[user_response_df['username'].str.lower() != 'seba test']

# Update responded_list after removal
responded_list = user_response_df[user_response_df['responded']][['email', 'username', 'assessment', 'grade']].values.tolist()

# --- NEW: Lists for report ---
# 1. Users who did not respond to any assessment
no_response_users = users_df.copy()
no_response_users['responded_any'] = no_response_users['id'].apply(lambda uid: user_response_df[user_response_df['user_id'] == uid]['responded'].any())
no_response_list = no_response_users[~no_response_users['responded_any']][['email', 'username']].values.tolist()

print("\n--- Users who did NOT respond to any assessment ---")
for item in no_response_list:
    print(item)

# --- Group responded_list by assessment for separated output ---
responded_by_assessment = defaultdict(list)
for email, username, assessment, grade in responded_list:
    responded_by_assessment[assessment].append([email, username, assessment, grade])

# Print grouped responded list
print("\n--- Users who responded (per assessment, separated) ---")
for assessment, rows in responded_by_assessment.items():
    for item in rows:
        print(item)
    print("\n\n")

# 3. Print summary: users, responses, grades
print("\n--- User Assessment Response Summary ---")
print(user_response_df)

# 4. Grade metrics per test
metrics = []
for assess_name in assessments.keys():
    grades = user_response_df[(user_response_df['assessment'] == assess_name) & (user_response_df['grade'].notnull())]['grade']
    if not grades.empty:
        metrics.append({
            'assessment': assess_name,
            'min': grades.min(),
            'q25': grades.quantile(0.25),
            'q50': grades.quantile(0.5),
            'q75': grades.quantile(0.75),
            'q100': grades.max(),
            'mean': grades.mean(),
            'count': grades.count()
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
            'count': 0
        })
metrics_df = pd.DataFrame(metrics)

print("\n--- Grade Metrics Per Assessment ---")
print(metrics_df)

# --- PDF REPORT GENERATION ---
pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", size=12)

# Title
pdf.cell(0, 10, "Resumen de respuestas y notas de usuarios", ln=True, align="C")

# List 1: Users who did not respond
pdf.set_font("Arial", size=11)
pdf.cell(0, 10, f"Usuarios que NO respondieron a ninguna evaluación: {len(no_response_list)}", ln=True)
# Table header
pdf.set_fill_color(200, 200, 200)
pdf.set_font("Arial", 'B', 10)
pdf.cell(60, 8, "Correo", border=1, fill=True)
pdf.cell(60, 8, "Usuario", border=1, fill=True)
pdf.ln()
pdf.set_font("Arial", size=10)
for email, username in no_response_list:
    pdf.cell(60, 8, str(email), border=1)
    pdf.cell(60, 8, str(username), border=1)
    pdf.ln()
pdf.ln(5)

# List 2: Users who responded (per assessment, separated)
pdf.set_font("Arial", size=11)
total_responded = sum(len(rows) for rows in responded_by_assessment.values())
pdf.cell(0, 10, f"Usuarios que respondieron (por evaluación)")
pdf.ln(7)
for assessment, rows in responded_by_assessment.items():
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 8, f"Evaluación: {assessment} ({len(rows)})", ln=True)
    pdf.cell(60, 8, "Correo", border=1, fill=True)
    pdf.cell(40, 8, "Usuario", border=1, fill=True)
    pdf.cell(50, 8, "Evaluación", border=1, fill=True)
    pdf.cell(20, 8, "Nota", border=1, fill=True)
    pdf.ln()
    pdf.set_font("Arial", size=10)
    for email, username, _, grade in rows:
        pdf.cell(60, 8, str(email), border=1)
        pdf.cell(40, 8, str(username), border=1)
        pdf.cell(50, 8, str(assessment), border=1)
        pdf.cell(20, 8, str(grade), border=1)
        pdf.ln()
    pdf.ln(3)
pdf.ln(5)

# Metrics Table
pdf.set_font("Arial", size=12)
pdf.cell(0, 10, "Métricas de notas por evaluación", ln=True, align="C")
pdf.set_font("Arial", 'B', 10)
metric_cols_es = ["Evaluación", "Mínimo", "Q25", "Q50", "Q75", "Máximo", "Promedio", "Cantidad"]
col_widths = [40, 18, 18, 18, 18, 18, 22, 22]
for i, col in enumerate(metric_cols_es):
    pdf.cell(col_widths[i], 8, col, border=1, fill=True)
pdf.ln()
pdf.set_font("Arial", size=10)
for _, row in metrics_df.iterrows():
    values = [
        str(row["assessment"]),
        str(row["min"]),
        str(row["q25"]),
        str(row["q50"]),
        str(row["q75"]),
        str(row["q100"]),
        f"{row['mean']:.2f}" if pd.notnull(row['mean']) else str(row['mean']),
        str(row["count"])
    ]
    for i, value in enumerate(values):
        pdf.cell(col_widths[i], 8, str(value), border=1)
    pdf.ln()
pdf.ln(5)

# --- Attendance Metrics ---
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

# --- Format all numbers in tables ---
def fmt(val):
    if isinstance(val, float):
        if val.is_integer():
            return str(int(val))
        return f"{val:.2f}"
    return str(val)

pdf.output("reporte.pdf")
print("\nPDF report generado: reporte.pdf")

# --- Export lists to Excel (grouped by assessment for responded) ---
with pd.ExcelWriter("reporte_listas.xlsx") as writer:
    pd.DataFrame(no_response_list, columns=["correo", "usuario"]).to_excel(writer, sheet_name="Sin Respuesta", index=False)
    for assessment, rows in responded_by_assessment.items():
        pd.DataFrame(rows, columns=["correo", "usuario", "evaluación", "nota"]).to_excel(writer, sheet_name=assessment[:31], index=False)
print("Archivo Excel generado: reporte_listas.xlsx")
