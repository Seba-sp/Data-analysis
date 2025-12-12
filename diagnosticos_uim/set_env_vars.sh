#!/bin/bash
# Script to set environment variables for Cloud Functions

# Configuration
PROJECT_ID="your-project-id"
REGION="us-central1"

echo "🔧 Setting environment variables for Cloud Functions..."

# Set environment variables for webhook-handler function
gcloud functions deploy webhook-handler \
  --project=$PROJECT_ID \
  --region=$REGION \
  --runtime=python39 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point=webhook_handler \
  --source=. \
  --memory=512MB \
  --timeout=540s \
  --set-env-vars="BATCH_INTERVAL_MINUTES=15,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,TASK_LOCATION=$REGION,TASK_QUEUE_ID=batch-processing-queue,PROCESS_BATCH_URL=https://$REGION-$PROJECT_ID.cloudfunctions.net/webhook-handler,LEARNWORLDS_WEBHOOK_SECRET=your_webhook_secret,M1_ASSESSMENT_ID=your_m1_assessment_id,CL_ASSESSMENT_ID=your_cl_assessment_id,CIEN_ASSESSMENT_ID=your_cien_assessment_id,HYST_ASSESSMENT_ID=your_hyst_assessment_id,CLIENT_ID=your_learnworlds_client_id,SCHOOL_DOMAIN=your_school.learnworlds.com,ACCESS_TOKEN=your_learnworlds_access_token,EMAIL_FROM=your-email@gmail.com,EMAIL_PASS=your-app-password"

echo "✅ Environment variables set for webhook-handler"

# Set environment variables for status-handler function
gcloud functions deploy status-handler \
  --project=$PROJECT_ID \
  --region=$REGION \
  --runtime=python39 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point=status_handler \
  --source=. \
  --memory=256MB \
  --timeout=60s \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID,TASK_LOCATION=$REGION,TASK_QUEUE_ID=batch-processing-queue"

echo "✅ Environment variables set for status-handler"

# Set environment variables for cleanup-handler function
gcloud functions deploy cleanup-handler \
  --project=$PROJECT_ID \
  --region=$REGION \
  --runtime=python39 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point=cleanup_handler \
  --source=. \
  --memory=256MB \
  --timeout=60s \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID,TASK_LOCATION=$REGION,TASK_QUEUE_ID=batch-processing-queue"

echo "✅ Environment variables set for cleanup-handler"

echo "🎉 All environment variables configured!"
echo ""
echo "📋 Next steps:"
echo "1. Update the values in this script with your actual credentials"
echo "2. Run: ./set_env_vars.sh"
echo "3. Test your webhook system"
