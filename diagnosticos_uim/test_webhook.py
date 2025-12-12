#!/usr/bin/env python3
"""
Test script for webhook service
"""

import requests
import json
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_webhook():
    """Test the webhook service with sample payloads"""
    
    # Get webhook URL from environment or use default
    webhook_url = os.getenv('WEBHOOK_URL', 'http://localhost:8080/webhook')
    status_url = os.getenv('STATUS_URL', 'http://localhost:8080/status')
    
    print(f"🧪 Testing webhook service...")
    print(f"📝 Webhook URL: {webhook_url}")
    print(f"📊 Status URL: {status_url}")
    
    # Sample webhook payloads for different assessment types
    test_payloads = [
        {
            "user": {
                "id": "test_user_1",
                "username": "student1",
                "email": "student1@test.com"
            },
                         "assessment": {
                 "title": "M1 Assessment",
                 "url": "https://school.learnworlds.com/unit=507f1f77bcf86cd799439011"
             },
            "school": {
                "name": "Test School",
                "url": "https://school.learnworlds.com",
                "description": "Test School Description",
                "address": "Test Address",
                "company_name": "Test Company",
                "contact_email": "contact@test.com",
                "support_email": "support@test.com",
                "sales_email": "sales@test.com"
            }
        },
        {
            "user": {
                "id": "test_user_2",
                "username": "student2",
                "email": "student2@test.com"
            },
                         "assessment": {
                 "title": "CL Assessment",
                 "url": "https://school.learnworlds.com/unit=507f1f77bcf86cd799439012"
             },
            "school": {
                "name": "Test School",
                "url": "https://school.learnworlds.com",
                "description": "Test School Description",
                "address": "Test Address",
                "company_name": "Test Company",
                "contact_email": "contact@test.com",
                "support_email": "support@test.com",
                "sales_email": "sales@test.com"
            }
        },
        {
            "user": {
                "id": "test_user_3",
                "username": "student3",
                "email": "student3@test.com"
            },
                         "assessment": {
                 "title": "HYST Assessment",
                 "url": "https://school.learnworlds.com/unit=507f1f77bcf86cd799439013"
             },
            "school": {
                "name": "Test School",
                "url": "https://school.learnworlds.com",
                "description": "Test School Description",
                "address": "Test Address",
                "company_name": "Test Company",
                "contact_email": "contact@test.com",
                "support_email": "support@test.com",
                "sales_email": "sales@test.com"
            }
        }
    ]
    
    # Test 1: Send webhook payloads
    print("\n📤 Sending webhook payloads...")
    for i, payload in enumerate(test_payloads, 1):
        print(f"  Sending payload {i}...")
        
        try:
            response = requests.post(
                webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✅ Success: {result.get('message', 'Unknown')}")
                print(f"     Assessment type: {result.get('assessment_type')}")
                print(f"     User email: {result.get('user_email')}")
            else:
                print(f"  ❌ Error: {response.status_code}")
                print(f"     Response: {response.text}")
                
        except Exception as e:
            print(f"  ❌ Exception: {str(e)}")
    
    # Test 2: Check status
    print("\n📊 Checking status...")
    try:
        response = requests.get(status_url, timeout=30)
        
        if response.status_code == 200:
            status = response.json()
            print(f"  ✅ Status: {status.get('status')}")
            
            batch_status = status.get('batch_status', {})
            counters = batch_status.get('counters', {})
            queued_students = batch_status.get('queued_students', 0)
            
            print(f"     Queued students: {queued_students}")
            print(f"     Counters: {counters}")
            
            if batch_status.get('batch_state'):
                batch_state = batch_status['batch_state']
                print(f"     Batch ID: {batch_state.get('batch_id')}")
                print(f"     Deadline: {batch_state.get('deadline')}")
                print(f"     Open: {batch_state.get('open')}")
        else:
            print(f"  ❌ Error: {response.status_code}")
            print(f"     Response: {response.text}")
            
    except Exception as e:
        print(f"  ❌ Exception: {str(e)}")
    
    # Test 3: Wait and check again (simulate batch processing)
    print("\n⏳ Waiting 30 seconds to simulate batch processing...")
    time.sleep(30)
    
    print("\n📊 Checking status again...")
    try:
        response = requests.get(status_url, timeout=30)
        
        if response.status_code == 200:
            status = response.json()
            print(f"  ✅ Status: {status.get('status')}")
            
            batch_status = status.get('batch_status', {})
            queued_students = batch_status.get('queued_students', 0)
            counters = batch_status.get('counters', {})
            
            print(f"     Queued students: {queued_students}")
            print(f"     Counters: {counters}")
        else:
            print(f"  ❌ Error: {response.status_code}")
            print(f"     Response: {response.text}")
            
    except Exception as e:
        print(f"  ❌ Exception: {str(e)}")

def test_invalid_payload():
    """Test webhook with invalid payloads"""
    
    webhook_url = os.getenv('WEBHOOK_URL', 'http://localhost:8080/webhook')
    
    print("\n🧪 Testing invalid payloads...")
    
    # Test 1: Missing assessment URL
    invalid_payload_1 = {
        "user": {
            "id": "test_user",
            "email": "test@test.com"
        },
        "assessment": {
            "title": "Test Assessment"
            # Missing URL
        }
    }
    
    print("  Testing missing assessment URL...")
    try:
        response = requests.post(
            webhook_url,
            json=invalid_payload_1,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 400:
            print("  ✅ Correctly rejected invalid payload")
        else:
            print(f"  ❌ Unexpected response: {response.status_code}")
            
    except Exception as e:
        print(f"  ❌ Exception: {str(e)}")
    
    # Test 2: Unknown assessment ID
    invalid_payload_2 = {
        "user": {
            "id": "test_user",
            "email": "test@test.com"
        },
                 "assessment": {
             "title": "Unknown Assessment",
             "url": "https://school.learnworlds.com/unit=507f1f77bcf86cd799439999"
         }
    }
    
    print("  Testing unknown assessment ID...")
    try:
        response = requests.post(
            webhook_url,
            json=invalid_payload_2,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 400:
            print("  ✅ Correctly rejected unknown assessment ID")
        else:
            print(f"  ❌ Unexpected response: {response.status_code}")
            
    except Exception as e:
        print(f"  ❌ Exception: {str(e)}")

if __name__ == "__main__":
    print("🚀 Webhook Service Test")
    print("=" * 50)
    
    # Test valid payloads
    test_webhook()
    
    # Test invalid payloads
    test_invalid_payload()
    
    print("\n✅ Test completed!")
