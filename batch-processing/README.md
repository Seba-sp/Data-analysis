# Batch Processing

## Overview

The Batch Processing feature downloads, processes, and analyzes course data in batches for multiple courses defined in `cursos.yml`. It generates comprehensive reports and integrates with Google Drive and Slack for automated delivery. The system includes up-to-date analysis using planification files and automatic course configuration updates.

## Quick Start

```bash
# Process all courses
python batch_process.py

# Process specific category
python batch_process.py --category Matematicas

# Process specific course
python batch_process.py --category Matematicas --course nivel-1-m30m
```

## Features

- **Download-only mode**: Only download and process raw data
- **Analysis-only mode**: Only generate reports from existing data
- **Upload-only mode**: Only upload reports to Google Drive/Slack
- **Category/Course filtering**: Process specific categories or courses
- **Incremental processing**: Only process new/updated data
- **Automated scheduling**: Works with Cloud Scheduler for daily execution
- **Up-to-date analysis**: Uses planification files for current assessment status
- **Automatic course discovery**: Updates `cursos.yml` from LearnWorlds API
- **Multi-storage support**: Local filesystem and Google Cloud Storage

## Usage

### Basic Usage
```bash
# Process all courses
python batch_process.py

# Process specific category
python batch_process.py --category Matematicas

# Process specific course
python batch_process.py --category Matematicas --course nivel-1-m30m
```

### Advanced Options
```bash
# Download only (no analysis or upload)
python batch_process.py --download-only

# Analysis only (no download or upload)
python batch_process.py --analysis-only

# Skip upload to Google Drive/Slack
python batch_process.py --no-upload

# Combine options
python batch_process.py --category Matematicas --download-only --no-upload
```

## Manual Execution

### Step-by-step Process
1. **Update course configurations**:
   ```bash
   python get_all_courses.py
   ```

2. **Download and process data**:
   ```bash
   python descarga_procesa_datos.py --category <category> --course <course>
   ```

3. **Upload planification files** (if using GCP):
   ```bash
   python upload_folder_to_gcs.py --folder data/planification --gcs-folder data/planification
   ```

4 **Generate reports**:
   ```bash
   python analisis.py --category <category> --course <course>
   ```

## Data Structure

```
data/
├── raw/
│   └── <category>/<course>/
│       ├── users.json
│       ├── grades.json
│       └── assessments.json
├── processed/
│   └── <category>/<course>/
│       ├── users.csv
│       ├── grades.csv
│       └── assessments.csv
├── reports/
│   └── <category>/<course>/
│       ├── course_report.pdf
│       └── course_report.xlsx
├── metrics/
│   └── kpi/
│       └── <category>/<course>/
└── planification/
    └── <category>/
        ├── lecciones.csv
        ├── nivel-1-m30m.csv
        ├── nivel-2-m30m.csv
        └── nivel-3-m30m.csv
```

## Core Components

### Storage Management (`storage.py`)
The `StorageClient` class provides unified storage access for both local filesystem and Google Cloud Storage:

```python
from storage import StorageClient

storage = StorageClient()

# Read files
df = storage.read_csv('data/processed/course.csv')
data = storage.read_json('data/raw/users.json')

# Write files
storage.write_csv('data/processed/course.csv', df)
storage.write_json('data/raw/users.json', data)
```

**Features:**
- Automatic backend detection (`STORAGE_BACKEND` environment variable)
- Unified API for local and GCS storage
- Robust file operations with proper encoding
- Error handling for missing files

### Course Configuration (`get_all_courses.py`)
Automatically updates `cursos.yml` by fetching course data from LearnWorlds API:

```bash
python get_all_courses.py
```

**Functionality:**
- Fetches all courses from LearnWorlds API
- Generates standardized KPI configuration
- Updates both `cursos.yml` and `courses_raw.json`
- Uses StorageClient for consistent file handling

### Up-to-Date Analysis
The analysis system includes planification-based up-to-date analysis:

**Planification Files Structure:**
```csv
date;assessment_id;assessment_name;status
2024-01-15;quiz_001;Introduction Quiz;active
2024-01-20;quiz_002;Basic Concepts;active
```

**Analysis Features:**
- Loads planification data for each course
- Calculates assessments due until today
- Provides up-to-date completion statistics
- Integrates with existing KPI calculations

## Configuration

### Course Configuration (`cursos.yml`)
```yaml
courses:
  Matemáticas:
    lecciones-m0m:
      name: Lecciones M30M
      kpis:
      - attendance_rate
      - average_grade
      - completion_rate
      - response_rate
```

### Environment Variables
```bash
# Storage backend
STORAGE_BACKEND=gcp  # or 'local'

# LearnWorlds API
CLIENT_ID=your_client_id
SCHOOL_DOMAIN=your_school_domain
ACCESS_TOKEN=your_access_token

# Google Cloud Platform
GCP_PROJECT_ID=your_project_id
GCP_BUCKET_NAME=your_bucket_name
REGION=us-central1

# Google Drive & Slack
GOOGLE_SERVICE_ACCOUNT_KEY=your_service_account_key_json_or_base64
GOOGLE_SHARED_DRIVE_ID=your_drive_id
GOOGLE_DRIVE_FOLDER_ID=your_folder_id
SLACK_BOT_TOKEN=your_slack_token
SLACK_CHANNEL=#reports

# Processing options
GRADE_ZERO_THRESHOLD=0
TIME_MAX_THRESHOLD_MINUTES=60
IGNORED_USERS=user1@gmail.com,user2@gmail.com
```

