#!/usr/bin/env python3
"""
Test script for Cloud Function
This script helps test the Cloud Function locally before deployment
"""

import os
import json
import requests
import argparse
from datetime import datetime

def test_cloud_function_locally():
    """Test the Cloud Function locally using Functions Framework"""
    print("🧪 Testing Cloud Function locally...")
    
    # Set test environment variables
    os.environ.setdefault('GCP_PROJECT_ID', 'test-project')
    os.environ.setdefault('GCP_BUCKET_NAME', 'test-bucket')
    os.environ.setdefault('SLACK_BOT_TOKEN', 'xoxb-test-token')
    os.environ.setdefault('SLACK_CHANNEL', '#test-channel')
    os.environ.setdefault('GOOGLE_DRIVE_FOLDER_ID', 'test-folder-id')
    os.environ.setdefault('CLIENT_ID', 'test-client-id')
    os.environ.setdefault('SCHOOL_DOMAIN', 'test-domain')
    os.environ.setdefault('ACCESS_TOKEN', 'test-access-token')
    os.environ.setdefault('IGNORED_USERS', 'test@email.com,test2@email.com')
    os.environ.setdefault('GOOGLE_SERVICE_ACCOUNT_KEY', '{"test": "key"}')
    
    # Import and test the function
    try:
        from cloud_function.main import main
        
        # Mock request object
        class MockRequest:
            def __init__(self):
                self.method = 'POST'
                self.headers = {}
                self.get_json = lambda: {}
        
        # Test the function
        result, status_code = main(MockRequest())
        
        print(f"✅ Function executed successfully!")
        print(f"Status Code: {status_code}")
        print(f"Result: {json.dumps(result, indent=2)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Function test failed: {e}")
        return False

def test_cloud_function_remote(function_url: str):
    """Test the deployed Cloud Function"""
    print(f"🌐 Testing remote Cloud Function: {function_url}")
    
    try:
        response = requests.post(function_url, timeout=300)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Remote function test successful!")
            return True
        else:
            print("❌ Remote function test failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error testing remote function: {e}")
        return False

def get_function_url(project_id: str, region: str = 'us-central1', function_name: str = 'course-analysis-pipeline'):
    """Get the Cloud Function URL"""
    try:
        import subprocess
        result = subprocess.run([
            'gcloud', 'functions', 'describe', function_name,
            '--region', region,
            '--format', 'value(httpsTrigger.url)'
        ], capture_output=True, text=True, check=True)
        
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Error getting function URL: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Test Cloud Function')
    parser.add_argument('--local', action='store_true', help='Test locally')
    parser.add_argument('--remote', action='store_true', help='Test remote function')
    parser.add_argument('--project-id', help='Google Cloud Project ID')
    parser.add_argument('--region', default='us-central1', help='Function region')
    parser.add_argument('--function-name', default='course-analysis-pipeline', help='Function name')
    
    args = parser.parse_args()
    
    if args.local:
        test_cloud_function_locally()
    
    elif args.remote:
        if not args.project_id:
            print("❌ --project-id is required for remote testing")
            return
        
        function_url = get_function_url(args.project_id, args.region, args.function_name)
        if function_url:
            test_cloud_function_remote(function_url)
        else:
            print("❌ Could not get function URL")
    
    else:
        print("🔧 Testing both local and remote...")
        
        # Test local first
        print("\n" + "="*50)
        local_success = test_cloud_function_locally()
        
        # Test remote if project ID provided
        if args.project_id:
            print("\n" + "="*50)
            function_url = get_function_url(args.project_id, args.region, args.function_name)
            if function_url:
                remote_success = test_cloud_function_remote(function_url)
            else:
                remote_success = False
        else:
            print("\n⚠️  Skipping remote test (no project ID provided)")
            remote_success = None
        
        # Summary
        print("\n" + "="*50)
        print("📊 Test Summary:")
        print(f"  Local Test: {'✅ PASS' if local_success else '❌ FAIL'}")
        if remote_success is not None:
            print(f"  Remote Test: {'✅ PASS' if remote_success else '❌ FAIL'}")
        else:
            print(f"  Remote Test: ⏭️  SKIPPED")

if __name__ == "__main__":
    main() 