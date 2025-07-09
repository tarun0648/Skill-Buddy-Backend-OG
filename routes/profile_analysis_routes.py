# routes/profile_analysis_routes.py (UPDATED for profile completion integration)
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
    """Analyze LinkedIn profile using Claude AI - UPDATED to integrate with profile completion"""
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
            return jsonify({'error': 'Invalid LinkedIn URL format. Please provide a valid LinkedIn profile URL.'}), 400
        
        # Get user profile for context
        user_doc = db.collection('users').document(user_id).get()
        if not user_doc.exists:
            return jsonify({'error': 'User profile not found'}), 404
        
        user_data = user_doc.to_dict()
        user_profile = user_data.get('profile', {})
        
        # Update user's LinkedIn link in profile if different from current
        current_linkedin = user_profile.get('linkedin_link', '')
        if current_linkedin != linkedin_url:
            logger.info(f"Updating LinkedIn link for user {user_id}: {current_linkedin} -> {linkedin_url}")
            
            # Update LinkedIn link in user profile
            try:
                from models.user_model import UserModel
                user_model = UserModel(db)
                
                # Get current completion
                old_completion = user_profile.get('completion_status', 0)
                
                # Update the profile
                updated_profile = user_profile.copy()
                updated_profile['linkedin_link'] = linkedin_url
                
                # Calculate new completion
                new_completion = user_model.calculate_profile_completion(updated_profile)
                
                update_data = {
                    'profile.linkedin_link': linkedin_url,
                    'profile.completion_status': new_completion,
                    'profile.is_profile_complete': new_completion == 100
                }
                
                # Calculate XP bonus
                milestones = user_model.get_completion_milestones(old_completion, new_completion)
                if milestones:
                    xp_bonus = user_model.calculate_xp_bonus(milestones)
                    if xp_bonus > 0:
                        current_xp = user_data.get('xp', {}).get('total_xp', 0)
                        new_total_xp = current_xp + xp_bonus
                        new_level = (new_total_xp // 100) + 1
                        
                        update_data['xp.total_xp'] = new_total_xp
                        update_data['xp.level'] = new_level
                        
                        logger.info(f"LinkedIn link XP bonus: {xp_bonus} for user {user_id}")
                
                # Apply update
                user_model.update_user(user_id, update_data)
                
                # Update local user_profile for analysis
                user_profile['linkedin_link'] = linkedin_url
                user_profile['completion_status'] = new_completion
                
                logger.info(f"LinkedIn link updated and completion recalculated: {old_completion}% -> {new_completion}%")
                
            except Exception as e:
                logger.error(f"Error updating LinkedIn link: {e}")
                # Continue with analysis even if update fails
        
        # Start LinkedIn analysis
        analysis_id, success = linkedin_service.start_linkedin_analysis(
            user_id=user_id,
            linkedin_url=linkedin_url,
            user_profile=user_profile
        )
        
        if not success:
            return jsonify({'error': 'Failed to start LinkedIn analysis'}), 500
        
        logger.info(f"LinkedIn analysis started for user {user_id}, analysis_id: {analysis_id}")
        
        return jsonify({
            'message': 'LinkedIn analysis started successfully',
            'analysis_id': analysis_id,
            'status': 'pending',
            'type': 'linkedin',
            'profile_updated': current_linkedin != linkedin_url  # Indicate if profile was updated
        }), 201
        
    except Exception as e:
        logger.error(f"LinkedIn analysis error: {e}")
        return jsonify({'error': 'LinkedIn analysis failed', 'details': str(e)}), 500

@profile_analysis_bp.route('/analyze/github', methods=['POST'])
@auth_required
def analyze_github_profile():
    """Analyze GitHub profile using Claude AI and GitHub API - UPDATED to integrate with profile completion"""
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
            logger.info(f"Updating GitHub link for user {user_id}: {current_github} -> {github_url}")
            
            # Update GitHub link in user profile
            try:
                from models.user_model import UserModel
                user_model = UserModel(db)
                
                # Get current completion
                old_completion = user_profile.get('completion_status', 0)
                
                # Update the profile
                updated_profile = user_profile.copy()
                updated_profile['github_link'] = github_url
                
                # Calculate new completion
                new_completion = user_model.calculate_profile_completion(updated_profile)
                
                update_data = {
                    'profile.github_link': github_url,
                    'profile.completion_status': new_completion,
                    'profile.is_profile_complete': new_completion == 100
                }
                
                # Calculate XP bonus
                milestones = user_model.get_completion_milestones(old_completion, new_completion)
                if milestones:
                    xp_bonus = user_model.calculate_xp_bonus(milestones)
                    if xp_bonus > 0:
                        current_xp = user_data.get('xp', {}).get('total_xp', 0)
                        new_total_xp = current_xp + xp_bonus
                        new_level = (new_total_xp // 100) + 1
                        
                        update_data['xp.total_xp'] = new_total_xp
                        update_data['xp.level'] = new_level
                        
                        logger.info(f"GitHub link XP bonus: {xp_bonus} for user {user_id}")
                
                # Apply update
                user_model.update_user(user_id, update_data)
                
                # Update local user_profile for analysis
                user_profile['github_link'] = github_url
                user_profile['completion_status'] = new_completion
                
                logger.info(f"GitHub link updated and completion recalculated: {old_completion}% -> {new_completion}%")
                
            except Exception as e:
                logger.error(f"Error updating GitHub link: {e}")
                # Continue with analysis even if update fails
        
        # Start GitHub analysis
        analysis_id, success = github_service.start_github_analysis(
            user_id=user_id,
            github_username=github_username,
            user_profile=user_profile
        )
        
        if not success:
            return jsonify({'error': 'Failed to start GitHub analysis'}), 500
        
        logger.info(f"GitHub analysis started for user {user_id}, analysis_id: {analysis_id}")
        
        return jsonify({
            'message': 'GitHub analysis started successfully',
            'analysis_id': analysis_id,
            'status': 'pending',
            'type': 'github',
            'github_username': github_username,
            'profile_updated': current_github != github_url  # Indicate if profile was updated
        }), 201
        
    except Exception as e:
        logger.error(f"GitHub analysis error: {e}")
        return jsonify({'error': 'GitHub analysis failed', 'details': str(e)}), 500

@profile_analysis_bp.route('/status/<analysis_id>', methods=['GET'])
@auth_required
def get_analysis_status(analysis_id):
    """Get profile analysis status"""
    try:
        user_id = request.user_id
        analysis_data = profile_analysis_model.get_analysis_by_id(analysis_id)
        
        if not analysis_data or analysis_data.get('user_id') != user_id:
            return jsonify({'error': 'Analysis not found or access denied'}), 404
        
        return jsonify({
            'analysis_id': analysis_id,
            'status': analysis_data.get('status', 'unknown'),
            'type': analysis_data.get('analysis_type'),
            'created_at': analysis_data.get('created_at'),
            'processed_at': analysis_data.get('processed_at'),
            'error_message': analysis_data.get('error_message'),
            'url_or_username': analysis_data.get('profile_url') or analysis_data.get('github_username')
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting analysis status: {e}")
        return jsonify({'error': 'Failed to get analysis status', 'details': str(e)}), 500

@profile_analysis_bp.route('/results/<analysis_id>', methods=['GET'])
@auth_required
def get_analysis_results(analysis_id):
    """Get complete profile analysis results"""
    try:
        user_id = request.user_id
        analysis_data = profile_analysis_model.get_analysis_by_id(analysis_id)
        
        if not analysis_data or analysis_data.get('user_id') != user_id:
            return jsonify({'error': 'Analysis not found or access denied'}), 404
        
        if analysis_data.get('status') != 'completed':
            return jsonify({
                'status': analysis_data.get('status', 'unknown'),
                'message': 'Analysis not completed yet'
            }), 200
        
        return jsonify({
            'analysis_id': analysis_id,
            'status': 'completed',
            'type': analysis_data.get('analysis_type'),
            'analysis_results': analysis_data.get('analysis_results'),
            'suggestions': analysis_data.get('suggestions'),
            'grade': analysis_data.get('grade'),
            'processed_at': analysis_data.get('processed_at'),
            'profile_info': {
                'linkedin_url': analysis_data.get('profile_url'),
                'github_username': analysis_data.get('github_username')
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting analysis results: {e}")
        return jsonify({'error': 'Failed to get analysis results', 'details': str(e)}), 500

@profile_analysis_bp.route('/user/analyses', methods=['GET'])
@auth_required
def get_user_analyses():
    """Get all profile analyses for the authenticated user"""
    try:
        if not profile_analysis_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        analysis_type = request.args.get('type')  # 'linkedin' or 'github'
        
        analyses = profile_analysis_model.get_user_analyses(user_id, analysis_type)
        
        return jsonify({
            'analyses': analyses,
            'total_count': len(analyses),
            'filter_type': analysis_type
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting user analyses: {e}")
        return jsonify({'error': 'Failed to get analyses', 'details': str(e)}), 500

@profile_analysis_bp.route('/suggestions/<analysis_id>', methods=['GET'])
@auth_required
def get_improvement_suggestions(analysis_id):
    """Get detailed improvement suggestions for a specific analysis"""
    try:
        user_id = request.user_id
        analysis_data = profile_analysis_model.get_analysis_by_id(analysis_id)
        
        if not analysis_data or analysis_data.get('user_id') != user_id:
            return jsonify({'error': 'Analysis not found or access denied'}), 404
        
        if analysis_data.get('status') != 'completed':
            return jsonify({'error': 'Analysis not completed yet'}), 400
        
        suggestions = analysis_data.get('suggestions', {})
        
        return jsonify({
            'analysis_id': analysis_id,
            'type': analysis_data.get('analysis_type'),
            'suggestions': suggestions,
            'grade': analysis_data.get('grade'),
            'profile_info': {
                'linkedin_url': analysis_data.get('profile_url'),
                'github_username': analysis_data.get('github_username')
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        return jsonify({'error': 'Failed to get suggestions', 'details': str(e)}), 500

@profile_analysis_bp.route('/reanalyze/<analysis_id>', methods=['POST'])
@auth_required
def reanalyze_profile(analysis_id):
    """Re-analyze a profile with updated information"""
    try:
        user_id = request.user_id
        analysis_data = profile_analysis_model.get_analysis_by_id(analysis_id)
        
        if not analysis_data or analysis_data.get('user_id') != user_id:
            return jsonify({'error': 'Analysis not found or access denied'}), 404
        
        analysis_type = analysis_data.get('analysis_type')
        
        # Get updated user profile
        user_doc = db.collection('users').document(user_id).get()
        if not user_doc.exists:
            return jsonify({'error': 'User profile not found'}), 404
        
        user_data = user_doc.to_dict()
        user_profile = user_data.get('profile', {})
        
        # Start re-analysis based on type
        if analysis_type == 'linkedin':
            linkedin_url = analysis_data.get('profile_url')
            new_analysis_id, success = linkedin_service.start_linkedin_analysis(
                user_id=user_id,
                linkedin_url=linkedin_url,
                user_profile=user_profile
            )
        elif analysis_type == 'github':
            github_username = analysis_data.get('github_username')
            new_analysis_id, success = github_service.start_github_analysis(
                user_id=user_id,
                github_username=github_username,
                user_profile=user_profile
            )
        else:
            return jsonify({'error': 'Invalid analysis type'}), 400
        
        if not success:
            return jsonify({'error': 'Failed to start re-analysis'}), 500
        
        return jsonify({
            'message': f'{analysis_type.title()} re-analysis started',
            'new_analysis_id': new_analysis_id,
            'original_analysis_id': analysis_id,
            'status': 'pending'
        }), 200
        
    except Exception as e:
        logger.error(f"Error re-analyzing profile: {e}")
        return jsonify({'error': 'Failed to re-analyze profile', 'details': str(e)}), 500

@profile_analysis_bp.route('/delete/<analysis_id>', methods=['DELETE'])
@auth_required
def delete_analysis(analysis_id):
    """Delete a profile analysis"""
    try:
        user_id = request.user_id
        analysis_data = profile_analysis_model.get_analysis_by_id(analysis_id)
        
        if not analysis_data or analysis_data.get('user_id') != user_id:
            return jsonify({'error': 'Analysis not found or access denied'}), 404
        
        success = profile_analysis_model.delete_analysis(analysis_id)
        
        if success:
            logger.info(f"Successfully deleted analysis: {analysis_id}")
            return jsonify({'message': 'Analysis deleted successfully'}), 200
        else:
            return jsonify({'error': 'Failed to delete analysis'}), 500
        
    except Exception as e:
        logger.error(f"Error deleting analysis: {e}")
        return jsonify({'error': 'Failed to delete analysis', 'details': str(e)}), 500

@profile_analysis_bp.route('/quick-analyze', methods=['POST'])
@auth_required
def quick_analyze():
    """Quick analyze both LinkedIn and GitHub if user has links in profile"""
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
        
        linkedin_url = user_profile.get('linkedin_link', '').strip()
        github_url = user_profile.get('github_link', '').strip()
        
        results = {
            'linkedin_analysis': None,
            'github_analysis': None,
            'message': 'Quick analysis started for available profiles'
        }
        
        # Start LinkedIn analysis if URL available
        if linkedin_url and 'linkedin.com/in/' in linkedin_url:
            analysis_id, success = linkedin_service.start_linkedin_analysis(
                user_id=user_id,
                linkedin_url=linkedin_url,
                user_profile=user_profile
            )
            if success:
                results['linkedin_analysis'] = {
                    'analysis_id': analysis_id,
                    'status': 'pending',
                    'url': linkedin_url
                }
        
        # Start GitHub analysis if URL available
        if github_url and 'github.com/' in github_url:
            github_username = github_url.split('github.com/')[-1].split('/')[0]
            analysis_id, success = github_service.start_github_analysis(
                user_id=user_id,
                github_username=github_username,
                user_profile=user_profile
            )
            if success:
                results['github_analysis'] = {
                    'analysis_id': analysis_id,
                    'status': 'pending',
                    'username': github_username
                }
        
        if not results['linkedin_analysis'] and not results['github_analysis']:
            return jsonify({
                'message': 'No LinkedIn or GitHub links found in profile',
                'suggestion': 'Add LinkedIn and GitHub links to your profile first'
            }), 400
        
        return jsonify(results), 200
        
    except Exception as e:
        logger.error(f"Quick analyze error: {e}")
        return jsonify({'error': 'Quick analyze failed', 'details': str(e)}), 500