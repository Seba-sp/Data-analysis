#!/bin/bash

# Google Cloud Platform Deployment Script
# This script sets up the complete infrastructure for the course analysis pipeline

set -e

# Configuration
PROJECT_ID="${PROJECT_ID:-your-project-id}"
REGION="${REGION:-us-central1}"
FUNCTION_NAME="course-analysis-pipeline"
BUCKET_NAME="${BUCKET_NAME:-course-analysis-data-$(date +%s)}"
SCHEDULER_NAME="daily-course-analysis"
SERVICE_ACCOUNT_NAME="course-analysis-function"

echo "🚀 Starting Google Cloud Platform deployment..."
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Function Name: $FUNCTION_NAME"
echo "Bucket Name: $BUCKET_NAME"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI is not installed. Please install it first:"
    echo "https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Set project
echo "📋 Setting project..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable drive.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable iam.googleapis.com

# Create Cloud Storage bucket
echo "🪣 Creating Cloud Storage bucket..."
gsutil mb -l $REGION gs://$BUCKET_NAME

# Create service account for the function
echo "👤 Creating service account..."
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
    --display-name="Course Analysis Function Service Account" \
    --description="Service account for course analysis Cloud Function"

# Grant necessary permissions to service account
echo "🔐 Granting permissions to service account..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectViewer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectCreator"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/drive.file"

# Create service account key (for Google Drive API)
echo "🔑 Creating service account key..."
gcloud iam service-accounts keys create service-account-key.json \
    --iam-account=$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com

# Deploy Cloud Function
echo "⚡ Deploying Cloud Function..."
cd cloud_function

# Set environment variables
export GOOGLE_SERVICE_ACCOUNT_KEY=$(cat ../service-account-key.json)

gcloud functions deploy $FUNCTION_NAME \
    --runtime python39 \
    --trigger-http \
    --allow-unauthenticated \
    --service-account=$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com \
    --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,GCP_BUCKET_NAME=$BUCKET_NAME" \
    --memory 2GB \
    --timeout 540s \
    --region $REGION

cd ..

# Get function URL
FUNCTION_URL=$(gcloud functions describe $FUNCTION_NAME --region=$REGION --format="value(httpsTrigger.url)")

# Create Cloud Scheduler job (8am Santiago time = 12pm UTC)
echo "⏰ Creating Cloud Scheduler job..."
gcloud scheduler jobs create http $SCHEDULER_NAME \
    --schedule="0 12 * * *" \
    --uri="$FUNCTION_URL" \
    --http-method=POST \
    --location=$REGION \
    --description="Daily course analysis pipeline at 8am Santiago time"

echo "✅ Deployment completed successfully!"
echo ""
echo "📋 Summary:"
echo "  - Cloud Function: $FUNCTION_NAME"
echo "  - Function URL: $FUNCTION_URL"
echo "  - Cloud Storage Bucket: gs://$BUCKET_NAME"
echo "  - Cloud Scheduler: $SCHEDULER_NAME (runs daily at 8am Santiago time)"
echo "  - Service Account: $SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com"
echo ""
echo "🔧 Next steps:"
echo "  1. Set up environment variables in the Cloud Function:"
echo "     - SLACK_BOT_TOKEN"
echo "     - SLACK_CHANNEL"
echo "     - GOOGLE_DRIVE_FOLDER_ID"
echo "     - CLIENT_ID"
echo "     - SCHOOL_DOMAIN"
echo "     - ACCESS_TOKEN"
echo "     - IGNORED_USERS"
echo "     - GOOGLE_SERVICE_ACCOUNT_KEY"
echo "  2. Share the Google Drive folder with the service account email"
echo "  3. Test the function manually"
echo "  4. Monitor the scheduler job"
echo ""
echo "💡 Use the setup_environment.py script to configure all variables at once:"
echo "   python setup_environment.py --project-id $PROJECT_ID --slack-token 'xoxb-...' --slack-channel '#channel' --drive-folder-id 'folder-id' --client-id 'your-client-id' --school-domain 'your-domain' --access-token 'your-token' --ignored-users 'user1@email.com,user2@email.com' --service-account-key-file service-account-key.json"
echo ""
echo "📚 Documentation:"
echo "  - Cloud Function logs: gcloud functions logs read $FUNCTION_NAME --region=$REGION"
echo "  - Scheduler logs: gcloud scheduler jobs describe $SCHEDULER_NAME --location=$REGION"
echo "  - Storage bucket: gsutil ls gs://$BUCKET_NAME" 