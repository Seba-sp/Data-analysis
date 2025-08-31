# Multi-Assessment Processor

## Overview

The Multi-Assessment Processor is an enhanced version of the assessment response analysis system that can handle multiple assessments simultaneously, join responses by user across different assessments, and automatically upload results to Google Drive with Slack notifications.

## Key Features

- **Multiple Assessment Support**: Download and process multiple assessments from a single configuration
- **User Response Joining**: Combine responses from different assessments for the same user
- **Flexible Grouping**: Group related assessments (e.g., "M1 TD Part 1" and "M1 TD Part 2")
- **Automated Workflow**: Download → Process → Join → Upload → Notify
- **Cloud Run Ready**: Designed for automated execution in Google Cloud Run
- **Scheduled Execution**: Runs twice daily (9 AM and 6 PM) via Cloud Scheduler

## Quick Start

### 1. Configuration

Create or update `assessments_config.yml` with your assessment details:

```yaml
course:
  id: "nivel-1-m30m"
  name: "Nivel 1 M30M"
  assessments:
    individual:
      - name: "cl td"
        id: "your_assessment_id_here"
        description: "CL Test Diagnóstico"
      
    grouped:
      m1_td_series:
        name: "M1 TD Series"
        description: "M1 Test Diagnóstico Parts 1 and 2 combined"
        assessments:
          - name: "m1 td part 1"
            id: "assessment_id_part1"
            description: "M1 Test Diagnóstico Part 1"
          - name: "m1 td part 2"
            id: "assessment_id_part2"
            description: "M1 Test Diagnóstico Part 2"
```

### 2. Environment Variables

Set up the required environment variables:

```bash
# LearnWorlds API
CLIENT_ID=your_client_id
SCHOOL_DOMAIN=your_school_domain
ACCESS_TOKEN=your_access_token

# Google Cloud Platform
GCP_PROJECT_ID=your_project_id
GCP_BUCKET_NAME=your_bucket_name
STORAGE_BACKEND=gcp

# Google Drive
GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id
GOOGLE_SERVICE_ACCOUNT_KEY=your_service_account_key_json

# Slack
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_CHANNEL=#assessment-reports

# Processing
REPORT_TOP_PERCENT=20
```

### 3. Local Testing

Test the configuration without processing:

```bash
python multi_assessment_processor.py --config assessments_config.yml --dry-run
```

Run the processor locally:

```bash
python multi_assessment_processor.py --config assessments_config.yml
```

### 4. Cloud Run Deployment

Deploy to Google Cloud Run:

```bash
# Set environment variables
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export SERVICE_NAME="multi-assessment-processor"
export GCP_BUCKET_NAME="your-bucket-name"
export CLIENT_ID="your-client-id"
export SCHOOL_DOMAIN="your-school-domain"
export ACCESS_TOKEN="your-access-token"
export GOOGLE_DRIVE_FOLDER_ID="your-drive-folder-id"
export GOOGLE_SERVICE_ACCOUNT_KEY="your-service-account-key"
export SLACK_BOT_TOKEN="your-slack-bot-token"
export SLACK_CHANNEL="#assessment-reports"

# Make deploy script executable and run
chmod +x deploy.sh
./deploy.sh
```

## Workflow

### 1. Individual Assessments
- Downloads responses for each individual assessment
- Processes and filters responses
- Saves to local/GCS storage

### 2. Grouped Assessments
- Downloads responses for all assessments in a group
- Processes each assessment individually
- Joins responses by user ID across all assessments in the group
- Creates a combined Excel/CSV file with one row per user
- Uploads combined file to Google Drive
- Sends Slack notification with Drive link

### 3. Output Structure

```
data/responses/
├── raw/
│   └── nivel-1-m30m/
│       ├── cl_td.json
│       ├── m1_td_part_1.json
│       └── m1_td_part_2.json
├── processed/
│   └── nivel-1-m30m/
│       ├── cl_td.csv
│       ├── m1_td_part_1.csv
│       └── m1_td_part_2.csv
├── reports/
│   └── nivel-1-m30m/
│       └── M1_TD_Series_combined.xlsx  # Joined file
└── questions/
    └── nivel-1-m30m/
        ├── cl_td.csv
        ├── m1_td_part_1.csv
        └── m1_td_part_2.csv
```

## Configuration Details

### Assessment Configuration

#### Individual Assessments
```yaml
individual:
  - name: "assessment_name"  # Used for file naming
    id: "learnworlds_assessment_id"  # Actual assessment ID
    description: "Human readable description"
```

#### Grouped Assessments
```yaml
grouped:
  group_key:  # Internal identifier
    name: "Group Display Name"  # Used for output files
    description: "Group description"
    assessments:
      - name: "assessment_name"
        id: "learnworlds_assessment_id"
        description: "Assessment description"
```

### Output Configuration

#### File Format
- `xlsx`: Excel format (recommended for joined files)
- `csv`: CSV format with semicolon separator

#### Drive Upload
- Files are uploaded to: `{folder_name}/{subfolder}/`
- File naming: `{group_name}_combined_{timestamp}.{format}`

#### Slack Notifications
- Success notifications include Drive links
- Error notifications include error details
- Configurable per success/error

### Processing Options

- `download_new`: Whether to download new responses or use existing
- `process_individual`: Process individual assessments
- `process_grouped`: Process grouped assessments
- `filter_incomplete`: Remove responses with empty last question
- `keep_latest_per_user`: Keep only the latest response per user

## User Response Joining

### How It Works

