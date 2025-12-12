#!/usr/bin/env python3
"""
Webhook Service - Main service for handling LearnWorlds webhooks and batch processing
"""

import functions_framework
import logging
import time
import uuid
import hmac
import os
from flask import Request, jsonify
from typing import Dict, Any

# Import services with error handling
try:
    from assessment_mapper import assessment_mapper
    from firestore_service import firestore_service
    from task_service import task_service
    from batch_processor import batch_processor
    SERVICES_AVAILABLE = True
except Exception as e:
    logger.warning(f"Some services not available during import: {e}")
    SERVICES_AVAILABLE = False
    # Create dummy objects to prevent import errors
    assessment_mapper = None
    firestore_service = None
    task_service = None
    batch_processor = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get webhook secret from environment
WEBHOOK_SECRET = os.getenv('LEARNWORLDS_WEBHOOK_SECRET')
if not WEBHOOK_SECRET:
    logger.warning("LEARNWORLDS_WEBHOOK_SECRET not set - webhook signature validation will be disabled")

# Configuration for queue size limits
MAX_QUEUE_SIZE = int(os.getenv('MAX_QUEUE_SIZE', '400'))  # Default 300 students
MEMORY_SIZE_MB = int(os.getenv('MEMORY_SIZE_MB', '512'))  # Default 512MB

# Calculate dynamic queue size based on memory
def get_max_queue_size() -> int:
    """Calculate max queue size based on available memory"""
    if MEMORY_SIZE_MB >= 2048:
        return min(MAX_QUEUE_SIZE, 1500)  # 2GB+ can handle ~1500 reports
    elif MEMORY_SIZE_MB >= 1024:
        return min(MAX_QUEUE_SIZE, 800)   # 1GB can handle ~800 reports
    else:
        return min(MAX_QUEUE_SIZE, 400)   # 512MB can handle ~400 reports

@functions_framework.http
def webhook_handler(request: Request):
    """
    Main webhook handler for Cloud Functions
    
    Handles:
    - POST: Incoming webhooks from LearnWorlds
    - GET: Batch processing triggered by Cloud Tasks
    """
    if request.method == 'POST':
        return handle_webhook(request)
    elif request.method == 'GET':
        return process_batch(request)
    else:
        return jsonify({'error': 'Method not allowed'}), 405

def validate_signature(request: Request) -> bool:
    """
    Validate LearnWorlds webhook signature
    
    Args:
        request: Flask request object
        
    Returns:
        True if signature is valid, False otherwise
    """
    try:
        if not WEBHOOK_SECRET:
            logger.warning("Webhook secret not configured - skipping signature validation")
            return True
        
        # Get signature from header
        signature_header = request.headers.get("Learnworlds-Webhook-Signature")
        if not signature_header:
            logger.warning("No signature header found")
            return False
        
        # Extract signature value (remove v1= prefix)
        if not signature_header.startswith("v1="):
            logger.warning("Invalid signature format")
            return False
        
        received_signature = signature_header[3:]  # Remove "v1=" prefix
        
        # Calculate expected signature
        payload = request.get_data()
        logger.info(f"Payload length: {len(payload)} bytes")
        
        # Use raw webhook secret without encoding
        expected_signature = WEBHOOK_SECRET
        
        logger.info(f"Webhook secret length: {len(WEBHOOK_SECRET)}")
        
        # Compare signatures
        if hmac.compare_digest(received_signature, expected_signature):
            logger.info("Webhook signature validated successfully")
            return True
        else:
            logger.warning("Signature validation failed")
            return False
            
    except Exception as e:
        logger.error(f"Error validating signature: {str(e)}")
        return False

