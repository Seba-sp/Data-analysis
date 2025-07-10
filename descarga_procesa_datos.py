import os
import json
import pandas as pd
from dotenv import load_dotenv
import requests
import argparse
from pathlib import Path
from datetime import datetime
import shutil

def parse_arguments():
    parser = argparse.ArgumentParser(description='Download and process course data')
    parser.add_argument('--course', '-c', required=True, help='Course ID to process')
    parser.add_argument('--reset-raw', action='store_true', help='Delete raw data and download from scratch')
    return parser.parse_args()

# Load environment variables
load_dotenv()

def setup_directories(course_id: str):
    """Create the new directory structure for the course"""
    root = Path("data")
    directories = [
        root / "raw" / course_id,
        root / "processed" / course_id,
        root / "metrics" / "kpi" / course_id,
        root / "reports" / course_id
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    
    return root

def get_assessments(course_id, school_domain, headers):
    assessment_dict = {}
    page = 1
    while True:
        url = f"https://{school_domain}/admin/api/v2/courses/{course_id}/contents?page={page}"
        response = requests.get(url, headers=headers)
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
        if page >= total_pages:
            break
        page += 1
    return assessment_dict

def get_latest_timestamp_from_json(json_file_path):
    """Get the latest 'created' timestamp from an existing JSON file"""
    if not json_file_path.exists():
        return None
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data:
            return None
        
        # Get the first record (newest) since data is sorted by created timestamp
        latest_record = data[0]
        return latest_record.get('created')
    except (json.JSONDecodeError, IndexError, KeyError):
        return None

def get_course_grades_incremental(course_id, school_domain, headers, json_file_path):
    """Download grades incrementally based on the latest timestamp"""
    print("Checking for existing grades data...")
    latest_timestamp = get_latest_timestamp_from_json(json_file_path)
    
    if latest_timestamp is None:
        print("No existing grades data found. Performing full download...")
        return get_course_grades_full(course_id, school_domain, headers)
    
    print(f"Latest grade timestamp: {datetime.fromtimestamp(latest_timestamp)}")
    print("Downloading new grades only...")
    
    # Load existing data
    existing_data = []
    if json_file_path.exists():
        with open(json_file_path, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
    
    new_data = []
    page = 1
    reached_existing = False
    
    while not reached_existing:
        url = f"https://{school_domain}/admin/api/v2/courses/{course_id}/grades?page={page}"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"Failed to fetch grades: {response.status_code}")
            break
        
        data = response.json()
        page_data = data.get("data", [])
        
        if not page_data:
            break
        
        # Check if we've reached existing data
        for record in page_data:
            record_timestamp = record.get('created')
            if record_timestamp and record_timestamp <= latest_timestamp:
                reached_existing = True
                break
            new_data.append(record)
        
        total_pages = data.get("meta", {}).get("totalPages", 1)
        if page >= total_pages:
            break
        page += 1
    
    if new_data:
        print(f"Found {len(new_data)} new grade records")
        # Combine new data with existing data and sort by created timestamp (newest first)
        combined_data = new_data + existing_data
        combined_data.sort(key=lambda x: x.get('created', 0), reverse=True)
        return combined_data
    else:
        print("No new grades found")
        return existing_data

def get_course_grades_full(course_id, school_domain, headers):
    """Download all grades (original function)"""
    all_data = []
    page = 1
    while True:
        url = f"https://{school_domain}/admin/api/v2/courses/{course_id}/grades?page={page}"
        response = requests.get(url, headers=headers)
        data = response.json()
        if response.status_code != 200:
            print(f"Failed to fetch grades: {response.status_code}")
            break
        all_data.extend(data.get("data", []))
        total_pages = data.get("meta", {}).get("totalPages", 1)
        if page >= total_pages:
            break
        page += 1
    return all_data

def get_course_users_incremental(course_id, school_domain, headers, json_file_path):
    """Download users incrementally based on the latest timestamp"""
    print("Checking for existing users data...")
    latest_timestamp = get_latest_timestamp_from_json(json_file_path)
    
    if latest_timestamp is None:
        print("No existing users data found. Performing full download...")
        return get_course_users_full(course_id, school_domain, headers)
    
    print(f"Latest user timestamp: {datetime.fromtimestamp(latest_timestamp)}")
    print("Downloading new users only...")
    
    # Load existing data
    existing_data = []
    if json_file_path.exists():
        with open(json_file_path, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
    
    new_data = []
    page = 1
    reached_existing = False
    
    while not reached_existing:
        url = f"https://{school_domain}/admin/api/v2/courses/{course_id}/users?page={page}"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"Failed to fetch users: {response.status_code}")
            break
        
        data = response.json()
        page_data = data.get("data", [])
        
        if not page_data:
            break
        
        # Check if we've reached existing data
        for record in page_data:
            record_timestamp = record.get('created')
            if record_timestamp and record_timestamp <= latest_timestamp:
                reached_existing = True
                break
            new_data.append(record)
        
        total_pages = data.get("meta", {}).get("totalPages", 1)
        if page >= total_pages:
            break
        page += 1
    
    if new_data:
        print(f"Found {len(new_data)} new user records")
        # Combine new data with existing data and sort by created timestamp (newest first)
        combined_data = new_data + existing_data
        combined_data.sort(key=lambda x: x.get('created', 0), reverse=True)
        return combined_data
    else:
        print("No new users found")
        return existing_data

def get_course_users_full(course_id, school_domain, headers):
    """Download all users (original function)"""
    users = []
    page = 1
    while True:
        url = f"https://{school_domain}/admin/api/v2/courses/{course_id}/users?page={page}"
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch users: {response.status_code}")
            break
        data = response.json()
        users.extend(data.get("data", []))
        total_pages = data.get("meta", {}).get("totalPages", 1)
        if page >= total_pages:
            break
        page += 1
    return users

def delete_raw_data(course_id: str):
    """Delete all raw data files for a course."""
    raw_dir = Path("data") / "raw" / course_id
    if raw_dir.exists() and raw_dir.is_dir():
        shutil.rmtree(raw_dir)
        print(f"Deleted raw data for course: {course_id}")
    else:
        print(f"No raw data found for course: {course_id}")

def run_full_pipeline(course_id: str):
    """Main pipeline function"""
    print(f"Processing course: {course_id}")
    
    # Setup environment
    client_id = os.getenv("CLIENT_ID")
    school_domain = os.getenv("SCHOOL_DOMAIN")
    access_token = os.getenv("ACCESS_TOKEN")
    
    if not all([client_id, school_domain, access_token]):
        raise ValueError("Missing required environment variables: CLIENT_ID, SCHOOL_DOMAIN, ACCESS_TOKEN")
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Lw-Client": client_id,
        "Accept": "application/json"
    }
    
    # Setup directories
    root = setup_directories(course_id)
    raw_dir = root / "raw" / course_id
    processed_dir = root / "processed" / course_id
    
    # Download and save assessments (full download since no timestamps)
    print("Downloading assessments...")
    assessments = get_assessments(course_id, school_domain, headers)
    with open(raw_dir / "assessments.json", "w", encoding="utf-8") as f:
        json.dump(assessments, f, ensure_ascii=False, indent=2)

    # Download users incrementally
    users_json_path = raw_dir / "users.json"
    users = get_course_users_incremental(course_id, school_domain, headers, users_json_path)
    with open(users_json_path, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

    # Download grades incrementally
    grades_json_path = raw_dir / "grades.json"
    grades = get_course_grades_incremental(course_id, school_domain, headers, grades_json_path)
    with open(grades_json_path, "w", encoding="utf-8") as f:
        json.dump(grades, f, ensure_ascii=False, indent=2)

    # Procesamiento y guardado como CSV (except responses)
    print("Processing data...")
    df_assessments = pd.DataFrame(list(assessments.items()), columns=["assessment_name", "assessment_id"])
    df_users = pd.DataFrame(users)
    df_grades = pd.DataFrame(grades)

    if "learningUnit" in df_grades.columns:
        df_grades["assessment_id"] = df_grades["learningUnit"].apply(lambda x: x.get("id") if isinstance(x, dict) and "id" in x else None)
        
    # Convertir timestamps en grades
    for col in ["created", "modified", "submittedTimestamp"]:
        if col in df_grades.columns:
            df_grades[col] = pd.to_datetime(df_grades[col], unit="s").dt.floor("s")

    # Convertir timestamps en users
    for col in ["created", "last_login"]:
        if col in df_users.columns:
            df_users[col] = pd.to_datetime(df_users[col], unit="s").dt.floor("s")

    sep = ";"
    df_assessments.to_csv(processed_dir / "assessments.csv", sep=sep, index=False)
    df_users.to_csv(processed_dir / "users.csv", sep=sep, index=False)
    df_grades.to_csv(processed_dir / "grades.csv", sep=sep, index=False)

    print(f"Download, processing and saving of data completed for course {course_id}")
    print(f"Raw data saved in: {raw_dir}")
    print(f"Processed data saved in: {processed_dir}")

if __name__ == "__main__":
    args = parse_arguments()
    if args.reset_raw:
        delete_raw_data(args.course)
    run_full_pipeline(args.course) 