"""Firestore queue management with per-report-type path namespacing."""

import logging
import time
from typing import Dict, List, Optional, Any
from google.cloud import firestore
from google.cloud.firestore import Transaction
from google.cloud.firestore_v1 import FieldFilter

logger = logging.getLogger(__name__)


class FirestoreService:
    def __init__(self, report_type: str):
        """Initialize Firestore client with per-report-type path namespacing.

        Args:
            report_type: Report type key (e.g. 'diagnosticos', 'diagnosticos_uim').
                         All collection paths are namespaced under
                         report_types/{report_type}/.
        """
        self.db = firestore.Client()
        self.report_type = report_type
        self.queue_collection = f"report_types/{report_type}/queue"
        self.state_collection = f"report_types/{report_type}/state"
        self.counters_collection = f"report_types/{report_type}/counters"

    def increment_counter(self, assessment_type: str, event_key: Optional[str] = None) -> bool:
        """Atomically increment counter for assessment type.

        Args:
            assessment_type: Assessment type document ID (e.g. 'M1', 'CL').
            event_key: Optional idempotency key. If already processed, the
                       counter is not incremented again.

        Returns:
            True if successful, False otherwise.
        """
        try:
            if not assessment_type:
                logger.error("Cannot increment counter: empty assessment_type")
                return False

            counter_ref = self.db.collection(self.counters_collection).document(assessment_type)

            @firestore.transactional
            def increment_in_transaction(transaction: Transaction, counter_ref):
                counter_doc = counter_ref.get(transaction=transaction)
                existing_event_keys = set()
                if counter_doc.exists:
                    counter_data = counter_doc.to_dict()
                    current_count = counter_data.get('count', 0)
                    existing_event_keys = set(counter_data.get('event_keys', []))
                    if event_key and event_key in existing_event_keys:
                        return False
                    next_event_keys = list(existing_event_keys)
                    if event_key:
                        next_event_keys.append(event_key)
                    payload = {'count': current_count + 1}
                    if next_event_keys:
                        payload['event_keys'] = sorted(set(next_event_keys))[-200:]
                    transaction.update(counter_ref, payload)
                else:
                    payload = {'count': 1}
                    if event_key:
                        payload['event_keys'] = [event_key]
                    transaction.set(counter_ref, payload)
                return True

            transaction = self.db.transaction()
            incremented = increment_in_transaction(transaction, counter_ref)
            if not incremented:
                logger.info(
                    f"Skipped duplicate counter increment for {assessment_type} event_key={event_key}"
                )
                return True

            logger.info(f"Incremented counter for {assessment_type}")
            return True

        except Exception as e:
            logger.error(f"Error incrementing counter for {assessment_type}: {str(e)}")
            return False

    def get_counters(self) -> Dict[str, int]:
        """Get current counters for all assessment types in this report type.

        Counters are read generically from Firestore — no hard-coded type list.

        Returns:
            Dictionary mapping document ID to count value.
        """
        try:
            counters: Dict[str, int] = {}
            counter_docs = self.db.collection(self.counters_collection).stream()

            for doc in counter_docs:
                counters[doc.id] = doc.to_dict().get('count', 0)

            logger.info(f"Retrieved counters: {counters}")
            return counters

        except Exception as e:
            logger.error(f"Error getting counters: {str(e)}")
            return {}

    def reset_counters(self) -> bool:
        """Reset all existing counters to zero.

        Reads existing counter documents generically — no hard-coded type list.

        Returns:
            True if successful, False otherwise.
        """
        try:
            batch = self.db.batch()

            counter_docs = self.db.collection(self.counters_collection).stream()
            for doc in counter_docs:
                batch.set(doc.reference, {'count': 0})

            batch.commit()
            logger.info("Reset all counters to zero")
            return True

        except Exception as e:
            logger.error(f"Error resetting counters: {str(e)}")
            return False

    def queue_student(self, student_data: Dict[str, Any]) -> bool:
        """Add student to queue.

        Args:
            student_data: Student data to queue.

        Returns:
            True if successful, False otherwise.
        """
        try:
            incoming_report_type = student_data.get('report_type')
            if incoming_report_type and incoming_report_type != self.report_type:
                logger.error(
                    f"Namespace mismatch while queuing student: expected report_type={self.report_type}, "
                    f"got report_type={incoming_report_type}"
                )
                return False

            if 'timestamp' not in student_data:
                student_data['timestamp'] = time.time()

            student_data['report_type'] = self.report_type
            student_data['status'] = 'queued'

            result = self.db.collection(self.queue_collection).add(student_data)

            logger.info(f"Queued student: {result[1].id}")
            return True

        except Exception as e:
            logger.error(f"Error queuing student: {str(e)}")
            return False

    def get_queued_students(self) -> List[Dict[str, Any]]:
        """Get all queued students.

        Returns:
            List of queued student data dictionaries.
        """
        try:
            students = []
            student_docs = (
                self.db.collection(self.queue_collection)
                .where(filter=FieldFilter('status', '==', 'queued'))
                .stream()
            )

            for doc in student_docs:
                student_data = doc.to_dict()
                student_data['id'] = doc.id
                students.append(student_data)

            logger.info(f"Retrieved {len(students)} queued students")
            return students

        except Exception as e:
            logger.error(f"Error getting queued students: {str(e)}")
            return []

    def get_queue_count(self) -> int:
        """Get count of queued students (aggregation query — more efficient than full list).

        Returns:
            Number of queued students.
        """
        try:
            query = (
                self.db.collection(self.queue_collection)
                .where(filter=FieldFilter('status', '==', 'queued'))
            )

            count_query = query.count()
            count_result = count_query.get()

            count = count_result[0][0].value if count_result else 0
            logger.info(f"Queue count: {count}")
            return count

        except Exception as e:
            logger.error(f"Error getting queue count: {str(e)}")
            try:
                students = self.get_queued_students()
                return len(students)
            except Exception:
                return 0

    def clear_queue(self) -> bool:
        """Clear all queued students.

        Returns:
            True if successful, False otherwise.
        """
        try:
            batch = self.db.batch()

            student_docs = (
                self.db.collection(self.queue_collection)
                .where(filter=FieldFilter('status', '==', 'queued'))
                .stream()
            )

            for doc in student_docs:
                batch.delete(doc.reference)

            batch.commit()
            logger.info("Cleared all queued students")
            return True

        except Exception as e:
            logger.error(f"Error clearing queue: {str(e)}")
            return False

    def create_batch_state(self, batch_id: str, deadline: int) -> bool:
        """Create batch state document.

        Args:
            batch_id: Unique batch identifier.
            deadline: Unix timestamp for batch deadline.

        Returns:
            True if successful, False otherwise.
        """
        try:
            state_data = {
                'batch_id': batch_id,
                'deadline': deadline,
                'open': True,
                'created_at': time.time()
            }

            self.db.collection(self.state_collection).document('currentBatch').set(state_data)
            logger.info(f"Created batch state: {batch_id}")
            return True

        except Exception as e:
            logger.error(f"Error creating batch state: {str(e)}")
            return False

    def get_batch_state(self) -> Optional[Dict[str, Any]]:
        """Get current batch state.

        Returns:
            Batch state data dict or None if not found.
        """
        try:
            state_doc = self.db.collection(self.state_collection).document('currentBatch').get()

            if state_doc.exists:
                return state_doc.to_dict()
            else:
                return None

        except Exception as e:
            logger.error(f"Error getting batch state: {str(e)}")
            return None

    def clear_batch_state(self) -> bool:
        """Clear current batch state document.

        Returns:
            True if successful, False otherwise.
        """
        try:
            self.db.collection(self.state_collection).document('currentBatch').delete()
            logger.info("Cleared batch state")
            return True

        except Exception as e:
            logger.error(f"Error clearing batch state: {str(e)}")
            return False

    def is_batch_active(self) -> bool:
        """Check if there is an active, non-expired batch.

        Returns:
            True if active batch exists and has not expired, False otherwise.
        """
        try:
            state = self.get_batch_state()

            if not state:
                return False

            if not state.get('open', False):
                return False

            deadline = state.get('deadline', 0)
            current_time = time.time()

            return current_time < deadline

        except Exception as e:
            logger.error(f"Error checking batch state: {str(e)}")
            return False
