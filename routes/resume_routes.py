# routes/resume_routes.py - Fixed with Redis Caching
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
import logging
from functools import wraps

# Import cache service
from services.redis_cache_service import cache, CacheKeys, CacheTTL, cache_result, invalidate_cache_pattern

logger = logging.getLogger(__name__)

resume_bp = Blueprint('resume', __name__)

# Global variables (will be set when blueprint is registered)
resume_model = None
user_model = None
db = None
email_service = None

def init_resume_routes(resume_model_instance, user_model_instance, db_instance, email_service_instance):
    """Initialize resume routes with model instances"""
    global resume_model, user_model, db, email_service
    resume_model = resume_model_instance
    user_model = user_model_instance
    db = db_instance
    email_service = email_service_instance

def auth_required(f):
    """Decorator to require user ID authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return jsonify({'error': 'User ID required in X-User-ID header'}), 401
        
        # Check cache first for user validation
        cache_key = cache.generate_cache_key(CacheKeys.USER_PROFILE, user_id, 'validation')
        cached_validation = cache.get(cache_key)
        
        if cached_validation is None:
            # Verify user exists in database
            if db:
                try:
                    doc_ref = db.collection('users').document(user_id)
                    doc = doc_ref.get()
                    if not doc.exists:
                        return jsonify({'error': 'Invalid user ID'}), 401
                    
                    # Cache the validation result
                    cache.set(cache_key, {'valid': True}, CacheTTL.MEDIUM)
                    
                except Exception as e:
                    return jsonify({'error': 'User verification failed'}), 401
        
        request.user_id = user_id
        return f(*args, **kwargs)
    
    return decorated

@resume_bp.route('/upload', methods=['POST'])
@auth_required
def upload_resume():
    """Upload and process resume with cache invalidation"""
    try:
        if not resume_model:
            return jsonify({'error': 'Resume service not available'}), 500
        
        user_id = request.user_id
        
        # Check if file was uploaded
        if 'resume' not in request.files:
            return jsonify({'error': 'No resume file provided'}), 400
        
        file = request.files['resume']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are allowed'}), 400
        
        # Generate unique filename
        filename = f"{user_id}_{uuid.uuid4().hex}.pdf"
        filepath = os.path.join('uploads/resumes', filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Save file
        file.save(filepath)
        
        # Create resume record
        resume_data = {
            'user_id': user_id,
            'filename': filename,
            'original_filename': file.filename,
            'file_path': filepath,
            'file_size': os.path.getsize(filepath),
            'upload_timestamp': datetime.utcnow(),
            'status': 'uploaded'
        }
        
        resume_id = resume_model.create_resume_record(resume_data)
        
        # Update user profile to indicate they have a resume
        user_model.update_resume_status(user_id, True)
        
        # Invalidate related caches
        profile_cache_key = cache.generate_cache_key(CacheKeys.USER_PROFILE, user_id)
        resumes_cache_pattern = f"{CacheKeys.USER_RESUMES}:{user_id}*"
        stats_cache_key = cache.generate_cache_key(CacheKeys.USER_STATS, user_id)
        
        cache.delete(profile_cache_key)
        cache.delete_pattern(resumes_cache_pattern)
        cache.delete(stats_cache_key)
        
        # Start processing asynchronously
        try:
            from services.resume_processor import ResumeProcessor
            processor = ResumeProcessor(db, email_service)
            processor.process_resume_async(resume_id)
            
            logger.info(f"Resume uploaded and processing started for user: {user_id}, resume: {resume_id}")
            
        except Exception as e:
            logger.error(f"Resume processing failed to start: {e}")
            # Update status to failed
            resume_model.update_resume_status(resume_id, 'failed', str(e))
        
        return jsonify({
            'message': 'Resume uploaded successfully',
            'resume_id': resume_id,
            'status': 'processing'
        }), 201
        
    except Exception as e:
        logger.error(f"Resume upload error: {str(e)}")
        return jsonify({'error': 'Resume upload failed', 'details': str(e)}), 500

@resume_bp.route('/status/<resume_id>', methods=['GET'])
@auth_required
def get_resume_status(resume_id):
    """Get resume processing status with caching"""
    try:
        if not resume_model:
            return jsonify({'error': 'Resume service not available'}), 500
        
        user_id = request.user_id
        
        # Check cache first
        cache_key = cache.generate_cache_key(CacheKeys.RESUME_STATUS, user_id, resume_id)
        cached_status = cache.get(cache_key)
        
        if cached_status:
            logger.info(f"Resume status cache hit for resume: {resume_id}")
            return jsonify(cached_status), 200
        
        # Get from database
        resume_data = resume_model.get_resume_by_id(resume_id)
        if not resume_data:
            return jsonify({'error': 'Resume not found'}), 404
        
        # Verify ownership
        if resume_data.get('user_id') != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        status_data = {
            'resume_id': resume_id,
            'status': resume_data.get('status', 'unknown'),
            'progress': resume_data.get('progress', 0),
            'created_at': resume_data.get('created_at'),
            'updated_at': resume_data.get('updated_at'),
            'processed_at': resume_data.get('processed_at'),
            'error_message': resume_data.get('error_message'),
            'filename': resume_data.get('original_filename')
        }
        
        # Cache based on status - completed/failed cache longer
        cache_ttl = CacheTTL.VERY_LONG if resume_data.get('status') in ['completed', 'failed'] else CacheTTL.SHORT
        cache.set(cache_key, status_data, cache_ttl)
        
        logger.info(f"Resume status cached for resume: {resume_id}")
        
        return jsonify(status_data), 200
        
    except Exception as e:
        logger.error(f"Get resume status error: {str(e)}")
        return jsonify({'error': 'Failed to get resume status', 'details': str(e)}), 500

@resume_bp.route('/results/<resume_id>', methods=['GET'])
@auth_required
def get_resume_results(resume_id):
    """Get resume analysis results with caching"""
    try:
        if not resume_model:
            return jsonify({'error': 'Resume service not available'}), 500
        
        user_id = request.user_id
        
        # Check cache first
        cache_key = cache.generate_cache_key(CacheKeys.RESUME_ANALYSIS, user_id, resume_id)
        cached_results = cache.get(cache_key)
        
        if cached_results:
            logger.info(f"Resume results cache hit for resume: {resume_id}")
            return jsonify(cached_results), 200
        
        # Get from database
        resume_data = resume_model.get_resume_by_id(resume_id)
        if not resume_data:
            return jsonify({'error': 'Resume not found'}), 404
        
        # Verify ownership
        if resume_data.get('user_id') != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Check if processing is complete
        if resume_data.get('status') != 'completed':
            return jsonify({
                'error': 'Resume processing not complete',
                'status': resume_data.get('status', 'unknown'),
                'message': 'Please wait for processing to complete'
            }), 202
        
        # Get analysis results
        results = resume_model.get_resume_analysis_results(resume_id)
        
        if not results:
            return jsonify({'error': 'Analysis results not found'}), 404
        
        # Cache the results (they shouldn't change)
        cache.set(cache_key, results, CacheTTL.VERY_LONG)
        logger.info(f"Resume results cached for resume: {resume_id}")
        
        return jsonify(results), 200
        
    except Exception as e:
        logger.error(f"Get resume results error: {str(e)}")
        return jsonify({'error': 'Failed to get resume results', 'details': str(e)}), 500

@resume_bp.route('/questions/<resume_id>', methods=['GET'])
@auth_required
def get_resume_questions(resume_id):
    """Get AI-generated interview questions with caching"""
    try:
        if not resume_model:
            return jsonify({'error': 'Resume service not available'}), 500
        
        user_id = request.user_id
        
        # Check cache first
        cache_key = cache.generate_cache_key(CacheKeys.RESUME_QUESTIONS, user_id, resume_id)
        cached_questions = cache.get(cache_key)
        
        if cached_questions:
            logger.info(f"Resume questions cache hit for resume: {resume_id}")
            return jsonify(cached_questions), 200
        
        # Get from database
        resume_data = resume_model.get_resume_by_id(resume_id)
        if not resume_data:
            return jsonify({'error': 'Resume not found'}), 404
        
        # Verify ownership
        if resume_data.get('user_id') != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Check if processing is complete
        if resume_data.get('status') != 'completed':
            return jsonify({
                'error': 'Resume processing not complete',
                'status': resume_data.get('status', 'unknown')
            }), 202
        
        # Get questions
        questions = resume_model.get_resume_questions(resume_id)
        
        if not questions:
            return jsonify({'error': 'Questions not found'}), 404
        
        # Cache the questions
        cache.set(cache_key, questions, CacheTTL.VERY_LONG)
        logger.info(f"Resume questions cached for resume: {resume_id}")
        
        return jsonify(questions), 200
        
    except Exception as e:
        logger.error(f"Get resume questions error: {str(e)}")
        return jsonify({'error': 'Failed to get resume questions', 'details': str(e)}), 500

@resume_bp.route('/analysis/<resume_id>', methods=['GET'])
@auth_required
def get_resume_analysis(resume_id):
    """Get comprehensive resume analysis with caching"""
    try:
        if not resume_model:
            return jsonify({'error': 'Resume service not available'}), 500
        
        user_id = request.user_id
        
        # Check cache first
        cache_key = cache.generate_cache_key(CacheKeys.RESUME_ANALYSIS, user_id, resume_id, 'full')
        cached_analysis = cache.get(cache_key)
        
        if cached_analysis:
            logger.info(f"Resume analysis cache hit for resume: {resume_id}")
            return jsonify(cached_analysis), 200
        
        # Get from database
        resume_data = resume_model.get_resume_by_id(resume_id)
        if not resume_data:
            return jsonify({'error': 'Resume not found'}), 404
        
        # Verify ownership
        if resume_data.get('user_id') != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Check if processing is complete
        if resume_data.get('status') != 'completed':
            return jsonify({
                'error': 'Resume processing not complete',
                'status': resume_data.get('status', 'unknown')
            }), 202
        
        # Get comprehensive analysis
        analysis = resume_model.get_comprehensive_analysis(resume_id)
        
        if not analysis:
            return jsonify({'error': 'Analysis not found'}), 404
        
        # Cache the analysis
        cache.set(cache_key, analysis, CacheTTL.VERY_LONG)
        logger.info(f"Resume analysis cached for resume: {resume_id}")
        
        return jsonify(analysis), 200
        
    except Exception as e:
        logger.error(f"Get resume analysis error: {str(e)}")
        return jsonify({'error': 'Failed to get resume analysis', 'details': str(e)}), 500

@resume_bp.route('/reprocess/<resume_id>', methods=['POST'])
@auth_required
def reprocess_resume(resume_id):
    """Reprocess resume with cache invalidation"""
    try:
        if not resume_model:
            return jsonify({'error': 'Resume service not available'}), 500
        
        user_id = request.user_id
        
        # Get resume data
        resume_data = resume_model.get_resume_by_id(resume_id)
        if not resume_data:
            return jsonify({'error': 'Resume not found'}), 404
        
        # Verify ownership
        if resume_data.get('user_id') != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Update status to processing
        resume_model.update_resume_status(resume_id, 'processing', progress=0)
        
        # Invalidate all related caches
        cache_patterns = [
            f"{CacheKeys.RESUME_STATUS}:{user_id}:{resume_id}*",
            f"{CacheKeys.RESUME_ANALYSIS}:{user_id}:{resume_id}*",
            f"{CacheKeys.RESUME_QUESTIONS}:{user_id}:{resume_id}*",
            f"{CacheKeys.USER_RESUMES}:{user_id}*"
        ]
        
        for pattern in cache_patterns:
            cache.delete_pattern(pattern)
        
        # Start reprocessing
        try:
            from services.resume_processor import ResumeProcessor
            processor = ResumeProcessor(db, email_service)
            processor.process_resume_async(resume_id, reprocess=True)
            
            logger.info(f"Resume reprocessing started for resume: {resume_id}")
            
        except Exception as e:
            logger.error(f"Resume reprocessing failed to start: {e}")
            resume_model.update_resume_status(resume_id, 'failed', str(e))
        
        return jsonify({
            'message': 'Resume reprocessing started',
            'resume_id': resume_id,
            'status': 'processing'
        }), 200
        
    except Exception as e:
        logger.error(f"Resume reprocess error: {str(e)}")
        return jsonify({'error': 'Resume reprocessing failed', 'details': str(e)}), 500

@resume_bp.route('/delete/<resume_id>', methods=['DELETE'])
@auth_required
def delete_resume(resume_id):
    """Delete resume with cache cleanup"""
    try:
        if not resume_model:
            return jsonify({'error': 'Resume service not available'}), 500
        
        user_id = request.user_id
        
        # Get resume data
        resume_data = resume_model.get_resume_by_id(resume_id)
        if not resume_data:
            return jsonify({'error': 'Resume not found'}), 404
        
        # Verify ownership
        if resume_data.get('user_id') != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Delete from database
        delete_result = resume_model.delete_resume(resume_id)
        
        if delete_result.get('success'):
            # Clean up all related cache entries
            cache_patterns = [
                f"{CacheKeys.RESUME_STATUS}:{user_id}:{resume_id}*",
                f"{CacheKeys.RESUME_ANALYSIS}:{user_id}:{resume_id}*",
                f"{CacheKeys.RESUME_QUESTIONS}:{user_id}:{resume_id}*",
                f"{CacheKeys.RESUME_CONTENT}:{user_id}:{resume_id}*",
                f"{CacheKeys.USER_RESUMES}:{user_id}*"
            ]
            
            for pattern in cache_patterns:
                cache.delete_pattern(pattern)
            
            # Also invalidate user profile and stats cache
            profile_cache_key = cache.generate_cache_key(CacheKeys.USER_PROFILE, user_id)
            stats_cache_key = cache.generate_cache_key(CacheKeys.USER_STATS, user_id)
            
            cache.delete(profile_cache_key)
            cache.delete(stats_cache_key)
            
            # Delete physical file if it exists
            file_path = resume_data.get('file_path')
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete file {file_path}: {e}")
            
            logger.info(f"Resume deleted and cache cleaned for resume: {resume_id}")
            
            return jsonify({
                'message': 'Resume deleted successfully',
                'resume_id': resume_id
            }), 200
        else:
            return jsonify({'error': 'Resume deletion failed'}), 500
        
    except Exception as e:
        logger.error(f"Delete resume error: {str(e)}")
        return jsonify({'error': 'Resume deletion failed', 'details': str(e)}), 500

@resume_bp.route('/content/<resume_id>', methods=['GET'])
@auth_required
def get_resume_content(resume_id):
    """Get extracted resume content with caching"""
    try:
        if not resume_model:
            return jsonify({'error': 'Resume service not available'}), 500
        
        user_id = request.user_id
        
        # Check cache first
        cache_key = cache.generate_cache_key(CacheKeys.RESUME_CONTENT, user_id, resume_id)
        cached_content = cache.get(cache_key)
        
        if cached_content:
            logger.info(f"Resume content cache hit for resume: {resume_id}")
            return jsonify(cached_content), 200
        
        # Get from database
        resume_data = resume_model.get_resume_by_id(resume_id)
        if not resume_data:
            return jsonify({'error': 'Resume not found'}), 404
        
        # Verify ownership
        if resume_data.get('user_id') != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Check if processing is complete
        if resume_data.get('status') != 'completed':
            return jsonify({
                'error': 'Resume processing not complete',
                'status': resume_data.get('status', 'unknown')
            }), 202
        
        # Get extracted content
        content = resume_model.get_resume_content(resume_id)
        
        if not content:
            return jsonify({'error': 'Content not found'}), 404
        
        # Cache the content
        cache.set(cache_key, content, CacheTTL.VERY_LONG)
        logger.info(f"Resume content cached for resume: {resume_id}")
        
        return jsonify(content), 200
        
    except Exception as e:
        logger.error(f"Get resume content error: {str(e)}")
        return jsonify({'error': 'Failed to get resume content', 'details': str(e)}), 500

# Cache management endpoints for resumes
@resume_bp.route('/cache/clear', methods=['POST'])
@auth_required
def clear_resume_cache():
    """Clear all resume-related cache entries for the authenticated user"""
    try:
        user_id = request.user_id
        
        # Clear all resume-related cache entries
        cache_patterns = [
            f"{CacheKeys.RESUME_STATUS}:{user_id}*",
            f"{CacheKeys.RESUME_ANALYSIS}:{user_id}*",
            f"{CacheKeys.RESUME_QUESTIONS}:{user_id}*",
            f"{CacheKeys.RESUME_CONTENT}:{user_id}*",
            f"{CacheKeys.USER_RESUMES}:{user_id}*"
        ]
        
        total_deleted = 0
        for pattern in cache_patterns:
            deleted = cache.delete_pattern(pattern)
            total_deleted += deleted
        
        logger.info(f"Cleared {total_deleted} resume cache entries for user: {user_id}")
        
        return jsonify({
            'message': 'Resume cache cleared successfully',
            'entries_deleted': total_deleted
        }), 200
        
    except Exception as e:
        logger.error(f"Clear resume cache error: {str(e)}")
        return jsonify({'error': 'Failed to clear resume cache', 'details': str(e)}), 500

@resume_bp.route('/cache/status', methods=['GET'])
@auth_required
def get_resume_cache_status():
    """Get cache status for resume-related data"""
    try:
        user_id = request.user_id
        
        # Get user's resumes to check cache status
        try:
            resumes = resume_model.get_user_resume_summary(user_id) if resume_model else []
        except Exception as e:
            logger.warning(f"Failed to get user resumes: {e}")
            resumes = []
        
        cache_status = {}
        for resume in resumes:
            resume_id = resume.get('id')
            if resume_id:
                cache_keys_to_check = [
                    (CacheKeys.RESUME_STATUS, 'status'),
                    (CacheKeys.RESUME_ANALYSIS, 'analysis'),
                    (CacheKeys.RESUME_QUESTIONS, 'questions'),
                    (CacheKeys.RESUME_CONTENT, 'content')
                ]
                
                resume_cache_status = {}
                for cache_key_prefix, name in cache_keys_to_check:
                    cache_key = cache.generate_cache_key(cache_key_prefix, user_id, resume_id)
                    exists = cache.exists(cache_key)
                    ttl = cache.get_ttl(cache_key) if exists else -1
                    
                    resume_cache_status[name] = {
                        'cached': exists,
                        'ttl_seconds': ttl,
                        'expires_in': f"{ttl // 60}m {ttl % 60}s" if ttl > 0 else 'Not cached'
                    }
                
                cache_status[resume_id] = {
                    'filename': resume.get('original_filename', 'Unknown'),
                    'status': resume.get('status', 'Unknown'),
                    'cache_status': resume_cache_status
                }
        
        return jsonify({
            'resume_cache_status': cache_status,
            'total_resumes': len(resumes),
            'user_id': user_id
        }), 200
        
    except Exception as e:
        logger.error(f"Get resume cache status error: {str(e)}")
        return jsonify({'error': 'Failed to get resume cache status', 'details': str(e)}), 500

@resume_bp.route('/bulk-cache-refresh', methods=['POST'])
@auth_required
def bulk_cache_refresh():
    """Refresh cache for all user's resumes"""
    try:
        user_id = request.user_id
        
        # Get all user's completed resumes
        try:
            resumes = resume_model.get_user_resumes(user_id) if resume_model else []
        except Exception as e:
            logger.warning(f"Failed to get user resumes: {e}")
            resumes = []
        
        completed_resumes = [r for r in resumes if r.get('status') == 'completed']
        
        refreshed_count = 0
        errors = []
        
        for resume in completed_resumes:
            resume_id = resume.get('id')
            if not resume_id:
                continue
                
            try:
                # Refresh each cache entry
                cache_keys_to_refresh = [
                    CacheKeys.RESUME_STATUS,
                    CacheKeys.RESUME_ANALYSIS,
                    CacheKeys.RESUME_QUESTIONS,
                    CacheKeys.RESUME_CONTENT
                ]
                
                for cache_key_prefix in cache_keys_to_refresh:
                    cache_key = cache.generate_cache_key(cache_key_prefix, user_id, resume_id)
                    cache.delete(cache_key)
                
                refreshed_count += 1
                
            except Exception as e:
                errors.append(f"Resume {resume_id}: {str(e)}")
        
        logger.info(f"Bulk cache refresh completed for user: {user_id}, refreshed: {refreshed_count}")
        
        return jsonify({
            'message': 'Bulk cache refresh completed',
            'refreshed_resumes': refreshed_count,
            'total_resumes': len(completed_resumes),
            'errors': errors
        }), 200
        
    except Exception as e:
        logger.error(f"Bulk cache refresh error: {str(e)}")
        return jsonify({'error': 'Bulk cache refresh failed', 'details': str(e)}), 500