# Google Cloud Function: Course Analysis Pipeline

This Google Cloud Function automates the daily analysis of course data, including data download, processing, report generation, and notifications via Slack.

## 🚀 Features

- **Incremental Data Processing**: Downloads only new data since last run using Cloud Storage state management
- **Automated Data Processing**: Downloads and processes course data from external APIs
- **Report Generation**: Creates comprehensive PDF and Excel reports
- **Cloud Storage Integration**: Uses Cloud Storage for persistent data storage and state management
- **Google Drive Integration**: Saves reports to Google Drive folders
- **Slack Notifications**: Sends daily summaries to Slack channels
- **Scheduled Execution**: Runs daily at 8:00 AM Santiago time via Cloud Scheduler

## 📋 Prerequisites

Before deploying this function, ensure you have:

1. **Google Cloud Project** with billing enabled
2. **Google Cloud SDK** installed and configured
3. **Service Account** with appropriate permissions
4. **Slack Bot Token** for notifications
5. **Google Drive Folder** for report storage

## 🛠️ Setup Instructions

### 1. Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example environment file and fill in your values:

```bash
cp env.yaml.example env.yaml
```

Edit `env.yaml` with your actual values:

```yaml
# Google Cloud Project Configuration
GCP_PROJECT_ID: "your-actual-project-id"
GCP_BUCKET_NAME: "your-actual-bucket-name"

# Slack Configuration
SLACK_BOT_TOKEN: "xoxb-your-actual-slack-bot-token"
SLACK_CHANNEL: "#your-actual-channel"

# Google Drive Configuration
GOOGLE_DRIVE_FOLDER_ID: "your-actual-folder-id"

# Service Account Key (base64 encoded)
GOOGLE_SERVICE_ACCOUNT_KEY: "your-base64-encoded-service-account-key"

# Optional: Users to ignore in analysis
IGNORED_USERS: "user1@example.com,user2@example.com"
```

### 3. Service Account Setup

1. Create a service account in your Google Cloud project
2. Grant the following roles:
   - Cloud Functions Developer
   - Storage Object Admin
   - Cloud Scheduler Admin
3. Download the JSON key file
4. Encode it as base64:

```bash
cat your-service-account.json | base64 -w 0
```

5. Add the encoded string to `env.yaml` as `GOOGLE_SERVICE_ACCOUNT_KEY`

### 4. Local Testing

Test the function locally before deployment:

```bash
# Test Cloud Storage integration
python test_gcs.py

# Test the complete function
python test_local.py
```

The `test_gcs.py` script will:
- Check environment variables
- Test Cloud Storage connectivity
- Test upload/download operations
- Test incremental logic

The `test_local.py` script will:
- Check dependencies
- Set up test environment variables
- Test the function logic
- Start a local server for testing

### 5. Deploy to Google Cloud

Deploy the function using the provided script:

```bash
chmod +x deploy.sh
./deploy.sh
```

The deployment script will:
- Enable required APIs
- Deploy the function
- Provide the function URL
- Test the deployment

### 6. Set Up Cloud Scheduler

Set up automatic daily execution:

```bash
chmod +x setup_scheduler.sh
./setup_scheduler.sh
```

This creates a Cloud Scheduler job that runs daily at 8:00 AM Santiago time.

## 📁 File Structure

```
cloud_function/
├── main.py                 # Main function entry point
├── requirements.txt        # Python dependencies
├── env.yaml               # Environment variables
├── cursos.yml             # Course configuration
├── deploy.sh              # Deployment script
├── setup_scheduler.sh     # Scheduler setup script
├── test_local.py          # Local testing script
├── README.md              # This file
├── analisis.py            # Analysis pipeline
├── descarga_procesa_datos.py  # Data download pipeline
└── batch_process.py       # Batch processing utilities
```

## 🔧 Configuration

### Course Configuration (`cursos.yml`)

Configure which courses to analyze:

```yaml
courses:
  course-id-1:
    name: "Course Display Name"
    kpis:
      - attendance_rate
      - average_grade
      - completion_rate
      - response_rate
  
  course-id-2:
    name: "Another Course"
    kpis:
      - attendance_rate
      - average_grade
```

### Function Configuration

The function can be configured via environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `GCP_PROJECT_ID` | Google Cloud Project ID | Yes |
| `GCP_BUCKET_NAME` | Cloud Storage bucket name | Yes |
| `SLACK_BOT_TOKEN` | Slack bot OAuth token | No |
| `SLACK_CHANNEL` | Slack channel for notifications | No |
| `GOOGLE_DRIVE_FOLDER_ID` | Google Drive folder ID | No |
| `GOOGLE_SERVICE_ACCOUNT_KEY` | Base64 encoded service account key | Yes |
| `IGNORED_USERS` | Comma-separated list of emails to ignore | No |
| `CLIENT_ID` | API client ID for data download | Yes |
| `SCHOOL_DOMAIN` | School domain for API calls | Yes |
| `ACCESS_TOKEN` | API access token for authentication | Yes |

## 🚀 Usage

### Manual Execution

Trigger the function manually via HTTP:

```bash
curl -X POST https://your-function-url \
  -H "Content-Type: application/json" \
  -d '{"trigger": "manual"}'
```

### Scheduled Execution

The function runs automatically daily at 8:00 AM Santiago time via Cloud Scheduler.

### Monitoring

Monitor function execution:

```bash
# View function logs
gcloud functions logs read course-analysis-pipeline --region=us-central1

# View function details
gcloud functions describe course-analysis-pipeline --region=us-central1

# View scheduler job details
gcloud scheduler jobs describe daily-course-analysis --location=us-central1
```

## 🔍 Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Ensure service account has correct permissions
   - Verify service account key is properly encoded

2. **Missing Dependencies**
   - Run `pip install -r requirements.txt`
   - Check Python version compatibility

3. **Environment Variables**
   - Verify all required variables are set in `env.yaml`
   - Check for typos in variable names

4. **API Quotas**
   - Monitor API usage in Google Cloud Console
   - Consider upgrading quotas if needed

### Debug Mode

Enable debug logging by setting the log level:

```bash
gcloud functions deploy course-analysis-pipeline \
  --set-env-vars LOG_LEVEL=DEBUG
```

## 📊 Output

The function generates:

1. **Raw Data**: JSON files stored in Cloud Storage with incremental updates
2. **Processed Data**: CSV files with cleaned data
3. **Reports**: PDF and Excel reports uploaded to Google Drive
4. **Slack Notifications**: Daily summary with links to reports

## 🔄 Incremental Processing

The function uses Cloud Storage for state management to enable efficient incremental processing:

- **First Run**: Downloads all historical data
- **Subsequent Runs**: Downloads only new data since the last timestamp
- **State Persistence**: Latest timestamps stored in Cloud Storage
- **Data Deduplication**: Automatically merges new and existing data

## 🔒 Security

- Service account keys are base64 encoded
- Function uses least-privilege access
- All API calls use authenticated credentials
- Environment variables are encrypted at rest

## 📈 Scaling

The function automatically scales based on demand:
- **Memory**: 2GB allocated
- **Timeout**: 9 minutes (maximum for free tier)
- **Concurrency**: Automatic scaling

## 🆘 Support

For issues or questions:

1. Check the function logs
2. Review this README
3. Test locally using `test_local.py`
4. Verify environment configuration

## 📝 License

This project is part of the M30M data analysis pipeline. 