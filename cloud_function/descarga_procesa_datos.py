import os
import json
import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
import shutil
from typing import Dict, List, Any
import yaml
import tempfile

# Google Cloud Storage imports
from google.cloud import storage
from google.oauth2 import service_account
import base64

def load_course_config(config_path: str = "cursos.yml"):
    """Load course configuration from YAML file"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_storage_client():
    """Initialize Google Cloud Storage client"""
    try:
        # Try to use default credentials first (for Cloud Functions)
        return storage.Client()
    except Exception:
        # Fallback to service account key from environment
        service_account_key = os.getenv('GOOGLE_SERVICE_ACCOUNT_KEY')
        if not service_account_key:
            raise ValueError("GOOGLE_SERVICE_ACCOUNT_KEY environment variable not set")
        
        try:
            # Try to decode as base64 first
            decoded_key = base64.b64decode(service_account_key).decode('utf-8')
            key_data = json.loads(decoded_key)
        except:
            # If base64 fails, try as raw JSON
            key_data = json.loads(service_account_key)
        
        credentials = service_account.Credentials.from_service_account_info(key_data)
        return storage.Client(credentials=credentials)

def get_bucket():
    """Get Cloud Storage bucket"""
    client = get_storage_client()
    bucket_name = os.getenv('GCP_BUCKET_NAME')
    if not bucket_name:
        raise ValueError("GCP_BUCKET_NAME environment variable not set")
    return client.bucket(bucket_name)

def download_from_gcs(gcs_path: str) -> Any:
    """Download JSON data from Cloud Storage"""
    try:
        bucket = get_bucket()
        blob = bucket.blob(gcs_path)
        
        if not blob.exists():
            return None
        
        # Download to temporary file
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
            blob.download_to_filename(temp_file.name)
            temp_file.seek(0)
            data = json.load(temp_file)
        
        # Clean up temp file
        os.unlink(temp_file.name)
        return data
    except Exception as e:
        print(f"Error downloading from GCS {gcs_path}: {e}")
        return None

def upload_to_gcs(data: Any, gcs_path: str):
    """Upload JSON data to Cloud Storage"""
    try:
        bucket = get_bucket()
        blob = bucket.blob(gcs_path)
        
        # Upload JSON data
        blob.upload_from_string(
            json.dumps(data, ensure_ascii=False, indent=2),
            content_type='application/json'
        )
        print(f"Uploaded data to gs://{bucket.name}/{gcs_path}")
    except Exception as e:
        print(f"Error uploading to GCS {gcs_path}: {e}")
        raise

def get_latest_timestamp_from_gcs(course_id: str, data_type: str) -> float:
    """Get the latest timestamp from Cloud Storage JSON file"""
    gcs_path = f"raw/{course_id}/{data_type}.json"
    
    try:
        data = download_from_gcs(gcs_path)
        if not data:
            return None
        
        # Get the first record (newest) since data is sorted by created timestamp
        latest_record = data[0]
        return latest_record.get('created')
    except Exception as e:
        print(f"Error getting latest timestamp from GCS: {e}")
        return None

def setup_directories(course_id: str):
    """Create temporary directory structure for processing"""
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

def get_course_grades_incremental(course_id, school_domain, headers):
    """Download grades incrementally based on the latest timestamp from Cloud Storage"""
    print("Checking for existing grades data in Cloud Storage...")
    latest_timestamp = get_latest_timestamp_from_gcs(course_id, "grades")
    
    if latest_timestamp is None:
        print("No existing grades data found. Performing full download...")
        return get_course_grades_full(course_id, school_domain, headers)
    
    print(f"Latest grade timestamp: {datetime.fromtimestamp(latest_timestamp)}")
    print("Downloading new grades only...")
    
    # Load existing data from Cloud Storage
    existing_data = download_from_gcs(f"raw/{course_id}/grades.json") or []
    
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

def get_course_users_incremental(course_id, school_domain, headers):
    """Download users incrementally based on the latest timestamp from Cloud Storage"""
    print("Checking for existing users data in Cloud Storage...")
    latest_timestamp = get_latest_timestamp_from_gcs(course_id, "users")
    
    if latest_timestamp is None:
        print("No existing users data found. Performing full download...")
        return get_course_users_full(course_id, school_domain, headers)
    
    print(f"Latest user timestamp: {datetime.fromtimestamp(latest_timestamp)}")
    print("Downloading new users only...")
    
    # Load existing data from Cloud Storage
    existing_data = download_from_gcs(f"raw/{course_id}/users.json") or []
    
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
    all_data = []
    page = 1
    while True:
        url = f"https://{school_domain}/admin/api/v2/courses/{course_id}/users?page={page}"
        response = requests.get(url, headers=headers)
        data = response.json()
        if response.status_code != 200:
            print(f"Failed to fetch users: {response.status_code}")
            break
        all_data.extend(data.get("data", []))
        total_pages = data.get("meta", {}).get("totalPages", 1)
        if page >= total_pages:
            break
        page += 1
    return all_data

def run_full_pipeline(course_id: str):
    """Run the complete download and processing pipeline for a course"""
    try:
        # Load configuration
        config = load_course_config()
        courses = config.get('courses', {})
        
        if course_id not in courses:
            raise ValueError(f"Course {course_id} not found in configuration")
        
        course_config = courses[course_id]
        
        # Setup temporary directories for processing
        root = setup_directories(course_id)
        
        # Get API credentials from environment variables
        client_id = os.getenv('CLIENT_ID')
        school_domain = os.getenv('SCHOOL_DOMAIN')
        access_token = os.getenv('ACCESS_TOKEN')
        
        if not all([client_id, school_domain, access_token]):
            raise ValueError("Missing API credentials. Set CLIENT_ID, SCHOOL_DOMAIN, and ACCESS_TOKEN environment variables.")
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        print(f"Processing course: {course_id}")
        print(f"School domain: {school_domain}")
        
        # Get assessments (always full download as they don't have timestamps)
        print("Downloading assessments...")
        assessments = get_assessments(course_id, school_domain, headers)
        print(f"Found {len(assessments)} assessments")
        
        # Save assessments to Cloud Storage
        upload_to_gcs(assessments, f"raw/{course_id}/assessments.json")
        
        # Convert assessments to DataFrame and save as CSV locally for processing
        assessments_list = [{"assessment_name": name, "assessment_id": id} for name, id in assessments.items()]
        df_assessments = pd.DataFrame(assessments_list)
        assessments_csv_path = root / "processed" / course_id / "assessments.csv"
        df_assessments.to_csv(assessments_csv_path, index=False, sep=';')
        print(f"Assessments saved to: {assessments_csv_path}")
        
        # Download grades incrementally from Cloud Storage
        grades_data = get_course_grades_incremental(course_id, school_domain, headers)
        
        # Save grades to Cloud Storage
        upload_to_gcs(grades_data, f"raw/{course_id}/grades.json")
        
        # Convert grades to DataFrame and save as CSV locally for processing
        if grades_data:
            df_grades = pd.json_normalize(grades_data)
            grades_csv_path = root / "processed" / course_id / "grades.csv"
            df_grades.to_csv(grades_csv_path, index=False, sep=';')
            print(f"Grades saved to: {grades_csv_path} ({len(grades_data)} records)")
        else:
            print("No grades data found")
        
        # Download users incrementally from Cloud Storage
        users_data = get_course_users_incremental(course_id, school_domain, headers)
        
        # Save users to Cloud Storage
        upload_to_gcs(users_data, f"raw/{course_id}/users.json")
        
        # Convert users to DataFrame and save as CSV locally for processing
        if users_data:
            df_users = pd.json_normalize(users_data)
            users_csv_path = root / "processed" / course_id / "users.csv"
            df_users.to_csv(users_csv_path, index=False, sep=';')
            print(f"Users saved to: {users_csv_path} ({len(users_data)} records)")
        else:
            print("No users data found")
        
        print(f"✅ Pipeline completed for {course_id}")
        
    except Exception as e:
        print(f"❌ Pipeline failed for {course_id}: {str(e)}")
        raise