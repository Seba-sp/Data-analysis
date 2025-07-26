# Data Analysis Project

## TL;DR

- **What is this?**
  - Download, process, and analyze course/assessment data. Generate reports. Integrate with Google Drive and Slack. Works locally or with Google Cloud Storage (GCP).

- **Most users:**
  1. **Update course configs:**
     ```sh
     python get_all_courses.py
     ```
  2. **Upload planification files (if using GCP):**
     ```sh
     python upload_folder_to_gcs.py --folder data/planification --gcs-folder data/planification
     ```
  3. **Batch process everything (download, analyze, upload):**
     ```sh
     python batch_process.py
     # Or for a specific category/course:
     python batch_process.py --category Matematicas
     python batch_process.py --category Matematicas --course nivel-1-m30m
     ```

- **Advanced/manual:**
  1. Download/process data:
     ```sh
     python descarga_procesa_datos.py --category <category> --course <course>
     ```
  2. Analyze and generate reports:
     ```sh
     python analisis.py --category <category> --course <course>
     # Add --no-upload to skip Google Drive/Slack
     ```

- **Assessment responses:**
  1. Download responses:
     ```sh
     python descarga_responses.py --course <course> --all
     python descarga_responses.py --course <course> --assessment <assessment>
     ```
  2. Upload question file from LearnWorlds to the questions folder (locally or on GCP).
  3. Run analysis (conversion happens automatically if needed):
     ```sh
     python analisis_responses.py --course <course> --all
     python analisis_responses.py --course <course> --assessment <assessment>
     ```

- **Where are my reports?**
  - Find them in `data/reports/<category>/<course>/` (local) or in your Google drive.

- **Need help?**
  - See the rest of this README for details, troubleshooting, and advanced usage.

---

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

### Environment Variables

#### Locally or on GCP "local" or "gcp"
- `STORAGE_BACKEND`

#### LearnWorlds API Credentials
- `CLIENT_ID`
- `SCHOOL_DOMAIN`
- `ACCESS_TOKEN`

#### Set filter for abandoned assessments
- `GRADE_ZERO_THRESHOLD`
- `TIME_MAX_THRESHOLD_MINUTES`

#### Set x percentage of most responses wrong
- `REPORT_TOP_PERCENT`

#### Google Cloud Platform Configuration
- `GCP_PROJECT_ID`
- `GCP_BUCKET_NAME`
- `REGION` (e.g., "us-central1")

#### Slack Configuration
- `SLACK_BOT_TOKEN`
- `SLACK_CHANNEL`

#### Google Drive Configuration
- `GOOGLE_SHARED_DRIVE_ID`
- `GOOGLE_DRIVE_FOLDER_ID`

#### Ignored Users
- `IGNORED_USERS` (comma-separated list)

#### Service Account Key (base64 encoded)
- `GOOGLE_SERVICE_ACCOUNT_KEY`

#### Local Development
- `GOOGLE_APPLICATION_CREDENTIALS`

---

## 4. Main Workflow

- **Quick option:** You can execute `batch_process.py` to run the full workflow (download, process, analyze, upload) for all courses as defined in your configuration, skipping the need to run `descarga_procesa_datos.py` and `analisis.py` manually for each course.
  ```sh
  python batch_process.py
  ```
  You can also use options like `--download-only`, `--analysis-only`, or `--no-upload` for partial workflows. Additionally, you can use `--category <category>` and/or `--course <course>` to process only a specific category or course:
  ```sh
  python batch_process.py --category Matematicas
  python batch_process.py --category Matematicas --course nivel-1-m30m
  ```

- **Step-by-step option:**
  1. **Set up your environment**
  2. **Download and process data**: Use `descarga_procesa_datos.py` for full course data (incremental by default).
  3. **Analyze and generate reports**: Use `analisis.py` for full course analysis (with up-to-date filtering and batch modes).
  4. **Batch process all courses**: Use `batch_process.py` for automation (supports download-only, analysis-only, upload-only, and combinations).
  5. **Test integrations**: Use the test scripts for Slack and Google Drive.

---

## 5. Core Scripts

### `get_all_courses.py`
- **Purpose:** Downloads `courses_raw.json` from the API and updates `cursos.yml` with the latest course information. Run this script to refresh your course configuration files from the API before downloading or analyzing courses.
- **Note:** The rest of the scripts (for downloading, processing, and analyzing data) get the list of courses to operate on from `cursos.yml`, which is updated by this script.
- **Usage:**
  ```sh
  python get_all_courses.py
  ```

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
- **Important:** For the report to include the "up to date" section, you must upload the relevant planification CSV files to the `planification` folder. If your backend is GCP, these files must be uploaded to the correct location in your Cloud Storage bucket (e.g., `data/planification/<category>/<course>.csv`).
- **Usage:**
  ```sh
  python analisis.py --category <category> --course <course>
  # Add --no-upload to skip Google Drive/Slack
  ```

### `upload_folder_to_gcs.py`
- **Purpose:** Uploads the `planification` folder or files inside it (or any other local files/folders) to your GCP bucket. Ensures correct GCS path formatting and supports uploading single files or entire folders. Essential for making planification files available to the analysis pipeline when using the GCP backend.
- **Usage:**
  ```sh
  python upload_folder_to_gcs.py --folder data/planification --gcs-folder data/planification
  # Or upload a single file:
  python upload_folder_to_gcs.py --file data/planification/<category>/<course>.csv --gcs-folder data/planification/<category>
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

- **encode_service_account.py**: Encodes your `service-account-key.json` file to a base64 string so you can safely copy it into your `.env` file for use with GCP authentication.
- **convert_questions_file.py**: Converts a raw question/correct answer file to the format needed for analysis.
- **setup_environment.py**, **create_env_file.py**: Help set up and validate your environment variables and service account keys.
- **test_slack_bot.py**: Test Slack bot integration and message sending.
- **test_upload_functionality.py**: Test Google Drive and Slack integration, including file upload and notification.
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
        assessment1.csv                # Raw question/correct answer file (from LearnWorlds)
        assessment1_questions.csv      # Processed question/correct answer file (used for analysis)
        ...
    reports/
      <course>/
        assessment1_report.xlsx
        assessment1_top_20pct.pdf
        ...
```

### Workflow
1. **Run** `descarga_responses.py` to download and process assessment responses.
2. **Upload** the question file for the assessment (downloaded from LearnWorlds) to the `questions` folder for the relevant course (locally or on GCP, depending on your backend).
3. **Run** `analisis_responses.py` to generate reports. If only the raw question file is present, the conversion to the required format will happen automatically during analysis.

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
- **Step 1:** Download the assessment question file from LearnWorlds and save it in the `questions` folder for the relevant course (either locally or on GCP, depending on your backend).
- Converts a raw question/correct answer file (downloaded from your platform) to the format needed for analysis.
- The input file should have columns like `Group`, `Type`, `Question`, `CorrectAns`, `Answer1`, `Answer2`, ...
- The output file will have columns: `question`, `correct_answer` (the text of the correct alternative).
- **Note:** If you run `analisis_responses.py` and only the raw file is present, the conversion will happen automatically.

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
