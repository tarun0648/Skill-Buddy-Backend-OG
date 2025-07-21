# routes/profile_analysis_routes.py (UPDATED for enhanced parallel processing)
from flask import Blueprint, request, jsonify
from config.firebase_config import firebase_config
from services.linkedin_analyzer import linkedin_service
from services.github_analyzer import github_service
from models.profile_analysis_model import ProfileAnalysisModel
import logging
from datetime import datetime

# Create blueprint
profile_analysis_bp = Blueprint('profile_analysis', __name__)

# Initialize components
db = firebase_config.get_db()
if db:
    profile_analysis_model = ProfileAnalysisModel(db)
else:
    profile_analysis_model = None

logger = logging.getLogger(__name__)

def auth_required(f):
    """Local auth decorator for profile analysis routes"""
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

@profile_analysis_bp.route('/analyze/linkedin', methods=['POST'])
@auth_required
def analyze_linkedin_profile():
    """Analyze LinkedIn profile using enhanced parallel processing"""
    try:
        if not profile_analysis_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        data = request.get_json()
        
        if not data or 'linkedin_url' not in data:
            return jsonify({'error': 'LinkedIn URL is required'}), 400
        
        linkedin_url = data['linkedin_url'].strip()
        
        # Validate LinkedIn URL format
        if not linkedin_url or 'linkedin.com/in/' not in linkedin_url:
            return jsonify({'error': 'Invalid LinkedIn URL format. Must be a valid LinkedIn profile URL.'}), 400
        
        # Get user profile for context
        user_doc = db.collection('users').document(user_id).get()
        if not user_doc.exists:
            return jsonify({'error': 'User profile not found'}), 404
        
        user_data = user_doc.to_dict()
        user_profile = user_data.get('profile', {})
        
        # Update user's LinkedIn link in profile if different from current
        current_linkedin = user_profile.get('linkedin_link', '')
        if current_linkedin != linkedin_url:
            from models.user_model import UserModel
            user_model = UserModel(db)
            user_model.update_linkedin_link(user_id, linkedin_url)
            logger.info(f"Updated LinkedIn link for user {user_id}: {linkedin_url}")
        
        # Start LinkedIn analysis using enhanced service
        task_id, success = linkedin_service.start_linkedin_analysis(
            user_id=user_id,
            linkedin_url=linkedin_url,
            user_profile=user_profile
        )
        
        if not success:
            return jsonify({'error': 'Failed to start LinkedIn analysis'}), 500
        
        logger.info(f"LinkedIn analysis started for user {user_id}, task_id: {task_id}")
        
        return jsonify({
            'message': 'LinkedIn analysis started',
            'user_id': user_id,
            'task_id': task_id,
            'status': 'pending',
            'progress': 0
        }), 200
        
    except Exception as e:
        logger.error(f"LinkedIn analysis error: {str(e)}")
        return jsonify({'error': 'Failed to start LinkedIn analysis', 'details': str(e)}), 500

@profile_analysis_bp.route('/analyze/github', methods=['POST'])
@auth_required
def analyze_github_profile():
    """Analyze GitHub profile using enhanced parallel processing"""
    try:
        if not profile_analysis_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        data = request.get_json()
        
        if not data or 'github_username' not in data:
            return jsonify({'error': 'GitHub username is required'}), 400
        
        github_username = data['github_username'].strip()
        
        # Validate GitHub username format
        if not github_username or len(github_username) < 1:
            return jsonify({'error': 'Invalid GitHub username format'}), 400
        
        # Remove @ symbol if present
        if github_username.startswith('@'):
            github_username = github_username[1:]
        
        # Extract username from URL if full URL provided
        if 'github.com/' in github_username:
            github_username = github_username.split('github.com/')[-1].split('/')[0]
        
        # Get user profile for context
        user_doc = db.collection('users').document(user_id).get()
        if not user_doc.exists:
            return jsonify({'error': 'User profile not found'}), 404
        
        user_data = user_doc.to_dict()
        user_profile = user_data.get('profile', {})
        
        # Update user's GitHub link in profile if different from current
        github_url = f"https://github.com/{github_username}"
        current_github = user_profile.get('github_link', '')
        if current_github != github_url:
            from models.user_model import UserModel
            user_model = UserModel(db)
            user_model.update_github_link(user_id, github_url)
            logger.info(f"Updated GitHub link for user {user_id}: {github_url}")
        
        # Start GitHub analysis using enhanced service
        task_id, success = github_service.start_github_analysis(
            user_id=user_id,
            github_username=github_username,
            user_profile=user_profile
        )
        
        if not success:
            return jsonify({'error': 'Failed to start GitHub analysis'}), 500
        
        logger.info(f"GitHub analysis started for user {user_id}, task_id: {task_id}")
        
        return jsonify({
            'message': 'GitHub analysis started',
            'user_id': user_id,
            'task_id': task_id,
            'status': 'pending',
            'progress': 0
        }), 200
        
    except Exception as e:
        logger.error(f"GitHub analysis error: {str(e)}")
        return jsonify({'error': 'Failed to start GitHub analysis', 'details': str(e)}), 500

