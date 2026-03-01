"""Cloud Tasks service for delayed batch processing callbacks."""

import datetime
import os
import logging
from typing import Optional
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

logger = logging.getLogger(__name__)


class TaskService:
    def __init__(self):
        """Initialize Cloud Tasks client from environment variables."""
        try:
            self.client = tasks_v2.CloudTasksClient()
        except Exception as e:
            logger.warning(f"Failed to initialize Cloud Tasks client: {e}")
            self.client = None

        self.project_id = os.getenv('GCP_PROJECT_ID')
        self.location = os.getenv('TASK_LOCATION', 'us-central1')
        self.queue_id = os.getenv('TASK_QUEUE_ID', 'batch-processing-queue')
        self.process_url = os.getenv('PROCESS_BATCH_URL')

        if not self.project_id:
            logger.warning("GCP_PROJECT_ID environment variable is not set")

        if not self.process_url:
            logger.warning("PROCESS_BATCH_URL environment variable is not set")

        if self.client and self.project_id:
            self.queue_path = self.client.queue_path(self.project_id, self.location, self.queue_id)
        else:
            self.queue_path = None

    def _make_schedule_timestamp(self, delay_seconds: int) -> timestamp_pb2.Timestamp:
        """Build a protobuf Timestamp for delay_seconds from now (UTC).

        Args:
            delay_seconds: Number of seconds to delay from current UTC time.

        Returns:
            A populated google.protobuf.timestamp_pb2.Timestamp.
        """
        ts = timestamp_pb2.Timestamp()
        ts.FromDatetime(
            datetime.datetime.now(tz=datetime.timezone.utc)
            + datetime.timedelta(seconds=delay_seconds)
        )
        return ts

    def create_delayed_task(self, report_type: str, delay_seconds: int, batch_id: str) -> bool:
        """Create a delayed Cloud Task for batch processing.

        The callback URL includes both report_type and batch_id so the
        receiving endpoint knows which Firestore namespace to use.

        Args:
            report_type: Report type key (e.g. 'diagnosticos').
            delay_seconds: Delay in seconds before task execution.
            batch_id: Batch identifier to pass to the processor.

        Returns:
            True if successful, False otherwise.
        """
        if not self.client or not self.queue_path or not self.process_url:
            logger.warning("TaskService not properly configured - cannot create delayed task")
            return False

        try:
            task = tasks_v2.Task(
                http_request=tasks_v2.HttpRequest(
                    http_method=tasks_v2.HttpMethod.GET,
                    url=f"{self.process_url}?report_type={report_type}&batch_id={batch_id}",
                ),
                schedule_time=self._make_schedule_timestamp(delay_seconds),
            )

            self.client.create_task(
                request={
                    'parent': self.queue_path,
                    'task': task,
                }
            )

            logger.info(
                f"Created delayed task for report_type={report_type} "
                f"batch_id={batch_id} delay={delay_seconds}s"
            )
            return True

        except Exception as e:
            logger.error(f"Error creating delayed task: {str(e)}")
            return False

    def delete_task(self, task_name: str) -> bool:
        """Delete a specific task.

        Args:
            task_name: Full task name to delete.

        Returns:
            True if successful, False otherwise.
        """
        try:
            self.client.delete_task(name=task_name)
            logger.info(f"Deleted task: {task_name}")
            return True

        except Exception as e:
            logger.error(f"Error deleting task {task_name}: {str(e)}")
            return False

    def list_tasks(self) -> list:
        """List all tasks in the queue.

        Returns:
            List of task name strings.
        """
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
        """Purge all tasks from the queue.

        Returns:
            True if successful, False otherwise.
        """
        try:
            request = tasks_v2.PurgeQueueRequest(name=self.queue_path)
            self.client.purge_queue(request=request)

            logger.info("Purged all tasks from queue")
            return True

        except Exception as e:
            logger.error(f"Error purging queue: {str(e)}")
            return False

    def get_queue_info(self) -> dict:
        """Get information about the Cloud Tasks queue.

        Returns:
            Dictionary with queue name, state, rate limits, and retry config.
        """
        try:
            request = tasks_v2.GetQueueRequest(name=self.queue_path)
            queue = self.client.get_queue(request=request)

            return {
                'name': queue.name,
                'state': queue.state.name,
                'rate_limits': {
                    'max_dispatches_per_second': queue.rate_limits.max_dispatches_per_second,
                    'max_concurrent_dispatches': queue.rate_limits.max_concurrent_dispatches,
                },
                'retry_config': {
                    'max_attempts': queue.retry_config.max_attempts,
                    'max_retry_duration': (
                        queue.retry_config.max_retry_duration.ToDatetime().isoformat()
                        if queue.retry_config.max_retry_duration
                        else None
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Error getting queue info: {str(e)}")
            return {}

    def create_queue_if_not_exists(self) -> bool:
        """Create the Cloud Tasks queue if it does not already exist.

        Returns:
            True if queue exists or was created, False on error.
        """
        try:
            request = tasks_v2.GetQueueRequest(name=self.queue_path)
            self.client.get_queue(request=request)
            logger.info("Queue already exists")
            return True

        except Exception:
            try:
                parent = self.client.location_path(self.project_id, self.location)

                queue = {
                    'name': self.queue_path,
                    'rate_limits': {
                        'max_dispatches_per_second': 500,
                        'max_concurrent_dispatches': 100,
                    },
                    'retry_config': {
                        'max_attempts': 5,
                        'max_retry_duration': {
                            'seconds': 300,
                        },
                    },
                }

                request = tasks_v2.CreateQueueRequest(
                    parent=parent,
                    queue=queue,
                )

                self.client.create_queue(request=request)
                logger.info(f"Created queue: {self.queue_path}")
                return True

            except Exception as e:
                logger.error(f"Error creating queue: {str(e)}")
                return False
