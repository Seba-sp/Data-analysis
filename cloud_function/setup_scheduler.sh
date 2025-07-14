#!/bin/bash

# Cloud Scheduler Setup Script
# This script sets up a Cloud Scheduler job to trigger the function daily

set -e  # Exit on any error

# Configuration
FUNCTION_NAME="course-analysis-pipeline"
REGION="us-central1"
SCHEDULER_JOB_NAME="daily-course-analysis"
TIMEZONE="America/Santiago"
SCHEDULE="0 8 * * *"  # Daily at 8:00 AM Santiago time

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}⏰ Setting up Cloud Scheduler for daily course analysis${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ Google Cloud SDK is not installed.${NC}"
    exit 1
fi

# Get the function URL
FUNCTION_URL=$(gcloud functions describe ${FUNCTION_NAME} --region=${REGION} --format="value(httpsTrigger.url)" 2>/dev/null)

if [ -z "$FUNCTION_URL" ]; then
    echo -e "${RED}❌ Function ${FUNCTION_NAME} not found in region ${REGION}.${NC}"
    echo "Please deploy the function first using: ./deploy.sh"
    exit 1
fi

echo -e "${GREEN}✅ Found function URL: ${FUNCTION_URL}${NC}"

# Enable Cloud Scheduler API
echo -e "${YELLOW}📋 Enabling Cloud Scheduler API...${NC}"
gcloud services enable cloudscheduler.googleapis.com

# Create the scheduler job
echo -e "${YELLOW}⏰ Creating Cloud Scheduler job...${NC}"
gcloud scheduler jobs create http ${SCHEDULER_JOB_NAME} \
    --schedule="${SCHEDULE}" \
    --uri="${FUNCTION_URL}" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body='{"trigger": "scheduler"}' \
    --time-zone="${TIMEZONE}" \
    --description="Daily course analysis pipeline trigger" \
    --location=${REGION}

echo -e "${GREEN}✅ Cloud Scheduler job created successfully!${NC}"
echo -e "${GREEN}📅 Job name: ${SCHEDULER_JOB_NAME}${NC}"
echo -e "${GREEN}⏰ Schedule: ${SCHEDULE} (${TIMEZONE})${NC}"
echo -e "${GREEN}🌐 Target: ${FUNCTION_URL}${NC}"

# Test the scheduler job
echo -e "${YELLOW}🧪 Testing the scheduler job...${NC}"
gcloud scheduler jobs run ${SCHEDULER_JOB_NAME} --location=${REGION}

echo -e "${GREEN}✅ Scheduler setup completed!${NC}"
echo ""
echo -e "${YELLOW}📝 Useful commands:${NC}"
echo "• View job details: gcloud scheduler jobs describe ${SCHEDULER_JOB_NAME} --location=${REGION}"
echo "• List all jobs: gcloud scheduler jobs list --location=${REGION}"
echo "• Run job manually: gcloud scheduler jobs run ${SCHEDULER_JOB_NAME} --location=${REGION}"
echo "• Delete job: gcloud scheduler jobs delete ${SCHEDULER_JOB_NAME} --location=${REGION}" 