1. **Load Assessment Data**: Load CSV files for all assessments in a group
2. **Identify User Column**: Find user ID column (`userId`, `user_id`, or `user`)
3. **Add Assessment Identifier**: Add `assessment_name` column to each dataset
4. **Combine Data**: Concatenate all assessment data
5. **Pivot by User**: Create one row per user with columns for each assessment
6. **Flatten Columns**: Create descriptive column names like `m1_td_part_1_pregunta_1`

### Output Format

The joined file will have:
- One row per unique user
- Columns for each assessment's questions
- User metadata (name, email, etc.) from the first assessment
- Timestamp information for each assessment

### Example Output

| userId | m1_td_part_1_pregunta_1 | m1_td_part_1_pregunta_2 | m1_td_part_2_pregunta_1 | m1_td_part_2_pregunta_2 |
|--------|-------------------------|-------------------------|-------------------------|-------------------------|
| 12345  | A                       | B                       | C                       | D                       |
| 67890  | B                       | A                       | D                       | C                       |

## Cloud Run Deployment

### Prerequisites

1. **Google Cloud Project** with billing enabled
2. **gcloud CLI** installed and authenticated
3. **Docker** installed
4. **Required APIs** enabled:
   - Cloud Run API
   - Cloud Build API
   - Cloud Storage API
   - Cloud Scheduler API

### Deployment Steps

1. **Set Environment Variables**:
   ```bash
   export PROJECT_ID="your-project-id"
   export GCP_BUCKET_NAME="your-bucket-name"
   # ... other variables
   ```

2. **Run Deployment Script**:
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

3. **Verify Deployment**:
   ```bash
   gcloud run jobs list --region=us-central1
   ```

### Manual Execution

Test the deployed job:

```bash
gcloud run jobs execute multi-assessment-processor --region=us-central1
```

### Monitoring

- **Cloud Run Jobs**: Monitor execution in Google Cloud Console
- **Cloud Scheduler**: Check scheduled job status
- **Cloud Storage**: Verify file uploads
- **Slack**: Receive notifications about processing status

## Troubleshooting

### Common Issues

#### 1. Assessment ID Not Found
```
Error: Assessment ID not found in LearnWorlds
```
**Solution**: Verify assessment IDs in `assessments_config.yml` match LearnWorlds

#### 2. Missing Assessment Data
```
Error: Assessment data not found
```
**Solution**: Check if assessments have been downloaded and processed

#### 3. Drive Upload Failures
```
Error: Failed to upload to Drive
```
**Solution**: Check Google Drive permissions and service account key

#### 4. Slack Notification Failures
```
Error: Failed to send Slack notification
```
**Solution**: Verify Slack bot token and channel permissions

### Debug Mode

Enable debug logging:

```bash
export DEBUG=true
python multi_assessment_processor.py --config assessments_config.yml
```

### Log Analysis

Check Cloud Run job logs:

```bash
gcloud run jobs logs read multi-assessment-processor --region=us-central1
```

## Cost Optimization

### Cloud Run Configuration
- **Memory**: 2Gi (sufficient for most workloads)
- **CPU**: 1 vCPU
- **Timeout**: 1800s (30 minutes)
- **Max Retries**: 3

### Estimated Costs
- **Cloud Run**: ~$0.36/month (twice daily execution)
- **Cloud Storage**: ~$0.02/month (for data storage)
- **Cloud Scheduler**: ~$0.10/month

### Optimization Tips
1. **Incremental Downloads**: Only download new responses
2. **Efficient Filtering**: Filter incomplete responses early
3. **Batch Processing**: Process multiple assessments together
4. **Storage Cleanup**: Archive old data periodically

## Security Considerations

### Environment Variables
- Store sensitive data in environment variables
- Use Google Secret Manager for production
- Rotate API tokens regularly

### Service Account Permissions
- Minimal required permissions
- Principle of least privilege
- Regular permission audits

### Data Privacy
- User data is processed in memory only
- No persistent storage of sensitive data
- Compliance with data protection regulations

## Integration Examples

### Custom Slack Notifications

Modify the notification format in `multi_assessment_processor.py`:

```python
def send_custom_notification(self, group_name, file_path, drive_file_id):
    message = f"📊 *Assessment Report Ready*\n"
    message += f"• *Group*: {group_name}\n"
    message += f"• *File*: {Path(file_path).name}\n"
    message += f"• *Drive*: <{drive_link}|View in Drive>\n"
    message += f"• *Generated*: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    self.slack_service.send_message(message, channel)
```

### Custom Drive Folder Structure

Modify the folder creation in `upload_to_drive`:

```python
# Create date-based folders
date_folder = datetime.now().strftime('%Y-%m')
date_folder_id = self.drive_service.find_or_create_folder(
    subfolder_id, 
    date_folder
)
```

### Custom Processing Logic

Add custom processing in `join_assessments_by_user`:

```python
# Add custom calculations
pivot_df['total_score'] = pivot_df[score_columns].sum(axis=1)
pivot_df['average_score'] = pivot_df[score_columns].mean(axis=1)
```

## Support

For issues and questions:

1. **Check logs** in Cloud Run console
2. **Verify configuration** in `assessments_config.yml`
3. **Test locally** with `--dry-run` flag
4. **Review environment variables** for missing values

## Migration from Single Assessment

If migrating from the single assessment system:

1. **Backup existing data**: Copy current assessment files
2. **Create configuration**: Set up `assessments_config.yml`
3. **Test locally**: Run with `--dry-run` first
4. **Deploy gradually**: Start with one assessment group
5. **Monitor results**: Verify output format and quality
6. **Scale up**: Add more assessments as needed
