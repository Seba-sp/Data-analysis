#!/bin/bash

# Example script to set up environment variables
# Copy this and fill in your actual values

echo "🔧 Setting up environment variables..."

# 1. Google Cloud Project ID
export PROJECT_ID="your-google-cloud-project-id"

# 2. LearnWorlds API (you already have these)
export CLIENT_ID="your_client_id"
export SCHOOL_DOMAIN="your_school_domain"
export ACCESS_TOKEN="your_access_token"

# 3. Slack Configuration (you need to create this)
export SLACK_BOT_TOKEN="xoxb-your-slack-bot-token"
export SLACK_CHANNEL="#your-channel-name"

# 4. Google Drive Folder ID (you need to create this)
export GOOGLE_DRIVE_FOLDER_ID="your-google-drive-folder-id"

# 5. Ignored Users (comma-separated)
export IGNORED_USERS="renepuente9000@gmail.com,nicolas.valenzuelar@sansano.usm.cl,sebastian.san.martin.p@gmail.com,jairopera01@gmail.com,tetahac783@iridales.com,theflaviomc@gmail.com,soporte@preum30m.com"

echo "✅ Environment variables set!"
echo ""
echo "📋 Next steps:"
echo "1. Deploy: ./deploy.sh"
echo "2. Configure: python setup_environment.py --project-id \$PROJECT_ID --slack-token \$SLACK_BOT_TOKEN --slack-channel \$SLACK_CHANNEL --drive-folder-id \$GOOGLE_DRIVE_FOLDER_ID --client-id \$CLIENT_ID --school-domain \$SCHOOL_DOMAIN --access-token \$ACCESS_TOKEN --ignored-users \$IGNORED_USERS --service-account-key-file service-account-key.json" 