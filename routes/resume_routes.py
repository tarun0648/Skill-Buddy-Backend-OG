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

@resume_bp.route('/upload', methods=['POST'])
@auth_required
def upload_resume():
    """Upload and process resume with real processing"""
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
        
        # Start real resume processing
        resume_id, success = resume_service.start_resume_processing(
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
        
        logger.info(f"Resume upload successful for user {user_id}, resume_id: {resume_id}")
        
        return jsonify({
            'message': 'Resume uploaded successfully. Processing started.',
            'resume_id': resume_id,
            'status': 'pending'
        }), 201
        
    except Exception as e:
        logger.error(f"Resume upload error: {e}")
        return jsonify({'error': 'Resume upload failed', 'details': str(e)}), 500

@resume_bp.route('/status/<resume_id>', methods=['GET'])
@auth_required
def get_processing_status(resume_id):
    """Get resume processing status"""
    try:
        user_id = request.user_id
        status_data = resume_service.get_processing_status(resume_id)
        
        if not status_data:
            return jsonify({'error': 'Resume not found'}), 404
        
        # Check ownership through resume service
        from models.resume_model import ResumeModel
        resume_model = ResumeModel(db)
        resume_data = resume_model.get_resume_by_id(resume_id)
        
        if not resume_data or resume_data.get('user_id') != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        return jsonify(status_data), 200
        
    except Exception as e:
        logger.error(f"Error getting processing status: {e}")
        return jsonify({'error': 'Failed to get processing status', 'details': str(e)}), 500

@resume_bp.route('/results/<resume_id>', methods=['GET'])
@auth_required
def get_resume_results(resume_id):
    """Get complete resume processing results"""
    try:
        user_id = request.user_id
        results = resume_service.get_resume_results(resume_id, user_id)
        
        if not results:
            return jsonify({'error': 'Resume not found or access denied'}), 404
        
        return jsonify(results), 200
        
    except Exception as e:
        logger.error(f"Error getting resume results: {e}")
        return jsonify({'error': 'Failed to get resume results', 'details': str(e)}), 500

@resume_bp.route('/questions/<resume_id>', methods=['GET'])
@auth_required
def get_interview_questions(resume_id):
    """Get interview questions for a specific resume"""
    try:
        user_id = request.user_id
        
        from models.resume_model import ResumeModel
        resume_model = ResumeModel(db)
        resume_data = resume_model.get_resume_by_id(resume_id)
        
        if not resume_data or resume_data.get('user_id') != user_id:
            return jsonify({'error': 'Resume not found or access denied'}), 404
        
        if resume_data.get('processing_status') != 'completed':
            return jsonify({'error': 'Resume processing not completed yet'}), 400
        
        questions = resume_data.get('interview_questions', [])
        
        return jsonify({
            'resume_id': resume_id,
            'questions': questions,
            'total_questions': len(questions)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting interview questions: {e}")
        return jsonify({'error': 'Failed to get interview questions', 'details': str(e)}), 500

@resume_bp.route('/analysis/<resume_id>', methods=['GET'])
@auth_required
def get_job_match_analysis(resume_id):
    """Get job match analysis for a specific resume"""
    try:
        user_id = request.user_id
        
        from models.resume_model import ResumeModel
        resume_model = ResumeModel(db)
        resume_data = resume_model.get_resume_by_id(resume_id)
        
        if not resume_data or resume_data.get('user_id') != user_id:
            return jsonify({'error': 'Resume not found or access denied'}), 404
        
        if resume_data.get('processing_status') != 'completed':
            return jsonify({'error': 'Resume processing not completed yet'}), 400
        
        analysis = resume_data.get('job_match_analysis', {})
        
        return jsonify({
            'resume_id': resume_id,
            'analysis': analysis
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting job match analysis: {e}")
        return jsonify({'error': 'Failed to get job match analysis', 'details': str(e)}), 500

@resume_bp.route('/reprocess/<resume_id>', methods=['POST'])
@auth_required
def reprocess_resume(resume_id):
    """Reprocess a resume with new job description"""
    try:
        user_id = request.user_id
        data = request.get_json()
        job_description = data.get('job_description', '') if data else ''
        
        from models.resume_model import ResumeModel
        resume_model = ResumeModel(db)
        resume_data = resume_model.get_resume_by_id(resume_id)
        
        if not resume_data or resume_data.get('user_id') != user_id:
            return jsonify({'error': 'Resume not found or access denied'}), 404
        
        # Start reprocessing
        file_path = resume_data.get('file_path')
        filename = resume_data.get('filename')
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'Original resume file not found'}), 400
        
        # Start new processing with updated job description
        new_resume_id, success = resume_service.start_resume_processing(
            user_id=user_id,
            file_path=file_path,
            filename=f"reprocessed_{filename}",
            job_description=job_description
        )
        
        if not success:
            return jsonify({'error': 'Failed to start reprocessing'}), 500
        
        return jsonify({
            'message': 'Resume reprocessing started',
            'new_resume_id': new_resume_id,
            'original_resume_id': resume_id,
            'status': 'pending'
        }), 200
        
    except Exception as e:
        logger.error(f"Error reprocessing resume: {e}")
        return jsonify({'error': 'Failed to reprocess resume', 'details': str(e)}), 500

@resume_bp.route('/delete/<resume_id>', methods=['DELETE'])
@auth_required
def delete_resume(resume_id):
    """Delete a resume and its associated data"""
    try:
        user_id = request.user_id
        
        from models.resume_model import ResumeModel
        resume_model = ResumeModel(db)
        resume_data = resume_model.get_resume_by_id(resume_id)
        
        if not resume_data or resume_data.get('user_id') != user_id:
            return jsonify({'error': 'Resume not found or access denied'}), 404
        
        # Delete file from filesystem
        file_path = resume_data.get('file_path')
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Deleted file: {file_path}")
            except Exception as e:
                logger.warning(f"Could not delete file {file_path}: {e}")
        
        # Delete associated JSON files
        if file_path:
            base_path = file_path.replace('.pdf', '')
            json_files = [
                f"{base_path}_extracted_resume.json",
                f"{base_path}_interview_questions.json"
            ]
            
            for json_file in json_files:
                if os.path.exists(json_file):
                    try:
                        os.remove(json_file)
                        logger.info(f"Deleted JSON file: {json_file}")
                    except Exception as e:
                        logger.warning(f"Could not delete JSON file {json_file}: {e}")
        
        # Delete from database
        success = resume_model.delete_resume(resume_id)
        
        if success:
            logger.info(f"Successfully deleted resume: {resume_id}")
            return jsonify({'message': 'Resume deleted successfully'}), 200
        else:
            return jsonify({'error': 'Failed to delete resume from database'}), 500
        
    except Exception as e:
        logger.error(f"Error deleting resume: {e}")
        return jsonify({'error': 'Failed to delete resume', 'details': str(e)}), 500