@profile_analysis_bp.route('/status/linkedin/<user_id>', methods=['GET'])
@auth_required
def get_linkedin_status(user_id):
    """Get LinkedIn analysis status for user with enhanced tracking"""
    try:
        # Verify the user_id in URL matches the authenticated user
        if user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get LinkedIn processing status using enhanced service
        status_data = linkedin_service.get_processing_status(user_id)
        
        if not status_data:
            return jsonify({'error': 'No LinkedIn analysis found for user'}), 404
        
        return jsonify({
            'user_id': user_id,
            'task_id': status_data.get('task_id'),
            'analysis_id': status_data.get('analysis_id'),
            'status': status_data.get('status'),
            'progress': status_data.get('progress', 0),
            'linkedin_url': status_data.get('linkedin_url', ''),
            'created_at': status_data.get('created_at'),
            'started_at': status_data.get('started_at'),
            'completed_at': status_data.get('completed_at'),
            'error_message': status_data.get('error_message'),
            'is_active': status_data.get('is_active', False)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting LinkedIn status: {e}")
        return jsonify({'error': 'Failed to get LinkedIn status', 'details': str(e)}), 500

@profile_analysis_bp.route('/status/github/<user_id>', methods=['GET'])
@auth_required
def get_github_status(user_id):
    """Get GitHub analysis status for user with enhanced tracking"""
    try:
        # Verify the user_id in URL matches the authenticated user
        if user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get GitHub processing status using enhanced service
        status_data = github_service.get_processing_status(user_id)
        
        if not status_data:
            return jsonify({'error': 'No GitHub analysis found for user'}), 404
        
        return jsonify({
            'user_id': user_id,
            'task_id': status_data.get('task_id'),
            'analysis_id': status_data.get('analysis_id'),
            'status': status_data.get('status'),
            'progress': status_data.get('progress', 0),
            'github_username': status_data.get('github_username', ''),
            'created_at': status_data.get('created_at'),
            'started_at': status_data.get('started_at'),
            'completed_at': status_data.get('completed_at'),
            'error_message': status_data.get('error_message'),
            'is_active': status_data.get('is_active', False)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting GitHub status: {e}")
        return jsonify({'error': 'Failed to get GitHub status', 'details': str(e)}), 500

@profile_analysis_bp.route('/results/linkedin/<user_id>', methods=['GET'])
@auth_required
def get_linkedin_results(user_id):
    """Get LinkedIn analysis results for user with enhanced tracking"""
    try:
        # Verify the user_id in URL matches the authenticated user
        if user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get LinkedIn results using enhanced service
        results = linkedin_service.get_analysis_results(user_id)
        
        if not results:
            return jsonify({'error': 'No LinkedIn analysis results found for user'}), 404
        
        # If processing is not completed, return status info
        if results.get('status') != 'completed':
            return jsonify({
                'user_id': user_id,
                'status': results.get('status'),
                'progress': results.get('progress', 0),
                'message': results.get('message', 'LinkedIn analysis in progress')
            }), 200
        
        # Return completed results
        return jsonify({
            'user_id': user_id,
            'task_id': results.get('task_id'),
            'analysis_id': results.get('analysis_id'),
            'status': 'completed',
            'analysis_results': results.get('analysis_results'),
            'suggestions': results.get('suggestions'),
            'grade': results.get('grade'),
            'linkedin_url': results.get('linkedin_url', ''),
            'processed_at': results.get('processed_at')
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting LinkedIn results: {e}")
        return jsonify({'error': 'Failed to get LinkedIn results', 'details': str(e)}), 500

@profile_analysis_bp.route('/results/github/<user_id>', methods=['GET'])
@auth_required
def get_github_results(user_id):
    """Get GitHub analysis results for user with enhanced tracking"""
    try:
        # Verify the user_id in URL matches the authenticated user
        if user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get GitHub results using enhanced service
        results = github_service.get_analysis_results(user_id)
        
        if not results:
            return jsonify({'error': 'No GitHub analysis results found for user'}), 404
        
        # If processing is not completed, return status info
        if results.get('status') != 'completed':
            return jsonify({
                'user_id': user_id,
                'status': results.get('status'),
                'progress': results.get('progress', 0),
                'message': results.get('message', 'GitHub analysis in progress')
            }), 200
        
        # Return completed results
        return jsonify({
            'user_id': user_id,
            'task_id': results.get('task_id'),
            'analysis_id': results.get('analysis_id'),
            'status': 'completed',
            'analysis_results': results.get('analysis_results'),
            'suggestions': results.get('suggestions'),
            'grade': results.get('grade'),
            'github_stats': results.get('github_stats'),
            'github_username': results.get('github_username', ''),
            'processed_at': results.get('processed_at')
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting GitHub results: {e}")
        return jsonify({'error': 'Failed to get GitHub results', 'details': str(e)}), 500

@profile_analysis_bp.route('/results/<user_id>', methods=['GET'])
@auth_required
def get_analysis_results(user_id):
    """Get latest analysis results for the authenticated user with enhanced tracking"""
    try:
        if not profile_analysis_model:
            return jsonify({'error': 'Database not available'}), 500
            
        # Verify the user_id in URL matches the authenticated user
        if user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get LinkedIn and GitHub results using enhanced services
        linkedin_results = linkedin_service.get_analysis_results(user_id)
        github_results = github_service.get_analysis_results(user_id)
        
        return jsonify({
            'user_id': user_id,
            'linkedin_analysis': linkedin_results,
            'github_analysis': github_results,
            'has_linkedin': linkedin_results is not None,
            'has_github': github_results is not None
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting analysis results: {e}")
        return jsonify({'error': 'Failed to get analysis results', 'details': str(e)}), 500

@profile_analysis_bp.route('/suggestions/<user_id>', methods=['GET'])
@auth_required
def get_improvement_suggestions(user_id):
    """Get improvement suggestions for user's latest analyses"""
    try:
        # Verify the user_id in URL matches the authenticated user
        if user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get suggestions from both LinkedIn and GitHub analyses
        linkedin_results = linkedin_service.get_analysis_results(user_id)
        github_results = github_service.get_analysis_results(user_id)
        
        suggestions = {
            'linkedin_suggestions': None,
            'github_suggestions': None,
            'combined_suggestions': []
        }
        
        if linkedin_results and linkedin_results.get('status') == 'completed':
            suggestions['linkedin_suggestions'] = linkedin_results.get('suggestions', {})
        
        if github_results and github_results.get('status') == 'completed':
            suggestions['github_suggestions'] = github_results.get('suggestions', {})
        
        # Combine suggestions for overall improvement
        if suggestions['linkedin_suggestions']:
            suggestions['combined_suggestions'].extend(
                suggestions['linkedin_suggestions'].get('improvement_suggestions', {}).get('immediate_actions', [])
            )
        
        if suggestions['github_suggestions']:
            suggestions['combined_suggestions'].extend(
                suggestions['github_suggestions'].get('improvement_suggestions', {}).get('immediate_actions', [])
            )
        
        return jsonify({
            'user_id': user_id,
            'suggestions': suggestions
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting improvement suggestions: {e}")
        return jsonify({'error': 'Failed to get improvement suggestions', 'details': str(e)}), 500

@profile_analysis_bp.route('/reanalyze/linkedin/<user_id>', methods=['POST'])
@auth_required
def reanalyze_linkedin(user_id):
    """Reanalyze LinkedIn profile for user"""
    try:
        # Verify the user_id in URL matches the authenticated user
        if user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get user's current LinkedIn URL
        user_doc = db.collection('users').document(user_id).get()
        if not user_doc.exists:
            return jsonify({'error': 'User profile not found'}), 404
        
        user_data = user_doc.to_dict()
        user_profile = user_data.get('profile', {})
        linkedin_url = user_profile.get('linkedin_link', '')
        
        if not linkedin_url:
            return jsonify({'error': 'No LinkedIn URL found for user'}), 400
        
        # Start LinkedIn reanalysis
        task_id, success = linkedin_service.start_linkedin_analysis(
            user_id=user_id,
            linkedin_url=linkedin_url,
            user_profile=user_profile
        )
        
        if not success:
            return jsonify({'error': 'Failed to start LinkedIn reanalysis'}), 500
        
        logger.info(f"LinkedIn reanalysis started for user {user_id}, task_id: {task_id}")
        
        return jsonify({
            'message': 'LinkedIn reanalysis started',
            'user_id': user_id,
            'task_id': task_id,
            'status': 'pending',
            'progress': 0
        }), 200
        
    except Exception as e:
        logger.error(f"LinkedIn reanalysis error: {str(e)}")
        return jsonify({'error': 'Failed to start LinkedIn reanalysis', 'details': str(e)}), 500

@profile_analysis_bp.route('/reanalyze/github/<user_id>', methods=['POST'])
@auth_required
def reanalyze_github(user_id):
    """Reanalyze GitHub profile for user"""
    try:
        # Verify the user_id in URL matches the authenticated user
        if user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get user's current GitHub URL
        user_doc = db.collection('users').document(user_id).get()
        if not user_doc.exists:
            return jsonify({'error': 'User profile not found'}), 404
        
        user_data = user_doc.to_dict()
        user_profile = user_data.get('profile', {})
        github_url = user_profile.get('github_link', '')
        
        if not github_url:
            return jsonify({'error': 'No GitHub URL found for user'}), 400
        
        # Extract username from URL
        github_username = github_url.split('github.com/')[-1].split('/')[0]
        
        # Start GitHub reanalysis
        task_id, success = github_service.start_github_analysis(
            user_id=user_id,
            github_username=github_username,
            user_profile=user_profile
        )
        
        if not success:
            return jsonify({'error': 'Failed to start GitHub reanalysis'}), 500
        
        logger.info(f"GitHub reanalysis started for user {user_id}, task_id: {task_id}")
        
        return jsonify({
            'message': 'GitHub reanalysis started',
            'user_id': user_id,
            'task_id': task_id,
            'status': 'pending',
            'progress': 0
        }), 200
        
    except Exception as e:
        logger.error(f"GitHub reanalysis error: {str(e)}")
        return jsonify({'error': 'Failed to start GitHub reanalysis', 'details': str(e)}), 500

@profile_analysis_bp.route('/delete/<user_id>', methods=['DELETE'])
@auth_required
def delete_analysis(user_id):
    """Delete user's latest analyses"""
    try:
        # Verify the user_id in URL matches the authenticated user
        if user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json() or {}
        analysis_type = data.get('analysis_type')  # 'linkedin', 'github', or None for all
        
        if not profile_analysis_model:
            return jsonify({'error': 'Database not available'}), 500
        
        # Get user's analyses
        user_analyses = profile_analysis_model.get_user_analyses(user_id, analysis_type)
        
        if not user_analyses:
            return jsonify({'error': 'No analyses found for user'}), 404
        
        deleted_count = 0
        deleted_ids = []
        
        for analysis in user_analyses:
            analysis_id = analysis.get('id')
            success = profile_analysis_model.delete_analysis(analysis_id)
            if success:
                deleted_count += 1
                deleted_ids.append(analysis_id)
        
        logger.info(f"Successfully deleted {deleted_count} analyses for user: {user_id}")
        
        return jsonify({
            'message': f'Successfully deleted {deleted_count} analyses',
            'user_id': user_id,
            'deleted_count': deleted_count,
            'deleted_ids': deleted_ids
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting analysis: {e}")
        return jsonify({'error': 'Failed to delete analysis', 'details': str(e)}), 500

@profile_analysis_bp.route('/quick-analyze', methods=['POST'])
@auth_required
def quick_analyze():
    """Quick analyze both LinkedIn and GitHub profiles for the authenticated user"""
    try:
        if not profile_analysis_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        
        # Get user profile
        user_doc = db.collection('users').document(user_id).get()
        if not user_doc.exists:
            return jsonify({'error': 'User profile not found'}), 404
        
        user_data = user_doc.to_dict()
        user_profile = user_data.get('profile', {})
        
        linkedin_url = user_profile.get('linkedin_link', '')
        github_link = user_profile.get('github_link', '')
        
        if not linkedin_url and not github_link:
            return jsonify({'error': 'No LinkedIn or GitHub links found in profile'}), 400
        
        analysis_ids = {}
        success_count = 0
        
        # Start LinkedIn analysis if URL exists
        if linkedin_url and 'linkedin.com/in/' in linkedin_url:
            analysis_id, success = linkedin_service.start_linkedin_analysis(
                user_id=user_id,
                linkedin_url=linkedin_url,
                user_profile=user_profile
            )
            if success:
                analysis_ids['linkedin'] = analysis_id
                success_count += 1
        
        # Start GitHub analysis if URL exists
        if github_link and 'github.com/' in github_link:
            github_username = github_link.split('github.com/')[-1].split('/')[0]
            analysis_id, success = github_service.start_github_analysis(
                user_id=user_id,
                github_username=github_username,
                user_profile=user_profile
            )
            if success:
                analysis_ids['github'] = analysis_id
                success_count += 1
        
        if success_count == 0:
            return jsonify({'error': 'Failed to start any analysis'}), 500
        
        logger.info(f"Quick analysis started for user {user_id}, analysis_ids: {analysis_ids}")
        
        return jsonify({
            'message': f'Quick analysis started for {success_count} profile(s)',
            'user_id': user_id,
            'analysis_ids': analysis_ids,
            'success_count': success_count,
            'status': 'pending'
        }), 200
        
    except Exception as e:
        logger.error(f"Quick analysis error: {str(e)}")
        return jsonify({'error': 'Failed to start quick analysis', 'details': str(e)}), 500