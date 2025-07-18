# services/task_manager.py
import threading
import time
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from config.firebase_config import firebase_config

logger = logging.getLogger(__name__)

class TaskManager:
    """Centralized task manager for handling parallel processing tasks"""
    
    def __init__(self):
        self.db = firebase_config.get_db()
        self._active_tasks = {}  # task_id -> task_info
        self._task_lock = threading.Lock()
    
    def start_task(self, task_type: str, user_id: str, task_data: Dict[str, Any], 
                   processing_func: Callable, **kwargs) -> str:
        """
        Start a new processing task
        
        Args:
            task_type: Type of task (resume, linkedin, github, portfolio)
            user_id: User ID
            task_data: Initial task data
            processing_func: Function to execute in background
            **kwargs: Additional arguments for processing function
        
        Returns:
            task_id: Unique task identifier
        """
        try:
            # Create task record in database
            task_id = self._create_task_record(task_type, user_id, task_data)
            
            # Start processing thread
            processing_thread = threading.Thread(
                target=self._execute_task,
                args=(task_id, task_type, user_id, processing_func, kwargs),
                daemon=True
            )
            processing_thread.start()
            
            # Track active task
            with self._task_lock:
                self._active_tasks[task_id] = {
                    'thread': processing_thread,
                    'started_at': datetime.now(),
                    'type': task_type,
                    'user_id': user_id,
                    'status': 'running'
                }
            
            logger.info(f"Started {task_type} task for user {user_id}, task_id: {task_id}")
            return task_id
            
        except Exception as e:
            logger.error(f"Error starting task: {e}")
            return ""
    
    def _create_task_record(self, task_type: str, user_id: str, task_data: Dict[str, Any]) -> str:
        """Create task record in database"""
        try:
            task_record = {
                'task_type': task_type,
                'user_id': user_id,
                'status': 'pending',
                'created_at': datetime.now(),
                'started_at': None,
                'completed_at': None,
                'error_message': None,
                'progress': 0,
                'task_data': task_data,
                'results': None
            }
            
            # Create document in tasks collection
            doc_ref = self.db.collection('tasks').document()
            doc_ref.set(task_record)
            
            return doc_ref.id
            
        except Exception as e:
            logger.error(f"Error creating task record: {e}")
            raise
    
    def _execute_task(self, task_id: str, task_type: str, user_id: str, 
                     processing_func: Callable, kwargs: Dict[str, Any]):
        """Execute task in background thread"""
        try:
            # Update status to running
            self._update_task_status(task_id, 'running', progress=10)
            
            # Execute the processing function with all parameters including user_id
            result = processing_func(task_id, user_id, **kwargs)
            
            # Check if result indicates failure
            if isinstance(result, dict) and result.get('error'):
                logger.error(f"Task {task_id} failed with error: {result['error']}")
                self._update_task_status(task_id, 'failed', error_message=result['error'])
            else:
                # Update with results
                self._update_task_status(task_id, 'completed', progress=100, results=result)
                logger.info(f"Task {task_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            self._update_task_status(task_id, 'failed', error_message=str(e))
        
        finally:
            # Clean up active task tracking
            with self._task_lock:
                if task_id in self._active_tasks:
                    del self._active_tasks[task_id]
    
    def _update_task_status(self, task_id: str, status: str, progress: int = None, 
                           error_message: str = None, results: Dict[str, Any] = None):
        """Update task status in database"""
        try:
            update_data = {
                'status': status,
                'progress': progress if progress is not None else 0
            }
            
            if status == 'running' and not self._get_task_field(task_id, 'started_at'):
                update_data['started_at'] = datetime.now()
            elif status in ['completed', 'failed']:
                update_data['completed_at'] = datetime.now()
            
            if error_message:
                update_data['error_message'] = error_message
            
            if results:
                update_data['results'] = results
            
            # Update document
            doc_ref = self.db.collection('tasks').document(task_id)
            doc_ref.update(update_data)
            
        except Exception as e:
            logger.error(f"Error updating task status: {e}")
    
    def _get_task_field(self, task_id: str, field: str) -> Any:
        """Get specific field from task record"""
        try:
            doc_ref = self.db.collection('tasks').document(task_id)
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict().get(field)
            return None
        except Exception as e:
            logger.error(f"Error getting task field: {e}")
            return None
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a task"""
        try:
            doc_ref = self.db.collection('tasks').document(task_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
            
            task_data = doc.to_dict()
            
            # Check if task is still running in memory
            with self._task_lock:
                is_active = task_id in self._active_tasks
            
            return {
                'task_id': task_id,
                'task_type': task_data.get('task_type'),
                'user_id': task_data.get('user_id'),
                'status': task_data.get('status'),
                'progress': task_data.get('progress', 0),
                'created_at': task_data.get('created_at'),
                'started_at': task_data.get('started_at'),
                'completed_at': task_data.get('completed_at'),
                'error_message': task_data.get('error_message'),
                'is_active': is_active
            }
            
        except Exception as e:
            logger.error(f"Error getting task status: {e}")
            return None
    
    def get_user_tasks(self, user_id: str, task_type: str = None) -> list:
        """Get all tasks for a user, optionally filtered by type"""
        try:
            # Try modern Firestore query syntax first
            try:
                from google.cloud.firestore_v1 import Query
                
                # Start with base query
                query = self.db.collection('tasks')
                
                # Add filters using the filter() method
                filters = [Query.field_path('user_id') == user_id]
                
                if task_type:
                    filters.append(Query.field_path('task_type') == task_type)
                
                # Apply filters
                for filter_condition in filters:
                    query = query.filter(filter_condition)
                
                # Add ordering
                query = query.order_by('created_at', direction='DESCENDING')
                
                docs = query.stream()
                tasks = []
                
                for doc in docs:
                    task_data = doc.to_dict()
                    task_data['id'] = doc.id
                    tasks.append(task_data)
                
                return tasks
                
            except Exception as index_error:
                logger.warning(f"Modern query failed, using fallback: {index_error}")
                
                # Fallback: Get all tasks and filter in memory
                docs = self.db.collection('tasks').stream()
                tasks = []
                
                for doc in docs:
                    task_data = doc.to_dict()
                    task_data['id'] = doc.id
                    
                    # Filter by user_id
                    if task_data.get('user_id') != user_id:
                        continue
                    
                    # Filter by task_type if specified
                    if task_type and task_data.get('task_type') != task_type:
                        continue
                    
                    tasks.append(task_data)
                
                # Sort by created_at descending
                tasks.sort(key=lambda x: x.get('created_at', datetime(1900, 1, 1)), reverse=True)
                
                return tasks
            
        except Exception as e:
            logger.error(f"Error getting user tasks: {e}")
            return []
    
    def get_latest_task(self, user_id: str, task_type: str) -> Optional[Dict[str, Any]]:
        """Get the latest task of a specific type for a user"""
        try:
            tasks = self.get_user_tasks(user_id, task_type)
            return tasks[0] if tasks else None
            
        except Exception as e:
            logger.error(f"Error getting latest task: {e}")
            return None
    
    def cancel_task(self, task_id: str, user_id: str) -> bool:
        """Cancel a running task"""
        try:
            # Verify task belongs to user
            task_status = self.get_task_status(task_id)
            if not task_status or task_status['user_id'] != user_id:
                return False
            
            # Check if task is still running
            with self._task_lock:
                if task_id in self._active_tasks:
                    # Mark as cancelled in database
                    self._update_task_status(task_id, 'cancelled')
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error cancelling task: {e}")
            return False
    
    def cleanup_old_tasks(self, days_old: int = 7):
        """Clean up old completed/failed tasks"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            # Try modern Firestore query syntax first
            try:
                from google.cloud.firestore_v1 import Query
                
                # Query for completed, failed, or cancelled tasks
                query = self.db.collection('tasks')
                
                # Add status filter
                status_filter = Query.field_path('status').in_(['completed', 'failed', 'cancelled'])
                query = query.filter(status_filter)
                
                docs = query.stream()
                
            except Exception as index_error:
                logger.warning(f"Modern cleanup query failed, using fallback: {index_error}")
                
                # Fallback: Get all tasks and filter in memory
                docs = self.db.collection('tasks').stream()
            
            # Process tasks for cleanup
            cleaned_count = 0
            for doc in docs:
                task_data = doc.to_dict()
                status = task_data.get('status')
                created_at = task_data.get('created_at')
                
                # Check if task should be cleaned up
                if (status in ['completed', 'failed', 'cancelled'] and 
                    created_at and created_at < cutoff_date):
                    # Delete old task
                    doc.reference.delete()
                    cleaned_count += 1
                    logger.info(f"Cleaned up old task: {doc.id}")
            
            logger.info(f"Cleanup completed: {cleaned_count} old tasks removed")
            
        except Exception as e:
            logger.error(f"Error cleaning up old tasks: {e}")
    
    def get_task_statistics(self, user_id: str = None) -> Dict[str, Any]:
        """Get task statistics"""
        try:
            # Get all tasks
            if user_id:
                tasks = self.get_user_tasks(user_id)
            else:
                # Get all tasks for all users (admin function)
                docs = self.db.collection('tasks').stream()
                tasks = [doc.to_dict() for doc in docs]
            
            total_tasks = len(tasks)
            completed_tasks = 0
            failed_tasks = 0
            running_tasks = 0
            pending_tasks = 0
            cancelled_tasks = 0
            
            for task in tasks:
                status = task.get('status', 'unknown')
                if status == 'completed':
                    completed_tasks += 1
                elif status == 'failed':
                    failed_tasks += 1
                elif status == 'running':
                    running_tasks += 1
                elif status == 'pending':
                    pending_tasks += 1
                elif status == 'cancelled':
                    cancelled_tasks += 1
            
            return {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'failed_tasks': failed_tasks,
                'running_tasks': running_tasks,
                'pending_tasks': pending_tasks,
                'cancelled_tasks': cancelled_tasks,
                'success_rate': round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting task statistics: {e}")
            return {
                'total_tasks': 0,
                'completed_tasks': 0,
                'failed_tasks': 0,
                'running_tasks': 0,
                'pending_tasks': 0,
                'cancelled_tasks': 0,
                'success_rate': 0
            }

# Global task manager instance
task_manager = TaskManager() 