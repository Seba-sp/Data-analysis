# Multi-Assessment Processor

> **📖 For detailed setup and configuration instructions, see [SETUP_GUIDE.md](SETUP_GUIDE.md) and [README_MULTI_ASSESSMENT.md](README_MULTI_ASSESSMENT.md)**

## Overview

The Multi-Assessment Processor is an enhanced system that downloads multiple assessments from LearnWorlds, joins responses by user across different assessments, and automatically uploads combined results to Google Drive with Slack notifications. It's designed for automated execution in Google Cloud Run.

## Quick Start

```bash
# Test configuration
python test_config.py

# Test the processor (dry run)
python multi_assessment_processor.py --config assessments_config.yml --dry-run

# Run the processor locally
python multi_assessment_processor.py --config assessments_config.yml

# Deploy to Cloud Run
chmod +x deploy.sh
./deploy.sh
```

## Features

- **Multiple Assessment Support**: Download and process multiple assessments from a single configuration
- **User Response Joining**: Combine responses from different assessments for the same user
- **Flexible Grouping**: Group related assessments (e.g., "M1 TD Part 1" and "M1 TD Part 2")
- **Automated Workflow**: Download → Process → Join → Upload → Notify
- **Cloud Run Ready**: Designed for automated execution in Google Cloud Run
- **Scheduled Execution**: Runs twice daily (9 AM and 6 PM) via Cloud Scheduler

## Workflow

### 1. Download Assessment Responses
```bash
# Download all assessments for a course
python descarga_responses.py --course <course> --all

# Download specific assessments
python descarga_responses.py --course <course> --assessment assessment1 --assessment assessment2

# Download only (no processing)
python descarga_responses.py --course <course> --all --download-only

# Process only (no download)
python descarga_responses.py --course <course> --all --process-only
```

### 2. Prepare Question Files
1. **Download question file** from LearnWorlds platform
2. **Upload to questions folder** (locally or on GCS):
   ```
   data/responses/questions/<course>/assessment1.csv
   ```
3. **Automatic conversion** happens during analysis (or manually):
   ```bash
   python convert_questions_file.py --input data/responses/questions/<course>/assessment1.csv --output data/responses/questions/<course>/assessment1_questions.csv
   ```

### 3. Generate Reports
```bash
# Analyze all assessments in a course
python analisis_responses.py --course <course> --all

# Analyze specific assessments
python analisis_responses.py --course <course> --assessment assessment1 --assessment assessment2
```

## Manual Execution

### Download Responses
```bash
# Download all assessments for a course
python descarga_responses.py --course nivel-1-m30m --all

# Download specific assessment
python descarga_responses.py --course nivel-1-m30m --assessment test-diagnostico
```

### Convert Question Files
```bash
# Manual conversion (if needed)
python convert_questions_file.py \
  --input data/responses/questions/nivel-1-m30m/test-diagnostico.csv \
  --output data/responses/questions/nivel-1-m30m/test-diagnostico_questions.csv
```

### Generate Analysis
```bash
# Analyze all assessments
python analisis_responses.py --course nivel-1-m30m --all

# Analyze specific assessment
python analisis_responses.py --course nivel-1-m30m --assessment test-diagnostico
```

## Configuration

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

# Report configuration
REPORT_TOP_PERCENT=20  # Percentage of most-missed questions to show in PDF
```

## Question File Format

### Input Format (from LearnWorlds)
```csv
Group,Type,Question,CorrectAns,Answer1,Answer2,Answer3,Answer4
1,Multiple Choice,What is 2+2?,A,4,3,5,6
2,Multiple Choice,What is 3x3?,C,6,8,9,12
```

### Output Format (for analysis)
```csv
question,correct_answer
What is 2+2?,4
What is 3x3?,9
```

## Reports Generated

### PDF Report (`assessment1_top_20pct.pdf`)
- **Title**: Assessment name + "Top X% Preguntas Más Falladas"
- **Columns**: Pregunta, Cantidad, Respuesta Correcta, A, B, C, D, etc.
- **Sorting**: Questions ordered by correct answer percentage (lowest first)
- **Highlighting**: Red highlighting for questions where correct answer was NOT most selected
- **Content**: Shows top X% most-missed questions (configurable via `REPORT_TOP_PERCENT`)

### Excel Report (`assessment1_report.xlsx`)
- **Same columns** as PDF report
- **All questions** included (not just top X%)
- **Same highlighting** as PDF
- **Multiple sheets** with different views

## Report Interpretation

### Understanding the Reports

**1. Question Performance**
- **Correct Answer Percentage**: Shows how many students got each question right
- **Most Selected Answer**: The answer chosen by the most students
- **Red Highlighting**: Indicates questions where the correct answer was NOT the most selected

**2. Question Ordering**
- Questions are sorted by correct answer percentage (lowest first)
- This helps identify the most problematic questions

**3. Alternative Analysis**
- Each column (A, B, C, D, etc.) shows the percentage of students who chose that option
- Helps understand common misconceptions

### Example Report Row
```
Pregunta: What is 2+2?
Cantidad: 100 students
Respuesta Correcta: 4
A (4): 60%    ← Correct answer, most selected
B (3): 25%
C (5): 10%
D (6): 5%
```

## GCP Deployment

### Cloud Run Job Deployment
```bash
# Build and push image
docker build -t gcr.io/PROJECT_ID/assessment-responses:latest .
docker push gcr.io/PROJECT_ID/assessment-responses:latest

