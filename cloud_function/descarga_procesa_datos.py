# Copy of the existing descarga_procesa_datos.py file for Cloud Function
# This file will be copied from the main directory during deployment

import os
import json
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
import argparse
from typing import Dict, List, Any
import yaml

def load_course_config(config_path: str = "cursos.yml"):
    """Load course configuration from YAML file"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_api_credentials():
    """Get API credentials from environment variables"""
    return {
        'client_id': os.getenv('CLIENT_ID'),
        'school_domain': os.getenv('SCHOOL_DOMAIN'),
        'access_token': os.getenv('ACCESS_TOKEN')
    }

def download_course_data(course_id: str, data_type: str) -> List[Dict[str, Any]]:
    """Download data from LearnWorlds API"""
    credentials = get_api_credentials()
    
    if not all(credentials.values()):
        raise ValueError("Missing API credentials. Set CLIENT_ID, SCHOOL_DOMAIN, and ACCESS_TOKEN environment variables.")
    
    base_url = f"https://{credentials['school_domain']}.learnworlds.com/api/v2"
    headers = {
        'Authorization': f'Bearer {credentials["access_token"]}',
        'Content-Type': 'application/json'
    }
    
    # API endpoints for different data types
    endpoints = {
        'assessments': f'/courses/{course_id}/assessments',
        'grades': f'/courses/{course_id}/grades',
        'users': f'/courses/{course_id}/users'
    }
    
    if data_type not in endpoints:
        raise ValueError(f"Invalid data type: {data_type}")
    
    url = f"{base_url}{endpoints[data_type]}"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"API request failed for {data_type}: {str(e)}")

def save_json_data(data: List[Dict[str, Any]], file_path: str):
    """Save data as JSON file"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def convert_timestamps(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert timestamp fields to readable format"""
    timestamp_fields = ['created_at', 'updated_at', 'completed_at', 'started_at']
    
    for item in data:
        for field in timestamp_fields:
            if field in item and item[field]:
                try:
                    # Convert Unix timestamp to datetime
                    dt = datetime.fromtimestamp(int(item[field]))
                    item[field] = dt.isoformat()
                except (ValueError, TypeError):
                    # If not a Unix timestamp, leave as is
                    pass
    
    return data

def filter_ignored_users(data: List[Dict[str, Any]], ignored_users: List[str]) -> List[Dict[str, Any]]:
    """Filter out ignored users from data"""
    if not ignored_users:
        return data
    
    filtered_data = []
    for item in data:
        # Check if user email is in ignored list
        user_email = item.get('email') or item.get('user_email')
        if user_email not in ignored_users:
            filtered_data.append(item)
    
    return filtered_data

def process_course_data(course_id: str, course_config: Dict[str, Any]):
    """Process data for a single course"""
    print(f"Processing course: {course_id}")
    
    # Create directories
    raw_dir = Path(f"data/raw/{course_id}")
    processed_dir = Path(f"data/processed/{course_id}")
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    # Get ignored users from environment variable
    ignored_users_str = os.getenv('IGNORED_USERS', '')
    ignored_users = [email.strip() for email in ignored_users_str.split(',') if email.strip()] if ignored_users_str else []
    
    # Download and process each data type
    data_types = ['assessments', 'grades', 'users']
    
    for data_type in data_types:
        print(f"  Downloading {data_type}...")
        
        try:
            # Download data
            raw_data = download_course_data(course_id, data_type)
            
            # Convert timestamps
            raw_data = convert_timestamps(raw_data)
            
            # Filter ignored users
            raw_data = filter_ignored_users(raw_data, ignored_users)
            
            # Save raw JSON
            json_path = raw_dir / f"{data_type}.json"
            save_json_data(raw_data, str(json_path))
            
            # Convert to CSV
            if raw_data:
                df = pd.json_normalize(raw_data)
                csv_path = processed_dir / f"{data_type}.csv"
                df.to_csv(csv_path, index=False, encoding='utf-8')
                print(f"    Saved {len(raw_data)} {data_type} records")
            else:
                print(f"    No {data_type} data found")
                
        except Exception as e:
            print(f"    Error processing {data_type}: {str(e)}")
            continue

def run_full_pipeline(course_id: str):
    """Run the complete download and processing pipeline for a course"""
    try:
        # Load configuration
        config = load_course_config()
        courses = config.get('courses', {})
        
        if course_id not in courses:
            raise ValueError(f"Course {course_id} not found in configuration")
        
        course_config = courses[course_id]
        process_course_data(course_id, course_config)
        
        print(f"✅ Pipeline completed for {course_id}")
        
    except Exception as e:
        print(f"❌ Pipeline failed for {course_id}: {str(e)}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Download and process course data from LearnWorlds API')
    parser.add_argument('--course', '-c', required=True, help='Course ID to process')
    parser.add_argument('--reset-raw', action='store_true', help='Delete raw data before downloading')
    
    args = parser.parse_args()
    
    if args.reset_raw:
        raw_dir = Path(f"data/raw/{args.course}")
        if raw_dir.exists():
            import shutil
            shutil.rmtree(raw_dir)
            print(f"Deleted raw data for {args.course}")
    
    run_full_pipeline(args.course)

if __name__ == "__main__":
    main() 