# Google Cloud Platform Integration

This document explains how to deploy your course analysis pipeline to Google Cloud Platform for automated daily execution.

## 🏗️ Architecture Overview

The integration consists of:

- **Cloud Function**: Runs the analysis pipeline
- **Cloud Scheduler**: Triggers the function daily at 8am Santiago time
- **Cloud Storage**: Stores JSON and CSV files
- **Google Drive**: Stores generated reports
- **Slack Bot**: Sends notifications with report links

## 📋 Prerequisites

1. **Google Cloud Project**: You need a GCP project with billing enabled
2. **gcloud CLI**: Install the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
3. **Slack Workspace**: For notifications
4. **Google Drive**: For storing reports

## 🚀 Quick Start

### Option 1: Using the Deployment Script (Recommended)

1. **Set your project ID**:
   ```bash
   export PROJECT_ID="your-project-id"
   ```

2. **Run the deployment script**:
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

3. **Set up environment variables**:
   ```bash
   python setup_environment.py \
     --project-id $PROJECT_ID \
     --slack-token "xoxb-your-slack-token" \
     --slack-channel "#your-channel" \
     --drive-folder-id "your-drive-folder-id" \
     --client-id "your-learnworlds-client-id" \
     --school-domain "your-learnworlds-domain" \
     --access-token "your-learnworlds-access-token" \
     --ignored-users "user1@email.com,user2@email.com" \
     --service-account-key-file "service-account-key.json"
   ```



## 🔧 Detailed Setup

### 1. Google Cloud Project Setup

1. Create a new project or use an existing one
2. Enable billing
3. Install and authenticate gcloud CLI:
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

### 2. Slack Bot Setup

