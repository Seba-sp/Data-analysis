#!/usr/bin/env python3
"""
Firestore Service - Handles queue management, counters, and state tracking
"""

import logging
import time
from typing import Dict, List, Optional, Any
from google.cloud import firestore
from google.cloud.firestore import Transaction

logger = logging.getLogger(__name__)

class FirestoreService:
    def __init__(self):
        """Initialize Firestore client"""
        self.db = firestore.Client()
        self.counters_collection = "counters"
        self.queue_collection = "queue"
        self.state_collection = "state"
    
    def increment_counter(self, assessment_type: str) -> bool:
        """
        Atomically increment counter for assessment type
        
        Args:
            assessment_type: Assessment type (M1, F30M, B30M, Q30M, HYST)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            counter_ref = self.db.collection(self.counters_collection).document(assessment_type)
            
            # Use transaction for atomic increment
            @firestore.transactional
            def increment_in_transaction(transaction: Transaction, counter_ref):
                counter_doc = counter_ref.get(transaction=transaction)
                if counter_doc.exists:
                    current_count = counter_doc.to_dict().get('count', 0)
                    transaction.update(counter_ref, {'count': current_count + 1})
                else:
                    transaction.set(counter_ref, {'count': 1})
            
            transaction = self.db.transaction()
            increment_in_transaction(transaction, counter_ref)
            
            logger.info(f"Incremented counter for {assessment_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error incrementing counter for {assessment_type}: {str(e)}")
            return False
    
    def get_counters(self) -> Dict[str, int]:
        """
        Get current counters for all assessment types
        
        Returns:
            Dictionary with assessment type to count mapping
        """
        try:
            counters = {}
            counter_docs = self.db.collection(self.counters_collection).stream()
            
            for doc in counter_docs:
                assessment_type = doc.id
                count = doc.to_dict().get('count', 0)
                counters[assessment_type] = count
            
            # Ensure all assessment types are present
            for assessment_type in ['M1', 'F30M', 'B30M', 'Q30M', 'HYST']:
                if assessment_type not in counters:
                    counters[assessment_type] = 0
            
            logger.info(f"Retrieved counters: {counters}")
            return counters
            
        except Exception as e:
            logger.error(f"Error getting counters: {str(e)}")
            return {'M1': 0, 'F30M': 0, 'B30M': 0, 'Q30M': 0, 'HYST': 0}
    
    def reset_counters(self) -> bool:
        """
        Reset all counters to zero
        
        Returns:
            True if successful, False otherwise
        """
        try:
            batch = self.db.batch()
            
            for assessment_type in ['M1', 'F30M', 'B30M', 'Q30M', 'HYST']:
                counter_ref = self.db.collection(self.counters_collection).document(assessment_type)
                batch.set(counter_ref, {'count': 0})
            
            batch.commit()
            logger.info("Reset all counters to zero")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting counters: {str(e)}")
            return False
    
    def queue_student(self, student_data: Dict[str, Any]) -> bool:
        """
        Add student to queue
        
        Args:
            student_data: Student data to queue
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add timestamp if not present
            if 'timestamp' not in student_data:
                student_data['timestamp'] = time.time()
            
            # Add status
            student_data['status'] = 'queued'
            
            # Add to queue with auto-generated ID
            doc_ref = self.db.collection(self.queue_collection).add(student_data)
            
            logger.info(f"Queued student: {doc_ref[1].id}")
            return True
            
        except Exception as e:
            logger.error(f"Error queuing student: {str(e)}")
            return False
    
    def get_queued_students(self) -> List[Dict[str, Any]]:
        """
        Get all queued students
        
        Returns:
            List of queued student data
        """
        try:
            students = []
            student_docs = self.db.collection(self.queue_collection).where('status', '==', 'queued').stream()
            
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
        """
        Get count of queued students (more efficient than getting full list)
        
        Returns:
            Number of queued students
        """
        try:
            # Use aggregation query for efficient counting
            query = self.db.collection(self.queue_collection).where('status', '==', 'queued')
            count_query = query.count()
            count_result = count_query.get()
            
            count = count_result[0][0].value if count_result else 0
            logger.info(f"Queue count: {count}")
            return count
            
        except Exception as e:
            logger.error(f"Error getting queue count: {str(e)}")
            # Fallback to manual counting if aggregation fails
            try:
                students = self.get_queued_students()
                return len(students)
            except:
                return 0
    
    def clear_queue(self) -> bool:
        """
        Clear all queued students
        
        Returns:
            True if successful, False otherwise
        """
        try:
            batch = self.db.batch()
            
            # Get all queued students
            student_docs = self.db.collection(self.queue_collection).where('status', '==', 'queued').stream()
            
            for doc in student_docs:
                batch.delete(doc.reference)
            
            batch.commit()
            logger.info("Cleared all queued students")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing queue: {str(e)}")
            return False
    
    def create_batch_state(self, batch_id: str, deadline: int) -> bool:
        """
        Create batch state document
        
        Args:
            batch_id: Unique batch identifier
            deadline: Unix timestamp for batch deadline
            
        Returns:
            True if successful, False otherwise
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
        """
        Get current batch state
        
        Returns:
            Batch state data or None if not found
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
        """
        Clear current batch state
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.db.collection(self.state_collection).document('currentBatch').delete()
            logger.info("Cleared batch state")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing batch state: {str(e)}")
            return False
    
    def is_batch_active(self) -> bool:
        """
        Check if there's an active batch
        
        Returns:
            True if active batch exists and is not expired, False otherwise
        """
        try:
            state = self.get_batch_state()
            
            if not state:
                return False
            
            # Check if batch is open and not expired
            if not state.get('open', False):
                return False
            
            deadline = state.get('deadline', 0)
            current_time = time.time()
            
            return current_time < deadline
            
        except Exception as e:
            logger.error(f"Error checking batch state: {str(e)}")
            return False
    


# Global instance
firestore_service = FirestoreService()
