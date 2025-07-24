# This script only downloads and processes responses into CSVs.
# Analysis and reporting (including correct answer statistics) is handled in analisis_responses.py.
# To include correct answers in reports, place a CSV named <assessment>_questions.csv in the same directory as the responses CSV, with columns: question, correct_answer.

import os
import json
import pandas as pd
from dotenv import load_dotenv
import requests
import argparse
from pathlib import Path
import time
from storage import StorageClient

def parse_arguments():
    parser = argparse.ArgumentParser(description='Download and/or process assessment responses for a course')
    parser.add_argument('--course', '-c', required=True, help='Course ID to process')
    parser.add_argument('--assessment', '-a', action='append', help='Assessment name to download/process (can be used multiple times)')
    parser.add_argument('--all', action='store_true', help='Download/process all assessments for the course')
    parser.add_argument('--download-only', action='store_true', help='Only download and save raw JSON, do not process to CSV')
    parser.add_argument('--process-only', action='store_true', help='Only process existing JSON to CSV, do not download')
    return parser.parse_args()

# Load environment variables
load_dotenv()

client_id = os.getenv("CLIENT_ID")
school_domain = os.getenv("SCHOOL_DOMAIN")
access_token = os.getenv("ACCESS_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {access_token}",
    "Lw-Client": client_id,
    "Accept": "application/json"
}

