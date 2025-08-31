#!/usr/bin/env python3
"""
Test script to validate configuration and environment setup
"""

import os
import yaml
import sys
from pathlib import Path

def test_yaml_config(config_path):
    """Test if YAML configuration is valid"""
    print("🔍 Testing YAML configuration...")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Check required sections
        required_sections = ['course']
        for section in required_sections:
            if section not in config:
                print(f"❌ Missing required section: {section}")
                return False
        
        # Check course configuration
        if 'id' not in config['course'] or 'name' not in config['course']:
            print("❌ Course configuration missing 'id' or 'name'")
            return False
        
        # Check assessments configuration
        if 'assessments' not in config['course']:
            print("❌ Course configuration missing 'assessments'")
            return False
        
        assessments = config['course']['assessments']
        if 'individual' not in assessments or 'grouped' not in assessments:
            print("❌ Assessments configuration missing 'individual' or 'grouped'")
            return False
        
        # Check individual assessments
        for i, assessment in enumerate(assessments['individual']):
            if 'name' not in assessment or 'id' not in assessment:
                print(f"❌ Individual assessment {i} missing 'name' or 'id'")
                return False
        
        # Check grouped assessments
        for group_key, group_config in assessments['grouped'].items():
            if 'name' not in group_config or 'assessments' not in group_config:
                print(f"❌ Group {group_key} missing 'name' or 'assessments'")
                return False
            
            for i, assessment in enumerate(group_config['assessments']):
                if 'name' not in assessment or 'id' not in assessment:
                    print(f"❌ Group assessment {group_key}[{i}] missing 'name' or 'id'")
                    return False
        
        print("✅ YAML configuration is valid")
        return True
        
    except Exception as e:
        print(f"❌ Error reading YAML configuration: {e}")
        return False

def test_environment_variables():
    """Test if required environment variables are set"""
    print("\n🔍 Testing environment variables...")
    
    required_vars = [
        'CLIENT_ID',
        'SCHOOL_DOMAIN', 
        'ACCESS_TOKEN',
        'GCP_PROJECT_ID',
        'GCP_BUCKET_NAME',
        'GOOGLE_DRIVE_FOLDER_ID',
        'GOOGLE_SERVICE_ACCOUNT_KEY',
        'SLACK_BOT_TOKEN',
        'SLACK_CHANNEL'
    ]
    
    optional_vars = [
        'STORAGE_BACKEND',
        'REPORT_TOP_PERCENT'
    ]
    
    missing_required = []
    missing_optional = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
    
    for var in optional_vars:
        if not os.getenv(var):
            missing_optional.append(var)
    
    if missing_required:
        print("❌ Missing required environment variables:")
        for var in missing_required:
            print(f"   - {var}")
        return False
    
    if missing_optional:
        print("⚠️  Missing optional environment variables:")
        for var in missing_optional:
            print(f"   - {var}")
    
    print("✅ All required environment variables are set")
    return True

def test_dependencies():
    """Test if required Python packages are installed"""
    print("\n🔍 Testing Python dependencies...")
    
    required_packages = [
        'pandas',
        'yaml',
        'requests',
        'dotenv'
    ]
    
    optional_packages = [
        'google.cloud.storage',
        'googleapiclient',
        'slack_sdk',
        'openpyxl'
    ]
    
    missing_required = []
    missing_optional = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_required.append(package)
    
    for package in optional_packages:
        try:
            __import__(package)
        except ImportError:
            missing_optional.append(package)
    
    if missing_required:
        print("❌ Missing required Python packages:")
        for package in missing_required:
            print(f"   - {package}")
        return False
    
    if missing_optional:
        print("⚠️  Missing optional Python packages:")
        for package in missing_optional:
            print(f"   - {package}")
    
    print("✅ All required Python packages are installed")
    return True

def test_file_structure():
    """Test if required files exist"""
    print("\n🔍 Testing file structure...")
    
    required_files = [
        'multi_assessment_processor.py',
        'descarga_responses.py',
        'drive_service.py',
        'slack_service.py',
        'storage.py'
    ]
    
    missing_files = []
    
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print("❌ Missing required files:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    print("✅ All required files exist")
    return True

def main():
    """Main test function"""
    print("🧪 Multi-Assessment Processor Configuration Test")
    print("=" * 50)
    
    config_path = "assessments_config.yml"
    
    # Test YAML configuration
    yaml_ok = test_yaml_config(config_path)
    
    # Test environment variables
    env_ok = test_environment_variables()
    
    # Test dependencies
    deps_ok = test_dependencies()
    
    # Test file structure
    files_ok = test_file_structure()
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"   YAML Configuration: {'✅ PASS' if yaml_ok else '❌ FAIL'}")
    print(f"   Environment Variables: {'✅ PASS' if env_ok else '❌ FAIL'}")
    print(f"   Python Dependencies: {'✅ PASS' if deps_ok else '❌ FAIL'}")
    print(f"   File Structure: {'✅ PASS' if files_ok else '❌ FAIL'}")
    
    if yaml_ok and env_ok and deps_ok and files_ok:
        print("\n🎉 All tests passed! The system is ready to run.")
        print("\nNext steps:")
        print("1. Update assessment IDs in assessments_config.yml")
        print("2. Test with: python multi_assessment_processor.py --config assessments_config.yml --dry-run")
        print("3. Run locally: python multi_assessment_processor.py --config assessments_config.yml")
        return 0
    else:
        print("\n❌ Some tests failed. Please fix the issues above before proceeding.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
