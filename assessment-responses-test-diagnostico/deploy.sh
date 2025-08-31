#!/bin/bash

# Cloud Run deployment script for multi-assessment processor
# This script builds and deploys the application to Google Cloud Run

set -e

# Configuration
PROJECT_ID=${PROJECT_ID:-"your-project-id"}
REGION=${REGION:-"us-central1"}
SERVICE_NAME=${SERVICE_NAME:-"multi-assessment-processor"}
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting deployment of Multi-Assessment Processor to Cloud Run${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install it first.${NC}"
    exit 1
fi

# Set project
echo -e "${YELLOW}📋 Setting project to ${PROJECT_ID}${NC}"
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo -e "${YELLOW}🔧 Enabling required APIs${NC}"
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable storage.googleapis.com

# Build and push Docker image
echo -e "${YELLOW}🐳 Building and pushing Docker image${NC}"
docker build -t ${IMAGE_NAME}:latest .
docker push ${IMAGE_NAME}:latest

# Deploy to Cloud Run
echo -e "${YELLOW}🚀 Deploying to Cloud Run${NC}"
gcloud run jobs create ${SERVICE_NAME} \
    --image ${IMAGE_NAME}:latest \
    --region ${REGION} \
    --memory 2Gi \
    --cpu 1 \
    --timeout 1800 \
    --max-retries 3 \
    --task-timeout 1800 \
    --set-env-vars "STORAGE_BACKEND=gcp" \
    --set-env-vars "GCP_PROJECT_ID=${PROJECT_ID}" \
    --set-env-vars "GCP_BUCKET_NAME=${GCP_BUCKET_NAME}" \
    --set-env-vars "CLIENT_ID=${CLIENT_ID}" \
    --set-env-vars "SCHOOL_DOMAIN=${SCHOOL_DOMAIN}" \
    --set-env-vars "ACCESS_TOKEN=${ACCESS_TOKEN}" \
    --set-env-vars "GOOGLE_DRIVE_FOLDER_ID=${GOOGLE_DRIVE_FOLDER_ID}" \
    --set-env-vars "GOOGLE_SERVICE_ACCOUNT_KEY=${GOOGLE_SERVICE_ACCOUNT_KEY}" \
    --set-env-vars "SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}" \
    --set-env-vars "SLACK_CHANNEL=${SLACK_CHANNEL}" \
    --set-env-vars "REPORT_TOP_PERCENT=20" \
    || echo -e "${YELLOW}⚠️  Job might already exist, updating...${NC}"

# Update existing job if it already exists
gcloud run jobs update ${SERVICE_NAME} \
    --image ${IMAGE_NAME}:latest \
    --region ${REGION} \
    --memory 2Gi \
    --cpu 1 \
    --timeout 1800 \
    --max-retries 3 \
    --task-timeout 1800 \
    --set-env-vars "STORAGE_BACKEND=gcp" \
    --set-env-vars "GCP_PROJECT_ID=${PROJECT_ID}" \
    --set-env-vars "GCP_BUCKET_NAME=${GCP_BUCKET_NAME}" \
    --set-env-vars "CLIENT_ID=${CLIENT_ID}" \
    --set-env-vars "SCHOOL_DOMAIN=${SCHOOL_DOMAIN}" \
    --set-env-vars "ACCESS_TOKEN=${ACCESS_TOKEN}" \
    --set-env-vars "GOOGLE_DRIVE_FOLDER_ID=${GOOGLE_DRIVE_FOLDER_ID}" \
    --set-env-vars "GOOGLE_SERVICE_ACCOUNT_KEY=${GOOGLE_SERVICE_ACCOUNT_KEY}" \
    --set-env-vars "SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}" \
    --set-env-vars "SLACK_CHANNEL=${SLACK_CHANNEL}" \
    --set-env-vars "REPORT_TOP_PERCENT=20"

echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${GREEN}📊 Job URL: https://console.cloud.google.com/run/jobs/${SERVICE_NAME}?project=${PROJECT_ID}&region=${REGION}${NC}"

# Create Cloud Scheduler job for twice daily execution
echo -e "${YELLOW}⏰ Creating Cloud Scheduler job for twice daily execution${NC}"

# Create service account for scheduler if it doesn't exist
SERVICE_ACCOUNT_EMAIL="${SERVICE_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
gcloud iam service-accounts create ${SERVICE_NAME} \
    --display-name="Multi-Assessment Processor Service Account" \
    --description="Service account for running multi-assessment processor" \
    || echo -e "${YELLOW}⚠️  Service account might already exist${NC}"

# Grant necessary permissions
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/run.invoker"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/storage.objectViewer"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/storage.objectCreator"

# Create scheduler job for 9 AM execution
gcloud scheduler jobs create http ${SERVICE_NAME}-morning \
    --schedule="0 9 * * *" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${SERVICE_NAME}:run" \
    --http-method=POST \
    --oauth-service-account-email=${SERVICE_ACCOUNT_EMAIL} \
    --location=${REGION} \
    || echo -e "${YELLOW}⚠️  Morning scheduler job might already exist${NC}"

# Create scheduler job for 6 PM execution
gcloud scheduler jobs create http ${SERVICE_NAME}-evening \
    --schedule="0 18 * * *" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${SERVICE_NAME}:run" \
    --http-method=POST \
    --oauth-service-account-email=${SERVICE_ACCOUNT_EMAIL} \
    --location=${REGION} \
    || echo -e "${YELLOW}⚠️  Evening scheduler job might already exist${NC}"

echo -e "${GREEN}✅ Cloud Scheduler jobs created successfully!${NC}"
echo -e "${GREEN}⏰ Jobs will run at 9:00 AM and 6:00 PM daily${NC}"
echo -e "${GREEN}📅 Scheduler URL: https://console.cloud.google.com/cloudscheduler?project=${PROJECT_ID}${NC}"

echo -e "${GREEN}🎉 Deployment and scheduling completed!${NC}"
echo -e "${YELLOW}📝 Don't forget to:${NC}"
echo -e "${YELLOW}   1. Update the assessment IDs in assessments_config.yml${NC}"
echo -e "${YELLOW}   2. Set up your question files in the questions directory${NC}"
echo -e "${YELLOW}   3. Test the job manually first: gcloud run jobs execute ${SERVICE_NAME} --region ${REGION}${NC}"
