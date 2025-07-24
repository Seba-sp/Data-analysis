# Data Analysis Project

## 1. Project Overview

This project provides a complete workflow for downloading, processing, and analyzing course and assessment data, generating actionable reports, and integrating with Google Drive and Slack for automated delivery and notifications. It supports both local and Google Cloud Storage (GCP) backends.

---

## 2. Directory Structure

```
data/
  raw/
    <category>/<course>/
      users.json
      grades.json
      assessments.json
  processed/
    <category>/<course>/
      users.csv
      grades.csv
      assessments.csv
  metrics/
    kpi/
      <category>/<course>/
  reports/
    <category>/<course>/
      <various reports>.pdf
      <various reports>.xlsx
  planification/
    <category>/<course>.csv   # Planification files for up-to-date analysis
responses/
  ...
```

---

## 3. Environment Setup

- Copy `env.template` to `.env` and fill in your credentials and settings.
- Use `create_env_file.py` and `setup_environment.py` to help create and validate your environment.
- Install dependencies:
  ```sh
  pip install -r requirements.txt
  ```
- Key environment variables:
  - `CLIENT_ID`, `SCHOOL_DOMAIN`, `ACCESS_TOKEN` (API credentials)
  - `GCP_PROJECT_ID`, `GCP_BUCKET_NAME`, `GOOGLE_DRIVE_FOLDER_ID`, `GOOGLE_SERVICE_ACCOUNT_KEY` (Google Cloud/Drive)
  - `SLACK_BOT_TOKEN`, `SLACK_CHANNEL` (Slack integration)
  - `IGNORED_USERS` (comma-separated emails to ignore)
  - `STORAGE_BACKEND` (`local` or `gcp`)

---

## 4. Main Workflow

1. **Set up your environment**
2. **Download and process data**: Use `descarga_procesa_datos.py` for full course data (incremental by default).
3. **Analyze and generate reports**: Use `analisis.py` for full course analysis (with up-to-date filtering and batch modes).
4. **Batch process all courses**: Use `batch_process.py` for automation (supports download-only, analysis-only, upload-only, and combinations).
5. **Test integrations**: Use the test scripts for Slack, Google Drive, and Cloud Function.

---

## 5. Core Scripts

### `descarga_procesa_datos.py`
- **Purpose:** Download and process all raw data (users, grades, assessments) for a course.
- **Features:** Incremental download, organized output, CSV conversion, reset option, robust error handling.
- **Usage:**
  ```sh
  python descarga_procesa_datos.py --category <category> --course <course>
  # Add --reset-raw to force a full re-download
  ```

### `analisis.py`
- **Purpose:** Analyze course data (grades, users, assessments), generate metrics, completion times, and custom reports (PDF, Excel).
- **Features:** Up-to-date student filtering, Google Drive & Slack integration, batch mode, robust file handling, PDF/Excel output.
- **Usage:**
  ```sh
  python analisis.py --category <category> --course <course>
  # Add --no-upload to skip Google Drive/Slack
  ```

### `batch_process.py`
- **Purpose:** Batch processing for multiple courses as defined in `cursos.yml`.
- **Features:** Download-only, analysis-only, and upload-only modes. Integrates with Google Drive and Slack.
- **Usage:**
  ```sh
  python batch_process.py
  python batch_process.py --category <category>
  python batch_process.py --course <course>
  python batch_process.py --download-only
  python batch_process.py --analysis-only
  python batch_process.py --no-upload
  ```

### `storage.py`
- **Purpose:** Unified storage abstraction for all file operations.
- **Features:** Supports both local filesystem and Google Cloud Storage (GCP) backends, controlled by the `STORAGE_BACKEND` environment variable. Used throughout the pipeline for robust, backend-agnostic file operations.

---

## 6. Utilities and Supporting Scripts

