#!/usr/bin/env python3
"""
Test script for webhook service
Helps test the webhook locally with sample data
"""

import requests
import json
import hmac
import hashlib
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def generate_signature(payload: str, secret: str) -> str:
    """Generate HMAC signature for webhook payload"""
    return hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def test_webhook():
    """Test webhook with sample data"""
    
    # Sample webhook payload (replace with actual data)
    sample_payload = {
        "user": {
            "id": "test_user_123",
            "username": "test_student",
            "email": "test@example.com"
        },
        "assessment": {
            "title": "Test de diagnóstico Parte 2",
            "url": "https://your-school.learnworlds.com/course/unit=507f1f77bcf86cd799439011"
        },
        "submission": {
            "id": "submission_123",
            "status": "completed",
            "grading_status": "graded",
            "answers": "sample_answers",
            "score": "85"
        },
        "school": {
            "name": "Test School",
            "url": "https://your-school.learnworlds.com",
            "description": "Test School Description",
            "address": "Test Address",
            "company_name": "Test Company",
            "contact_email": "contact@test.com",
            "support_email": "support@test.com",
            "sales_email": "sales@test.com"
        }
    }
    
    # Convert payload to JSON string
    payload_json = json.dumps(sample_payload)
    
    # Get webhook secret from environment
    webhook_secret = os.getenv("LEARNWORLDS_WEBHOOK_SECRET")
    if not webhook_secret:
        print("ERROR: LEARNWORLDS_WEBHOOK_SECRET not set in environment")
        return
    
    # Generate signature
    signature = generate_signature(payload_json, webhook_secret)
    
    # Prepare headers
    headers = {
        "Content-Type": "application/json",
        "Learnworlds-Webhook-Signature": f"v1={signature}"
    }
    
    # Send request to local webhook service
    webhook_url = "http://localhost:8080/webhook"
    
    try:
        print(f"Sending test webhook to {webhook_url}")
        print(f"Payload: {json.dumps(sample_payload, indent=2)}")
        print(f"Signature: v1={signature}")
        
        response = requests.post(
            webhook_url,
            data=payload_json,
            headers=headers,
            timeout=30
        )
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("\n✅ Webhook test successful!")
        else:
            print(f"\n❌ Webhook test failed with status {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Make sure the webhook service is running on localhost:8080")
        print("   Run: python webhook_main.py")
    except Exception as e:
        print(f"❌ Error testing webhook: {str(e)}")

def test_health_check():
    """Test health check endpoint"""
    try:
        response = requests.get("http://localhost:8080/healthz")
        print(f"Health check status: {response.status_code}")
        print(f"Health check response: {response.text}")
    except Exception as e:
        print(f"Health check failed: {str(e)}")

if __name__ == "__main__":
    print("=== Webhook Service Test ===\n")
    
    # Test health check first
    print("1. Testing health check...")
    test_health_check()
    print()
    
    # Test webhook
    print("2. Testing webhook...")
    test_webhook() 