#!/usr/bin/env python3
"""
Webhook service for individual student assessment completions
Handles real-time processing when students complete diagnosis assessments
"""

import os
from flask import Flask, request, jsonify
from webhook_service import WebhookService
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Initialize webhook service
webhook_service = WebhookService()

@app.route("/webhook", methods=["POST"])
def webhook():
    """Handle incoming webhook from LearnWorlds"""
    try:
        logger.info("Webhook received")
        
        # Validate webhook signature
        if not webhook_service.validate_signature(request):
            logger.warning("Invalid webhook signature")
            return jsonify({"error": "Invalid signature"}), 401
        
        # Process the webhook
        result = webhook_service.process_webhook(request.json)
        
        if result["success"]:
            logger.info(f"Webhook processed successfully for user {result.get('user_id')}")
            return jsonify({"status": "ok", "message": result["message"]}), 200
        else:
            logger.error(f"Webhook processing failed: {result['error']}")
            return jsonify({"error": result["error"]}), 400
            
    except Exception as e:
        logger.error(f"Unexpected error in webhook: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/healthz", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok"}), 200

@app.route("/", methods=["GET"])
def root():
    """Root endpoint"""
    return jsonify({
        "service": "Data Analysis Webhook Service",
        "version": "1.0.0",
        "endpoints": {
            "webhook": "/webhook (POST)",
            "health": "/healthz (GET)"
        }
    }), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    
    logger.info(f"Starting webhook service on port {port}")
    app.run(host="0.0.0.0", port=port) 