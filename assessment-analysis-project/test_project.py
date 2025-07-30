#!/usr/bin/env python3
"""
Test script for Assessment Analysis Project
Tests individual components and integration
"""

import logging
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from assessment_downloader import AssessmentDownloader
from assessment_analyzer import AssessmentAnalyzer
from report_generator import ReportGenerator
from email_sender import EmailSender

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_assessment_downloader():
    """Test the assessment downloader"""
    print("=== Testing Assessment Downloader ===")
    
    try:
        downloader = AssessmentDownloader()
        print("✅ AssessmentDownloader initialized successfully")
        
        # Test connection
        if downloader.test_connection():
            print("✅ API connection test successful")
        else:
            print("❌ API connection test failed")
            
    except Exception as e:
        print(f"❌ AssessmentDownloader test failed: {e}")

def test_assessment_analyzer():
    """Test the assessment analyzer"""
    print("\n=== Testing Assessment Analyzer ===")
    
    try:
        analyzer = AssessmentAnalyzer()
        print("✅ AssessmentAnalyzer initialized successfully")
        
        # Test with dummy data
        dummy_response = {
            "user_id": "test_user",
            "answers": [
                {"answer": "A"},
                {"answer": "B"},
                {"answer": "C"}
            ]
        }
        
        dummy_question_bank = {
            "question_number": [1, 2, 3],
            "correct_alternative": ["A", "B", "C"],
            "lecture": ["Lección 1", "Lección 1", "Lección 2"]
        }
        
        import pandas as pd
        df = pd.DataFrame(dummy_question_bank)
        
        # Test lecture-based analysis
        result = analyzer.analyze_lecture_based(dummy_response, df, "Test Assessment")
        print(f"✅ Lecture-based analysis completed: {result.get('lectures_passed', 0)}/{result.get('lectures_analyzed', 0)} lectures passed")
        
        # Test percentage-based analysis
        result = analyzer.analyze_percentage_based(dummy_response, df, "Test Assessment")
        print(f"✅ Percentage-based analysis completed: {result.get('overall_percentage', 0):.1f}% overall")
        
    except Exception as e:
        print(f"❌ AssessmentAnalyzer test failed: {e}")

def test_email_sender():
    """Test the email sender"""
    print("\n=== Testing Email Sender ===")
    
    try:
        email_sender = EmailSender()
        print("✅ EmailSender initialized successfully")
        
        # Test connection
        if email_sender.test_email_connection():
            print("✅ Email connection test successful")
        else:
            print("❌ Email connection test failed")
            
    except Exception as e:
        print(f"❌ EmailSender test failed: {e}")

def test_report_generator():
    """Test the report generator"""
    print("\n=== Testing Report Generator ===")
    
    try:
        report_generator = ReportGenerator()
        print("✅ ReportGenerator initialized successfully")
        
        # Test with dummy results
        dummy_results = {
            "M1": {
                "type": "lecture_based",
                "lectures_passed": 2,
                "lectures_analyzed": 3,
                "lecture_results": {
                    "Lección 1": {"status": "Aprobado"},
                    "Lección 2": {"status": "Aprobado"},
                    "Lección 3": {"status": "Reprobado"}
                }
            },
            "CL": {
                "type": "percentage_based",
                "overall_percentage": 75.0,
                "lecture_results": {
                    "Lección 1": {"percentage": 80.0, "status": "80.0%"},
                    "Lección 2": {"percentage": 70.0, "status": "70.0%"}
                }
            }
        }
        
        # Note: This would require the HTML template to exist
        print("✅ ReportGenerator initialized (HTML template test skipped)")
        
    except Exception as e:
        print(f"❌ ReportGenerator test failed: {e}")

def test_file_structure():
    """Test that required files exist"""
    print("\n=== Testing File Structure ===")
    
    required_files = [
        "main.py",
        "assessment_downloader.py",
        "assessment_analyzer.py",
        "report_generator.py",
        "email_sender.py",
        "storage.py",
        "drive_service.py",
        "requirements.txt",
        "README.md"
    ]
    
    missing_files = []
    for file in required_files:
        if Path(file).exists():
            print(f"✅ {file} exists")
        else:
            print(f"❌ {file} missing")
            missing_files.append(file)
    
    if missing_files:
        print(f"\nMissing files: {', '.join(missing_files)}")
    else:
        print("\n✅ All required files present")

def test_question_banks():
    """Test that question bank files exist"""
    print("\n=== Testing Question Banks ===")
    
    question_banks = ["M1.csv", "CL.csv", "CIEN.csv", "HYST.csv"]
    
    for bank in question_banks:
        path = Path("data/questions") / bank
        if path.exists():
            print(f"✅ {bank} exists")
        else:
            print(f"❌ {bank} missing")

def main():
    """Run all tests"""
    print("Assessment Analysis Project - Component Tests")
    print("=" * 50)
    
    test_file_structure()
    test_question_banks()
    test_assessment_downloader()
    test_assessment_analyzer()
    test_email_sender()
    test_report_generator()
    
    print("\n" + "=" * 50)
    print("Test completed!")
    print("\nTo run the full project:")
    print("python main.py sample_assessment_list.txt")

if __name__ == "__main__":
    main() 