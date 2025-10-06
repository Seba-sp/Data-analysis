#!/usr/bin/env python3
"""
Minimal Webhook Service for Cloud Functions deployment
"""

import functions_framework
import logging
import json
import os
from flask import Request, jsonify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@functions_framework.http
def webhook_handler(request: Request):
    """
    Main webhook handler for Cloud Functions
    """
    try:
        logger.info(f"Received {request.method} request")
        
        if request.method == 'POST':
            return handle_webhook(request)
        elif request.method == 'GET':
            return jsonify({
                'status': 'healthy',
                'message': 'Webhook service is running',
                'timestamp': str(os.time.time())
            }), 200
        else:
            return jsonify({'error': 'Method not allowed'}), 405
            
    except Exception as e:
        logger.error(f"Error in webhook_handler: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

def handle_webhook(request: Request):
    """
    Handle incoming webhook from LearnWorlds
    """
    try:
        # Get webhook payload
        payload = request.get_json()
        if not payload:
            return jsonify({'error': 'No payload received'}), 400
        
        logger.info(f"Received webhook payload: {payload}")
        
        # Extract basic information
        assessment_url = payload.get('assessment', {}).get('url', '')
        user_email = payload.get('user', {}).get('email', '')
        
        if not assessment_url:
            return jsonify({'error': 'No assessment URL in payload'}), 400
        
        if not user_email:
            return jsonify({'error': 'No user email in payload'}), 400
        
        # For now, just log and return success
        logger.info(f"Processing webhook for user: {user_email}, assessment: {assessment_url}")
        
        return jsonify({
            'status': 'success',
            'message': 'Webhook received successfully',
            'user_email': user_email,
            'assessment_url': assessment_url
        }), 200
        
    except Exception as e:
        logger.error(f"Error handling webhook: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@functions_framework.http
def status_handler(request: Request):
    """
    Status endpoint
    """
    try:
        return jsonify({
            'status': 'healthy',
            'message': 'Status service is running',
            'services_available': False,
            'note': 'This is a minimal deployment for testing'
        }), 200
    except Exception as e:
        logger.error(f"Error in status_handler: {str(e)}")
        return jsonify({'error': str(e)}), 500

@functions_framework.http
def cleanup_handler(request: Request):
    """
    Cleanup endpoint
    """
    try:
        return jsonify({
            'status': 'success',
            'message': 'Cleanup service is running (minimal mode)'
        }), 200
    except Exception as e:
        logger.error(f"Error in cleanup_handler: {str(e)}")
        return jsonify({'error': str(e)}), 500

# For local development
if __name__ == "__main__":
    from flask import Flask, request
    
    app = Flask(__name__)
    
    @app.route('/webhook', methods=['POST', 'GET'])
    def local_webhook():
        return webhook_handler(request)
    
    @app.route('/status', methods=['GET'])
    def local_status():
        return status_handler(request)
    
    @app.route('/cleanup', methods=['POST'])
    def local_cleanup():
        return cleanup_handler(request)
    
    app.run(host='0.0.0.0', port=8080, debug=True)
