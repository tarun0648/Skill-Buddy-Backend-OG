# routes/task_routes.py
from flask import Blueprint, request, jsonify
from config.firebase_config import firebase_config
from services.task_manager import task_manager
import logging

# Create blueprint
task_bp = Blueprint('task', __name__)

# Initialize components
db = firebase_config.get_db()
logger = logging.getLogger(__name__)

def auth_required(f):
    """Local auth decorator for task routes"""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return jsonify({'error': 'User ID required in X-User-ID header'}), 401
        
        # Verify user exists in database
        if db:
            try:
                doc_ref = db.collection('users').document(user_id)
                doc = doc_ref.get()
                if not doc.exists:
                    return jsonify({'error': 'Invalid user ID'}), 401
            except Exception as e:
                return jsonify({'error': 'User verification failed'}), 401
        
        request.user_id = user_id
        return f(*args, **kwargs)
    
    return decorated

@task_bp.route('/status/<user_id>', methods=['GET'])
@auth_required
def get_all_task_status(user_id):
    """Get status of all tasks for a user"""
    try:
        # Verify the user_id in URL matches the authenticated user
        if user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get all tasks for user
        all_tasks = task_manager.get_user_tasks(user_id)
        
        # Group tasks by type
        task_summary = {
            'resume': None,
            'linkedin': None,
            'github': None,
            'portfolio': None
        }
        
        for task in all_tasks:
            task_type = task.get('task_type')
            if task_type in task_summary:
                # Get the latest task of each type
                if task_summary[task_type] is None or task.get('created_at') > task_summary[task_type].get('created_at'):
                    task_summary[task_type] = {
                        'task_id': task.get('id'),
                        'status': task.get('status'),
                        'progress': task.get('progress', 0),
                        'created_at': task.get('created_at'),
                        'started_at': task.get('started_at'),
                        'completed_at': task.get('completed_at'),
                        'error_message': task.get('error_message'),
                        'is_active': task.get('is_active', False)
                    }
        
        return jsonify({
            'user_id': user_id,
            'tasks': task_summary,
            'active_tasks': sum(1 for task in task_summary.values() if task and task.get('is_active', False)),
            'completed_tasks': sum(1 for task in task_summary.values() if task and task.get('status') == 'completed'),
            'failed_tasks': sum(1 for task in task_summary.values() if task and task.get('status') == 'failed')
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting all task status: {e}")
        return jsonify({'error': 'Failed to get task status', 'details': str(e)}), 500

@task_bp.route('/status/<user_id>/<task_type>', methods=['GET'])
@auth_required
def get_task_status_by_type(user_id, task_type):
    """Get status of tasks for a specific type"""
    try:
        # Verify the user_id in URL matches the authenticated user
        if user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Validate task type
        valid_types = ['resume', 'linkedin', 'github', 'portfolio']
        if task_type not in valid_types:
            return jsonify({'error': 'Invalid task type'}), 400
        
        # Get tasks for specific type
        tasks = task_manager.get_user_tasks(user_id, task_type)
        
        if not tasks:
            return jsonify({'error': f'No {task_type} tasks found for user'}), 404
        
        # Get the latest task
        latest_task = tasks[0]
        
        return jsonify({
            'user_id': user_id,
            'task_type': task_type,
            'task_id': latest_task.get('id'),
            'status': latest_task.get('status'),
            'progress': latest_task.get('progress', 0),
            'created_at': latest_task.get('created_at'),
            'started_at': latest_task.get('started_at'),
            'completed_at': latest_task.get('completed_at'),
            'error_message': latest_task.get('error_message'),
            'is_active': latest_task.get('is_active', False),
            'task_data': latest_task.get('task_data', {})
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting task status for {task_type}: {e}")
        return jsonify({'error': 'Failed to get task status', 'details': str(e)}), 500

@task_bp.route('/cancel/<task_id>', methods=['POST'])
@auth_required
def cancel_task(task_id):
    """Cancel a running task"""
    try:
        user_id = request.user_id
        
        # Cancel the task
        success = task_manager.cancel_task(task_id, user_id)
        
        if not success:
            return jsonify({'error': 'Failed to cancel task or task not found'}), 404
        
        logger.info(f"Task {task_id} cancelled for user {user_id}")
        
        return jsonify({
            'message': 'Task cancelled successfully',
            'task_id': task_id,
            'user_id': user_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error cancelling task: {e}")
        return jsonify({'error': 'Failed to cancel task', 'details': str(e)}), 500

@task_bp.route('/history/<user_id>', methods=['GET'])
@auth_required
def get_task_history(user_id):
    """Get task history for a user"""
    try:
        # Verify the user_id in URL matches the authenticated user
        if user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get all tasks for user
        all_tasks = task_manager.get_user_tasks(user_id)
        
        # Format task history
        task_history = []
        for task in all_tasks:
            task_history.append({
                'task_id': task.get('id'),
                'task_type': task.get('task_type'),
                'status': task.get('status'),
                'progress': task.get('progress', 0),
                'created_at': task.get('created_at'),
                'started_at': task.get('started_at'),
                'completed_at': task.get('completed_at'),
                'error_message': task.get('error_message'),
                'task_data': task.get('task_data', {})
            })
        
        return jsonify({
            'user_id': user_id,
            'task_history': task_history,
            'total_tasks': len(task_history)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting task history: {e}")
        return jsonify({'error': 'Failed to get task history', 'details': str(e)}), 500

@task_bp.route('/cleanup', methods=['POST'])
@auth_required
def cleanup_old_tasks():
    """Clean up old completed/failed tasks (admin function)"""
    try:
        user_id = request.user_id
        
        # Get cleanup parameters
        data = request.get_json() or {}
        days_old = data.get('days_old', 7)
        
        # Perform cleanup
        task_manager.cleanup_old_tasks(days_old)
        
        logger.info(f"Task cleanup completed for user {user_id}, cleaned tasks older than {days_old} days")
        
        return jsonify({
            'message': 'Task cleanup completed',
            'days_old': days_old,
            'user_id': user_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error during task cleanup: {e}")
        return jsonify({'error': 'Failed to cleanup tasks', 'details': str(e)}), 500

@task_bp.route('/stats/<user_id>', methods=['GET'])
@auth_required
def get_task_stats(user_id):
    """Get task statistics for a user"""
    try:
        # Verify the user_id in URL matches the authenticated user
        if user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get all tasks for user
        all_tasks = task_manager.get_user_tasks(user_id)
        
        # Calculate statistics
        stats = {
            'total_tasks': len(all_tasks),
            'by_status': {},
            'by_type': {},
            'recent_tasks': 0,
            'average_duration': 0
        }
        
        total_duration = 0
        completed_tasks = 0
        
        for task in all_tasks:
            # Count by status
            status = task.get('status', 'unknown')
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
            
            # Count by type
            task_type = task.get('task_type', 'unknown')
            stats['by_type'][task_type] = stats['by_type'].get(task_type, 0) + 1
            
            # Calculate duration for completed tasks
            if task.get('started_at') and task.get('completed_at'):
                duration = (task['completed_at'] - task['started_at']).total_seconds()
                total_duration += duration
                completed_tasks += 1
        
        # Calculate average duration
        if completed_tasks > 0:
            stats['average_duration'] = total_duration / completed_tasks
        
        # Count recent tasks (last 24 hours)
        from datetime import datetime, timedelta
        recent_cutoff = datetime.now() - timedelta(days=1)
        stats['recent_tasks'] = sum(1 for task in all_tasks if task.get('created_at') > recent_cutoff)
        
        return jsonify({
            'user_id': user_id,
            'stats': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting task stats: {e}")
        return jsonify({'error': 'Failed to get task stats', 'details': str(e)}), 500 