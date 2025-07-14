# Course Data Analysis Pipeline

This project provides a complete pipeline for downloading, processing, and analyzing course data from LearnWorlds API.

## New Directory Structure

```
proyecto/
├── data/
│   ├── raw/{course_id}/...          # Raw JSON data from API
│   ├── processed/{course_id}/...     # Processed CSV files
│   ├── planification/               # Assessment schedule files
│   │   └── {course_id}.csv         # Assessment names and due dates
│   └── reports/{course_id}/...       # Generated reports (PDF, Excel)
├── metrics/{kpi}/{course_id}.csv     # KPI metrics per course
└── reports/{course_id}/...           # Generated reports (PDF, Excel)
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your API credentials:
```
CLIENT_ID=your_client_id
SCHOOL_DOMAIN=your_school_domain
ACCESS_TOKEN=your_access_token
```

## Usage

### Single Course Processing

#### Download and Process Data
```bash
python descarga_procesa_datos.py --course test-de-diagnostico-m30m
```

#### Download and Process Data from Scratch (Delete Raw Data)
```bash
python descarga_procesa_datos.py --course test-de-diagnostico-m30m --reset-raw
```
This will delete all raw data for the course and re-download everything from the API.

#### Analyze Data and Generate Reports
```bash
python analisis.py --course test-de-diagnostico-m30m
```

#### Analyze Data with Up-to-Date Student Filtering
```bash
python analisis.py --course test-de-diagnostico-m30m --up-to-date
```
This will filter the analysis to only include students who have completed all assessments due until yesterday (based on the planification schedule).

#### Analyze Data and Upload to Google Drive with Slack Notification
```bash
python analisis.py --course test-de-diagnostico-m30m --upload
```

#### Analyze Data with Up-to-Date Filtering and Upload
```bash
python analisis.py --course test-de-diagnostico-m30m --up-to-date --upload
```

### Batch Processing

#### Process All Courses from Configuration
```bash
python batch_process.py
```

#### Process All Courses with Up-to-Date Filtering
```bash
python batch_process.py --up-to-date
```

#### Process Specific Courses with Up-to-Date Filtering
```bash
python batch_process.py --courses test-de-diagnostico-m30m test-de-diagnostico-m0m --up-to-date
```

#### To upload only today's files for all courses (replacing files with the same name) and send Slack notifications, use:
```bash
python batch_process.py --upload-only
```

#### Download Only (Skip Analysis)
```bash
python batch_process.py --download-only
```

#### Analysis Only (Skip Download)
```bash
python batch_process.py --analysis-only
```

### Bash Loop Example

```bash
# Process courses from cursos.txt
while IFS= read -r course_id; do
    echo "Processing course: $course_id"
    python descarga_procesa_datos.py --course "$course_id"
    python analisis.py --course "$course_id"
done < cursos.txt
```

## Planification Feature

The system now supports filtering analysis to only include students who are up to date with their assessments based on a planification schedule.

### Planification Files

Create CSV files in `data/planification/` with the following structure:
- **Filename**: `{course_id}.csv` (e.g., `nivel-1-m30m.csv`)
- **Format**: CSV with semicolon separator
- **Columns**:
  - `assessment_name`: Name of the assessment (must match exactly with assessment names in the course)
  - `date`: Due date in format `DD-MM-YYYY`

Example planification file (`data/planification/nivel-1-m30m.csv`):
```csv
assessment_name;date
Test [M30M-CNE1];08-07-2025
Test [M30M-CNE2];08-07-2025
Test [M30M-CNE3];08-07-2025
Guía acumulativa 1;08-07-2025
```

### How Up-to-Date Filtering Works

1. **Date Logic**: Since data is downloaded in the morning, the system considers assessments due until **yesterday** as "up to date"
2. **Student Filtering**: Only students who have completed ALL assessments due until yesterday are included in the analysis
3. **Report Generation**: Reports are generated with the suffix `_up_to_date` to distinguish them from regular reports
4. **Metrics**: Both regular and up-to-date metrics are saved separately

### Use Cases

- **Regular Analysis**: Analyze all students regardless of their progress
- **Up-to-Date Analysis**: Focus on students who are following the schedule, useful for:
  - Identifying students who need intervention
  - Analyzing performance of engaged students
  - Planning interventions for students falling behind

## Configuration

### cursos.yml
YAML configuration file for course-specific settings:

```yaml
courses:
  test-de-diagnostico-m30m:
    name: "Test de Diagnóstico M30M"
    kpis:
      - attendance_rate
      - average_grade
      - completion_rate
      - response_rate
