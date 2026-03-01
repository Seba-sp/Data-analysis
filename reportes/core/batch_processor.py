"""Batch processor that delegates report execution to PipelineRunner."""

import logging
import os
import time
from typing import Dict, Any

from core.firestore_service import FirestoreService
from core.runner import PipelineRunner

logger = logging.getLogger(__name__)


class BatchProcessor:
    def __init__(self):
        """Initialize batch processor from environment variables."""
        self.batch_interval_minutes = int(os.getenv('BATCH_INTERVAL_MINUTES', '15'))

    def process_report_type(self, report_type: str) -> bool:
        """Run the full report pipeline for a given report type.

        Delegates directly to PipelineRunner.run() — no subprocess involved.

        Args:
            report_type: Report type key (e.g. 'diagnosticos').

        Returns:
            True if pipeline succeeded, False on any error.
        """
        try:
            runner = PipelineRunner(report_type=report_type)
            result = runner.run()
            logger.info(f"[{report_type}] Pipeline result: {result}")
            return result["success"]
        except Exception as exc:
            logger.error(f"[{report_type}] Pipeline error: {exc}")
            return False

    def process_batch(self, report_type: str, batch_id: str) -> Dict[str, Any]:
        """Process all queued students for a report type in a single batch.

        Retrieves queued students from Firestore, runs the pipeline once, then
        cleans up queue and batch state.

        Args:
            report_type: Report type key determining the Firestore namespace.
            batch_id: Batch identifier for logging and result tracking.

        Returns:
            Dict with keys: success, batch_id, students_processed,
            processing_time, errors.
        """
        results: Dict[str, Any] = {
            'success': True,
            'batch_id': batch_id,
            'students_processed': 0,
            'processing_time': 0,
            'errors': [],
        }

        start_time = time.time()
        fs = FirestoreService(report_type)

        try:
            logger.info(f"[{report_type}] Starting batch processing for batch {batch_id}")

            students = fs.get_queued_students()
            if not students:
                logger.info(f"[{report_type}] No students in queue to process")
                results['students_processed'] = 0
                return results

            results['students_processed'] = len(students)
            logger.info(f"[{report_type}] Processing {len(students)} students")

            success = self.process_report_type(report_type)
            if not success:
                results['errors'].append(f"Pipeline failed for {report_type}")

            # Cleanup — clear queue and batch state regardless of pipeline outcome
            if not fs.clear_queue():
                logger.warning(f"[{report_type}] Failed to clear queue")

            if not fs.clear_batch_state():
                logger.warning(f"[{report_type}] Failed to clear batch state")

            results['processing_time'] = time.time() - start_time
            logger.info(
                f"[{report_type}] Batch processing completed in "
                f"{results['processing_time']:.2f}s"
            )
            return results

        except Exception as e:
            results['success'] = False
            results['errors'].append(f"Unexpected error: {str(e)}")
            logger.error(f"[{report_type}] Error in batch processing: {str(e)}")
            return results
