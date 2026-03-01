#!/usr/bin/env python3
"""
Unified webhook service — handles LearnWorlds webhooks for all registered report types.

Entry point: webhook_handler (functions-framework target)
Routes:
  POST /             -> handle_webhook   (LearnWorlds event)
  GET  /process-batch?report_type=X&batch_id=Y  -> process_batch (Cloud Tasks callback)
  GET  /status       -> status_handler   (health + queue state)
  POST /cleanup      -> cleanup_handler  (manual queue reset)
"""

import functions_framework
import logging
import time
import uuid
import hmac
import os
from flask import Request, jsonify
from typing import Optional

from core.firestore_service import FirestoreService
from core.task_service import TaskService
from core.batch_processor import BatchProcessor
from core.assessment_mapper import AssessmentMapper
from reports import REGISTRY

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level configuration
# ---------------------------------------------------------------------------
WEBHOOK_SECRET = os.getenv('LEARNWORLDS_WEBHOOK_SECRET')
if not WEBHOOK_SECRET:
    logger.warning("LEARNWORLDS_WEBHOOK_SECRET not set — webhook signature validation will be disabled")

BATCH_INTERVAL_MINUTES = int(os.getenv('BATCH_INTERVAL_MINUTES', '15'))
MAX_QUEUE_SIZE = int(os.getenv('MAX_QUEUE_SIZE', '400'))
MEMORY_SIZE_MB = int(os.getenv('MEMORY_SIZE_MB', '512'))

# ---------------------------------------------------------------------------
# Lazy service initialization
# ---------------------------------------------------------------------------
_am: Optional[AssessmentMapper] = None
_ts: Optional[TaskService] = None
_bp: Optional[BatchProcessor] = None
_SERVICES_AVAILABLE = False


def _initialize_services() -> bool:
    """Initialize module-level service instances on first call (lazy init).

    Returns:
        True if services were already initialized or successfully initialized now.
        False if initialization failed.
    """
    global _am, _ts, _bp, _SERVICES_AVAILABLE

    if _SERVICES_AVAILABLE:
        return True

    try:
        _am = AssessmentMapper()
        _ts = TaskService()
        _bp = BatchProcessor()
        _SERVICES_AVAILABLE = True
        logger.info("Webhook services initialized successfully")
        return True
    except Exception as exc:
        logger.error(f"Failed to initialize webhook services: {exc}")
        _SERVICES_AVAILABLE = False
        return False


# ---------------------------------------------------------------------------
# Queue size helper
# ---------------------------------------------------------------------------

def get_max_queue_size() -> int:
    """Return the effective maximum queue size based on available memory."""
    if MEMORY_SIZE_MB >= 2048:
        return min(MAX_QUEUE_SIZE, 1500)
    elif MEMORY_SIZE_MB >= 1024:
        return min(MAX_QUEUE_SIZE, 800)
    else:
        return min(MAX_QUEUE_SIZE, 400)


# ---------------------------------------------------------------------------
# Single functions-framework entry point
# ---------------------------------------------------------------------------

@functions_framework.http
def webhook_handler(request: Request):
    """Single entry point — dispatches to sub-handlers by method and path."""
    if request.method == 'POST':
        if request.path == '/cleanup':
            return cleanup_handler(request)
        return handle_webhook(request)
    elif request.method == 'GET':
        if request.args.get('batch_id') or request.path == '/process-batch':
            return process_batch(request)
        elif request.path == '/status':
            return status_handler(request)
    return jsonify({'error': 'Method not allowed'}), 405


# ---------------------------------------------------------------------------
# HMAC signature validation
# ---------------------------------------------------------------------------

def validate_signature(request: Request) -> bool:
    """Validate the LearnWorlds webhook HMAC signature.

    Args:
        request: Incoming Flask request.

    Returns:
        True if the signature is valid (or secret is not configured), False otherwise.
    """
    try:
        if not WEBHOOK_SECRET:
            logger.warning("Webhook secret not configured — skipping signature validation")
            return True

        signature_header = request.headers.get("Learnworlds-Webhook-Signature")
        if not signature_header:
            logger.warning("No signature header found")
            return False

        if not signature_header.startswith("v1="):
            logger.warning("Invalid signature format (expected 'v1=' prefix)")
            return False

        received_signature = signature_header[3:]  # Remove "v1=" prefix

        payload = request.get_data()
        logger.info(f"Validating signature for payload length={len(payload)} bytes")

        # Compare received signature against the webhook secret directly
        if hmac.compare_digest(received_signature, WEBHOOK_SECRET):
            logger.info("Webhook signature validated successfully")
            return True
        else:
            logger.warning("Signature validation failed")
            return False

    except Exception as exc:
        logger.error(f"Error validating signature: {exc}")
        return False


