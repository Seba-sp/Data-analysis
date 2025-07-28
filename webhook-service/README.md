# Webhook Service

## Overview

The Webhook Service provides real-time processing of individual student assessment completions with immediate email delivery. When a student completes a diagnostic assessment, the service automatically analyzes their performance and sends a personalized report via email.


## Quick Start

```bash
# Run locally
python webhook_main.py

# Test webhook functionality
python test_webhook_local.py
```

## Features

- **Real-time processing**: Instant analysis when students complete assessments
- **Email delivery**: Automatic personalized report delivery
- **Word template support**: Uses Word templates for professional report formatting
- **Individual analysis**: Per-student performance analysis
- **GCS integration**: Works with Google Cloud Storage for scalability
- **Health monitoring**: Built-in health check endpoints

## Architecture

### Flow Diagram
```
LearnWorlds Platform → Webhook → Flask Service → Analysis → Email Delivery
```

### Components
- **`webhook_main.py`**: Flask application entry point
- **`webhook_service.py`**: Core webhook processing logic
- **`assessment_analyzer.py`**: Individual student assessment analysis
- **`report_generator.py`**: PDF report generation using Word templates
- **`email_sender.py`**: Email delivery for individual reports

## Local Development

### Running Locally
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export STORAGE_BACKEND=local
export CLIENT_ID=your_client_id
# ... other variables

# Run service
python webhook_main.py
```

### Testing
```bash
# Test webhook functionality
python test_webhook_local.py

# Test with sample data
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d @test_data.json
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

# Email configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# Webhook security
WEBHOOK_SECRET=your_webhook_secret
```

### LearnWorlds Webhook Configuration
1. **Webhook URL**: `https://webhook-service-xxxxx-uc.a.run.app/webhook`
2. **Events**: Assessment completion events
3. **Secret**: Match the `WEBHOOK_SECRET` environment variable

## API Endpoints

### Webhook Endpoint
```
POST /webhook
```
- **Purpose**: Receives assessment completion events from LearnWorlds
- **Authentication**: Webhook signature validation
- **Response**: JSON with processing status

### Health Check
```
GET /healthz
```
- **Purpose**: Health monitoring endpoint
- **Response**: `{"status": "ok"}`

### Root Endpoint
```
GET /
```
- **Purpose**: Service information
- **Response**: Service details and available endpoints

## Data Structure

```
data/webhook_reports/
├── <course>/
│   ├── <student_id>_<assessment>_<timestamp>.pdf
│   └── processed.csv                    # Processing tracking
└── templates/
    └── plantilla_test_diagnostico.docx  # Word template
```

## Report Generation

### Word Template
- **Location**: `templates/plantilla_test_diagnostico.docx`
- **Format**: Microsoft Word document with placeholders
- **Placeholders**: Student name, score, answers, etc.

### PDF Output
- **Format**: Professional PDF report
- **Content**: Individual student performance analysis
- **Delivery**: Email attachment

## GCP Deployment

### Cloud Run Service Deployment
```bash
# Build and push image
docker build -t gcr.io/PROJECT_ID/webhook-service:latest .
docker push gcr.io/PROJECT_ID/webhook-service:latest

# Deploy Cloud Run Service
gcloud run deploy webhook-service \
  --image gcr.io/PROJECT_ID/webhook-service:latest \
  --region us-central1 \
  --memory 1Gi \
  --cpu 1 \
  --port 8080 \
  --allow-unauthenticated \
  --max-instances 10
```

### Environment Variables
```bash
# Set environment variables
gcloud run services update webhook-service \
  --region us-central1 \
  --set-env-vars STORAGE_BACKEND=gcp,GCP_PROJECT_ID=YOUR_PROJECT_ID,GCP_BUCKET_NAME=YOUR_BUCKET_NAME
```

## Monitoring and Logging

### Cloud Run Logs
```bash
# View service logs
gcloud run services logs read webhook-service --region us-central1

# Follow logs in real-time
gcloud run services logs tail webhook-service --region us-central1
```

### Health Monitoring
```bash
# Check service health
curl https://webhook-service-xxxxx-uc.a.run.app/healthz

# Get service info
curl https://webhook-service-xxxxx-uc.a.run.app/
```

