#!/usr/bin/env python3
"""
Script to encode service account key for .env file
This avoids issues with newlines in the private_key field
"""

import json
import base64
import os

def encode_service_account_key():
    """Encode service account key file to base64 for .env file"""
    
    # Check if service account key file exists
    key_file = 'service-account-key.json'
    if not os.path.exists(key_file):
        print(f"❌ {key_file} not found in current directory")
        print("Please make sure the service account key file is in the same directory as this script")
        return
    
    try:
        # Read the JSON file
        with open(key_file, 'r') as f:
            service_account_data = json.load(f)
        
        # Convert to JSON string (this will escape newlines properly)
        json_string = json.dumps(service_account_data)
        
        # Encode to base64
        encoded = base64.b64encode(json_string.encode('utf-8')).decode('utf-8')
        
        print("✅ Service account key encoded successfully!")
        print("\n📋 Add this line to your .env file:")
        print(f"GOOGLE_SERVICE_ACCOUNT_KEY={encoded}")
        
        print("\n💡 Or use this complete line (copy and paste):")
        print("-" * 50)
        print(f"GOOGLE_SERVICE_ACCOUNT_KEY={encoded}")
        print("-" * 50)
        
        # Also show how to decode it back (for verification)
        print("\n🔍 To verify the encoding, you can decode it back:")
        decoded = base64.b64decode(encoded).decode('utf-8')
        print("Decoded length:", len(decoded))
        print("First 100 characters:", decoded[:100])
        
    except Exception as e:
        print(f"❌ Error encoding service account key: {e}")

if __name__ == "__main__":
    encode_service_account_key() 