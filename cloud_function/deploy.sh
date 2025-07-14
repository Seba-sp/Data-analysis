#!/bin/bash

# Google Cloud Functions Deployment Script
# This script deploys the course analysis pipeline to Google Cloud Functions

set -e  # Exit on any error

# Configuration
FUNCTION_NAME="course-analysis-pipeline"
REGION="us-central1"  # Change to your preferred region
RUNTIME="python39"    # Python 3.9 runtime
MEMORY="2GB"          # Memory allocation
TIMEOUT="540s"        # 9 minutes timeout (max for free tier)
ENTRY_POINT="course_analysis_pipeline"
TRIGGER_TYPE="http"   # HTTP trigger

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Deploying Google Cloud Function: ${FUNCTION_NAME}${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ Google Cloud SDK is not installed. Please install it first.${NC}"
    echo "Visit: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${YELLOW}⚠️  You are not authenticated with Google Cloud.${NC}"
    echo "Please run: gcloud auth login"
    exit 1
fi

# Check if project is set
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}❌ No Google Cloud project is set.${NC}"
    echo "Please set your project: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo -e "${GREEN}✅ Using project: ${PROJECT_ID}${NC}"

# Check if env.yaml exists
if [ ! -f "env.yaml" ]; then
    echo -e "${RED}❌ env.yaml file not found. Please create it with your environment variables.${NC}"
    echo "Copy env.yaml.example to env.yaml and fill in your values."
    exit 1
fi

# Enable required APIs
echo -e "${YELLOW}📋 Enabling required Google Cloud APIs...${NC}"
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable drive.googleapis.com

# Deploy the function
echo -e "${YELLOW}📦 Deploying function...${NC}"
gcloud functions deploy ${FUNCTION_NAME} \
    --runtime=${RUNTIME} \
    --region=${REGION} \
    --source=. \
    --entry-point=${ENTRY_POINT} \
    --trigger-${TRIGGER_TYPE} \
    --memory=${MEMORY} \
    --timeout=${TIMEOUT} \
    --env-vars-file=env.yaml \
    --allow-unauthenticated

# Get the function URL
FUNCTION_URL=$(gcloud functions describe ${FUNCTION_NAME} --region=${REGION} --format="value(httpsTrigger.url)")

echo -e "${GREEN}✅ Function deployed successfully!${NC}"
echo -e "${GREEN}🌐 Function URL: ${FUNCTION_URL}${NC}"
echo -e "${GREEN}📊 Function name: ${FUNCTION_NAME}${NC}"
echo -e "${GREEN}📍 Region: ${REGION}${NC}"

# Test the function
echo -e "${YELLOW}🧪 Testing the function...${NC}"
curl -X POST ${FUNCTION_URL} \
    -H "Content-Type: application/json" \
    -d '{"test": "true"}' \
    --max-time 30

echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo ""
echo -e "${YELLOW}📝 Next steps:${NC}"
echo "1. Set up a Cloud Scheduler job to trigger the function daily"
echo "2. Monitor the function logs: gcloud functions logs read ${FUNCTION_NAME} --region=${REGION}"
echo "3. View function details: gcloud functions describe ${FUNCTION_NAME} --region=${REGION}" 