# ---------------------------------------------------------------------------
# POST / — handle incoming LearnWorlds webhook event
# ---------------------------------------------------------------------------

def handle_webhook(request: Request):
    """Process an incoming LearnWorlds assessment-completion webhook.

    Flow:
      1. Validate HMAC signature.
      2. Extract assessment URL from payload.
      3. Map assessment_id -> (report_type, assessment_type) via AssessmentMapper.
      4. Queue student in FirestoreService(report_type).
      5. Schedule Cloud Tasks callback via TaskService if no batch is active.
    """
    try:
        if not _initialize_services():
            return jsonify({'error': 'Services not properly initialized. Check environment variables.'}), 500

        if not validate_signature(request):
            return jsonify({'error': 'Invalid webhook signature'}), 401

        payload = request.get_json()
        if not payload:
            return jsonify({'error': 'No payload received'}), 400

        logger.info(f"Received webhook payload keys: {list(payload.keys())}")

        # Extract assessment URL
        assessment_url = payload.get('assessment', {}).get('url')
        if not assessment_url:
            return jsonify({'error': 'No assessment URL in payload'}), 400

        # Map URL -> assessment_id -> (report_type, assessment_type)
        assessment_id = _am.extract_assessment_id(assessment_url)
        if not assessment_id:
            return jsonify({'error': 'Could not extract assessment ID from URL'}), 400

        route = _am.get_route(assessment_id)
        if route is None:
            return jsonify({'error': f'Unknown assessment ID: {assessment_id}'}), 400

        report_type, assessment_type = route

        # Extract user data
        user_info = payload.get('user', {})
        user_email = user_info.get('email')
        user_id = user_info.get('id')

        if not user_email:
            return jsonify({'error': 'No user email in payload'}), 400

        # Build student record
        student_data = {
            'report_type': report_type,
            'assessment_type': assessment_type,
            'assessment_id': assessment_id,
            'user_email': user_email,
            'user_id': user_id,
            'assessment_url': assessment_url,
            'timestamp': time.time(),
        }

        # Queue student and increment per-type counter
        fs = FirestoreService(report_type)

        if not fs.queue_student(student_data):
            return jsonify({'error': 'Failed to queue student'}), 500

        if not fs.increment_counter(assessment_type):
            logger.warning(f"[{report_type}] Failed to increment counter for {assessment_type}")

        # Determine if early triggering applies
        current_queue_size = fs.get_queue_count()
        max_queue_size = get_max_queue_size()
        should_trigger_early = current_queue_size >= max_queue_size
        batch_created = False

        if not fs.is_batch_active():
            batch_id = str(uuid.uuid4())

            if should_trigger_early:
                delay_seconds = 30
                deadline = int(time.time() + delay_seconds)
                logger.info(
                    f"[{report_type}] Queue size ({current_queue_size}) reached limit "
                    f"({max_queue_size}). Triggering immediate processing."
                )
            else:
                delay_seconds = BATCH_INTERVAL_MINUTES * 60
                deadline = int(time.time() + delay_seconds)

            if not fs.create_batch_state(batch_id, deadline):
                logger.error(f"[{report_type}] Failed to create batch state")
                return jsonify({'error': 'Failed to create batch state'}), 500

            if not _ts.create_delayed_task(report_type, delay_seconds, batch_id):
                logger.error(f"[{report_type}] Failed to create delayed task")
                return jsonify({'error': 'Failed to create delayed task'}), 500

            batch_created = True
            logger.info(
                f"[{report_type}] Created batch {batch_id} "
                f"({'immediate' if should_trigger_early else 'normal'} processing)"
            )
        else:
            if should_trigger_early:
                logger.info(
                    f"[{report_type}] Queue size ({current_queue_size}) reached limit "
                    f"({max_queue_size}) in active batch. Processing will trigger shortly."
                )
            else:
                logger.info(f"[{report_type}] Added student to existing batch")

        return jsonify({
            'status': 'success',
            'message': 'Student queued for batch processing',
            'report_type': report_type,
            'assessment_type': assessment_type,
            'user_email': user_email,
            'queue_info': {
                'current_size': current_queue_size,
                'max_size': max_queue_size,
                'batch_created': batch_created,
                'early_trigger': should_trigger_early,
            },
        }), 200

    except Exception as exc:
        logger.error(f"Error handling webhook: {exc}")
        return jsonify({'error': f'Internal server error: {exc}'}), 500