## Reports Generated

### Course Analysis Reports
- **PDF Report**: Comprehensive course overview with KPIs
- **Excel Report**: Detailed data with multiple sheets
- **KPI Metrics**: Performance indicators and trends

### Report Content
- Student attendance and participation
- Grade distributions and averages
- Assessment completion rates
- Response rates and engagement
- **Up-to-date analysis**: Current assessment status based on planification files
- **Due assessments**: Assessments that should be completed by today
- **Progress tracking**: Real-time completion vs. planned schedule

## GCP Deployment

### Cloud Run Job Deployment
```bash
# Build and push image
docker build -t gcr.io/PROJECT_ID/batch-processing:latest .
docker push gcr.io/PROJECT_ID/batch-processing:latest

# Deploy Cloud Run Job
gcloud run jobs update batch-processing \
  --image gcr.io/PROJECT_ID/batch-processing:latest \
  --region us-central1 \
  --cpu 1 \
  --timeout 3600 \
  --set-env-vars STORAGE_BACKEND=gcp,GCP_BUCKET_NAME=your-bucket \
  --set-secrets ACCESS_TOKEN=projects/PROJECT_ID/secrets/learnworlds-token/versions/latest
```

### Service Account Permissions

The Cloud Run job service account needs the following IAM roles:

#### 1. Cloud Storage Permissions
```bash
# Grant Storage Object Admin for GCS bucket access
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

# Or for specific bucket only
gsutil iam ch serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com:objectAdmin gs://YOUR_BUCKET_NAME
```

#### 2. Secret Manager Permissions
```bash
# Grant Secret Accessor for accessing secrets
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

#### 3. Cloud Run Permissions (for job execution)
```bash
# Grant Cloud Run Invoker for job execution
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/run.invoker"
```

#### 4. Logging Permissions
```bash
# Grant Logs Writer for Cloud Logging
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/logging.logWriter"
```

#### 5. Google Drive API Permissions
```bash

# Enable Google Drive API
gcloud services enable drive.googleapis.com
```

#### 6. Monitoring Permissions (optional)
```bash
# Grant Monitoring Metric Writer for metrics
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/monitoring.metricWriter"
```

#### 7. Custom Service Account (Recommended)
For better security, create a custom service account:

```bash
# Create custom service account
gcloud iam service-accounts create batch-processing-sa \
  --display-name="Batch Processing Service Account"

# Grant necessary roles
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:batch-processing-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:batch-processing-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:batch-processing-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/logging.logWriter"

# Deploy with custom service account
gcloud run jobs update batch-processing \
  --image gcr.io/PROJECT_ID/batch-processing:latest \
  --region us-central1 \
  --service-account=batch-processing-sa@PROJECT_ID.iam.gserviceaccount.com \
  --cpu 1 \
  --timeout 3600 \
  --set-env-vars STORAGE_BACKEND=gcp,GCP_BUCKET_NAME=your-bucket \
  --set-secrets ACCESS_TOKEN=projects/PROJECT_ID/secrets/learnworlds-token/versions/latest
```

### Scheduled Execution
```bash
# Create daily scheduler
gcloud scheduler jobs create http batch-processing-daily \
  --schedule="0 8 * * *" \
  --uri="https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/PROJECT_ID/jobs/batch-processing:run" \
  --http-method=POST \
  --oauth-service-account-email=SERVICE_ACCOUNT@PROJECT_ID.iam.gserviceaccount.com
```

#### Cloud Scheduler Service Account Permissions
The Cloud Scheduler service account needs permission to invoke Cloud Run jobs:

```bash
# Grant Cloud Run Invoker to Cloud Scheduler service account
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:service-PROJECT_NUMBER@gcp-sa-cloudscheduler.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

## Troubleshooting

### Common Issues

**1. Storage Configuration**
```bash
# Check storage backend
echo $STORAGE_BACKEND

# Verify GCS bucket access
gsutil ls gs://YOUR_BUCKET_NAME/
```

**2. Authentication Issues**
```bash
# Verify service account
gcloud auth list

# Check environment variables
python ../scripts/setup_environment.py
```

**3. Course Configuration Issues**
```bash
# Update course configurations
python get_all_courses.py

# Check generated files
cat cursos.yml
```

**4. Planification Data Issues**
```bash
# Verify planification files exist
ls data/planification/Matemáticas/

# Check file format
head -5 data/planification/Matemáticas/nivel-1-m30m.csv
```

**5. Job Execution Failures**
```bash
# View job logs
gcloud run jobs logs read batch-processing --region us-central1

# Check job status
gcloud run jobs describe batch-processing --region us-central1
```

### Debug Mode
```bash
# Enable debug logging
export DEBUG=true
python batch_process.py
```

## Cost Optimization

- **Memory**: 512Mi is usually sufficient
- **CPU**: 1 vCPU for most workloads
- **Timeout**: 3600s (1 hour) default
- **Scheduling**: Daily execution ~$1.62/month

## Integration

### Google Drive
- Reports automatically uploaded to configured folder
- Supports shared drives and team folders
- Maintains folder structure by category/course

### Slack
- Automatic notifications when reports are generated
- Includes summary statistics and direct links
- Configurable channel and message format

### Storage Backends
- **Local**: Files stored on local filesystem
- **GCS**: Files stored in Google Cloud Storage bucket
- **Hybrid**: Local processing with GCS storage

### LearnWorlds Integration
- Automatic course discovery and configuration
- Real-time data synchronization
- Standardized KPI configuration across all courses 