# Webhook Service for LearnWorlds Assessment Reports

A Flask-based webhook service that automatically generates and sends personalized PDF reports when students complete assessments in LearnWorlds.

## Overview

This service processes webhook events from LearnWorlds when students complete assessments, analyzes their performance, generates personalized PDF reports using Word templates, and sends them via email. It also saves reports to Google Drive for persistent storage.

## Features

- **Real-time Processing**: Handles webhook events from LearnWorlds instantly
- **Assessment Analysis**: Analyzes student performance by lecture (all questions correct = pass)
- **PDF Report Generation**: Creates personalized reports using Word templates
- **Email Delivery**: Sends reports via SMTP (Gmail/SendGrid)
- **Google Drive Storage**: Saves reports to organized folders in Google Drive
- **Duplicate Prevention**: Tracks processed assessments to avoid duplicates
- **Admin Notifications**: Sends error notifications to administrators
- **Multi-backend Storage**: Supports local filesystem and Google Cloud Storage
- **Security**: Validates webhook signatures for authenticity

## Quick Start

### Prerequisites
- Python 3.8+
- LearnWorlds API access
- Gmail account (for email delivery)
- Google Cloud project (for production deployment)

### Local Development Setup

1. **Clone and install dependencies:**
   ```bash
   git clone <repository>
   cd webhook-service
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   # Copy template and edit
   cp env.template .env
   # Edit .env with your configuration
   ```

3. **Run the service:**
   ```bash
   python webhook_main.py
   ```

## Google Cloud Setup

### 1. Create Google Cloud Project

1. **Create a new project** or use existing one
2. **Enable billing** for the project
3. **Enable required APIs**:
   ```bash
   gcloud services enable run.googleapis.com
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable storage.googleapis.com
   gcloud services enable drive.googleapis.com
   gcloud services enable logging.googleapis.com
   ```

### 2. Service Account Setup

#### **Create Service Account:**
```bash
# Create service account
gcloud iam service-accounts create webhook-service \
  --display-name="Webhook Service Account" \
  --description="Service account for webhook service"

# Get the service account email
SA_EMAIL=$(gcloud iam service-accounts list --filter="displayName:Webhook Service Account" --format="value(email)")
echo $SA_EMAIL
```

#### **Required Permissions:**

**For Google Cloud Storage:**
```bash
# Storage Object Admin (for reading/writing files)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/storage.objectAdmin"

# Storage Object Viewer (for reading files)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/storage.objectViewer"
```

**For Cloud Run (if using default service account):**
```bash
# Cloud Run Invoker (if needed for service-to-service calls)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/run.invoker"
```

**For Logging (optional but recommended):**
```bash
# Logs Writer (for structured logging)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/logging.logWriter"
```

#### **Download Service Account Key:**
```bash
# Create and download the key
gcloud iam service-accounts keys create service-account-key.json \
  --iam-account=$SA_EMAIL

# Encode as base64 for environment variable
base64 -i service-account-key.json | tr -d '\n'
```

### 3. Google Drive Setup

#### **Create Base Folder:**
1. **Create a folder** in Google Drive called "Webhook Reports"
2. **Get the folder ID** from the URL: `https://drive.google.com/drive/folders/FOLDER_ID`
3. **Share the folder** with your service account email (with Editor permissions)

#### **For Shared Drives (Optional):**
1. **Create a shared drive** in Google Drive
2. **Add the service account** as a member with Editor role
3. **Get the shared drive ID** from the URL

### 4. Storage Bucket Setup

```bash
# Create GCS bucket
gsutil mb gs://your-bucket-name

```

## Configuration

### Environment Variables

#### Required Variables
```bash
# LearnWorlds Configuration
CLIENT_ID=your_client_id
SCHOOL_DOMAIN=your_school_domain
ACCESS_TOKEN=your_access_token
LEARNWORLDS_WEBHOOK_SECRET=your_webhook_secret

# Email Configuration
EMAIL_FROM=your_email@gmail.com
EMAIL_PASS=your_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Storage Configuration
STORAGE_BACKEND=local  # or 'gcp' for production
```

#### Optional Variables
```bash
# Admin Error Notifications
ADMIN_EMAIL=admin@example.com

# Google Cloud Storage (for production)
GCP_PROJECT_ID=your_project_id
GCP_BUCKET_NAME=your_bucket_name

# Google Drive Storage (for GCP backend)
GOOGLE_DRIVE_FOLDER_ID=your_base_folder_id
GOOGLE_SHARED_DRIVE_ID=your_shared_drive_id  # Optional - for shared drives
GOOGLE_SERVICE_ACCOUNT_KEY=base64_encoded_service_account_key
```

