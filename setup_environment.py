#!/usr/bin/env python3
"""
Environment setup script for Google Cloud Function
This script helps configure the necessary environment variables and settings
"""

import os
import json
import argparse
from google.cloud import functions_v1
from google.cloud.functions_v1 import CloudFunction
from google.protobuf import field_mask_pb2

def set_cloud_function_env_vars(project_id: str, region: str, function_name: str, env_vars: dict):
    """Set environment variables for a Cloud Function"""
    client = functions_v1.CloudFunctionsServiceClient()
    
    # Get the function
    function_path = client.cloud_function_path(project_id, region, function_name)
    function = client.get_cloud_function(request={"name": function_path})
    
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

def main():
    parser = argparse.ArgumentParser(description='Setup environment for Cloud Function')
    parser.add_argument('--project-id', required=True, help='Google Cloud Project ID')
    parser.add_argument('--region', default='us-central1', help='Cloud Function region')
    parser.add_argument('--function-name', default='course-analysis-pipeline', help='Cloud Function name')
    parser.add_argument('--slack-token', help='Slack Bot Token')
    parser.add_argument('--slack-channel', help='Slack channel (e.g., #general)')
    parser.add_argument('--drive-folder-id', help='Google Drive folder ID')
    parser.add_argument('--service-account-key-file', help='Path to service account key JSON file')
    parser.add_argument('--client-id', help='LearnWorlds Client ID')
    parser.add_argument('--school-domain', help='LearnWorlds School Domain')
    parser.add_argument('--access-token', help='LearnWorlds Access Token')
    parser.add_argument('--ignored-users', help='Comma-separated list of ignored user emails')
    
    args = parser.parse_args()
    
    print("🔧 Setting up Cloud Function environment...")
    
    # Check if service account key file exists
    if args.service_account_key_file and os.path.exists(args.service_account_key_file):
        with open(args.service_account_key_file, 'r') as f:
            service_account_key = json.load(f)
        print(f"✅ Loaded service account key from {args.service_account_key_file}")
    else:
        print("⚠️  Service account key file not found. Please provide --service-account-key-file")
        return
    
    # Prepare environment variables
    env_vars = {
        'GOOGLE_SERVICE_ACCOUNT_KEY': json.dumps(service_account_key)
    }
    
    if args.slack_token:
        env_vars['SLACK_BOT_TOKEN'] = args.slack_token
    else:
        print("⚠️  Slack token not provided. Use --slack-token")
        create_slack_app()
    
    if args.slack_channel:
        env_vars['SLACK_CHANNEL'] = args.slack_channel
    else:
        print("⚠️  Slack channel not provided. Use --slack-channel")
    
    if args.drive_folder_id:
        env_vars['GOOGLE_DRIVE_FOLDER_ID'] = args.drive_folder_id
    else:
        print("⚠️  Google Drive folder ID not provided. Use --drive-folder-id")
        create_google_drive_folder()
    
    # LearnWorlds API credentials
    if args.client_id:
        env_vars['CLIENT_ID'] = args.client_id
    else:
        print("⚠️  LearnWorlds Client ID not provided. Use --client-id")
    
    if args.school_domain:
        env_vars['SCHOOL_DOMAIN'] = args.school_domain
    else:
        print("⚠️  LearnWorlds School Domain not provided. Use --school-domain")
    
    if args.access_token:
        env_vars['ACCESS_TOKEN'] = args.access_token
    else:
        print("⚠️  LearnWorlds Access Token not provided. Use --access-token")
    
    # Ignored users
    if args.ignored_users:
        env_vars['IGNORED_USERS'] = args.ignored_users
    else:
        print("⚠️  Ignored users not provided. Use --ignored-users")
        print("   Example: --ignored-users 'user1@email.com,user2@email.com'")
    
    # Set environment variables in Cloud Function
    if len(env_vars) > 1:  # More than just the service account key
        try:
            set_cloud_function_env_vars(
                args.project_id,
                args.region,
                args.function_name,
                env_vars
            )
            print("✅ Environment variables updated successfully!")
        except Exception as e:
            print(f"❌ Error updating environment variables: {e}")
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

if __name__ == "__main__":
    main() 