# ---------------------------------------------------------------------------
# GET /process-batch?report_type=X&batch_id=Y — Cloud Tasks callback
# ---------------------------------------------------------------------------

def process_batch(request: Request):
    """Delegate to BatchProcessor.process_batch() for the given report type.

    Query parameters:
        report_type: Report type key (e.g. 'diagnosticos').
        batch_id: Batch identifier matching the one stored in Firestore.
    """
    try:
        if not _initialize_services():
            return jsonify({'error': 'Services not properly initialized. Check environment variables.'}), 500

        report_type = request.args.get('report_type')
        if not report_type:
            return jsonify({'error': 'Missing required query parameter: report_type'}), 400

        batch_id = request.args.get('batch_id')
        if not batch_id:
            return jsonify({'error': 'Missing required query parameter: batch_id'}), 400

        logger.info(f"[{report_type}] Processing batch {batch_id}")

        results = _bp.process_batch(report_type, batch_id)

        if results.get('success'):
            return jsonify({
                'status': 'success',
                'message': 'Batch processing completed',
                'results': results,
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Batch processing failed',
                'results': results,
            }), 500

    except Exception as exc:
        logger.error(f"Error processing batch: {exc}")
        return jsonify({'error': f'Internal server error: {exc}'}), 500


# ---------------------------------------------------------------------------
# GET /status — health check and per-type queue state
# ---------------------------------------------------------------------------

def status_handler(request: Request):
    """Return health status and per-report-type queue information.

    Iterates REGISTRY keys — no hard-coded report type list.
    Response shape:
        {
            "status": "healthy",
            "timestamp": <float>,
            "report_types": {
                "<report_type>": {
                    "queue_count": N,
                    "batch_active": bool,
                    "batch_state": {...} | null
                }
            }
        }
    """
    try:
        if not _initialize_services():
            return jsonify({'error': 'Services not properly initialized. Check environment variables.'}), 500

        status_by_type = {}
        for report_type in REGISTRY:
            fs = FirestoreService(report_type)
            status_by_type[report_type] = {
                'queue_count': fs.get_queue_count(),
                'batch_active': fs.is_batch_active(),
                'batch_state': fs.get_batch_state(),
            }

        return jsonify({
            'status': 'healthy',
            'timestamp': time.time(),
            'report_types': status_by_type,
        }), 200

    except Exception as exc:
        logger.error(f"Error in status handler: {exc}")
        return jsonify({
            'status': 'error',
            'error': str(exc),
            'timestamp': time.time(),
        }), 500


# ---------------------------------------------------------------------------
# POST /cleanup — manual queue + state reset
# ---------------------------------------------------------------------------

def cleanup_handler(request: Request):
    """Clear queues, counters, and batch state for every registered report type.

    Iterates REGISTRY keys — no hard-coded report type list.
    Purges the shared Cloud Tasks queue once after per-type cleanup.
    """
    try:
        if not _initialize_services():
            return jsonify({'error': 'Services not properly initialized. Check environment variables.'}), 500

        results_by_type = {}
        for report_type in REGISTRY:
            fs = FirestoreService(report_type)
            results_by_type[report_type] = {
                'queue_cleared': fs.clear_queue(),
                'counters_reset': fs.reset_counters(),
                'state_cleared': fs.clear_batch_state(),
            }

        # Purge the shared Cloud Tasks queue once
        queue_purged = _ts.purge_queue()

        return jsonify({
            'status': 'success',
            'message': 'Cleanup completed',
            'results': results_by_type,
            'queue_purged': queue_purged,
        }), 200

    except Exception as exc:
        logger.error(f"Error during cleanup: {exc}")
        return jsonify({'error': f'Cleanup failed: {exc}'}), 500


# ---------------------------------------------------------------------------
# Local development
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from flask import Flask, request as flask_request

    app = Flask(__name__)

    @app.route('/', methods=['POST'])
    def local_webhook():
        return handle_webhook(flask_request)

    @app.route('/process-batch', methods=['GET'])
    def local_process_batch():
        return process_batch(flask_request)

    @app.route('/status', methods=['GET'])
    def local_status():
        return status_handler(flask_request)

    @app.route('/cleanup', methods=['POST'])
    def local_cleanup():
        return cleanup_handler(flask_request)

    app.run(host='0.0.0.0', port=8080, debug=True)
