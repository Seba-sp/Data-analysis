import json
import yaml
from dotenv import load_dotenv
import os
import requests
from storage import StorageClient

# Hardcoded KPIs for all courses
HARDCODED_KPIS = [
    "attendance_rate",
    "average_grade",
    "completion_rate",
    "response_rate"
]

RAW_JSON_PATH = "courses_raw.json"
TXT_PATH = "cursos.txt"
YML_PATH = "cursos.yml"

def fetch_courses_from_learnworlds():
    load_dotenv()
    client_id = os.getenv("CLIENT_ID")
    school_domain = os.getenv("SCHOOL_DOMAIN")
    access_token = os.getenv("ACCESS_TOKEN")
    if not all([client_id, school_domain, access_token]):
        print("Missing required environment variables: CLIENT_ID, SCHOOL_DOMAIN, ACCESS_TOKEN")
        return None
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Lw-Client": client_id,
        "Accept": "application/json"
    }
    courses = []
    page = 1
    while True:
        url = f"https://{school_domain}/admin/api/v2/courses?page={page}"
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch courses: {response.status_code}")
            print(response.text)
            return None
        data = response.json()
        page_courses = data.get("data", [])
        if not page_courses:
            break
        courses.extend(page_courses)
        total_pages = data.get("meta", {}).get("totalPages", 1)
        if page >= total_pages:
            break
        page += 1
    return courses

def build_cursos_txt_and_yml(courses):
    txt_lines = []
    yml_data = {"courses": {}}
    for course in courses:
        course_id = course.get("id")
        name = course.get("title") or course_id
        categories = course.get("categories") or []
        category = categories[0] if categories else "SinCategoria"
        # TXT
        txt_lines.append(f"{category},{course_id}")
        # YML
        if category not in yml_data["courses"]:
            yml_data["courses"][category] = {}
        yml_data["courses"][category][course_id] = {
            "name": name,
            "kpis": HARDCODED_KPIS
        }
    return txt_lines, yml_data

def write_files_with_storage(txt_lines, yml_data, raw_json, txt_path=TXT_PATH, yml_path=YML_PATH, raw_json_path=RAW_JSON_PATH):
    storage = StorageClient()
    # Write cursos.txt
    storage.write_bytes(txt_path, ("\n".join(txt_lines) + "\n").encode("utf-8"), content_type="text/plain")
    print(f"Wrote {txt_path} with {len(txt_lines)} lines.")
    # Write cursos.yml
    yml_str = yaml.dump(yml_data, allow_unicode=True, sort_keys=False)
    storage.write_bytes(yml_path, yml_str.encode("utf-8"), content_type="text/yaml")
    print(f"Wrote {yml_path}.")
    # Write courses_raw.json
    storage.write_bytes(raw_json_path, json.dumps(raw_json, ensure_ascii=False, indent=2).encode("utf-8"), content_type="application/json")
    print(f"Wrote {raw_json_path}.")

def main():
    print("Fetching courses from LearnWorlds API...")
    courses = fetch_courses_from_learnworlds()
    if courses is None:
        print("No courses fetched. Exiting.")
        return
    txt_lines, yml_data = build_cursos_txt_and_yml(courses)
    print("Writing files with StorageClient...")
    write_files_with_storage(txt_lines, yml_data, courses)
    print("Done.")

if __name__ == "__main__":
    main() 