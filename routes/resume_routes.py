# routes/resume_routes.py
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from config.firebase_config import firebase_config
from services.resume_processing_service import resume_service
from utils.file_utils import get_file_size, calculate_file_hash
import logging
import os
import uuid

# Create blueprint
resume_bp = Blueprint('resume', __name__)

# Initialize components
db = firebase_config.get_db()
logger = logging.getLogger(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads/resumes'
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'pdf'}

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def auth_required(f):
    """Local auth decorator for resume routes"""
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

def update_user_resume_status(user_id: str, has_resume: bool):
    """Update user's resume status and recalculate profile completion"""
    try:
        from models.user_model import UserModel
        user_model = UserModel(db)
        user_model.update_resume_status(user_id, has_resume)
        logger.info(f"Updated resume status for user {user_id}: {has_resume}")
    except Exception as e:
        logger.error(f"Error updating user resume status: {e}")

@resume_bp.route('/upload', methods=['POST'])
@auth_required
def upload_resume():
    """Upload and process resume with enhanced parallel processing"""
    try:
        user_id = request.user_id
        
        # Check if file is present
        if 'resume' not in request.files:
            return jsonify({'error': 'No resume file provided'}), 400
        
        file = request.files['resume']
        job_description = request.form.get('job_description', '')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check file extension
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are allowed'}), 400
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({'error': f'File size exceeds maximum limit of {MAX_FILE_SIZE // (1024*1024)}MB'}), 400
        
        # Generate unique filename
        filename = secure_filename(file.filename)
        unique_id = str(uuid.uuid4())
        unique_filename = f"{unique_id}_{filename}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        
        # Save file
        file.save(file_path)
        
        # Start enhanced resume processing
        task_id, success = resume_service.start_resume_processing(
            user_id=user_id,
            file_path=file_path,
            filename=filename,
            job_description=job_description
        )
        
        if not success:
            # Clean up file if processing failed to start
            try:
                os.remove(file_path)
            except:
                pass
            return jsonify({'error': 'Failed to start resume processing'}), 500
        
        # Update user's resume status immediately (optimistic update)
        update_user_resume_status(user_id, True)
        
        logger.info(f"Resume upload successful for user {user_id}, task_id: {task_id}")
        
        return jsonify({
            'message': 'Resume uploaded and processing started',
            'task_id': task_id,
            'user_id': user_id,
            'status': 'pending',
            'progress': 0
        }), 201
        
    except Exception as e:
        logger.error(f"Resume upload error: {str(e)}")
        return jsonify({'error': 'Failed to upload resume', 'details': str(e)}), 500

