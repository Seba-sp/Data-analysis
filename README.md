# Data Analysis Project Overview

This project provides a complete workflow for downloading, processing, and analyzing course and assessment data, generating actionable reports, and integrating with Google Drive and Slack for automated delivery and notifications.

## Directory Structure

### General Course Data
```
data/
  raw/
    <course>/
      users.json
      grades.json
      assessments.json
      ...
  processed/
    <course>/
      users.csv
      grades.csv
      assessments.csv
      ...
  metrics/
    kpi/
      <course>/
        ...
  reports/
    <course>/
      <various reports>.pdf
      <various reports>.xlsx
      ...
  planification/
    <course>.csv   # Planification files for up-to-date analysis
```

## High-Level Workflow

1. **Environment Setup:** Configure your `.env` file and credentials.
2. **Download Data:** Download raw data (users, grades, assessments) and/or detailed assessment responses.
3. **Process Data:** Incrementally process and filter data for analysis.
4. **Analyze & Report:** Generate detailed reports (PDF, Excel) for courses and assessments.
5. **Batch Processing:** Automate the above steps for multiple courses.
6. **Integrations:** Upload reports to Google Drive and send Slack notifications.

---

## Environment Setup

- Copy `env.template` to `.env` and fill in your credentials and settings.
- Use `create_env_file.py` and `setup_environment.py` to help create and validate your environment.
- Key environment variables:
  - `CLIENT_ID`, `SCHOOL_DOMAIN`, `ACCESS_TOKEN` (API credentials)
  - `GCP_PROJECT_ID`, `GOOGLE_DRIVE_FOLDER_ID`, `GOOGLE_SERVICE_ACCOUNT_KEY` (Google Cloud/Drive)
  - `SLACK_BOT_TOKEN`, `SLACK_CHANNEL` (Slack integration)
  - `IGNORED_USERS` (comma-separated emails to ignore)
  - `UP_TO_DATE_BASE_COURSE` (for up-to-date filtering)

---

## Main Course Analysis & Reporting

### `analisis.py`
- **Purpose:** Analyze course data (grades, users, assessments), generate metrics, completion times, and custom reports (PDF, Excel).
- **Features:**
  - Up-to-date student filtering based on planification files in `data/planification/`.
  - Uploads reports to Google Drive and sends Slack notifications (optional).
- **Usage:**
  ```sh
  python analisis.py --course <course>
  # Add --upload to upload reports to Google Drive and notify Slack
  ```

### `descarga_procesa_datos.py`
- **Purpose:** Download and process all raw data (users, grades, assessments) for a course.
- **Features:** Incremental download, organized output in `data/raw/`, `data/processed/`, `data/metrics/`, `data/reports/`.
- **Usage:**
  ```sh
  python descarga_procesa_datos.py --course <course>
  # Add --reset-raw to force a full re-download
  ```

### `batch_process.py`
- **Purpose:** Batch processing for multiple courses as defined in `cursos.yml`.
- **Features:** Download-only, analysis-only, and upload-only modes. Integrates with Google Drive and Slack.
- **Usage:**
  ```sh
  python batch_process.py
  python batch_process.py --courses nivel-1-m30m nivel-2-m30m
  python batch_process.py --download-only
  python batch_process.py --analysis-only
  python batch_process.py --upload-only
  ```

### `cursos.yml`
- **Purpose:** YAML configuration for all courses, including course names and KPIs to track.

### Planification & Up-to-Date Analysis
- Place planification CSVs in `data/planification/` with columns `assessment_name` and `date`.
- The analysis pipeline can filter students who are up to date with the planification schedule, and even intersect with a base course (see `UP_TO_DATE_BASE_COURSE` in `.env`).

---

## Assessment Responses Workflow

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
- Place the resulting `<assessment>_questions.csv` file in the `data/responses/questions/<course>/` directory.
- When running analysis, if only the raw file is present, the analysis script will attempt to convert it automatically.

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

## Utilities and Testing

- `setup_environment.py`, `create_env_file.py`: Help set up and validate your environment variables and service account keys.
- `test_slack_bot.py`: Test Slack bot integration and message sending.
- `test_upload_functionality.py`: Test Google Drive and Slack integration, including file upload and notification.
- `test_cloud_function.py`: Test script for running the Cloud Function locally or remotely (for GCP deployments).
- `prompts cursor.txt`: Contains project planning notes and feature requests (not a script).

---

## General Workflow

1. **Set up your environment:**
   - Copy `env.template` to `.env` and fill in your credentials.
   - Use `create_env_file.py` and `setup_environment.py` for help.
2. **Download and process data:**
   - Use `descarga_procesa_datos.py` for full course data.
   - Use `descarga_responses.py` for detailed assessment responses.
3. **Analyze and generate reports:**
   - Use `analisis.py` for full course analysis.
   - Use `analisis_responses.py` for detailed assessment response analysis.
4. **Batch process all courses:**
   - Use `batch_process.py` for automation.
5. **Test integrations:**
   - Use the test scripts for Slack, Google Drive, and Cloud Function.

---

For any issues or questions, see the comments in each script or open an issue.
