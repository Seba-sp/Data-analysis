#!/bin/bash

# Deployment script for Cloud Functions webhook service

set -e

echo "🚀 Deploying Cloud Functions..."

# Set variables
PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
FUNCTION_NAME="webhook-handler"

echo "📋 Project: $PROJECT_ID"
echo "🌍 Region: $REGION"
echo "⚡ Function: $FUNCTION_NAME"

# Create Cloud Tasks queue if it doesn't exist
echo "📋 Creating Cloud Tasks queue..."
gcloud tasks queues create batch-processing-queue \
    --location=$REGION \
    --max-dispatches-per-second=500 \
    --max-concurrent-dispatches=100 \
    --max-attempts=5 \
    --max-retry-duration=300s

# Deploy main webhook handler
echo "🚀 Deploying webhook handler..."
gcloud functions deploy webhook-handler \
    --runtime=python39 \
    --trigger-http \
    --allow-unauthenticated \
    --entry-point=webhook_handler \
    --source=. \
    --region=$REGION \
    --memory=512MB \
    --timeout=540s \
    --set-env-vars=BATCH_INTERVAL_MINUTES=15

# Deploy status handler
echo "📊 Deploying status handler..."
gcloud functions deploy status-handler \
    --runtime=python39 \
    --trigger-http \
    --allow-unauthenticated \
    --entry-point=status_handler \
    --source=. \
    --region=$REGION \
    --memory=256MB \
    --timeout=60s

# Deploy cleanup handler
echo "🧹 Deploying cleanup handler..."
gcloud functions deploy cleanup-handler \
    --runtime=python39 \
    --trigger-http \
    --allow-unauthenticated \
    --entry-point=cleanup_handler \
    --source=. \
    --region=$REGION \
    --memory=256MB \
    --timeout=60s

# Get function URLs
echo "🔗 Function URLs:"
WEBHOOK_URL=$(gcloud functions describe webhook-handler --region=$REGION --format="value(httpsTrigger.url)")
STATUS_URL=$(gcloud functions describe status-handler --region=$REGION --format="value(httpsTrigger.url)")
CLEANUP_URL=$(gcloud functions describe cleanup-handler --region=$REGION --format="value(httpsTrigger.url)")

echo "📝 Webhook URL: $WEBHOOK_URL"
echo "📊 Status URL: $STATUS_URL"
echo "🧹 Cleanup URL: $CLEANUP_URL"

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Configure LearnWorlds webhook to point to: $WEBHOOK_URL"
echo "2. Set environment variables in Cloud Functions:"
echo "   - GOOGLE_CLOUD_PROJECT=$PROJECT_ID"
echo "   - TASK_LOCATION=$REGION"
echo "   - TASK_QUEUE_ID=batch-processing-queue"
echo "   - PROCESS_BATCH_URL=$WEBHOOK_URL"
echo "   - LEARNWORLDS_WEBHOOK_SECRET=your_webhook_secret"
echo "   - M1_ASSESSMENT_ID=your_m1_assessment_id"
echo "   - CL_ASSESSMENT_ID=your_cl_assessment_id"
echo "   - CIEN_ASSESSMENT_ID=your_cien_assessment_id"
echo "   - HYST_ASSESSMENT_ID=your_hyst_assessment_id"
echo "   - CLIENT_ID=your_learnworlds_client_id"
echo "   - SCHOOL_DOMAIN=your_school_domain"
echo "   - ACCESS_TOKEN=your_learnworlds_access_token"
echo "   - EMAIL_FROM=your_email@gmail.com"
echo "   - EMAIL_PASS=your_app_password"
echo "3. Test the webhook with a sample payload"
echo "4. Monitor status at: $STATUS_URL"
