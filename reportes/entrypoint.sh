#!/bin/bash
# entrypoint.sh — mode switch for unified Cloud Run container
# If REPORT_TYPE is set: run pipeline as one-shot batch job and exit
# If REPORT_TYPE is not set: start webhook HTTP server (persistent)
set -e

if [ -n "$REPORT_TYPE" ]; then
    echo "[entrypoint] Batch mode: REPORT_TYPE=$REPORT_TYPE"
    exec python main.py --report-type "$REPORT_TYPE"
else
    echo "[entrypoint] Webhook server mode"
    exec functions-framework \
        --source=webhook_service.py \
        --target=webhook_handler \
        --port=8080
fi