## Troubleshooting

### Common Issues

**1. Webhook Not Receiving Events**
```bash
# Check service is running
gcloud run services describe webhook-service --region us-central1

# Verify LearnWorlds webhook configuration
# Check webhook URL and secret match
```

**2. Email Delivery Failures**
```bash
# Check email configuration
echo $EMAIL_USER
echo $EMAIL_PASSWORD

# Test email sending
python email_sender.py --test
```

**3. Template Processing Errors**
```bash
# Check template file exists
ls templates/plantilla_test_diagnostico.docx

# Verify template format
python report_generator.py --validate-template
```

**4. Storage Access Issues**
```bash
# Check GCS bucket access
gsutil ls gs://YOUR_BUCKET_NAME/

# Verify service account permissions
gcloud projects get-iam-policy YOUR_PROJECT_ID
```

### Debug Mode
```bash
# Enable debug logging
export DEBUG=true
python webhook_main.py
```

## Security

### Webhook Authentication
- **Signature validation**: Verifies webhook authenticity
- **Secret matching**: Ensures requests come from LearnWorlds
- **Rate limiting**: Prevents abuse

### Email Security
- **SMTP authentication**: Secure email delivery
- **App passwords**: Use Gmail app passwords, not regular passwords
- **TLS encryption**: Secure email transmission

## Cost Optimization

- **Memory**: 1Gi is usually sufficient
- **CPU**: 1 vCPU for most workloads
- **Instances**: 0-10 instances (auto-scaling)
- **Requests**: ~$0.12/month for 1000 requests

## Integration

### LearnWorlds Platform
- **Webhook URL**: Configure in LearnWorlds admin panel
- **Event Types**: Assessment completion events
- **Authentication**: Webhook secret validation

### Email Providers
- **Gmail**: Recommended for SMTP
- **SendGrid**: Alternative for high volume
- **Custom SMTP**: Any SMTP server

### Storage Backends
- **Local**: Files stored on local filesystem
- **GCS**: Files stored in Google Cloud Storage bucket
- **Hybrid**: Local processing with GCS storage

## Best Practices

### Webhook Configuration
1. **HTTPS only**: Always use HTTPS for webhook URLs
2. **Secret rotation**: Regularly update webhook secrets
3. **Error handling**: Implement proper error responses
4. **Idempotency**: Handle duplicate webhook events

### Email Delivery
1. **Template testing**: Test templates with various data
2. **Email validation**: Verify email addresses before sending
3. **Retry logic**: Implement retry for failed deliveries
4. **Monitoring**: Track email delivery success rates

### Performance
1. **Async processing**: Process webhooks asynchronously
2. **Resource limits**: Set appropriate memory and CPU limits
3. **Auto-scaling**: Configure auto-scaling based on load
4. **Caching**: Cache frequently accessed data

## Development Workflow

### 1. Local Development
```bash
# Clone and setup
git clone <repository>
cd webhook-service
pip install -r requirements.txt

# Configure environment
cp ../shared/env.template .env
# Edit .env with your credentials

# Run locally
python webhook_main.py
```

### 2. Testing
```bash
# Test webhook functionality
python test_webhook_local.py

# Test with sample data
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d @test_data.json
```

### 3. Deployment
```bash
# Build and deploy
docker build -t gcr.io/PROJECT_ID/webhook-service:latest .
docker push gcr.io/PROJECT_ID/webhook-service:latest
gcloud run deploy webhook-service --image gcr.io/PROJECT_ID/webhook-service:latest
```

### 4. Configuration
```bash
# Set environment variables
gcloud run services update webhook-service --set-env-vars KEY=value

# Configure LearnWorlds webhook
# Use the service URL in LearnWorlds admin panel
```

## Monitoring and Alerts

### Cloud Monitoring
```bash
# Set up monitoring
gcloud monitoring dashboards create --config=dashboard.json

# Create alerts
gcloud alpha monitoring policies create --policy-from-file=alert-policy.yaml
```

### Log Analysis
```bash
# Search logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=webhook-service"

# Export logs
gcloud logging export logs-bucket gs://YOUR_BUCKET_NAME/logs 