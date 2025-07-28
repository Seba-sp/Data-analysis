# Webhook Service Deployment Guide

This guide explains how to deploy the webhook service to Google Cloud Platform for handling real-time assessment completions.

## Overview

The webhook service is designed to:
- Receive webhook notifications from LearnWorlds when students complete assessments
- Generate personalized PDF reports for individual students
- Send reports via email immediately after completion
- Handle high-volume scenarios (2000+ students per week)

## Prerequisites

1. **Google Cloud Project** with billing enabled
2. **Google Cloud SDK** installed and authenticated
3. **Required APIs enabled**:
   ```sh
   gcloud services enable run.googleapis.com
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable storage.googleapis.com
   ```

## Environment Setup

### 1. Create Environment File

Copy the template and fill in your values:
```sh
cp env.template .env
```

### 2. Required Environment Variables

Add these to your `.env` file:

```bash
# LearnWorlds API (existing)
CLIENT_ID=your_client_id
SCHOOL_DOMAIN=your_school_domain
ACCESS_TOKEN=your_access_token

# Webhook Security (NEW)
LEARNWORLDS_WEBHOOK_SECRET=your_webhook_secret_from_learnworlds

# Email Configuration (NEW)
EMAIL_FROM=your_email@gmail.com
EMAIL_PASS=your_app_password_here
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Optional: Admin notifications
ADMIN_EMAIL=admin@yourdomain.com

# GCP Configuration (existing)
STORAGE_BACKEND=gcp
GCP_PROJECT_ID=your_project_id
GCP_BUCKET_NAME=your_bucket_name
GOOGLE_SERVICE_ACCOUNT_KEY=your_base64_encoded_service_account_key
```

### 3. Get LearnWorlds Webhook Secret

1. Go to your LearnWorlds platform
2. Navigate to **Settings > Developers > Webhooks**
3. Copy the webhook signature secret
4. Add it to your `.env` file as `LEARNWORLDS_WEBHOOK_SECRET`

### 4. Set Up Gmail App Password

For Gmail SMTP:
1. Enable 2-factor authentication on your Gmail account
2. Generate an App Password: **Google Account > Security > App Passwords**
3. Use the generated password as `EMAIL_PASS`

## Local Testing

### 1. Install Dependencies

```sh
pip install -r requirements.txt
```

### 2. Set Up Question Banks

Upload your question bank files to the correct location:

**For Local Testing:**
```sh
# Create directories
mkdir -p data/responses/questions

# Copy question bank files
cp "Test-diagnostico-pdf/bancos_preguntas/banco_preguntas_Test de diagnóstico Parte 2.csv" \
   "data/responses/questions/Test de diagnóstico Parte 2_questions.csv"
```

**For GCP:**
```sh
# Upload to GCS
gsutil cp "Test-diagnostico-pdf/bancos_preguntas/banco_preguntas_Test de diagnóstico Parte 2.csv" \
          "gs://YOUR_BUCKET_NAME/data/responses/questions/Test de diagnóstico Parte 2_questions.csv"
```

### 3. Test Locally

```sh
# Start webhook service
python webhook_main.py

# In another terminal, test the webhook
python test_webhook_local.py
```

## GCP Deployment

### 1. Build and Push Docker Image

```sh
# Set your project ID
export PROJECT_ID=your_project_id

# Build webhook service image
docker build -f Dockerfile.webhook -t gcr.io/$PROJECT_ID/data-analysis-webhook:latest .

# Push to Google Container Registry
docker push gcr.io/$PROJECT_ID/data-analysis-webhook:latest
```

### 2. Deploy to Cloud Run

```sh
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

```sh
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

```sh
# Get the webhook URL
gcloud run services describe data-analysis-webhook \
  --region us-central1 \
  --format="value(status.url)"
```

The webhook URL will be something like:
`https://data-analysis-webhook-xxxxx-uc.a.run.app`

## LearnWorlds Configuration

### 1. Configure Webhook in LearnWorlds

1. Go to your LearnWorlds platform
2. Navigate to **Settings > Developers > Webhooks**
3. Add a new webhook:
   - **URL**: Your Cloud Run webhook URL + `/webhook`
   - **Events**: Select "Assessment submission"
   - **Status**: Active

### 2. Test Webhook

Use the test script with your deployed URL:

```sh
# Update test_webhook_local.py with your deployed URL
WEBHOOK_URL="https://data-analysis-webhook-xxxxx-uc.a.run.app/webhook"

# Test the deployed webhook
python test_webhook_local.py
```

## Monitoring and Troubleshooting

### 1. View Logs

```sh
# View webhook service logs
gcloud run services logs read data-analysis-webhook \
  --region us-central1 \
  --limit 50
```

### 2. Check Service Status

```sh
# Check service status
gcloud run services describe data-analysis-webhook \
  --region us-central1
```

### 3. Common Issues

**Webhook Signature Validation Fails:**
- Verify `LEARNWORLDS_WEBHOOK_SECRET` is correct
- Check that the secret in LearnWorlds matches your environment variable

**Email Sending Fails:**
- Verify Gmail app password is correct
- Check that 2FA is enabled on Gmail account
- Verify `EMAIL_FROM` and `EMAIL_PASS` are set correctly

**Question Bank Not Found:**
- Ensure question bank files are uploaded to the correct GCS path
- Verify file naming convention: `{assessment_title}_questions.csv`

**API Authentication Fails:**
- Verify LearnWorlds API credentials are correct
- Check that `CLIENT_ID`, `SCHOOL_DOMAIN`, and `ACCESS_TOKEN` are set

## Scaling Considerations

### High Volume Scenarios

For handling 2000+ students per week:

1. **Increase Resources:**
   ```sh
   gcloud run services update data-analysis-webhook \
     --region us-central1 \
     --memory 4Gi \
     --cpu 2 \
     --max-instances 20
   ```

2. **Monitor Performance:**
   - Use Cloud Monitoring to track response times
   - Set up alerts for high error rates
   - Monitor memory and CPU usage

3. **Error Handling:**
   - Failed webhooks are logged but not retried automatically
   - Consider implementing a dead letter queue for failed processing
   - Set up admin notifications for critical errors

## Security Best Practices

1. **Webhook Security:**
   - Always validate webhook signatures
   - Use HTTPS endpoints (Cloud Run provides this automatically)
   - Consider IP whitelisting if LearnWorlds supports it

2. **Email Security:**
   - Use app passwords instead of regular passwords
   - Enable 2FA on email accounts
   - Consider using GCP SendGrid for production

3. **Data Security:**
   - Store sensitive data in environment variables
   - Use service account keys with minimal required permissions
   - Enable audit logging for GCS access

## Cost Optimization

### Estimated Costs (US Central)

- **Cloud Run**: ~$0.40 per million requests
- **Container Registry**: ~$0.026 per GB per month
- **Cloud Storage**: ~$0.02 per GB per month

For 2000 students per week:
- **Monthly cost**: ~$5-10 USD

### Cost Optimization Tips

1. **Set Max Instances:**
   ```sh
   gcloud run services update data-analysis-webhook \
     --region us-central1 \
     --max-instances 10
   ```

2. **Use Cold Storage:**
   - Move old reports to cold storage after 30 days
   - Implement lifecycle policies for GCS

3. **Monitor Usage:**
   - Set up billing alerts
   - Monitor request volume and adjust resources accordingly 