**Note:** Shared drive support is limited. The service will work with personal Google Drive folders. For shared drives, ensure the service account has proper permissions.

## Data Storage

The service uses a storage abstraction layer that supports both local filesystem and Google Cloud Storage (GCS):

- **Local Development**: Files stored in local `data/` directory
- **Production**: Files stored in GCS bucket specified by `GCP_BUCKET_NAME`

### Directory Structure
```
data/
├── webhook_reports/
│   ├── processed.csv                    # Processing tracking
│   └── <student_id>_<assessment>.pdf   # Generated PDFs
├── responses/
│   └── questions/                      # CSV question banks
│       ├── Test de diagnóstico 1.csv
│       ├── Test de diagnóstico 2.csv
│       ├── Test de diagnóstico 3.csv
│       └── Test de diagnóstico 4.csv
└── templates/
    └── plantilla_test_diagnostico.docx  # Word template
```

### Processed Records Tracking

The service tracks processed assessments in `data/webhook_reports/processed.csv` with the following columns:
- `user_id`: LearnWorlds user ID
- `assessment_title`: Name of the assessment
- `user_email`: User's email address
- `processed_at`: Timestamp when the report was generated and sent

## Google Drive PDF Storage

The webhook service can save generated PDF reports to Google Drive for persistent storage and easy access.

### Features
- **Automatic folder creation** based on assessment title
- **File deduplication** - updates existing files instead of creating duplicates
- **Shared drive support** for team collaboration
- **Backend-aware storage** - only uses Google Drive when STORAGE_BACKEND=gcp

### Storage Behavior
- **Local Backend**: PDFs are saved locally in `data/webhook_reports/{assessment_title}/`
- **GCP Backend**: PDFs are uploaded to Google Drive in organized folders

### Folder Structure
```
Base Folder (GOOGLE_DRIVE_FOLDER_ID)
└── webhook_reports/
    ├── Assessment Title 1/
    │   ├── informe_username_userid_assessment1.pdf
    │   └── informe_username_userid_assessment1.pdf
    └── Assessment Title 2/
        └── informe_username_userid_assessment2.pdf
```

### Filename Handling
- **Google Drive**: Uses `informe_{username}_{user_id}_{assessment_title}.pdf` for uniqueness
- **Email Attachment**: Uses `informe_{username}_{assessment_title}.pdf` for student-friendly naming
- **No Overwrites**: Multiple users with same name won't overwrite each other's files

### Setup Instructions
1. Create a Google Cloud project
2. Enable Google Drive API
3. Create a service account with Drive permissions
4. Download the service account key and encode it as base64
5. Set the environment variables above
6. Share the base folder with the service account email

## Admin Error Notifications

The service can send error notifications to administrators when critical failures occur.

### Features
- **Automatic notifications** for processing failures
- **Email-based alerts** to specified admin email
- **Detailed error messages** with context information
- **Non-blocking** - doesn't prevent email delivery to students

### Configuration
Set the `ADMIN_EMAIL` environment variable to enable notifications:
```bash
ADMIN_EMAIL=admin@example.com
```

### Error Types Covered
- Webhook processing failures
- API request failures
- Missing question banks
- Email delivery failures
- PDF generation errors

## Email Delivery Solutions

### Gmail Limitations

**Free Gmail Account:**
- 500 emails/day limit
- 100 emails/hour limit
- Requires app password setup

**Gmail Workspace (Paid):**
- 2000 emails/day limit
- 500 emails/hour limit
- Better for production use

### Alternative Email Providers

#### **1. SendGrid (Recommended)**
```bash
# Environment variables for SendGrid
EMAIL_FROM=your-verified-sender@yourdomain.com
EMAIL_PASS=your_sendgrid_api_key
SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587
```

**Benefits:**
- 100 emails/day free tier
- 40,000 emails/day on paid plans ($15/month)
- Excellent deliverability
- Detailed analytics

#### **2. Mailgun**
```bash
# Environment variables for Mailgun
EMAIL_FROM=your-verified-sender@yourdomain.com
EMAIL_PASS=your_mailgun_api_key
SMTP_SERVER=smtp.mailgun.org
SMTP_PORT=587
```

**Benefits:**
- 5,000 emails/month free tier
- 50,000 emails/month on paid plans ($35/month)
- Great for high volume