def setup_output_dirs(course):
    base = Path("data/responses")
    raw_dir = base / "raw" / course
    processed_dir = base / "processed" / course
    questions_dir = base / "questions" / course
    reports_dir = base / "reports" / course
    for directory in [raw_dir, processed_dir, questions_dir, reports_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    return raw_dir, processed_dir, questions_dir, reports_dir

def load_assessments(course):
    assessments_path = Path(f"data/raw/{course}/assessments.json")
    if not assessments_path.exists():
        raise FileNotFoundError(f"Assessments file not found: {assessments_path}")
    with open(assessments_path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_latest_timestamp_from_json(json_file_path):
    if not json_file_path.exists():
        return None
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not data:
            return None
        latest_record = data[0]
        return latest_record.get('created')
    except (json.JSONDecodeError, IndexError, KeyError):
        return None

def get_assessment_responses(assessment_id, latest_timestamp=None):
    rows = []
    page = 1
    reached_existing = False
    while not reached_existing:
        url = f"https://{school_domain}/admin/api/v2/assessments/{assessment_id}/responses?page={page}"
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            print(f"Failed to fetch responses for assessment {assessment_id}: {response.status_code}")
            break
        data = response.json().get('data', [])
        if not data:
            break
        for record in data:
            record_timestamp = record.get('created')
            if latest_timestamp and record_timestamp and record_timestamp <= latest_timestamp:
                reached_existing = True
                break
            rows.append(record)
        total_pages = response.json().get("meta", {}).get("totalPages", 1)
        if page >= total_pages:
            break
        page += 1
        time.sleep(1)
    return rows

def save_responses(raw_dir, processed_dir, name, responses):
    storage = StorageClient()
    json_path = raw_dir / f"{name.replace('/', '_')}.json"
    storage.write_json(str(json_path), responses)
    df = pd.DataFrame(responses)
    csv_path = processed_dir / f"{name.replace('/', '_')}.csv"
    storage.write_csv(str(csv_path), df, sep=';', index=False)

def add_and_update_answer_columns_inplace(csv_path, responses):
    storage = StorageClient()
    # Load the existing CSV
    df = storage.read_csv(str(csv_path), sep=';')
    # Convert timestamps
    for col in ["created", "modified", "submittedTimestamp"]:
        if col in df.columns:
            try:
                df[col] = pd.to_datetime(df[col], unit="s")
            except Exception:
                pass
    # Prepare answer columns
    all_questions = set()
    answers_per_row = []
    for r in responses:
        answers = r.get("answers", [])
        ans_dict = {}
        for ans in answers:
            desc = ans.get("description")
            answer_val = ans.get("answer")
            if desc:
                ans_dict[desc] = answer_val
                all_questions.add(desc)
        answers_per_row.append(ans_dict)
    # Add columns for each question, ordered by number
    def question_sort_key(q):
        import re
        m = re.match(r"pregunta (\d+)", str(q).lower())
        return int(m.group(1)) if m else float('inf')
    ordered_questions = sorted([q for q in all_questions if q], key=question_sort_key)
    for q in ordered_questions:
        df[q] = [row.get(q) if isinstance(row, dict) else None for row in answers_per_row]
    # Do NOT reorder columns; keep original order and just append new question columns
    storage.write_csv(str(csv_path), df, sep=';', index=False)

def filter_responses(responses):
    # 1. Remove responses where the answer to the last question is empty
    filtered = []
    for r in responses:
        answers = r.get('answers', [])
        if answers and isinstance(answers, list):
            last_answer = answers[-1].get('answer', None)
            if last_answer is not None and str(last_answer).strip() != '':
                filtered.append(r)
    # 2. For each user, keep only the newest response
    user_latest = {}
    for r in filtered:
        user_id = r.get('userId') or r.get('user_id')
        created = r.get('created', 0)
        if user_id is not None:
            if user_id not in user_latest or created > user_latest[user_id].get('created', 0):
                user_latest[user_id] = r
    return list(user_latest.values())

def main():
    storage = StorageClient()
    args = parse_arguments()
    course = args.course
    raw_dir, processed_dir, questions_dir, reports_dir = setup_output_dirs(course)
    assessments = load_assessments(course)

    if args.all:
        selected = list(assessments.items())
    elif args.assessment:
        selected = [(name, assessments[name]) for name in args.assessment if name in assessments]
        missing = [name for name in args.assessment if name not in assessments]
        if missing:
            print(f"Warning: The following assessments were not found: {missing}")
    else:
        print("Error: You must specify either --all or at least one --assessment.")
        return

    for name, aid in selected:
        json_path = raw_dir / f"{name.replace('/', '_')}.json"
        # Download step
        if not args.process_only:
            print(f"Downloading responses for: {name}")
            latest_timestamp = get_latest_timestamp_from_json(json_path)
            new_responses = get_assessment_responses(aid, latest_timestamp)
            # If incremental, combine with existing
            if latest_timestamp and json_path.exists():
                existing = storage.read_json(str(json_path))
                combined = new_responses + existing
                # Remove duplicates by response id if available
                seen = set()
                unique = []
                for r in combined:
                    rid = r.get('id')
                    if rid and rid not in seen:
                        seen.add(rid)
                        unique.append(r)
                    elif not rid:
                        unique.append(r)
                # Sort by created timestamp, newest first
                unique.sort(key=lambda x: x.get('created', 0), reverse=True)
                # Save raw JSON as downloaded (no filtering)
                storage.write_json(str(json_path), unique)
            else:
                # Save raw JSON as downloaded (no filtering)
                storage.write_json(str(json_path), new_responses)
            print(f"Saved raw JSON for {name} to {json_path}")
        # Processing step
        if not args.download_only:
            print(f"Processing responses for: {name}")
            if not json_path.exists():
                print(f"Raw JSON file not found: {json_path}. Skipping.")
                continue
            responses = storage.read_json(str(json_path))
            filtered = filter_responses(responses)
            save_responses(raw_dir, processed_dir, name, filtered)
            add_and_update_answer_columns_inplace(processed_dir / f"{name.replace('/', '_')}.csv", filtered)
        time.sleep(1)

    print(f"JSON files saved in: {raw_dir}")
    print(f"CSV files saved in: {processed_dir}")
    print(f"Question files should be placed in: {questions_dir}")
    print(f"Reports will be generated in: {reports_dir}")

if __name__ == "__main__":
    main() 