```

### Environment Variables
Set ignored users via the `IGNORED_USERS` environment variable (comma-separated list):
```bash
export IGNORED_USERS="user1@email.com,user2@email.com,user3@email.com"
```

### Google Drive and Slack Integration
For automatic upload to Google Drive and Slack notifications, set these environment variables:

```bash
# Google Drive
export GOOGLE_DRIVE_FOLDER_ID="your-google-drive-folder-id"
export GOOGLE_SERVICE_ACCOUNT_KEY="your-service-account-key-json"

# Slack
export SLACK_BOT_TOKEN="xoxb-your-slack-bot-token"
export SLACK_CHANNEL="#your-channel-name"
```

**How uploads work:**
- Files are uploaded to a subfolder in Google Drive named after each course (`{course_id}`) inside your main Drive folder.
- If a file with the same name already exists in the course folder (e.g., `users.csv`, `reporte_{course_id}_YYYY-MM-DD.pdf`), it is replaced (not duplicated).
- Only files created or modified today are uploaded.
- After upload, a Slack notification is sent (for reports only) with links to the uploaded files.

**Note:** The service account key should be the full JSON content or base64-encoded JSON.

### cursos.txt
Simple text file with one course ID per line:
```
test-de-diagnostico-m30m
test-de-diagnostico-m0m
```

## Output Files

- **Raw Data**: `data/raw/{course_id}/assessments.json`, `users.json`, `grades.json`
- **Processed Data**: `data/processed/{course_id}/assessments.csv`, `users.csv`, `grades.csv`
- **Metrics**: `data/metrics/kpi/{course_id}.csv` (regular) and `data/metrics/kpi/{course_id}_up_to_date.csv` (filtered)
- **Reports**: `data/reports/{course_id}/reporte.pdf`, `reporte_listas.xlsx` (regular) and `data/reports/{course_id}/reporte_up_to_date.pdf`, `reporte_up_to_date.xlsx` (filtered)

## 🚀 Google Cloud Platform Integration

For automated daily execution, see the complete GCP integration guide:

**[📖 README_GCP.md](README_GCP.md)**

This includes:
- Cloud Function deployment
- Cloud Scheduler setup (8am Santiago time)
- Cloud Storage integration (single files, not dated)
- Google Drive storage (reports + CSV files)
- Slack notifications
- Environment variable configuration
- Complete setup instructions

### Cloud Function with Up-to-Date Filtering

The Cloud Function now supports up-to-date filtering via HTTP request:

```bash
# Regular execution (all students)
curl -X POST https://your-function-url

# Up-to-date filtering
curl -X POST https://your-function-url \
  -H "Content-Type: application/json" \
  -d '{"up_to_date": true}'
```

## Features

- ✅ No hard-coded course IDs
- ✅ Command-line argument support with argparse
- ✅ New organized directory structure
- ✅ Batch processing capabilities
- ✅ YAML configuration support
- ✅ Automatic directory creation
- ✅ Timestamp conversion for all date fields
- ✅ Ignored users filtering
- ✅ Comprehensive error handling
- ✅ **Up-to-Date Student Filtering**
  - Filter analysis to students following planification schedule
  - Separate reports for regular and filtered analysis
  - Configurable assessment due dates via CSV files
- ✅ **Google Drive and Slack Integration**
  - Automatic upload of reports and CSV files to Google Drive
  - Slack notifications with file links
  - Optional functionality (use `--upload` flag)
- ✅ **Google Cloud Platform Integration** (see [README_GCP.md](README_GCP.md))
  - Automated daily execution at 8am Santiago time
  - Cloud Storage for data storage
  - Google Drive for report storage
  - Slack notifications with report links
  - Support for up-to-date filtering via HTTP requests
