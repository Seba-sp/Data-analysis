#!/usr/bin/env python3
"""
Script to create a properly formatted .env file
This handles the service account key encoding automatically
"""

import json
import base64
import os

def create_env_file():
    """Create a .env file with proper formatting"""
    
    print("🔧 Creating .env file...")
    
    # Check if service account key exists
    key_file = 'service-account-key.json'
    if not os.path.exists(key_file):
        print(f"❌ {key_file} not found in current directory")
        print("Please make sure the service account key file is in the same directory as this script")
        return
    
    # Read and encode service account key
    try:
        with open(key_file, 'r') as f:
            service_account_data = json.load(f)
        
        json_string = json.dumps(service_account_data)
        encoded_key = base64.b64encode(json_string.encode('utf-8')).decode('utf-8')
        
        print("✅ Service account key encoded successfully")
        
    except Exception as e:
        print(f"❌ Error encoding service account key: {e}")
        return
    
    # Create .env file content
    env_content = f"""# Google Cloud Configuration
GCP_PROJECT_ID=data-analysis-465601
GCP_BUCKET_NAME=course-analysis-data

# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-slack-token-here
SLACK_CHANNEL=#your-channel-here

# Google Drive Configuration
GOOGLE_DRIVE_FOLDER_ID=your-drive-folder-id-here

# LearnWorlds API Configuration
CLIENT_ID=your-client-id-here
SCHOOL_DOMAIN=your-school-domain-here
ACCESS_TOKEN=your-access-token-here

# Ignored Users (comma-separated emails)
IGNORED_USERS=user1@email.com,user2@email.com

# Service Account Key (base64 encoded)
GOOGLE_SERVICE_ACCOUNT_KEY={encoded_key}

# Local Development
GOOGLE_APPLICATION_CREDENTIALS=service-account-key.json
"""
    
    # Write to .env file
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        
        print("✅ .env file created successfully!")
        print("\n📋 Next steps:")
        print("1. Edit the .env file and replace the placeholder values:")
        print("   - SLACK_BOT_TOKEN: Your Slack bot token")
        print("   - SLACK_CHANNEL: Your Slack channel (e.g., #general)")
        print("   - GOOGLE_DRIVE_FOLDER_ID: Your Google Drive folder ID")
        print("   - CLIENT_ID: Your LearnWorlds Client ID")
        print("   - SCHOOL_DOMAIN: Your LearnWorlds School Domain")
        print("   - ACCESS_TOKEN: Your LearnWorlds Access Token")
        print("   - IGNORED_USERS: Comma-separated list of ignored user emails")
        print("\n2. The GOOGLE_SERVICE_ACCOUNT_KEY is already set correctly")
        print("\n3. Test your setup with: python setup_environment.py --load-env")
        
    except Exception as e:
        print(f"❌ Error creating .env file: {e}")

if __name__ == "__main__":
    create_env_file() 