#### **3. Amazon SES**
```bash
# Environment variables for Amazon SES
EMAIL_FROM=your-verified-sender@yourdomain.com
EMAIL_PASS=your_ses_smtp_password
SMTP_SERVER=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
```

**Benefits:**
- 62,000 emails/month free tier
- Very cost-effective for high volume
- Excellent deliverability

### Implementation Options

#### **Option 1: Upgrade to Gmail Workspace**
```bash
# Cost: ~$6/month per user
# Benefits: 2000 emails/day, professional domain
```

#### **Option 2: Switch to SendGrid**
1. **Sign up**: [sendgrid.com](https://sendgrid.com)
2. **Verify sender**: Add your domain/email
3. **Get API key**: Generate SMTP credentials
4. **Update environment**:
   ```bash
   EMAIL_FROM=your-verified-sender@yourdomain.com
   EMAIL_PASS=your_sendgrid_api_key
   SMTP_SERVER=smtp.sendgrid.net
   SMTP_PORT=587
   ```

#### **Option 3: Hybrid Approach**
- Use Gmail for development/testing
- Use SendGrid for production
- Switch based on environment variable

### Cost Comparison

| Provider | Free Tier | Paid Tier | Cost/Month |
|----------|-----------|-----------|------------|
| Gmail Free | 500/day | N/A | $0 |
| Gmail Workspace | 2000/day | 2000/day | $6 |
| SendGrid | 100/day | 40,000/day | $15 |
| Mailgun | 5,000/month | 50,000/month | $35 |
| Amazon SES | 62,000/month | 62,000/month | $0.10/1000 |

### Recommendation

**For your use case (2000+ students/week):**

1. **Immediate**: Upgrade to Gmail Workspace ($6/month)
2. **Long-term**: Switch to SendGrid ($15/month)
3. **High volume**: Consider Amazon SES (very cost-effective)

### Implementation Steps

#### **Quick Fix - Gmail Workspace:**
1. Sign up for Google Workspace
2. Update environment variables (same as current)
3. No code changes needed

#### **Production Ready - SendGrid:**
1. Create SendGrid account
2. Verify your sender email/domain
3. Generate API key
4. Update environment variables
5. Test with small batch

### Monitoring Email Delivery

Add email delivery monitoring to your admin notifications:

```python
# In email_sender.py - add delivery tracking
def send_report_email(self, recipient_email: str, pdf_content: bytes, username: str, assessment_title: str, filename: str = None) -> bool:
    try:
        # ... existing code ...
        
        # Log successful delivery
        logger.info(f"Email sent successfully to {recipient_email}")
        return True
        
    except Exception as e:
        # Log failed delivery
        logger.error(f"Failed to send email to {recipient_email}: {e}")
        
        # Notify admin of delivery failure
        if self.admin_email:
            self.send_error_notification(f"Email delivery failed to {recipient_email}: {e}")
        
        return False
```

## GCP Deployment

### Prerequisites
1. **Google Cloud Project** with billing enabled
2. **Google Cloud SDK** installed and authenticated
3. **Required APIs enabled**:
   ```bash
   gcloud services enable run.googleapis.com
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable storage.googleapis.com
   ```

### 1. Build and Push Docker Image
```bash
# Set your project ID
export PROJECT_ID=your_project_id

# Build webhook service image with Docker
docker build -f Dockerfile.webhook -t gcr.io/$PROJECT_ID/data-analysis-webhook:latest .

# Push to Google Container Registry with Docker
docker push gcr.io/$PROJECT_ID/data-analysis-webhook:latest

# Alternatively, build and push using gcloud (Cloud Build)
gcloud builds submit --tag gcr.io/$PROJECT_ID/data-analysis-webhook:latest
```

### 2. Deploy to Cloud Run
```bash
# Deploy webhook service
gcloud run deploy data-analysis-webhook \
  --image gcr.io/$PROJECT_ID/data-analysis-webhook:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --set-env-vars STORAGE_BACKEND=gcp
```

### 3. Set Environment Variables
```bash
# Set environment variables for the webhook service
gcloud run services update data-analysis-webhook \
  --region us-central1 \
  --set-env-vars \
    CLIENT_ID=your_client_id,\
    SCHOOL_DOMAIN=your_school_domain,\
    ACCESS_TOKEN=your_access_token,\
    LEARNWORLDS_WEBHOOK_SECRET=your_webhook_secret,\
    EMAIL_FROM=your_email@gmail.com,\
    EMAIL_PASS=your_app_password,\
    SMTP_SERVER=smtp.gmail.com,\
    SMTP_PORT=587,\
    GCP_PROJECT_ID=your_project_id,\
    GCP_BUCKET_NAME=your_bucket_name,\
    GOOGLE_SERVICE_ACCOUNT_KEY=your_base64_encoded_key
```

### 4. Get Webhook URL
```bash
# Get the webhook URL
gcloud run services describe data-analysis-webhook \
  --region us-central1 \
  --format="value(status.url)"
```

## LearnWorlds Webhook Configuration

### Webhook URL
Set the webhook URL in your LearnWorlds admin panel:
```
https://your-cloud-run-url/webhook
```

### Supported Events
- Assessment completion events
- Student submission events

### Security
The service validates webhook signatures using HMAC-SHA256 to ensure authenticity.

## API Endpoints

### POST /webhook
Processes LearnWorlds webhook events.

**Request Body:**
```json
{
  "event": "assessment.completed",
  "user_id": "12345",
  "assessment_id": "67890",
  "timestamp": 1640995200
}
```

**Response:**
```json
{
  "success": true,
  "message": "Report generated and sent successfully",
  "user_id": "12345",
  "assessment_title": "Test de diagnóstico Parte 1"
}
```

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-28T22:00:00Z"
}
```

## Performance and Concurrency

### High-Volume Handling

The service is designed to handle concurrent webhook processing efficiently:

#### **Concurrency Features:**
- **Auto-scaling**: Cloud Run scales to 10 concurrent instances
- **Duplicate Prevention**: Atomic operations prevent duplicate processing
- **Race Condition Protection**: Retry logic for CSV file updates
- **Unique File Handling**: UUID-based temporary files prevent conflicts

#### **Performance Limits:**
- **Concurrent Requests**: Up to 10 simultaneous webhook processes
- **Processing Time**: ~30-60 seconds per assessment (PDF generation + email)
- **Memory Usage**: 2GB per instance (sufficient for PDF generation)
- **Timeout**: 300 seconds per request

#### **Resource Considerations:**
- **Google Drive API**: 1000 requests/minute quota
- **Gmail SMTP**: 500 emails/day (free tier), 2000/day (paid)
- **GCS Operations**: No practical limits for this use case

### Monitoring High Volume

For handling 20+ concurrent assessments:

1. **Monitor Cloud Run Metrics**:
   ```bash
   gcloud run services describe data-analysis-webhook --region us-central1
   ```

2. **Check Logs for Errors**:
   ```bash
   gcloud run services logs read data-analysis-webhook --region us-central1
   ```

3. **Scale Up if Needed**:
   ```bash
   gcloud run services update data-analysis-webhook \
     --region us-central1 \
     --max-instances 20 \
     --memory 4Gi \
     --cpu 2
   ```

### Error Handling

The service includes robust error handling for concurrent scenarios:

- **Retry Logic**: 3 attempts for CSV file operations
- **Exponential Backoff**: Prevents thundering herd problems
- **Graceful Degradation**: Failed operations don't block others
- **Admin Notifications**: Critical errors are reported immediately

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
   ```bash
   pip install -r requirements.txt
   ```

2. **Email Delivery Failures**: Check SMTP configuration and app passwords

3. **Google Drive Upload Failures**: Verify service account permissions and folder sharing

4. **PDF Generation Errors**: Ensure Word template exists and is accessible

5. **Webhook Signature Validation**: Verify the webhook secret is correct

6. **Service Account Permission Errors**: Ensure all required IAM roles are assigned

### Service Account Permission Troubleshooting

**Common Permission Errors:**

1. **"Access Denied" for GCS operations:**
   ```bash
   # Ensure Storage Object Admin role is assigned
   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:$SA_EMAIL" \
     --role="roles/storage.objectAdmin"
   ```

2. **"Drive API not enabled" errors:**
   ```bash
   # Enable Drive API
   gcloud services enable drive.googleapis.com
   ```

3. **"Service account key invalid" errors:**
   ```bash
   # Regenerate service account key
   gcloud iam service-accounts keys create service-account-key.json \
     --iam-account=$SA_EMAIL
   
   # Re-encode as base64
   base64 -i service-account-key.json | tr -d '\n'
   ```

**Verify Permissions:**
```bash
# Check current IAM bindings for service account
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --format="table(bindings.role)" \
  --filter="bindings.members:$SA_EMAIL"
```

### Logs
The service provides detailed logging for debugging:
- Webhook processing events
- PDF generation status
- Email delivery confirmations
- Error notifications

### Support
For issues or questions, check the logs and verify your configuration matches the requirements above. 