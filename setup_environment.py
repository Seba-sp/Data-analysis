#!/usr/bin/env python3
"""
Environment setup script for Google Cloud Function
This script helps configure the necessary environment variables and settings
"""

import os
import json
import argparse
from dotenv import load_dotenv
from google.cloud import functions_v1
from google.cloud.functions_v1 import CloudFunction
from google.protobuf import field_mask_pb2

def set_cloud_function_env_vars(project_id: str, region: str, function_name: str, env_vars: dict):
    """Set environment variables for a Cloud Function"""
    client = functions_v1.CloudFunctionsServiceClient()
    
    # Get the function
    function_path = client.cloud_function_path(project_id, region, function_name)
    function = client.get_function(request={"name": function_path})
    
    # Update environment variables
    if not function.environment_variables:
        function.environment_variables = {}
    
    function.environment_variables.update(env_vars)
    
    # Update the function
    update_mask = field_mask_pb2.FieldMask(paths=["environment_variables"])
    operation = client.update_cloud_function(
        request={
            "cloud_function": function,
            "update_mask": update_mask,
        }
    )
    
    print(f"✅ Updated environment variables for function {function_name}")
    return operation

def create_google_drive_folder():
    """Instructions for creating Google Drive folder"""
    print("\n📁 Google Drive Setup:")
    print("1. Go to Google Drive (https://drive.google.com)")
    print("2. Create a new folder called 'Course Analysis Reports'")
    print("3. Right-click on the folder and select 'Share'")
    print("4. Add the service account email with 'Editor' permissions")
    print("5. Copy the folder ID from the URL (the long string after /folders/)")
    print("6. Use this ID as GOOGLE_DRIVE_FOLDER_ID")

def create_slack_app():
    """Instructions for creating Slack app"""
    print("\n💬 Slack Setup:")
    print("1. Go to https://api.slack.com/apps")
    print("2. Click 'Create New App' → 'From scratch'")
    print("3. Name: 'Course Analysis Bot'")
    print("4. Select your workspace")
    print("5. Go to 'OAuth & Permissions' in the sidebar")
    print("6. Add these scopes:")
    print("   - chat:write")
    print("   - chat:write.public")
    print("7. Install the app to your workspace")
    print("8. Copy the 'Bot User OAuth Token' (starts with xoxb-)")
    print("9. Invite the bot to your channel: /invite @Course Analysis Bot")

def validate_env_file():
    """Validate and provide guidance for .env file issues"""
    env_file = '.env'
    if os.path.exists(env_file):
        print(f"\n🔍 Validating {env_file} file...")
        
        with open(env_file, 'r') as f:
            content = f.read()
        
        issues = []
        
        # Check for missing = signs
        if 'GOOGLE_DRIVE_FOLDER_ID\n' in content and 'GOOGLE_DRIVE_FOLDER_ID=' not in content:
            issues.append("GOOGLE_DRIVE_FOLDER_ID is missing the = sign")
        
        # Check for invalid IGNORED_USERS value
        if 'IGNORED_USERS=.' in content:
            issues.append("IGNORED_USERS has invalid value '.' - should be email addresses")
        
        # Check for incorrect GOOGLE_SERVICE_ACCOUNT_KEY format
        if 'GOOGLE_SERVICE_ACCOUNT_KEY=service-account-key.json' in content:
            issues.append("GOOGLE_SERVICE_ACCOUNT_KEY should contain JSON content, not filename")
        
        if issues:
            print("⚠️  Found issues in .env file:")
            for issue in issues:
                print(f"   - {issue}")
            print("\n💡 Fix your .env file:")
            print("   GOOGLE_DRIVE_FOLDER_ID=your_folder_id_here")
            print("   IGNORED_USERS=user1@email.com,user2@email.com")
            print("   GOOGLE_SERVICE_ACCOUNT_KEY={\"type\":\"service_account\",...}")
            print("   GOOGLE_APPLICATION_CREDENTIALS=service-account-key.json")
        else:
            print("✅ .env file format looks good!")
        
        return len(issues) == 0
    return False

