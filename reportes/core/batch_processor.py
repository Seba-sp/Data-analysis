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

    def process_report_type(self, report_type: str, assessment_name: str = "") -> Dict[str, Any]:
        """Run the full report pipeline for a given report type and assessment.

        Delegates directly to PipelineRunner.run() — no subprocess involved.

        Args:
            report_type: Report type key (e.g. 'test_de_eje').
            assessment_name: Specific assessment name to scope the download.
                When non-empty, the generator will download only this assessment.
                Empty string means all assessments (legacy behaviour).

        Returns:
            Pipeline result payload with success, records_processed, emails_sent, errors.
        """
        try:
            runner = PipelineRunner(report_type=report_type, assessment_name=assessment_name)
            result = runner.run()
            logger.info(f"[{report_type}] Pipeline result: {result}")
            return {
                "success": bool(result.get("success")),
                "records_processed": int(result.get("records_processed", 0)),
                "emails_sent": int(result.get("emails_sent", 0)),
                "errors": list(result.get("errors", [])),
            }
        except Exception as exc:
            logger.error(f"[{report_type}] Pipeline error: {exc}")
            return {
                "success": False,
                "records_processed": 0,
                "emails_sent": 0,
                "errors": [f"Pipeline exception for {report_type}: {exc}"],
            }

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
            'records_processed': 0,
            'emails_sent': 0,
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

            # Group students by assessment_name so each assessment is downloaded independently.
            # Students with no assessment_name key (legacy records) fall into the "" group.
            by_assessment: Dict[str, list] = {}
            for student in students:
                name = student.get("assessment_name", "")
                by_assessment.setdefault(name, []).append(student)

            logger.info(
                f"[{report_type}] Grouped into {len(by_assessment)} assessment group(s): "
                f"{list(by_assessment.keys())}"
            )

            for assessment_name_key, _group in by_assessment.items():
                pipeline_result = self.process_report_type(
                    report_type, assessment_name=assessment_name_key
                )
                results['records_processed'] += pipeline_result.get('records_processed', 0)
                results['emails_sent'] += pipeline_result.get('emails_sent', 0)
                results['errors'].extend(pipeline_result.get('errors', []))
                if not pipeline_result.get('success', False):
                    results['errors'].append(
                        f"Pipeline failed for {report_type} assessment={assessment_name_key!r}"
                    )

            # Cleanup — clear queue and batch state regardless of pipeline outcome
            if not fs.clear_queue():
                cleanup_error = f"Failed to clear queue for {report_type}"
                logger.warning(f"[{report_type}] {cleanup_error}")
                results['errors'].append(cleanup_error)

            if not fs.clear_batch_state():
                cleanup_error = f"Failed to clear batch state for {report_type}"
                logger.warning(f"[{report_type}] {cleanup_error}")
                results['errors'].append(cleanup_error)

            results['processing_time'] = time.time() - start_time
            results['success'] = len(results['errors']) == 0

            if results['success']:
                logger.info(
                    f"[{report_type}] Batch processing completed successfully in "
                    f"{results['processing_time']:.2f}s "
                    f"(records_processed={results['records_processed']}, emails_sent={results['emails_sent']})"
                )
            else:
                logger.warning(
                    f"[{report_type}] Batch processing completed with errors in "
                    f"{results['processing_time']:.2f}s "
                    f"(records_processed={results['records_processed']}, "
                    f"emails_sent={results['emails_sent']}, errors={len(results['errors'])})"
                )
            return results

        except Exception as e:
            results['success'] = False
            results['errors'].append(f"Unexpected error: {str(e)}")
            logger.error(f"[{report_type}] Error in batch processing: {str(e)}")
            return results
