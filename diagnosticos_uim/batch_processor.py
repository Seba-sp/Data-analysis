#!/usr/bin/env python3
"""
Batch Processor - Handles batch processing of queued students
"""

import logging
import subprocess
import os
import time
from typing import Dict, List, Any
from firestore_service import firestore_service

logger = logging.getLogger(__name__)

class BatchProcessor:
    def __init__(self):
        """Initialize batch processor"""
        self.assessment_types = ['M1', 'F30M', 'B30M', 'Q30M', 'HYST']
        self.batch_interval_minutes = int(os.getenv('BATCH_INTERVAL_MINUTES', '15'))
    
    def process_batch(self, batch_id: str) -> Dict[str, Any]:
        """
        Process all queued students in a batch
        
        Args:
            batch_id: Batch identifier
            
        Returns:
            Dictionary with processing results
        """
        results = {
            'success': True,
            'batch_id': batch_id,
            'students_processed': 0,
            'assessments_processed': 0,
            'errors': [],
            'processing_time': 0
        }
        
        start_time = time.time()
        
        try:
            logger.info(f"Starting batch processing for batch {batch_id}")
            
            # Get queued students
            students = firestore_service.get_queued_students()
            if not students:
                logger.info("No students in queue to process")
                results['students_processed'] = 0
                return results
            
            results['students_processed'] = len(students)
            logger.info(f"Processing {len(students)} students")
            
            # Count students by assessment type
            counts = self._count_by_assessment_type(students)
            logger.info(f"Student counts by assessment type: {counts}")
            
            # Process each assessment type with students (includes email sending now)
            for assessment_type, count in counts.items():
                if count > 0:
                    logger.info(f"Processing {assessment_type} with {count} students (includes email sending)")
                    
                    success = self._process_assessment_type(assessment_type)
                    if success:
                        results['assessments_processed'] += 1
                        logger.info(f"Successfully completed all processing for {assessment_type} including email sending")
                    else:
                        results['errors'].append(f"Failed to process {assessment_type}")
            
            # Note: Email sending is now handled within main.py for each assessment type
            
            # Clear queue and reset counters
            self._cleanup_batch()
            
            results['processing_time'] = time.time() - start_time
            logger.info(f"Batch processing completed in {results['processing_time']:.2f} seconds")
            
            return results
            
        except Exception as e:
            results['success'] = False
            results['errors'].append(f"Unexpected error: {str(e)}")
            logger.error(f"Error in batch processing: {str(e)}")
            return results
    
    def _count_by_assessment_type(self, students: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Count students by assessment type
        
        Args:
            students: List of student data
            
        Returns:
            Dictionary with assessment type to count mapping
        """
        counts = {assessment_type: 0 for assessment_type in self.assessment_types}
        
        for student in students:
            assessment_type = student.get('assessment_type')
            if assessment_type in counts:
                counts[assessment_type] += 1
        
        return counts
    
    def _process_assessment_type(self, assessment_type: str) -> bool:
        """
        Process a specific assessment type using main.py
        
        Args:
            assessment_type: Assessment type to process
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Executing main.py for {assessment_type}")
            
            # Build command - now includes email sending
            cmd = [
                'python', 'main.py',
                '--assessment', assessment_type,
                '--download', '--process', '--analyze', '--reports', '--send-emails', '--incremental'
            ]
            
            logger.info(f"Command: {' '.join(cmd)}")
            
            # Execute command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully processed {assessment_type}")
                logger.debug(f"Output: {result.stdout}")
                return True
            else:
                logger.error(f"Failed to process {assessment_type}")
                logger.error(f"Return code: {result.returncode}")
                logger.error(f"Error output: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout processing {assessment_type}")
            return False
        except Exception as e:
            logger.error(f"Error processing {assessment_type}: {str(e)}")
            return False
    
    # NOTE: _send_emails method removed - email sending is now integrated into main.py
    # This eliminates the need for separate send_emails.py execution and
    # allows PDFs to be sent directly from memory without storage
    
    def _cleanup_batch(self) -> bool:
        """
        Clean up after batch processing
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Clear queue
            queue_cleared = firestore_service.clear_queue()
            if not queue_cleared:
                logger.warning("Failed to clear queue")
            
            # Reset counters
            counters_reset = firestore_service.reset_counters()
            if not counters_reset:
                logger.warning("Failed to reset counters")
            
            # Clear batch state
            state_cleared = firestore_service.clear_batch_state()
            if not state_cleared:
                logger.warning("Failed to clear batch state")
            
            logger.info("Batch cleanup completed")
            return True
            
        except Exception as e:
            logger.error(f"Error in batch cleanup: {str(e)}")
            return False
    
    def get_batch_status(self) -> Dict[str, Any]:
        """
        Get current batch status
        
        Returns:
            Dictionary with batch status information
        """
        try:
            # Get counters
            counters = firestore_service.get_counters()
            
            # Get batch state
            batch_state = firestore_service.get_batch_state()
            
            # Get queued students count
            students = firestore_service.get_queued_students()
            
            return {
                'counters': counters,
                'batch_state': batch_state,
                'queued_students': len(students),
                'batch_interval_minutes': self.batch_interval_minutes,
                'total_students': sum(counters.values())
            }
            
        except Exception as e:
            logger.error(f"Error getting batch status: {str(e)}")
            return {
                'counters': {},
                'batch_state': None,
                'queued_students': 0,
                'batch_interval_minutes': self.batch_interval_minutes,
                'total_students': 0
            }

# Global instance
batch_processor = BatchProcessor()