- **get_all_courses.py**: Loads `courses_raw.json` and updates `cursos.yml` and `cursos.txt` with the latest course information. Run this script to refresh your course configuration files from the raw data.
- **upload_folder_to_gcs.py**: Uploads folders and files created locally to your GCP bucket, such as files inside `planification` and `base_courses.yml`. Supports uploading single files or entire folders, and ensures correct GCS path formatting.
- **encode_service_account.py**: Encodes your `service-account-key.json` file to a base64 string so you can safely copy it into your `.env` file for use with GCP authentication.
- **convert_questions_file.py**: Converts a raw question/correct answer file to the format needed for analysis.
- **setup_environment.py**, **create_env_file.py**: Help set up and validate your environment variables and service account keys.
- **test_slack_bot.py**: Test Slack bot integration and message sending.
- **test_upload_functionality.py**: Test Google Drive and Slack integration, including file upload and notification.
- **test_cloud_function.py**: Test script for running the Cloud Function locally or remotely (for GCP deployments).
- **prompts cursor.txt**: Contains project planning notes and feature requests (not a script).

---

## 7. Assessment Responses Workflow

### Directory Structure
```
data/
  responses/
    raw/
      <course>/
        assessment1.json
        ...
    processed/
      <course>/
        assessment1.csv
        ...
    questions/
      <course>/
        assessment1.csv                # Raw question/correct answer file (optional, see below)
        assessment1_questions.csv      # Processed question/correct answer file (used for analysis)
        ...
    reports/
      <course>/
        assessment1_report.xlsx
        assessment1_top_20pct.pdf
        ...
```

### 1. Download and Process Responses
**Script:** `descarga_responses.py`
- Downloads assessment responses from the API and saves them as raw JSON files.
- Processes the responses to CSV, filtering out incomplete attempts and keeping only the latest response per user.
- You can choose to only download, only process, or do both.

**Example usage:**
```sh
python descarga_responses.py --course <course> --all
python descarga_responses.py --course <course> --all --download-only
python descarga_responses.py --course <course> --all --process-only
python descarga_responses.py --course <course> --assessment assessment1 --assessment assessment2
```

### 2. Prepare Question/Correct Answer Files
**Script:** `convert_questions_file.py`
- Converts a raw question/correct answer file (downloaded from your platform) to the format needed for analysis.
- The input file should have columns like `Group`, `Type`, `Question`, `CorrectAns`, `Answer1`, `Answer2`, ...
- The output file will have columns: `question`, `correct_answer` (the text of the correct alternative).

**Example usage:**
```sh
python convert_questions_file.py --input data/responses/questions/<course>/assessment1.csv --output data/responses/questions/<course>/assessment1_questions.csv
```

### 3. Generate Reports
**Script:** `analisis_responses.py`
- Generates PDF and XLSX reports for one or more assessments in a course.
- Reports show, for each question: the percentage of students who selected each alternative, the correct answer, and highlight questions where the correct answer is not the most selected.
- Questions are ordered by the percentage of students who selected the correct answer (lowest first).
- The PDF report shows the top X% most-missed questions (set by the `REPORT_TOP_PERCENT` environment variable, default 20%).
- The XLSX report includes all questions.

**Example usage:**
```sh
python analisis_responses.py --course <course> --all
python analisis_responses.py --course <course> --assessment assessment1 --assessment assessment2
```

#### How to Interpret the Reports
- **PDF:**
  - Title: Assessment name and "Top X% Preguntas Más Falladas"
  - Table columns: Pregunta, Cantidad, Respuesta Correcta, and one column for each alternative (e.g., A, B, No lo sé)
  - Rows are sorted by the percentage of students who selected the correct answer (lowest first)
  - Rows highlighted in soft red indicate the correct answer was NOT the most selected
- **XLSX:**
  - Same columns as PDF, but includes all questions
  - Same row highlighting as PDF

---

## 8. Configuration Files

- **cursos.yml**: YAML configuration for all courses, including course names and KPIs to track.
- **base_courses.yml**: Base course mapping for up-to-date intersection logic.
- **env.template**: Template for environment variables.

---

## 9. Troubleshooting & Tips

- Always use forward slashes (`/`) for GCS object names and paths.
- Ensure all environment variables are set correctly.
- If up-to-date analysis is not working, check that planification files are uploaded to the correct GCS path and that the category and course_id match exactly (including accents and case).
- Use the debug prints in your scripts to verify file existence and paths.
- For GCP authentication, use `encode_service_account.py` to encode your service account key for the `.env` file.

---

## 10. License / Contact / Contributing

(Include your license, contact information, or contributing guidelines here if applicable.)