@resume_bp.route('/status/<user_id>', methods=['GET'])
@auth_required
def get_processing_status(user_id):
    """Get processing status for user's latest resume with enhanced tracking"""
    try:
        # Verify the user_id in URL matches the authenticated user
        if user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get processing status using enhanced service
        status_data = resume_service.get_processing_status(user_id)
        
        if not status_data:
            return jsonify({'error': 'No resume processing found for user'}), 404
        
        return jsonify({
            'user_id': user_id,
            'task_id': status_data.get('task_id'),
            'resume_id': status_data.get('resume_id'),
            'status': status_data.get('status'),
            'progress': status_data.get('progress', 0),
            'filename': status_data.get('filename', ''),
            'created_at': status_data.get('created_at'),
            'started_at': status_data.get('started_at'),
            'completed_at': status_data.get('completed_at'),
            'error_message': status_data.get('error_message'),
            'is_active': status_data.get('is_active', False)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting processing status: {e}")
        return jsonify({'error': 'Failed to get processing status', 'details': str(e)}), 500

@resume_bp.route('/results/<user_id>', methods=['GET'])
@auth_required
def get_resume_results(user_id):
    """Get resume results for user's latest resume with enhanced tracking"""
    try:
        # Verify the user_id in URL matches the authenticated user
        if user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get results using enhanced service
        results = resume_service.get_resume_results(user_id)
        
        if not results:
            return jsonify({'error': 'No resume results found for user'}), 404
        
        # If processing is not completed, return status info
        if results.get('status') != 'completed':
            return jsonify({
                'user_id': user_id,
                'status': results.get('status'),
                'progress': results.get('progress', 0),
                'message': results.get('message', 'Resume processing in progress')
            }), 200
        
        # Return completed results
        return jsonify({
            'user_id': user_id,
            'task_id': results.get('task_id'),
            'resume_id': results.get('resume_id'),
            'status': 'completed',
            'extracted_data': results.get('extracted_data'),
            'interview_questions': results.get('interview_questions'),
            'job_match_analysis': results.get('job_match_analysis'),
            'filename': results.get('filename', ''),
            'processed_at': results.get('processed_at')
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting resume results: {e}")
        return jsonify({'error': 'Failed to get resume results', 'details': str(e)}), 500

@resume_bp.route('/questions/<user_id>', methods=['GET'])
@auth_required
def get_interview_questions(user_id):
    """Get interview questions for user's latest resume"""
    try:
        # Verify the user_id in URL matches the authenticated user
        if user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get results using enhanced service
        results = resume_service.get_resume_results(user_id)
        
        if not results:
            return jsonify({'error': 'No resume results found for user'}), 404
        
        if results.get('status') != 'completed':
            return jsonify({
                'user_id': user_id,
                'status': results.get('status'),
                'progress': results.get('progress', 0),
                'message': 'Resume processing not completed yet'
            }), 200
        
        interview_questions = results.get('interview_questions', [])
        
        return jsonify({
            'user_id': user_id,
            'resume_id': results.get('resume_id'),
            'interview_questions': interview_questions,
            'total_questions': len(interview_questions)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting interview questions: {e}")
        return jsonify({'error': 'Failed to get interview questions', 'details': str(e)}), 500

@resume_bp.route('/analysis/<user_id>', methods=['GET'])
@auth_required
def get_job_match_analysis(user_id):
    """Get job match analysis for user's latest resume"""
    try:
        # Verify the user_id in URL matches the authenticated user
        if user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get results using enhanced service
        results = resume_service.get_resume_results(user_id)
        
        if not results:
            return jsonify({'error': 'No resume results found for user'}), 404
        
        if results.get('status') != 'completed':
            return jsonify({
                'user_id': user_id,
                'status': results.get('status'),
                'progress': results.get('progress', 0),
                'message': 'Resume processing not completed yet'
            }), 200
        
        job_match_analysis = results.get('job_match_analysis', {})
        
        return jsonify({
            'user_id': user_id,
            'resume_id': results.get('resume_id'),
            'job_match_analysis': job_match_analysis
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting job match analysis: {e}")
        return jsonify({'error': 'Failed to get job match analysis', 'details': str(e)}), 500

@resume_bp.route('/reprocess/<user_id>', methods=['POST'])
@auth_required
def reprocess_resume(user_id):
    """Reprocess user's latest resume with new job description"""
    try:
        # Verify the user_id in URL matches the authenticated user
        if user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        job_description = data.get('job_description', '') if data else ''
        
        # Get user's latest resume
        from models.resume_model import ResumeModel
        resume_model = ResumeModel(db)
        user_resumes = resume_model.get_user_resumes(user_id)
        
        if not user_resumes:
            return jsonify({'error': 'No resumes found for user'}), 404
        
        latest_resume = user_resumes[0]
        file_path = latest_resume.get('file_path')
        filename = latest_resume.get('filename')
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'Resume file not found'}), 404
        
        # Start reprocessing
        task_id, success = resume_service.start_resume_processing(
            user_id=user_id,
            file_path=file_path,
            filename=filename,
            job_description=job_description
        )
        
        if not success:
            return jsonify({'error': 'Failed to start resume reprocessing'}), 500
        
        logger.info(f"Resume reprocessing started for user {user_id}, task_id: {task_id}")
        
        return jsonify({
            'message': 'Resume reprocessing started',
            'task_id': task_id,
            'user_id': user_id,
            'status': 'pending',
            'progress': 0
        }), 200
        
    except Exception as e:
        logger.error(f"Resume reprocessing error: {str(e)}")
        return jsonify({'error': 'Failed to reprocess resume', 'details': str(e)}), 500

@resume_bp.route('/delete/<user_id>', methods=['DELETE'])
@auth_required
def delete_resume(user_id):
    """Delete user's latest resume"""
    try:
        # Verify the user_id in URL matches the authenticated user
        if user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get user's latest resume
        from models.resume_model import ResumeModel
        resume_model = ResumeModel(db)
        user_resumes = resume_model.get_user_resumes(user_id)
        
        if not user_resumes:
            return jsonify({'error': 'No resumes found for user'}), 404
        
        latest_resume = user_resumes[0]
        resume_id = latest_resume['id']
        file_path = latest_resume.get('file_path')
        
        # Delete from database
        success = resume_model.delete_resume(resume_id)
        
        if not success:
            return jsonify({'error': 'Failed to delete resume from database'}), 500
        
        # Delete file if exists
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.warning(f"Failed to delete resume file: {e}")
        
        # Update user's resume status
        remaining_resumes = resume_model.get_user_resumes(user_id)
        has_resumes = len(remaining_resumes) > 0
        update_user_resume_status(user_id, has_resumes)
        
        logger.info(f"Resume deleted for user {user_id}, resume_id: {resume_id}")
        
        return jsonify({
            'message': 'Resume deleted successfully',
            'user_id': user_id,
            'resume_id': resume_id
        }), 200
        
    except Exception as e:
        logger.error(f"Resume deletion error: {str(e)}")
        return jsonify({'error': 'Failed to delete resume', 'details': str(e)}), 500

@resume_bp.route('/list/<user_id>', methods=['GET'])
@auth_required
def get_user_resumes(user_id):
    """Get all resumes for a user with task status"""
    try:
        # Verify the user_id in URL matches the authenticated user
        if user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get resumes with task status
        resumes = resume_service.get_user_resumes(user_id)
        
        return jsonify({
            'user_id': user_id,
            'resumes': resumes,
            'total_count': len(resumes)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting user resumes: {e}")
        return jsonify({'error': 'Failed to get user resumes', 'details': str(e)}), 500