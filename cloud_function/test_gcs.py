#!/usr/bin/env python3
"""
Test script for Google Cloud Storage functionality
This script tests the Cloud Storage integration used by the Cloud Function
"""

import os
import json
import tempfile
from pathlib import Path

def test_gcs_connectivity():
    """Test basic Cloud Storage connectivity"""
    print("🔍 Testing Cloud Storage connectivity...")
    
    try:
        from descarga_procesa_datos import get_storage_client, get_bucket
        
        # Test client creation
        client = get_storage_client()
        print("✅ Storage client created successfully")
        
        # Test bucket access
        bucket = get_bucket()
        print(f"✅ Bucket access successful: {bucket.name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Cloud Storage connectivity failed: {e}")
        return False

def test_gcs_operations():
    """Test basic Cloud Storage operations"""
    print("🧪 Testing Cloud Storage operations...")
    
    try:
        from descarga_procesa_datos import upload_to_gcs, download_from_gcs
        
        # Test data
        test_data = {
            "test": True,
            "message": "Hello from Cloud Storage test",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        # Test upload
        test_path = "test/test_data.json"
        upload_to_gcs(test_data, test_path)
        print("✅ Upload test successful")
        
        # Test download
        downloaded_data = download_from_gcs(test_path)
        if downloaded_data and downloaded_data.get("test"):
            print("✅ Download test successful")
        else:
            print("❌ Download test failed - data mismatch")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Cloud Storage operations failed: {e}")
        return False

def test_incremental_logic():
    """Test incremental download logic"""
    print("🔄 Testing incremental download logic...")
    
    try:
        from descarga_procesa_datos import get_latest_timestamp_from_gcs
        
        # Test with non-existent file
        timestamp = get_latest_timestamp_from_gcs("test-course", "grades")
        if timestamp is None:
            print("✅ Correctly returned None for non-existent file")
        else:
            print("❌ Should return None for non-existent file")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Incremental logic test failed: {e}")
        return False

def check_environment():
    """Check required environment variables"""
    print("🔧 Checking environment variables...")
    
    required_vars = [
        'GCP_PROJECT_ID',
        'GCP_BUCKET_NAME',
        'GOOGLE_SERVICE_ACCOUNT_KEY',
        'CLIENT_ID',
        'SCHOOL_DOMAIN',
        'ACCESS_TOKEN'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
        else:
            print(f"✅ {var} is set")
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    return True

def main():
    """Main test function"""
    print("🧪 Google Cloud Storage Test Suite")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("descarga_procesa_datos.py").exists():
        print("❌ descarga_procesa_datos.py not found. Please run this script from the cloud_function directory.")
        return
    
    # Check environment
    if not check_environment():
        print("\n❌ Environment check failed. Please set all required environment variables.")
        return
    
    # Run tests
    tests = [
        ("Environment Variables", check_environment),
        ("Cloud Storage Connectivity", test_gcs_connectivity),
        ("Cloud Storage Operations", test_gcs_operations),
        ("Incremental Logic", test_incremental_logic)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        if test_func():
            passed += 1
            print(f"✅ {test_name} test passed")
        else:
            print(f"❌ {test_name} test failed")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Cloud Storage integration is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the configuration and try again.")

if __name__ == "__main__":
    main() 