def handle_webhook(request: Request):
    """
    Handle incoming webhook from LearnWorlds
    
    Args:
        request: Flask request object
        
    Returns:
        JSON response
    """
    try:
        # Check if services are available
        if not SERVICES_AVAILABLE:
            return jsonify({'error': 'Services not properly initialized. Check environment variables.'}), 500
        # Validate webhook signature
        if not validate_signature(request):
            return jsonify({'error': 'Invalid webhook signature'}), 401
        
        # Get webhook payload
        payload = request.get_json()
        if not payload:
            return jsonify({'error': 'No payload received'}), 400
        
        logger.info(f"Received webhook payload: {payload}")
        
        # Extract assessment URL
        assessment_url = payload.get('assessment', {}).get('url')
        if not assessment_url:
            return jsonify({'error': 'No assessment URL in payload'}), 400
        
        # Extract assessment ID from URL
        assessment_id = assessment_mapper.extract_assessment_id(assessment_url)
        if not assessment_id:
            return jsonify({'error': 'Could not extract assessment ID from URL'}), 400
        
        # Map assessment ID to type
        assessment_type = assessment_mapper.get_assessment_type(assessment_id)
        if not assessment_type:
            return jsonify({'error': f'Unknown assessment ID: {assessment_id}'}), 400
        
        # Extract user information
        user_info = payload.get('user', {})
        user_email = user_info.get('email')
        user_id = user_info.get('id')
        
        if not user_email:
            return jsonify({'error': 'No user email in payload'}), 400
        
        # Create student data for queue
        student_data = {
            'assessment_type': assessment_type,
            'assessment_id': assessment_id,
            'user_email': user_email,
            'user_id': user_id,
            'assessment_url': assessment_url,
            'timestamp': time.time()
        }
        
        # Queue student
        if not firestore_service.queue_student(student_data):
            return jsonify({'error': 'Failed to queue student'}), 500
        
        # Increment counter
        if not firestore_service.increment_counter(assessment_type):
            logger.warning(f"Failed to increment counter for {assessment_type}")
        
        # Check queue size for early processing trigger
        current_queue_size = firestore_service.get_queue_count()
        max_queue_size = get_max_queue_size()
        
        should_trigger_early = current_queue_size >= max_queue_size
        batch_created = False
        
        # Check if this is the first student in a new batch
        if not firestore_service.is_batch_active():
            # Create new batch
            batch_id = str(uuid.uuid4())
            
            if should_trigger_early:
                # Trigger immediate processing
                deadline = int(time.time() + 30)  # 30 seconds from now for immediate processing
                logger.info(f"Queue size ({current_queue_size}) reached limit ({max_queue_size}). Triggering immediate processing.")
            else:
                # Normal 15-minute delay
                deadline = int(time.time() + (15 * 60))  # 15 minutes from now
            
            # Create batch state
            if not firestore_service.create_batch_state(batch_id, deadline):
                logger.error("Failed to create batch state")
                return jsonify({'error': 'Failed to create batch state'}), 500
            
            # Create delayed task for batch processing
            delay_seconds = 30 if should_trigger_early else (15 * 60)
            if not task_service.create_delayed_task(delay_seconds, batch_id):
                logger.error("Failed to create delayed task")
                return jsonify({'error': 'Failed to create delayed task'}), 500
            
            batch_created = True
            logger.info(f"Created new batch {batch_id} with deadline {deadline} ({'immediate' if should_trigger_early else 'normal'} processing)")
        else:
            # Check if we should trigger early processing for existing batch
            if should_trigger_early:
                logger.info(f"Queue size ({current_queue_size}) reached limit ({max_queue_size}) for existing batch. Processing will be triggered shortly.")
            else:
                logger.info("Added student to existing batch")
        
        # Return success response
        return jsonify({
            'status': 'success',
            'message': 'Student queued for batch processing',
            'assessment_type': assessment_type,
            'user_email': user_email,
            'queue_info': {
                'current_size': current_queue_size,
                'max_size': max_queue_size,
                'batch_created': batch_created,
                'early_trigger': should_trigger_early
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error handling webhook: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

def process_batch(request: Request):
    """
    Process batch of queued students
    
    Args:
        request: Flask request object
        
    Returns:
        JSON response
    """
    try:
        # Check if services are available
        if not SERVICES_AVAILABLE:
            return jsonify({'error': 'Services not properly initialized. Check environment variables.'}), 500
        # Get batch ID from query parameters
        batch_id = request.args.get('batch_id')
        if not batch_id:
            return jsonify({'error': 'No batch_id provided'}), 400
        
        logger.info(f"Processing batch: {batch_id}")
        
        # Process the batch
        results = batch_processor.process_batch(batch_id)
        
        if results['success']:
            return jsonify({
                'status': 'success',
                'message': 'Batch processing completed',
                'results': results
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Batch processing failed',
                'results': results
            }), 500
            
    except Exception as e:
        logger.error(f"Error processing batch: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@functions_framework.http
def status_handler(request: Request):
    """
    Status endpoint to check system health and current batch status
    
    Args:
        request: Flask request object
        
    Returns:
        JSON response with system status
    """
    try:
        # Check if services are available
        if not SERVICES_AVAILABLE:
            return jsonify({'error': 'Services not properly initialized. Check environment variables.'}), 500
        # Get batch status
        status = batch_processor.get_batch_status()
        
        # Get queue info
        queue_info = task_service.get_queue_info()
        
        # Get assessment mapping info
        mapping_info = assessment_mapper.get_mapping_info()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': time.time(),
            'batch_status': status,
            'queue_info': queue_info,
            'assessment_mapping': mapping_info
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': time.time()
        }), 500

@functions_framework.http
def cleanup_handler(request: Request):
    """
    Cleanup endpoint to manually clear queue and reset state
    
    Args:
        request: Flask request object
        
    Returns:
        JSON response
    """
    try:
        # Check if services are available
        if not SERVICES_AVAILABLE:
            return jsonify({'error': 'Services not properly initialized. Check environment variables.'}), 500
        # Clear queue
        queue_cleared = firestore_service.clear_queue()
        
        # Reset counters
        counters_reset = firestore_service.reset_counters()
        
        # Clear batch state
        state_cleared = firestore_service.clear_batch_state()
        
        # Purge task queue
        queue_purged = task_service.purge_queue()
        
        return jsonify({
            'status': 'success',
            'message': 'Cleanup completed',
            'results': {
                'queue_cleared': queue_cleared,
                'counters_reset': counters_reset,
                'state_cleared': state_cleared,
                'queue_purged': queue_purged
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        return jsonify({'error': f'Cleanup failed: {str(e)}'}), 500

# For local development and testing
if __name__ == "__main__":
    from flask import Flask, request
    
    app = Flask(__name__)
    
    @app.route('/webhook', methods=['POST'])
    def local_webhook():
        return handle_webhook(request)
    
    @app.route('/process-batch', methods=['GET'])
    def local_process_batch():
        return process_batch(request)
    
    @app.route('/status', methods=['GET'])
    def local_status():
        return status_handler(request)
    
    @app.route('/cleanup', methods=['POST'])
    def local_cleanup():
        return cleanup_handler(request)
    
    app.run(host='0.0.0.0', port=8080, debug=True)
