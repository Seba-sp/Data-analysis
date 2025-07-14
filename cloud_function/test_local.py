#!/usr/bin/env python3
"""
Local testing script for Google Cloud Function
This script allows you to test the function locally before deployment
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    try:
        import functions_framework
        print("✅ functions-framework installed")
    except ImportError:
        print("❌ functions-framework not installed")
        print("Install with: pip install functions-framework")
        return False
    
    try:
        import google.cloud.storage
        print("✅ google-cloud-storage installed")
    except ImportError:
        print("❌ google-cloud-storage not installed")
        print("Install with: pip install google-cloud-storage")
        return False
    
    try:
        import slack_sdk
        print("✅ slack-sdk installed")
    except ImportError:
        print("❌ slack-sdk not installed")
        print("Install with: pip install slack-sdk")
        return False
    
    return True

def setup_environment():
    """Set up environment variables for local testing"""
    print("🔧 Setting up environment variables...")
    
    # Default values for local testing
    env_vars = {
        'GCP_PROJECT_ID': 'test-project-id',
        'GCP_BUCKET_NAME': 'test-bucket-name',
        'SLACK_BOT_TOKEN': 'xoxb-test-token',
        'SLACK_CHANNEL': '#test-channel',
        'GOOGLE_DRIVE_FOLDER_ID': 'test-folder-id',
        'GOOGLE_SERVICE_ACCOUNT_KEY': '{"type": "service_account", "project_id": "test"}',
        'IGNORED_USERS': 'test@example.com'
    }
    
    # Set environment variables
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"✅ Set {key}")
    
    return True

def test_function():
    """Test the function locally"""
    print("🧪 Testing function locally...")
    
    try:
        # Import the function
        from main import course_analysis_pipeline
        
        # Create a mock request
        class MockRequest:
            def __init__(self):
                self.method = 'POST'
                self.headers = {'Content-Type': 'application/json'}
                self.get_json = lambda: {"test": "local"}
        
        # Test the function
        response = course_analysis_pipeline(MockRequest())
        
        if isinstance(response, tuple):
            data, status_code, headers = response
            print(f"✅ Function executed successfully")
            print(f"📊 Status code: {status_code}")
            print(f"📄 Response: {data[:200]}...")  # Show first 200 chars
        else:
            print(f"✅ Function executed successfully")
            print(f"📄 Response: {response}")
        
        return True
        
    except Exception as e:
        print(f"❌ Function test failed: {e}")
        return False

def run_functions_framework():
    """Run the function using functions-framework for local testing"""
    print("🚀 Starting functions-framework server...")
    print("📝 The function will be available at: http://localhost:8080")
    print("📝 Press Ctrl+C to stop the server")
    print("📝 You can test with: curl -X POST http://localhost:8080 -H 'Content-Type: application/json' -d '{}'")
    
    try:
        # Run functions-framework
        subprocess.run([
            sys.executable, "-m", "functions_framework",
            "--target", "course_analysis_pipeline",
            "--port", "8080",
            "--debug"
        ])
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error running functions-framework: {e}")

def main():
    """Main function"""
    print("🧪 Google Cloud Function Local Testing")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("main.py").exists():
        print("❌ main.py not found. Please run this script from the cloud_function directory.")
        return
    
    # Check dependencies
    if not check_dependencies():
        print("❌ Dependencies check failed. Please install missing packages.")
        return
    
    # Setup environment
    setup_environment()
    
    # Test function
    if not test_function():
        print("❌ Function test failed.")
        return
    
    print("\n✅ All tests passed!")
    print("\n🚀 Starting local server...")
    
    # Run functions-framework
    run_functions_framework()

if __name__ == "__main__":
    main() 