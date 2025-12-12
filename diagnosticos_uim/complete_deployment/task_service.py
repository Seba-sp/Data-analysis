#!/usr/bin/env python3
"""
Task Service - Handles Cloud Tasks operations for delayed batch processing
"""

import os
import logging
import time
from datetime import datetime, timezone
from typing import Optional
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

logger = logging.getLogger(__name__)

class TaskService:
    def __init__(self):
        """Initialize Cloud Tasks client"""
        try:
            self.client = tasks_v2.CloudTasksClient()
        except Exception as e:
            logger.warning(f"Failed to initialize Cloud Tasks client: {e}")
            self.client = None
        
        # Get configuration from environment variables
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        self.location = os.getenv('TASK_LOCATION', 'us-central1')
        self.queue_id = os.getenv('TASK_QUEUE_ID', 'batch-processing-queue')
        self.process_url = os.getenv('PROCESS_BATCH_URL')
        
        # Log warnings instead of raising errors for missing env vars
        if not self.project_id:
            logger.warning("GOOGLE_CLOUD_PROJECT environment variable is not set")
        
        if not self.process_url:
            logger.warning("PROCESS_BATCH_URL environment variable is not set")
        
        # Construct queue path if client is available
        if self.client and self.project_id:
            self.queue_path = self.client.queue_path(self.project_id, self.location, self.queue_id)
        else:
            self.queue_path = None
    
    def create_delayed_task(self, delay_seconds: int, batch_id: str) -> bool:
        """
        Create a delayed task for batch processing
        
        Args:
            delay_seconds: Delay in seconds before task execution
            batch_id: Batch identifier to pass to the processor
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client or not self.queue_path or not self.process_url:
            logger.warning("TaskService not properly configured - cannot create delayed task")
            return False
            
        try:
            # Calculate schedule time
            schedule_time = timestamp_pb2.Timestamp()
            # Convert float timestamp to datetime object
            schedule_datetime = datetime.fromtimestamp(
                time.time() + delay_seconds, 
                tz=timezone.utc
            )
            schedule_time.FromDatetime(schedule_datetime)
            
            # Create task
            task = {
                'http_request': {
                    'http_method': tasks_v2.HttpMethod.GET,
                    'url': f"{self.process_url}?batch_id={batch_id}",
                    'headers': {
                        'Content-Type': 'application/json',
                    }
                },
                'schedule_time': schedule_time
            }
            
            # Create the task
            response = self.client.create_task(
                request={
                    'parent': self.queue_path,
                    'task': task
                }
            )
            
            logger.info(f"Created delayed task for batch {batch_id} with {delay_seconds}s delay")
            return True
            
        except Exception as e:
            logger.error(f"Error creating delayed task: {str(e)}")
            return False
    

    
    def delete_task(self, task_name: str) -> bool:
        """
        Delete a specific task
        
        Args:
            task_name: Full task name to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            logger.warning("TaskService client not available - cannot delete task")
            return False
            
        try:
            self.client.delete_task(name=task_name)
            logger.info(f"Deleted task: {task_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting task {task_name}: {str(e)}")
            return False
    
    def list_tasks(self) -> list:
        """
        List all tasks in the queue
        
        Returns:
            List of task names
        """
        if not self.client or not self.queue_path:
            logger.warning("TaskService not properly configured - cannot list tasks")
            return []
            
        try:
            tasks = []
            request = tasks_v2.ListTasksRequest(parent=self.queue_path)
            
            for task in self.client.list_tasks(request=request):
                tasks.append(task.name)
            
            logger.info(f"Found {len(tasks)} tasks in queue")
            return tasks
            
        except Exception as e:
            logger.error(f"Error listing tasks: {str(e)}")
            return []
    
    def purge_queue(self) -> bool:
        """
        Purge all tasks from the queue
        
        Returns:
            True if successful, False otherwise
        """
        if not self.client or not self.queue_path:
            logger.warning("TaskService not properly configured - cannot purge queue")
            return False
            
        try:
            request = tasks_v2.PurgeQueueRequest(name=self.queue_path)
            self.client.purge_queue(request=request)
            
            logger.info("Purged all tasks from queue")
            return True
            
        except Exception as e:
            logger.error(f"Error purging queue: {str(e)}")
            return False
    
    def get_queue_info(self) -> dict:
        """
        Get information about the queue
        
        Returns:
            Dictionary with queue information
        """
        if not self.client or not self.queue_path:
            logger.warning("TaskService not properly configured - cannot get queue info")
            return {}
            
        try:
            request = tasks_v2.GetQueueRequest(name=self.queue_path)
            queue = self.client.get_queue(request=request)
            
            return {
                'name': queue.name,
                'state': queue.state.name,
                'rate_limits': {
                    'max_dispatches_per_second': queue.rate_limits.max_dispatches_per_second,
                    'max_concurrent_dispatches': queue.rate_limits.max_concurrent_dispatches
                },
                'retry_config': {
                    'max_attempts': queue.retry_config.max_attempts,
                    'max_retry_duration': queue.retry_config.max_retry_duration.ToDatetime().isoformat() if queue.retry_config.max_retry_duration else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting queue info: {str(e)}")
            return {}
    
    def create_queue_if_not_exists(self) -> bool:
        """
        Create the queue if it doesn't exist
        
        Returns:
            True if successful, False otherwise
        """
        if not self.client or not self.queue_path or not self.project_id:
            logger.warning("TaskService not properly configured - cannot create queue")
            return False
            
        try:
            # Try to get the queue
            request = tasks_v2.GetQueueRequest(name=self.queue_path)
            self.client.get_queue(request=request)
            logger.info("Queue already exists")
            return True
            
        except Exception:
            # Queue doesn't exist, create it
            try:
                parent = self.client.location_path(self.project_id, self.location)
                
                queue = {
                    'name': self.queue_path,
                    'rate_limits': {
                        'max_dispatches_per_second': 500,
                        'max_concurrent_dispatches': 100
                    },
                    'retry_config': {
                        'max_attempts': 5,
                        'max_retry_duration': {
                            'seconds': 300  # 5 minutes
                        }
                    }
                }
                
                request = tasks_v2.CreateQueueRequest(
                    parent=parent,
                    queue=queue
                )
                
                self.client.create_queue(request=request)
                logger.info(f"Created queue: {self.queue_path}")
                return True
                
            except Exception as e:
                logger.error(f"Error creating queue: {str(e)}")
                return False

# Global instance
task_service = TaskService()
