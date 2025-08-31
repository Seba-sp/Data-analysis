# Multi-Assessment Processor Setup Guide

## 🎯 What's New

This project has been enhanced to support **multiple assessments** with the following new capabilities:

- ✅ **Multiple Assessment Processing**: Download and process multiple assessments simultaneously
- ✅ **User Response Joining**: Combine responses from different assessments for the same user
- ✅ **Flexible Grouping**: Group related assessments (e.g., "M1 TD Part 1" and "M1 TD Part 2")
- ✅ **Automated Workflow**: Download → Process → Join → Upload → Notify
- ✅ **Cloud Run Ready**: Designed for automated execution in Google Cloud Run
- ✅ **Scheduled Execution**: Runs twice daily (9 AM and 6 PM) via Cloud Scheduler

## 📁 New Files Created

### Core Files
- `multi_assessment_processor.py` - Main orchestrator script
- `assessments_config.yml` - Configuration file for assessments
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container configuration for Cloud Run
- `deploy.sh` - Deployment script for Google Cloud Run

### Helper Files
- `test_config.py` - Configuration validation script
- `README_MULTI_ASSESSMENT.md` - Comprehensive documentation

### Modified Files
- `storage.py` - Added `write_excel()` method for Excel file support

## 🚀 Quick Start

### Step 1: Configure Assessments

Update `assessments_config.yml` with your assessment details:

```yaml
course:
  id: "nivel-1-m30m"
  name: "Nivel 1 M30M"
  assessments:
    individual:
      - name: "cl td"
        id: "your_actual_assessment_id"
        description: "CL Test Diagnóstico"
      
    grouped:
      m1_td_series:
        name: "M1 TD Series"
        description: "M1 Test Diagnóstico Parts 1 and 2 combined"
        assessments:
          - name: "m1 td part 1"
            id: "your_actual_part1_id"
            description: "M1 Test Diagnóstico Part 1"
          - name: "m1 td part 2"
            id: "your_actual_part2_id"
            description: "M1 Test Diagnóstico Part 2"
```

### Step 2: Set Environment Variables

Create a `.env` file or set environment variables:

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
```

### Step 3: Test Configuration

Validate your setup:

```bash
python test_config.py
```

### Step 4: Test Locally

Test the configuration without processing:

```bash
python multi_assessment_processor.py --config assessments_config.yml --dry-run
```

Run the processor locally:

```bash
python multi_assessment_processor.py --config assessments_config.yml
```

### Step 5: Deploy to Cloud Run

Deploy to Google Cloud Run for automated execution:

```bash
# Set deployment variables
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

# Deploy
chmod +x deploy.sh
./deploy.sh
```

## 🔄 Workflow Overview

### Individual Assessments
1. Downloads responses for each individual assessment
2. Processes and filters responses
3. Saves to local/GCS storage

### Grouped Assessments
1. Downloads responses for all assessments in a group
2. Processes each assessment individually
3. Joins responses by user ID across all assessments
4. Creates a combined Excel/CSV file with one row per user
5. Uploads combined file to Google Drive
6. Sends Slack notification with Drive link

## 📊 Output Structure

```
data/responses/
├── raw/                    # Raw JSON responses
├── processed/              # Processed CSV files
├── reports/                # Generated reports
│   └── combined/           # Joined assessment files
└── questions/              # Question files from LearnWorlds
```

## 🎯 Key Features

### User Response Joining
- Combines responses from multiple assessments for the same user
- Creates one row per user with columns for each assessment's questions
- Example: `m1_td_part_1_pregunta_1`, `m1_td_part_2_pregunta_1`

### Automated Notifications
- Slack notifications on success/failure
- Includes Google Drive links to uploaded files
- Configurable notification settings

### Cloud Run Integration
- Runs twice daily (9 AM and 6 PM)
- Automatic retries on failure
- Scalable and cost-effective

## 🔧 Configuration Options

### Processing Options
- `download_new`: Whether to download new responses
- `process_individual`: Process individual assessments
- `process_grouped`: Process grouped assessments
- `filter_incomplete`: Remove incomplete responses
- `keep_latest_per_user`: Keep only latest response per user

### Output Options
- `format`: Excel or CSV output
- `drive.folder_name`: Google Drive folder name
- `slack.channel`: Slack notification channel

## 🚨 Troubleshooting

### Common Issues

1. **Assessment ID Not Found**
   - Verify IDs in `assessments_config.yml` match LearnWorlds

2. **Missing Environment Variables**
   - Run `test_config.py` to check configuration
   - Verify all required variables are set

3. **Drive Upload Failures**
   - Check Google Drive permissions
   - Verify service account key

4. **Slack Notification Failures**
   - Check Slack bot token
   - Verify channel permissions

### Debug Commands

```bash
# Test configuration
python test_config.py

# Dry run
python multi_assessment_processor.py --config assessments_config.yml --dry-run

# Check Cloud Run logs
gcloud run jobs logs read multi-assessment-processor --region=us-central1

# Manual execution
gcloud run jobs execute multi-assessment-processor --region=us-central1
```

## 📈 Migration from Single Assessment

If you're migrating from the original single assessment system:

1. **Backup existing data**: Copy current assessment files
2. **Create configuration**: Set up `assessments_config.yml`
3. **Test locally**: Run with `--dry-run` first
4. **Deploy gradually**: Start with one assessment group
5. **Monitor results**: Verify output format and quality
6. **Scale up**: Add more assessments as needed

## 💰 Cost Optimization

### Estimated Monthly Costs
- **Cloud Run**: ~$0.36 (twice daily execution)
- **Cloud Storage**: ~$0.02 (data storage)
- **Cloud Scheduler**: ~$0.10

### Optimization Tips
1. Use incremental downloads (only new responses)
2. Filter incomplete responses early
3. Process multiple assessments together
4. Archive old data periodically

## 🎉 Next Steps

1. **Update assessment IDs** in `assessments_config.yml`
2. **Test locally** with `--dry-run` flag
3. **Deploy to Cloud Run** for automated execution
4. **Monitor results** and adjust configuration as needed
5. **Scale up** by adding more assessment groups

## 📞 Support

For issues and questions:

1. Check the comprehensive documentation in `README_MULTI_ASSESSMENT.md`
2. Run `test_config.py` to validate your setup
3. Check Cloud Run logs for execution issues
4. Review environment variables for missing values

---

**🎯 The system is now ready to process multiple assessments automatically!**
