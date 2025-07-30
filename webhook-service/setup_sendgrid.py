#!/usr/bin/env python3
"""
SendGrid Setup Script
Helps configure SendGrid for email delivery in the webhook service
"""

import os
import requests
import json
from dotenv import load_dotenv

def check_sendgrid_config():
    """Check if SendGrid is properly configured"""
    load_dotenv()
    
    required_vars = [
        'EMAIL_FROM',
        'EMAIL_PASS',  # SendGrid API key
        'SMTP_SERVER',
        'SMTP_PORT'
    ]
    
    print("🔍 Checking SendGrid Configuration...")
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            print(f"✅ {var}: {'*' * len(value)}")
    
    if missing_vars:
        print(f"\n❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    # Check if SendGrid server is configured
    smtp_server = os.getenv('SMTP_SERVER')
    if smtp_server != 'smtp.sendgrid.net':
        print(f"⚠️  SMTP_SERVER should be 'smtp.sendgrid.net', got: {smtp_server}")
    
    smtp_port = os.getenv('SMTP_PORT')
    if smtp_port != '587':
        print(f"⚠️  SMTP_PORT should be '587', got: {smtp_port}")
    
    print("\n✅ SendGrid configuration looks good!")
    return True

def test_sendgrid_connection():
    """Test SendGrid SMTP connection"""
    import smtplib
    from email.mime.text import MIMEText
    
    print("\n🧪 Testing SendGrid SMTP Connection...")
    
    try:
        # Create test email
        msg = MIMEText('This is a test email from your webhook service.')
        msg['Subject'] = 'SendGrid Test - Webhook Service'
        msg['From'] = os.getenv('EMAIL_FROM')
        msg['To'] = os.getenv('EMAIL_FROM')  # Send to yourself for testing
        
        # Connect to SendGrid
        server = smtplib.SMTP(os.getenv('SMTP_SERVER'), int(os.getenv('SMTP_PORT')))
        server.starttls()
        server.login(os.getenv('EMAIL_FROM'), os.getenv('EMAIL_PASS'))
        
        # Send test email
        server.send_message(msg)
        server.quit()
        
        print("✅ SendGrid connection test successful!")
        print("📧 Check your email for the test message.")
        return True
        
    except Exception as e:
        print(f"❌ SendGrid connection test failed: {e}")
        return False

def generate_env_template():
    """Generate SendGrid environment template"""
    template = """# SendGrid Configuration
EMAIL_FROM=your-verified-sender@yourdomain.com
EMAIL_PASS=your_sendgrid_api_key
SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587

# Other required variables
CLIENT_ID=your_client_id
SCHOOL_DOMAIN=your_school_domain
ACCESS_TOKEN=your_access_token
LEARNWORLDS_WEBHOOK_SECRET=your_webhook_secret
STORAGE_BACKEND=gcp
GCP_PROJECT_ID=your_project_id
GCP_BUCKET_NAME=your_bucket_name
GOOGLE_SERVICE_ACCOUNT_KEY=your_base64_encoded_key
"""
    
    with open('env.sendgrid.template', 'w') as f:
        f.write(template)
    
    print("📝 Created env.sendgrid.template file")
    print("📋 Copy this file to .env and update with your SendGrid credentials")

def main():
    """Main setup function"""
    print("🚀 SendGrid Setup for Webhook Service")
    print("=" * 50)
    
    # Check current configuration
    if check_sendgrid_config():
        # Test connection
        test_sendgrid_connection()
    else:
        print("\n📋 Setup Instructions:")
        print("1. Sign up at sendgrid.com")
        print("2. Verify your sender email/domain")
        print("3. Generate an API key")
        print("4. Update your environment variables")
        print("5. Run this script again to test")
        
        # Generate template
        generate_env_template()

if __name__ == "__main__":
    main()