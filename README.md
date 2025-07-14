# Course Data Analysis Pipeline

This project provides a complete pipeline for downloading, processing, and analyzing course data from LearnWorlds API.

## New Directory Structure

```
proyecto/
├── data/
│   ├── raw/{course_id}/...          # Raw JSON data from API
│   └── processed/{course_id}/...     # Processed CSV files
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

### Batch Processing

#### Process All Courses from Configuration
```bash
python batch_process.py
```

#### Process Specific Courses
```bash
python batch_process.py --courses test-de-diagnostico-m30m test-de-diagnostico-m0m
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

### cursos.txt
Simple text file with one course ID per line:
```
test-de-diagnostico-m30m
test-de-diagnostico-m0m
```

## Output Files

- **Raw Data**: `data/raw/{course_id}/assessments.json`, `users.json`, `grades.json`
- **Processed Data**: `data/processed/{course_id}/assessments.csv`, `users.csv`, `grades.csv`
- **Metrics**: `data/metrics/kpi/{course_id}.csv`
- **Reports**: `data/reports/{course_id}/reporte.pdf`, `reporte_listas.xlsx`

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
- ✅ **Google Cloud Platform Integration** (see [README_GCP.md](README_GCP.md))
  - Automated daily execution at 8am Santiago time
  - Cloud Storage for data storage
  - Google Drive for report storage
  - Slack notifications with report links