def load_env_file():
    """Load environment variables from .env file"""
    env_file = '.env'
    if os.path.exists(env_file):
        try:
            load_dotenv(env_file)
            print(f"✅ Loaded environment variables from {env_file}")
            return True
        except Exception as e:
            print(f"⚠️  Error loading {env_file}: {e}")
            print("   This might be due to the service account key format.")
            print("   The service account key should be on a single line without line breaks.")
            return False
    else:
        print(f"⚠️  {env_file} file not found. Please create one from env.template")
        print("   Copy env.template to .env and fill in your values")
        return False

def main():
    parser = argparse.ArgumentParser(description='Setup environment for Cloud Function')
    parser.add_argument('--project-id', help='Google Cloud Project ID (or set GCP_PROJECT_ID in .env)')
    parser.add_argument('--region',  help='Cloud Function region')
    parser.add_argument('--function-name', help='Cloud Function name')
    parser.add_argument('--slack-token', help='Slack Bot Token (or set SLACK_BOT_TOKEN in .env)')
    parser.add_argument('--slack-channel', help='Slack channel (or set SLACK_CHANNEL in .env)')
    parser.add_argument('--drive-folder-id', help='Google Drive folder ID (or set GOOGLE_DRIVE_FOLDER_ID in .env)')
    parser.add_argument('--service-account-key-file', help='Path to service account key JSON file')
    parser.add_argument('--client-id', help='LearnWorlds Client ID (or set CLIENT_ID in .env)')
    parser.add_argument('--school-domain', help='LearnWorlds School Domain (or set SCHOOL_DOMAIN in .env)')
    parser.add_argument('--access-token', help='LearnWorlds Access Token (or set ACCESS_TOKEN in .env)')
    parser.add_argument('--ignored-users', help='Comma-separated list of ignored user emails (or set IGNORED_USERS in .env)')
    parser.add_argument('--load-env', action='store_true', help='Load variables from .env file')
    
    args = parser.parse_args()
    
    print("🔧 Setting up Cloud Function environment...")
    
    # Validate .env file format first
    validate_env_file()
    
    # Load environment variables from .env file if requested or if no command line args provided
    env_loaded = False
    if args.load_env or not any([args.project_id, args.slack_token, args.slack_channel, args.drive_folder_id, 
                                args.client_id, args.school_domain, args.access_token, args.ignored_users]):
        env_loaded = load_env_file()
    
    # Check if service account key file exists
    service_account_key_file = args.service_account_key_file or os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'service-account-key.json')
    if os.path.exists(service_account_key_file):
        print(f"✅ Found service account key file: {service_account_key_file}")
    else:
        print(f"❌ Service account key file not found: {service_account_key_file}")
        print("   Please check your .env file and ensure GOOGLE_APPLICATION_CREDENTIALS points to a valid file")
        print("   Or use --service-account-key-file to specify the path")
        return
    
    # Prepare environment variables - prioritize command line args, then env vars
    env_vars = {}
    
    # Handle service account key (encode as base64 to avoid newline issues)
    if service_account_key_file and os.path.exists(service_account_key_file):
        try:
            with open(service_account_key_file, 'r') as f:
                service_account_data = json.load(f)
            # Encode as base64 to avoid newline issues in .env files
            import base64
            json_string = json.dumps(service_account_data)
            encoded_key = base64.b64encode(json_string.encode('utf-8')).decode('utf-8')
            env_vars['GOOGLE_SERVICE_ACCOUNT_KEY'] = encoded_key
            print(f"✅ Service account key encoded and ready")
        except Exception as e:
            print(f"❌ Error processing service account key: {e}")
            return
    else:
        print(f"❌ Service account key file not found: {service_account_key_file}")
        return
    
    # Project ID
    project_id = args.project_id or os.getenv('GCP_PROJECT_ID')
    if not project_id:
        print("❌ Project ID is required. Set --project-id or GCP_PROJECT_ID in .env")
        print("   Example: GCP_PROJECT_ID=your-project-id")
        return
    
    # Slack configuration
    slack_token = args.slack_token or os.getenv('SLACK_BOT_TOKEN')
    if slack_token:
        env_vars['SLACK_BOT_TOKEN'] = slack_token
    else:
        print("⚠️  Slack token not provided. Set --slack-token or SLACK_BOT_TOKEN in .env")
        if not env_loaded:
            create_slack_app()
    
    slack_channel = args.slack_channel or os.getenv('SLACK_CHANNEL')
    if slack_channel:
        env_vars['SLACK_CHANNEL'] = slack_channel
    else:
        print("⚠️  Slack channel not provided. Set --slack-channel or SLACK_CHANNEL in .env")
    
    # Google Drive configuration
    drive_folder_id = args.drive_folder_id or os.getenv('GOOGLE_DRIVE_FOLDER_ID')
    if drive_folder_id:
        env_vars['GOOGLE_DRIVE_FOLDER_ID'] = drive_folder_id
    else:
        print("⚠️  Google Drive folder ID not provided. Set --drive-folder-id or GOOGLE_DRIVE_FOLDER_ID in .env")
        if not env_loaded:
            create_google_drive_folder()
    
    # LearnWorlds API credentials
    client_id = args.client_id or os.getenv('CLIENT_ID')
    if client_id:
        env_vars['CLIENT_ID'] = client_id
    else:
        print("⚠️  LearnWorlds Client ID not provided. Set --client-id or CLIENT_ID in .env")
    
    school_domain = args.school_domain or os.getenv('SCHOOL_DOMAIN')
    if school_domain:
        env_vars['SCHOOL_DOMAIN'] = school_domain
    else:
        print("⚠️  LearnWorlds School Domain not provided. Set --school-domain or SCHOOL_DOMAIN in .env")
    
    access_token = args.access_token or os.getenv('ACCESS_TOKEN')
    if access_token:
        env_vars['ACCESS_TOKEN'] = access_token
    else:
        print("⚠️  LearnWorlds Access Token not provided. Set --access-token or ACCESS_TOKEN in .env")
    
    # Ignored users
    ignored_users = args.ignored_users or os.getenv('IGNORED_USERS')
    if ignored_users and ignored_users.strip() and ignored_users != '.':
        env_vars['IGNORED_USERS'] = ignored_users
    else:
        print("⚠️  Ignored users not provided or invalid. Set --ignored-users or IGNORED_USERS in .env")
        print("   Example: IGNORED_USERS=user1@email.com,user2@email.com")
        print("   Current value: " + (ignored_users or "not set"))
    
    # Set environment variables in Cloud Function
    if len(env_vars) > 1:  # More than just the service account key
        try:
            set_cloud_function_env_vars(
                project_id,
                args.region,
                args.function_name,
                env_vars
            )
            print("✅ Environment variables updated successfully!")
        except Exception as e:
            print(f"❌ Error updating environment variables: {e}")
            if "default credentials were not found" in str(e):
                print("\n🔐 Authentication Setup Required:")
                print("1. Install Google Cloud CLI: https://cloud.google.com/sdk/docs/install")
                print("2. Run: gcloud auth login")
                print("3. Run: gcloud config set project YOUR_PROJECT_ID")
                print("4. Or set GOOGLE_APPLICATION_CREDENTIALS environment variable:")
                print(f"   set GOOGLE_APPLICATION_CREDENTIALS={os.path.abspath(service_account_key_file)}")
    else:
        print("⚠️  Please provide all required environment variables")
    
    print("\n📋 Summary of required environment variables:")
    print("  - SLACK_BOT_TOKEN: Your Slack bot token")
    print("  - SLACK_CHANNEL: Channel to send notifications (e.g., #general)")
    print("  - GOOGLE_DRIVE_FOLDER_ID: Google Drive folder ID for reports")
    print("  - CLIENT_ID: LearnWorlds Client ID")
    print("  - SCHOOL_DOMAIN: LearnWorlds School Domain")
    print("  - ACCESS_TOKEN: LearnWorlds Access Token")
    print("  - IGNORED_USERS: Comma-separated list of ignored user emails")
    print("  - GOOGLE_SERVICE_ACCOUNT_KEY: Service account key (automatically set)")
    print("\n💡 Tip: Create a .env file from env.template for easier configuration")

if __name__ == "__main__":
    main() 