1. Go to [Slack API Apps](https://api.slack.com/apps)
2. Click "Create New App" → "From scratch"
3. Name: "Course Analysis Bot"
4. Select your workspace
5. Go to "OAuth & Permissions" in the sidebar
6. Add these scopes:
   - `chat:write`
   - `chat:write.public`
7. Install the app to your workspace
8. Copy the "Bot User OAuth Token" (starts with `xoxb-`)
9. Invite the bot to your channel: `/invite @Course Analysis Bot`

### 3. Google Drive Setup

1. Go to [Google Drive](https://drive.google.com)
2. Create a new folder called "Course Analysis Reports"
3. Right-click on the folder and select "Share"
4. Add the service account email (will be shown after deployment) with "Editor" permissions
5. Copy the folder ID from the URL (the long string after `/folders/`)

### 4. Environment Variables

After deployment, you need to set these environment variables in the Cloud Function:

- `SLACK_BOT_TOKEN`: Your Slack bot token
- `SLACK_CHANNEL`: Channel to send notifications (e.g., `#general`)
- `GOOGLE_DRIVE_FOLDER_ID`: Google Drive folder ID for reports
- `CLIENT_ID`: LearnWorlds Client ID
- `SCHOOL_DOMAIN`: LearnWorlds School Domain
- `ACCESS_TOKEN`: LearnWorlds Access Token
- `IGNORED_USERS`: Comma-separated list of ignored user emails
- `GOOGLE_SERVICE_ACCOUNT_KEY`: Service account key (automatically set)

Use the `setup_environment.py` script to configure these automatically.

## 📊 How It Works

### Daily Execution Flow

1. **8am Santiago time**: Cloud Scheduler triggers the Cloud Function
2. **Data Download**: Function downloads data from LearnWorlds API
3. **Data Processing**: Processes and analyzes the data
4. **Cloud Storage**: Uploads JSON and CSV files to Cloud Storage
5. **Google Drive**: Uploads reports (Excel/PDF) to Google Drive
6. **Slack Notification**: Sends notification with report links

### File Structure in Cloud Storage

```
gs://your-bucket/
├── raw/
│   ├── course-id/
│   │   ├── assessments.json
│   │   ├── grades.json
│   │   └── users.json
└── processed/
    ├── course-id/
    │   ├── assessments.csv
    │   ├── grades.csv
    │   └── users.csv
```

### File Structure in Google Drive

```
Course Analysis Reports/
├── course-id_reporte_2025-01-15.xlsx
├── course-id_reporte_listas_2025-01-15.xlsx
├── course-id_reporte_2025-01-15.pdf
├── course-id_assessments_2025-01-15.csv
├── course-id_grades_2025-01-15.csv
└── course-id_users_2025-01-15.csv
```

## 🔍 Monitoring and Troubleshooting

### View Function Logs

```bash
gcloud functions logs read course-analysis-pipeline --region=us-central1
```

### View Scheduler Logs

```bash
gcloud scheduler jobs describe daily-course-analysis --location=us-central1
```

### Test Function Manually

```bash
# Get function URL
FUNCTION_URL=$(gcloud functions describe course-analysis-pipeline --region=us-central1 --format="value(httpsTrigger.url)")

# Test with curl
curl -X POST $FUNCTION_URL
```

### Common Issues

1. **Permission Denied**: Ensure service account has proper IAM roles
2. **Slack Token Invalid**: Check bot token and channel permissions
3. **Drive Access Denied**: Share the folder with the service account email
4. **Function Timeout**: Increase timeout in deployment (max 540s)

## 💰 Cost Estimation

**Realistic monthly costs** (based on 4 courses, 330 executions/year, ~1 minute runtime):

- **Cloud Function**: ~$0.40/month (2GB memory, 1 minute execution)
- **Cloud Storage**: ~$0.50/month (~27GB/year for JSON/CSV files)
- **Cloud Scheduler**: ~$0.40/month (330 executions/year)
- **Google Drive API**: $0/month (well within free tier)
- **Network**: ~$0.10/month

**Total: ~$1.40/month** (likely under $1/month in practice)

*Note: Costs scale linearly with number of courses and execution time.*

## 🔒 Security Considerations

1. **Service Account**: Uses minimal required permissions
2. **Environment Variables**: Sensitive data stored securely
3. **HTTPS**: All communications use HTTPS
4. **IAM**: Proper role-based access control

## 📝 Configuration Files

### cursos.yml
Your existing course configuration file will be used by the Cloud Function. Make sure it's properly configured with all your courses.

### Environment Variables
The function uses these environment variables (set automatically by the deployment):

- `GCP_PROJECT_ID`: Your Google Cloud project ID
- `GCP_BUCKET_NAME`: Cloud Storage bucket name
- `SLACK_BOT_TOKEN`: Slack bot token
- `SLACK_CHANNEL`: Slack channel for notifications
- `GOOGLE_DRIVE_FOLDER_ID`: Google Drive folder ID
- `CLIENT_ID`: LearnWorlds Client ID
- `SCHOOL_DOMAIN`: LearnWorlds School Domain
- `ACCESS_TOKEN`: LearnWorlds Access Token
- `IGNORED_USERS`: Comma-separated list of ignored user emails
- `GOOGLE_SERVICE_ACCOUNT_KEY`: Service account key (JSON)

## 🚀 Deployment Commands Summary

```bash
# 1. Deploy infrastructure
./deploy.sh

# 2. Set up environment variables
python setup_environment.py \
  --project-id your-project-id \
  --slack-token xoxb-your-token \
  --slack-channel "#your-channel" \
  --drive-folder-id your-folder-id \
  --client-id your-learnworlds-client-id \
  --school-domain your-learnworlds-domain \
  --access-token your-learnworlds-access-token \
  --ignored-users "user1@email.com,user2@email.com" \
  --service-account-key-file service-account-key.json

# 3. Test the function
curl -X POST $(gcloud functions describe course-analysis-pipeline --region=us-central1 --format="value(httpsTrigger.url)")

# 4. Monitor logs
gcloud functions logs read course-analysis-pipeline --region=us-central1
```

## 📞 Support

If you encounter issues:

1. Check the function logs for error messages
2. Verify all environment variables are set correctly
3. Ensure the service account has proper permissions
4. Test the Slack bot and Google Drive access manually

The system is designed to be robust and will continue processing other courses even if one fails. 