# Deploy Cloud Run Job
gcloud run jobs update assessment-responses \
  --image gcr.io/PROJECT_ID/assessment-responses:latest \
  --region us-central1 \
  --memory 2Gi \
  --cpu 1 \
  --timeout 1800
```

### Scheduled Execution
```bash
# Create weekly scheduler
gcloud scheduler jobs create http assessment-analysis-weekly \
  --schedule="0 9 * * 1" \
  --uri="https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/PROJECT_ID/jobs/assessment-responses:run" \
  --http-method=POST \
  --oauth-service-account-email=SERVICE_ACCOUNT@PROJECT_ID.iam.gserviceaccount.com
```

## Troubleshooting

### Common Issues

**1. Missing Question Files**
```bash
# Check if question file exists
ls data/responses/questions/<course>/

# Upload question file to GCS (if using GCP)
gsutil cp question_file.csv gs://BUCKET/data/responses/questions/<course>/
```

**2. Conversion Errors**
```bash
# Check question file format
head -5 data/responses/questions/<course>/assessment1.csv

# Manual conversion with debug
python convert_questions_file.py --input file.csv --output file_questions.csv --debug
```

**3. Analysis Failures**
```bash
# Check processed data exists
ls data/responses/processed/<course>/

# Verify question file format
python convert_questions_file.py --validate-only --input file.csv
```

### Debug Mode
```bash
# Enable debug logging
export DEBUG=true
python analisis_responses.py --course <course> --all
```

## Cost Optimization

- **Memory**: 2Gi is usually sufficient
- **CPU**: 1 vCPU for most workloads
- **Timeout**: 1800s (30 minutes) default
- **Scheduling**: Weekly execution ~$0.36/month

## Integration

### Storage Backends
- **Local**: Files stored on local filesystem
- **GCS**: Files stored in Google Cloud Storage bucket
- **Hybrid**: Local processing with GCS storage

### Question File Sources
- **LearnWorlds Platform**: Download question banks from admin panel
- **Manual Upload**: Upload CSV files to questions folder
- **GCS Sync**: Automatically sync from GCS bucket

## Data Structure

```
data/responses/
├── raw/
│   └── <course>/
│       ├── assessment1.json
│       └── assessment2.json
├── processed/
│   └── <course>/
│       ├── assessment1.csv
│       └── assessment2.csv
├── questions/
│   └── <course>/
│       ├── assessment1.csv              # Raw question file (from LearnWorlds)
│       ├── assessment1_questions.csv    # Processed question file (for analysis)
│       ├── assessment2.csv
│       └── assessment2_questions.csv
└── reports/
    └── <course>/
        ├── assessment1_report.xlsx
        ├── assessment1_top_20pct.pdf
        ├── assessment2_report.xlsx
        └── assessment2_top_20pct.pdf
```

## Best Practices

### Question File Management
1. **Consistent naming**: Use assessment names that match LearnWorlds
2. **Regular updates**: Update question files when assessments change
3. **Version control**: Keep track of question file versions

### Analysis Timing
1. **After assessment completion**: Wait for all students to complete
2. **Regular intervals**: Run analysis weekly or after major assessments
3. **Before curriculum updates**: Use insights to improve content

### Report Distribution
1. **PDF for quick review**: Share top-missed questions with teachers
2. **Excel for detailed analysis**: Use for curriculum development
3. **Automated delivery**: Integrate with Google Drive/Slack for automatic sharing 