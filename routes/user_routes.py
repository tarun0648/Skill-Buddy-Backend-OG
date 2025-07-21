# routes/user_routes.py (COMPLETE with Email Integration)
from flask import Blueprint, request, jsonify
from config.firebase_config import firebase_config
from models.user_model import UserModel
from utils.validation import Validator
from services.email_service import email_service
import logging
from datetime import datetime
import os

# Create blueprint
user_bp = Blueprint('user', __name__)

# Initialize components
db = firebase_config.get_db()
if db:
    user_model = UserModel(db)
else:
    user_model = None

logger = logging.getLogger(__name__)

def auth_required(f):
    """Local auth decorator for user routes"""
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

@user_bp.route('/profile', methods=['GET'])
@auth_required
def get_profile():
    """Get user profile endpoint"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        user = user_model.get_user_by_id(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Format response properly
        safe_user_data = {
            'id': user_id,
            'email': user.get('email'),
            'profile': user.get('profile', {
                'name': '',
                'profession': '',
                'career_choices': [],
                'college_name': '',
                'college_email': '',
                'github_link': '',
                'linkedin_link': '',
                'completion_status': 0,
                'is_profile_complete': False,
                'profile_picture': '',
                'has_resume': False
            }),
            'xp': user.get('xp', {
                'total_xp': 0,
                'level': 1,
                'badges': []
            }),
            'sso_provider': user.get('sso_provider', 'email'),
            'is_verified': user.get('is_verified', False),
            'created_at': user.get('created_at'),
            'last_login': user.get('last_login'),
            'settings': user.get('settings', {
                'notifications': True,
                'email_updates': True,
                'privacy_level': 'normal'
            })
        }
        
        return jsonify({'user': safe_user_data}), 200
        
    except Exception as e:
        logger.error(f"Get profile error: {str(e)}")
        return jsonify({'error': 'Failed to get profile', 'details': str(e)}), 500

@user_bp.route('/profile', methods=['PUT'])
@auth_required
def update_profile():
    """Update user profile endpoint - Updated for new completion system with email notifications"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Get current user data
        current_user = user_model.get_user_by_id(user_id)
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        current_profile = current_user.get('profile', {})
        old_completion = current_profile.get('completion_status', 0)
        
        # Prepare update data
        update_data = {}
        
        # Handle each profile field
        if 'name' in data and data['name'] and data['name'].strip():
            update_data['profile.name'] = data['name'].strip()
        
        if 'profession' in data and data['profession']:
            valid_professions = ['Student', 'Graduate', 'Post Graduate', 'Professional', 'Switch Career']
            if data['profession'] in valid_professions:
                update_data['profile.profession'] = data['profession']
        
        if 'career_choices' in data and isinstance(data['career_choices'], list):
            # Limit to 3 choices
            career_choices = data['career_choices'][:3]
            update_data['profile.career_choices'] = career_choices
        
        if 'college_name' in data and data['college_name'] and data['college_name'].strip():
            update_data['profile.college_name'] = data['college_name'].strip()
        
        if 'college_email' in data and data['college_email'] and data['college_email'].strip():
            college_email = data['college_email'].lower().strip()
            if Validator.validate_email(college_email):
                update_data['profile.college_email'] = college_email
        
        if 'github_link' in data:
            github_link = data['github_link'].strip() if data['github_link'] else ''
            update_data['profile.github_link'] = github_link
        
        if 'linkedin_link' in data:
            linkedin_link = data['linkedin_link'].strip() if data['linkedin_link'] else ''
            update_data['profile.linkedin_link'] = linkedin_link
        
        if 'phone' in data and data['phone']:
            update_data['profile.phone'] = data['phone'].strip()
        
        if 'profile_picture' in data:
            update_data['profile.profile_picture'] = data['profile_picture']
        
        # Create updated profile for completion calculation
        updated_profile = current_profile.copy()
        for key, value in update_data.items():
            if key.startswith('profile.'):
                field_name = key.replace('profile.', '')
                updated_profile[field_name] = value
        
        # Calculate new completion status
        new_completion = user_model.calculate_profile_completion(updated_profile)
        update_data['profile.completion_status'] = new_completion
        update_data['profile.is_profile_complete'] = new_completion == 100
        
        # Calculate XP bonus for milestones
        milestones = user_model.get_completion_milestones(old_completion, new_completion)
        xp_earned = 0
        if milestones:
            xp_bonus = user_model.calculate_xp_bonus(milestones)
            
            if xp_bonus > 0:
                current_xp = current_user.get('xp', {}).get('total_xp', 0)
                new_total_xp = current_xp + xp_bonus
                new_level = (new_total_xp // 100) + 1
                
                update_data['xp.total_xp'] = new_total_xp
                update_data['xp.level'] = new_level
                xp_earned = xp_bonus
        
        # Apply updates with milestone email integration
        if update_data:
            success = user_model.update_profile_with_milestone_email(user_id, update_data, old_completion)
            if not success:
                return jsonify({'error': 'Failed to update profile'}), 500
        
        # Get updated user data
        updated_user = user_model.get_user_by_id(user_id)
        
        logger.info(f"Profile updated for user: {user_id}")
        
        return jsonify({
            'message': 'Profile updated successfully',
            'profile': updated_user.get('profile', {}),
            'xp': updated_user.get('xp', {}),
            'completion_status': updated_user.get('profile', {}).get('completion_status', 0),
            'milestones_reached': milestones if milestones else [],
            'xp_earned': xp_earned,
            'email_notifications_sent': email_service.enabled and len([m for m in milestones if m in [55, 85, 100]]) > 0
        }), 200
        
    except Exception as e:
        logger.error(f"Profile update error: {str(e)}")
        return jsonify({'error': 'Profile update failed', 'details': str(e)}), 500

@user_bp.route('/settings', methods=['GET'])
@auth_required
def get_user_settings():
    """Get user settings"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        user = user_model.get_user_by_id(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        settings = user.get('settings', {
            'notifications': True,
            'email_updates': True,
            'privacy_level': 'normal'
        })
        
        # Add email service status
        settings['email_service_enabled'] = email_service.enabled
        
        return jsonify({'settings': settings}), 200
        
    except Exception as e:
        logger.error(f"Get settings error: {str(e)}")
        return jsonify({'error': 'Failed to get settings', 'details': str(e)}), 500

@user_bp.route('/settings', methods=['PUT'])
@auth_required
def update_user_settings():
    """Update user settings"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Get current user
        user = user_model.get_user_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        current_settings = user.get('settings', {})
        
        # Update settings
        update_data = {}
        
        if 'notifications' in data:
            update_data['settings.notifications'] = bool(data['notifications'])
        
        if 'email_updates' in data:
            update_data['settings.email_updates'] = bool(data['email_updates'])
        
        if 'privacy_level' in data:
            valid_levels = ['private', 'normal', 'public']
            if data['privacy_level'] in valid_levels:
                update_data['settings.privacy_level'] = data['privacy_level']
        
        # Apply updates
        if update_data:
            success = user_model.update_user(user_id, update_data)
            if not success:
                return jsonify({'error': 'Failed to update settings'}), 500
        
        # Get updated settings
        updated_user = user_model.get_user_by_id(user_id)
        updated_settings = updated_user.get('settings', {})
        updated_settings['email_service_enabled'] = email_service.enabled
        
        logger.info(f"Settings updated for user: {user_id}")
        
        return jsonify({
            'message': 'Settings updated successfully',
            'settings': updated_settings
        }), 200
        
    except Exception as e:
        logger.error(f"Settings update error: {str(e)}")
        return jsonify({'error': 'Settings update failed', 'details': str(e)}), 500

@user_bp.route('/resumes', methods=['GET'])
@auth_required
def get_user_resumes():
    """Get all resumes for the authenticated user with detailed statistics"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        
        # Import resume model
        from models.resume_model import ResumeModel
        resume_model = ResumeModel(db)
        
        # Get query parameters for filtering/pagination
        include_details = request.args.get('details', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 50))  # Default limit of 50
        
        if include_details:
            # Get full resume data
            resumes = resume_model.get_user_resumes(user_id)
            if limit and len(resumes) > limit:
                resumes = resumes[:limit]
        else:
            # Get optimized summary data
            resumes = resume_model.get_user_resume_summary(user_id)
            if limit and len(resumes) > limit:
                resumes = resumes[:limit]
        
        # Get statistics
        statistics = resume_model.get_user_resume_statistics(user_id)
        
        # Update user's resume status if they have completed resumes
        has_resume = statistics['completed'] > 0
        current_user = user_model.get_user_by_id(user_id)
        if current_user:
            current_has_resume = current_user.get('profile', {}).get('has_resume', False)
            if has_resume != current_has_resume:
                user_model.update_resume_status(user_id, has_resume)
        
        # Prepare response
        response_data = {
            'resumes': resumes,
            'statistics': statistics,
            'meta': {
                'total_count': statistics['total_resumes'],
                'returned_count': len(resumes),
                'includes_full_details': include_details,
                'limit_applied': limit
            }
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error getting user resumes: {e}")
        return jsonify({'error': 'Failed to get resumes', 'details': str(e)}), 500

@user_bp.route('/resumes/statistics', methods=['GET'])
@auth_required
def get_user_resume_statistics():
    """Get detailed resume statistics for the user"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        
        # Import resume model
        from models.resume_model import ResumeModel
        resume_model = ResumeModel(db)
        
        # Get statistics
        statistics = resume_model.get_user_resume_statistics(user_id)
        
        # Add additional computed statistics
        statistics['average_file_size_mb'] = round(
            statistics['total_size_mb'] / statistics['total_resumes'], 2
        ) if statistics['total_resumes'] > 0 else 0
        
        return jsonify({'statistics': statistics}), 200
        
    except Exception as e:
        logger.error(f"Error getting resume statistics: {e}")
        return jsonify({'error': 'Failed to get resume statistics', 'details': str(e)}), 500

@user_bp.route('/xp', methods=['GET'])
@auth_required
def get_user_xp():
    """Get user XP and level information"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        user = user_model.get_user_by_id(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        xp_data = user.get('xp', {})
        total_xp = xp_data.get('total_xp', 0)
        
        # Calculate level progress
        current_level = (total_xp // 100) + 1
        xp_for_current_level = (current_level - 1) * 100
        xp_in_current_level = total_xp - xp_for_current_level
        xp_needed_for_next_level = 100
        
        level_progress = {
            'current_level_xp': xp_in_current_level,
            'xp_needed_for_next_level': xp_needed_for_next_level - xp_in_current_level,
            'progress_percentage': round((xp_in_current_level / xp_needed_for_next_level) * 100, 1)
        }
        
        return jsonify({
            'total_xp': total_xp,
            'level': xp_data.get('level', 1),
            'badges': xp_data.get('badges', []),
            'level_progress': level_progress
        }), 200
        
    except Exception as e:
        logger.error(f"Get user XP error: {str(e)}")
        return jsonify({'error': 'Failed to get XP data', 'details': str(e)}), 500

@user_bp.route('/profile/completion', methods=['GET'])
@auth_required
def get_profile_completion():
    """Get profile completion status - Updated for new completion system"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        user = user_model.get_user_by_id(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        profile = user.get('profile', {})
        completion_status = profile.get('completion_status', 0)
        
        # Get next steps based on new completion system
        next_steps = []
        
        # Basic profile steps (55% total)
        if not profile.get('name'):
            next_steps.append({
                'step': 'name', 
                'description': 'Add your name', 
                'completion': 10,
                'category': 'basic'
            })
        elif not profile.get('profession'):
            next_steps.append({
                'step': 'profession', 
                'description': 'Select your profession', 
                'completion': 20,
                'category': 'basic'
            })
        elif not profile.get('career_choices') or len(profile.get('career_choices', [])) == 0:
            next_steps.append({
                'step': 'career_choices', 
                'description': 'Choose your career interests', 
                'completion': 30,
                'category': 'basic'
            })
        elif not profile.get('college_name'):
            next_steps.append({
                'step': 'college_name', 
                'description': 'Add your college/university name', 
                'completion': 40,
                'category': 'basic'
            })
        elif not profile.get('college_email'):
            next_steps.append({
                'step': 'college_email', 
                'description': 'Add your college email', 
                'completion': 55,
                'category': 'basic'
            })
        
        # Additional steps (45% total)
        if completion_status >= 55:  # Only show these after basic profile is complete
            if not profile.get('github_link'):
                next_steps.append({
                    'step': 'github_link', 
                    'description': 'Add your GitHub profile link', 
                    'completion': 70,
                    'category': 'additional'
                })
            
            if not profile.get('linkedin_link'):
                next_steps.append({
                    'step': 'linkedin_link', 
                    'description': 'Add your LinkedIn profile link', 
                    'completion': 85,
                    'category': 'additional'
                })
            
            if not profile.get('has_resume'):
                next_steps.append({
                    'step': 'resume_upload', 
                    'description': 'Upload your resume', 
                    'completion': 100,
                    'category': 'additional'
                })
        
        # Completion breakdown
        completion_breakdown = {
            'basic_profile': min(completion_status, 55),
            'basic_profile_complete': completion_status >= 55,
            'github_linked': bool(profile.get('github_link')),
            'linkedin_linked': bool(profile.get('linkedin_link')),
            'resume_uploaded': bool(profile.get('has_resume')),
            'additional_completion': max(0, completion_status - 55) if completion_status > 55 else 0
        }
        
        return jsonify({
            'completion_status': completion_status,
            'is_complete': profile.get('is_profile_complete', False),
            'next_steps': next_steps,
            'completion_breakdown': completion_breakdown,
            'milestones': {
                'basic_profile_complete': completion_status >= 55,
                'github_added': bool(profile.get('github_link')),
                'linkedin_added': bool(profile.get('linkedin_link')),
                'resume_uploaded': bool(profile.get('has_resume')),
                'fully_complete': completion_status >= 100
            },
            'email_notifications_enabled': email_service.enabled and user.get('settings', {}).get('email_updates', True)
        }), 200
        
    except Exception as e:
        logger.error(f"Get profile completion error: {str(e)}")
        return jsonify({'error': 'Failed to get profile completion', 'details': str(e)}), 500

@user_bp.route('/profile/links', methods=['PUT'])
@auth_required
def update_profile_links():
    """Update GitHub and LinkedIn links specifically with email notifications"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Get current user data
        current_user = user_model.get_user_by_id(user_id)
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        current_profile = current_user.get('profile', {})
        old_completion = current_profile.get('completion_status', 0)
        
        # Prepare update data
        update_data = {}
        
        if 'github_link' in data:
            github_link = data['github_link'].strip() if data['github_link'] else ''
            # Basic GitHub URL validation
            if github_link and not github_link.startswith(('http://', 'https://')):
                github_link = 'https://' + github_link
            update_data['profile.github_link'] = github_link
        
        if 'linkedin_link' in data:
            linkedin_link = data['linkedin_link'].strip() if data['linkedin_link'] else ''
            # Basic LinkedIn URL validation
            if linkedin_link and not linkedin_link.startswith(('http://', 'https://')):
                linkedin_link = 'https://' + linkedin_link
            update_data['profile.linkedin_link'] = linkedin_link
        
        # Create updated profile for completion calculation
        updated_profile = current_profile.copy()
        for key, value in update_data.items():
            if key.startswith('profile.'):
                field_name = key.replace('profile.', '')
                updated_profile[field_name] = value
        
        # Calculate new completion status
        new_completion = user_model.calculate_profile_completion(updated_profile)
        update_data['profile.completion_status'] = new_completion
        update_data['profile.is_profile_complete'] = new_completion == 100
        
        # Calculate XP bonus for milestones
        milestones = user_model.get_completion_milestones(old_completion, new_completion)
        xp_earned = 0
        if milestones:
            xp_bonus = user_model.calculate_xp_bonus(milestones)
            
            if xp_bonus > 0:
                current_xp = current_user.get('xp', {}).get('total_xp', 0)
                new_total_xp = current_xp + xp_bonus
                new_level = (new_total_xp // 100) + 1
                
                update_data['xp.total_xp'] = new_total_xp
                update_data['xp.level'] = new_level
                xp_earned = xp_bonus
        
        # Apply updates with milestone email integration
        if update_data:
            success = user_model.update_profile_with_milestone_email(user_id, update_data, old_completion)
            if not success:
                return jsonify({'error': 'Failed to update profile links'}), 500
        
        # Get updated user data
        updated_user = user_model.get_user_by_id(user_id)
        
        logger.info(f"Profile links updated for user: {user_id}")
        
        return jsonify({
            'message': 'Profile links updated successfully',
            'profile': updated_user.get('profile', {}),
            'completion_status': updated_user.get('profile', {}).get('completion_status', 0),
            'milestones_reached': milestones if milestones else [],
            'xp_earned': xp_earned,
            'email_notifications_sent': email_service.enabled and len([m for m in milestones if m in [55, 85, 100]]) > 0
        }), 200
        
    except Exception as e:
        logger.error(f"Profile links update error: {str(e)}")
        return jsonify({'error': 'Profile links update failed', 'details': str(e)}), 500

@user_bp.route('/test-milestone-email', methods=['POST'])
@auth_required
def test_milestone_email():
    """Test milestone email functionality (for development/testing)"""
    try:
        if not email_service.enabled:
            return jsonify({'error': 'Email service is not configured'}), 503
        
        user_id = request.user_id
        data = request.get_json()
        
        milestone = data.get('milestone', 55) if data else 55
        xp_earned = data.get('xp_earned', 15) if data else 15
        
        # Get user data
        user = user_model.get_user_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user_profile = user.get('profile', {})
        user_name = user_profile.get('name', 'Test User')
        user_email = user.get('email', '')
        
        if not user_email:
            return jsonify({'error': 'User email not found'}), 400
        
        # Send test milestone email
        success = email_service.send_profile_completion_milestone_email(
            user_email, user_name, milestone, xp_earned
        )
        
        if success:
            return jsonify({
                'message': 'Test milestone email sent successfully',
                'email': user_email,
                'milestone': milestone,
                'xp_earned': xp_earned
            }), 200
        else:
            return jsonify({'error': 'Failed to send test milestone email'}), 500
        
    except Exception as e:
        logger.error(f"Test milestone email error: {str(e)}")
        return jsonify({'error': 'Test email failed', 'details': str(e)}), 500

@user_bp.route('/sso/linkedin/data', methods=['GET'])
@auth_required
def get_linkedin_data():
    """Get LinkedIn profile data for the authenticated user"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
        
        user_id = request.user_id
        user = user_model.get_user_by_id(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        linkedin_data = user.get('linkedin_profile_data')
        
        if not linkedin_data:
            return jsonify({
                'message': 'No LinkedIn data found',
                'connected': False
            }), 404
        
        return jsonify({
            'connected': True,
            'data': linkedin_data,
            'last_updated': linkedin_data.get('fetched_at')
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting LinkedIn data: {e}")
        return jsonify({'error': 'Failed to get LinkedIn data'}), 500

@user_bp.route('/sso/github/data', methods=['GET'])
@auth_required
def get_github_data():
    """Get GitHub profile data for the authenticated user"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
        
        user_id = request.user_id
        user = user_model.get_user_by_id(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        github_data = user.get('github_profile_data')
        
        if not github_data:
            return jsonify({
                'message': 'No GitHub data found',
                'connected': False
            }), 404
        
        return jsonify({
            'connected': True,
            'data': github_data,
            'last_updated': github_data.get('fetched_at')
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting GitHub data: {e}")
        return jsonify({'error': 'Failed to get GitHub data'}), 500

@user_bp.route('/sso/data/export', methods=['GET'])
@auth_required
def export_sso_data():
    """Export all SSO data for the authenticated user"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
        
        user_id = request.user_id
        user = user_model.get_user_by_id(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        export_data = {
            'user_id': user_id,
            'exported_at': datetime.utcnow().isoformat(),
            'linkedin_data': user.get('linkedin_profile_data'),
            'github_data': user.get('github_profile_data'),
            'connections': {
                'linkedin_connected': user.get('linkedin_connected', False),
                'github_connected': user.get('github_connected', False)
            }
        }
        
        return jsonify(export_data), 200
        
    except Exception as e:
        logger.error(f"Error exporting SSO data: {e}")
        return jsonify({'error': 'Failed to export SSO data'}), 500

@user_bp.route('/all-data', methods=['GET'])
@auth_required
def get_all_user_data():
    """Get all user data including resume, GitHub, LinkedIn, portfolio, and all results stored in the database"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        
        # Get query parameters for filtering
        include_resumes = request.args.get('include_resumes', 'true').lower() == 'true'
        include_profile_analyses = request.args.get('include_profile_analyses', 'true').lower() == 'true'
        include_portfolio_analyses = request.args.get('include_portfolio_analyses', 'true').lower() == 'true'
        include_sso_data = request.args.get('include_sso_data', 'true').lower() == 'true'
        include_statistics = request.args.get('include_statistics', 'true').lower() == 'true'
        
        # Get basic user data
        user = user_model.get_user_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Prepare comprehensive response
        all_user_data = {
            'user_id': user_id,
            'fetched_at': datetime.utcnow().isoformat(),
            'basic_profile': {
                'id': user_id,
                'email': user.get('email'),
                'phone': user.get('phone'),
                'sso_provider': user.get('sso_provider', 'email'),
                'is_verified': user.get('is_verified', False),
                'is_active': user.get('is_active', True),
                'created_at': user.get('created_at'),
                'updated_at': user.get('updated_at'),
                'last_login': user.get('last_login')
            },
            'profile': user.get('profile', {
                'name': '',
                'profession': '',
                'career_choices': [],
                'college_name': '',
                'college_email': '',
                'github_link': '',
                'linkedin_link': '',
                'completion_status': 0,
                'is_profile_complete': False,
                'profile_picture': '',
                'phone': '',
                'has_resume': False
            }),
            'xp': user.get('xp', {
                'total_xp': 0,
                'level': 1,
                'badges': []
            }),
            'settings': user.get('settings', {
                'notifications': True,
                'email_updates': True,
                'privacy_level': 'normal'
            })
        }
        
        # Add SSO connections data
        if include_sso_data:
            sso_connections = user_model.get_sso_connections(user_id)
            all_user_data['sso_connections'] = sso_connections
            
            # Add LinkedIn profile data if available
            if user.get('linkedin_profile_data'):
                all_user_data['linkedin_profile_data'] = user.get('linkedin_profile_data')
            
            # Add GitHub profile data if available
            if user.get('github_profile_data'):
                all_user_data['github_profile_data'] = user.get('github_profile_data')
        
        # Add resume data
        if include_resumes:
            try:
                from models.resume_model import ResumeModel
                resume_model = ResumeModel(db)
                
                # Get all resumes with full details
                resumes = resume_model.get_user_resumes(user_id)
                all_user_data['resumes'] = {
                    'data': resumes,
                    'count': len(resumes),
                    'statistics': resume_model.get_user_resume_statistics(user_id) if include_statistics else None
                }
            except Exception as e:
                logger.error(f"Error fetching resume data: {e}")
                all_user_data['resumes'] = {
                    'error': f"Failed to fetch resume data: {str(e)}",
                    'data': [],
                    'count': 0
                }
        
        # Add profile analysis data (LinkedIn and GitHub analyses)
        if include_profile_analyses:
            try:
                from models.profile_analysis_model import ProfileAnalysisModel
                profile_analysis_model = ProfileAnalysisModel(db)
                
                # Get all profile analyses
                profile_analyses = profile_analysis_model.get_user_analyses(user_id)
                
                # Separate by type
                linkedin_analyses = [analysis for analysis in profile_analyses if analysis.get('analysis_type') == 'linkedin']
                github_analyses = [analysis for analysis in profile_analyses if analysis.get('analysis_type') == 'github']
                
                all_user_data['profile_analyses'] = {
                    'all_analyses': profile_analyses,
                    'linkedin_analyses': linkedin_analyses,
                    'github_analyses': github_analyses,
                    'count': len(profile_analyses),
                    'linkedin_count': len(linkedin_analyses),
                    'github_count': len(github_analyses),
                    'statistics': profile_analysis_model.get_user_analysis_statistics(user_id) if include_statistics else None
                }
            except Exception as e:
                logger.error(f"Error fetching profile analysis data: {e}")
                all_user_data['profile_analyses'] = {
                    'error': f"Failed to fetch profile analysis data: {str(e)}",
                    'all_analyses': [],
                    'linkedin_analyses': [],
                    'github_analyses': [],
                    'count': 0,
                    'linkedin_count': 0,
                    'github_count': 0
                }
        
        # Add portfolio analysis data
        if include_portfolio_analyses:
            try:
                from models.portfolio_analysis_model import PortfolioAnalysisModel
                portfolio_analysis_model = PortfolioAnalysisModel(db)
                
                # Get all portfolio analyses
                portfolio_analyses = portfolio_analysis_model.get_user_analyses(user_id, 'portfolio')
                
                all_user_data['portfolio_analyses'] = {
                    'data': portfolio_analyses,
                    'count': len(portfolio_analyses),
                    'statistics': portfolio_analysis_model.get_user_analysis_statistics(user_id) if include_statistics else None
                }
            except Exception as e:
                logger.error(f"Error fetching portfolio analysis data: {e}")
                all_user_data['portfolio_analyses'] = {
                    'error': f"Failed to fetch portfolio analysis data: {str(e)}",
                    'data': [],
                    'count': 0
                }
        
        # Add comprehensive statistics
        if include_statistics:
            all_user_data['comprehensive_statistics'] = {
                'total_resumes': all_user_data.get('resumes', {}).get('count', 0),
                'total_profile_analyses': all_user_data.get('profile_analyses', {}).get('count', 0),
                'total_portfolio_analyses': all_user_data.get('portfolio_analyses', {}).get('count', 0),
                'profile_completion': user.get('profile', {}).get('completion_status', 0),
                'total_xp': user.get('xp', {}).get('total_xp', 0),
                'level': user.get('xp', {}).get('level', 1),
                'has_linkedin_data': bool(user.get('linkedin_profile_data')),
                'has_github_data': bool(user.get('github_profile_data')),
                'has_resume': user.get('profile', {}).get('has_resume', False),
                'is_verified': user.get('is_verified', False),
                'account_age_days': None  # Will be calculated below
            }
            
            # Calculate account age
            if user.get('created_at'):
                try:
                    created_date = datetime.fromisoformat(user['created_at'].replace('Z', '+00:00'))
                    account_age = datetime.utcnow() - created_date.replace(tzinfo=None)
                    all_user_data['comprehensive_statistics']['account_age_days'] = account_age.days
                except:
                    pass
        
        # Add meta information
        all_user_data['meta'] = {
            'data_included': {
                'resumes': include_resumes,
                'profile_analyses': include_profile_analyses,
                'portfolio_analyses': include_portfolio_analyses,
                'sso_data': include_sso_data,
                'statistics': include_statistics
            },
            'total_data_points': len(all_user_data) - 3,  # Exclude user_id, fetched_at, and meta
            'response_size_estimate': len(str(all_user_data))
        }
        
        logger.info(f"Retrieved comprehensive data for user: {user_id}")
        
        return jsonify(all_user_data), 200
        
    except Exception as e:
        logger.error(f"Error getting all user data: {e}")
        return jsonify({'error': 'Failed to get all user data', 'details': str(e)}), 500

@user_bp.route('/all-data/summary', methods=['GET'])
@auth_required
def get_all_user_data_summary():
    """Get a summary of all user data - optimized for dashboard views"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        
        # Get basic user data
        user = user_model.get_user_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Prepare summary response
        summary_data = {
            'user_id': user_id,
            'fetched_at': datetime.utcnow().isoformat(),
            'profile_summary': {
                'name': user.get('profile', {}).get('name', ''),
                'profession': user.get('profile', {}).get('profession', ''),
                'completion_status': user.get('profile', {}).get('completion_status', 0),
                'is_profile_complete': user.get('profile', {}).get('is_profile_complete', False),
                'has_resume': user.get('profile', {}).get('has_resume', False),
                'github_link': user.get('profile', {}).get('github_link', ''),
                'linkedin_link': user.get('profile', {}).get('linkedin_link', ''),
                'profile_picture': user.get('profile', {}).get('profile_picture', '')
            },
            'xp_summary': {
                'total_xp': user.get('xp', {}).get('total_xp', 0),
                'level': user.get('xp', {}).get('level', 1),
                'badges_count': len(user.get('xp', {}).get('badges', [])),
                'badges': user.get('xp', {}).get('badges', [])
            },
            'account_summary': {
                'email': user.get('email', ''),
                'phone': user.get('phone', ''),
                'sso_provider': user.get('sso_provider', 'email'),
                'is_verified': user.get('is_verified', False),
                'created_at': user.get('created_at'),
                'last_login': user.get('last_login')
            }
        }
        
        # Add data counts
        data_counts = {
            'resumes': 0,
            'linkedin_analyses': 0,
            'github_analyses': 0,
            'portfolio_analyses': 0
        }
        
        # Get resume count
        try:
            from models.resume_model import ResumeModel
            resume_model = ResumeModel(db)
            resume_summary = resume_model.get_user_resume_summary(user_id)
            data_counts['resumes'] = len(resume_summary)
        except Exception as e:
            logger.error(f"Error fetching resume count: {e}")
        
        # Get profile analysis counts
        try:
            from models.profile_analysis_model import ProfileAnalysisModel
            profile_analysis_model = ProfileAnalysisModel(db)
            profile_summary = profile_analysis_model.get_user_analysis_summary(user_id)
            
            linkedin_count = len([analysis for analysis in profile_summary if analysis.get('analysis_type') == 'linkedin'])
            github_count = len([analysis for analysis in profile_summary if analysis.get('analysis_type') == 'github'])
            
            data_counts['linkedin_analyses'] = linkedin_count
            data_counts['github_analyses'] = github_count
        except Exception as e:
            logger.error(f"Error fetching profile analysis counts: {e}")
        
        # Get portfolio analysis count
        try:
            from models.portfolio_analysis_model import PortfolioAnalysisModel
            portfolio_analysis_model = PortfolioAnalysisModel(db)
            portfolio_summary = portfolio_analysis_model.get_user_analysis_summary(user_id)
            data_counts['portfolio_analyses'] = len(portfolio_summary)
        except Exception as e:
            logger.error(f"Error fetching portfolio analysis count: {e}")
        
        summary_data['data_counts'] = data_counts
        
        # Add SSO connections summary
        sso_connections = user_model.get_sso_connections(user_id)
        summary_data['sso_connections'] = sso_connections
        
        # Add recent activity (last 5 items from each category)
        recent_activity = {
            'recent_resumes': [],
            'recent_linkedin_analyses': [],
            'recent_github_analyses': [],
            'recent_portfolio_analyses': []
        }
        
        # Get recent resumes
        try:
            from models.resume_model import ResumeModel
            resume_model = ResumeModel(db)
            resume_summary = resume_model.get_user_resume_summary(user_id)
            recent_activity['recent_resumes'] = resume_summary[:5]  # Last 5
        except Exception as e:
            logger.error(f"Error fetching recent resumes: {e}")
        
        # Get recent profile analyses
        try:
            from models.profile_analysis_model import ProfileAnalysisModel
            profile_analysis_model = ProfileAnalysisModel(db)
            profile_summary = profile_analysis_model.get_user_analysis_summary(user_id)
            
            linkedin_recent = [analysis for analysis in profile_summary if analysis.get('analysis_type') == 'linkedin'][:5]
            github_recent = [analysis for analysis in profile_summary if analysis.get('analysis_type') == 'github'][:5]
            
            recent_activity['recent_linkedin_analyses'] = linkedin_recent
            recent_activity['recent_github_analyses'] = github_recent
        except Exception as e:
            logger.error(f"Error fetching recent profile analyses: {e}")
        
        # Get recent portfolio analyses
        try:
            from models.portfolio_analysis_model import PortfolioAnalysisModel
            portfolio_analysis_model = PortfolioAnalysisModel(db)
            portfolio_summary = portfolio_analysis_model.get_user_analysis_summary(user_id)
            recent_activity['recent_portfolio_analyses'] = portfolio_summary[:5]  # Last 5
        except Exception as e:
            logger.error(f"Error fetching recent portfolio analyses: {e}")
        
        summary_data['recent_activity'] = recent_activity
        
        # Add quick statistics
        quick_stats = {
            'total_analyses': data_counts['linkedin_analyses'] + data_counts['github_analyses'] + data_counts['portfolio_analyses'],
            'total_documents': data_counts['resumes'],
            'profile_completion_percentage': user.get('profile', {}).get('completion_status', 0),
            'has_linkedin_data': bool(user.get('linkedin_profile_data')),
            'has_github_data': bool(user.get('github_profile_data')),
            'is_verified': user.get('is_verified', False)
        }
        
        # Calculate account age
        if user.get('created_at'):
            try:
                created_date = datetime.fromisoformat(user['created_at'].replace('Z', '+00:00'))
                account_age = datetime.utcnow() - created_date.replace(tzinfo=None)
                quick_stats['account_age_days'] = account_age.days
            except:
                pass
        
        summary_data['quick_stats'] = quick_stats
        
        logger.info(f"Retrieved summary data for user: {user_id}")
        
        return jsonify(summary_data), 200
        
    except Exception as e:
        logger.error(f"Error getting user data summary: {e}")
        return jsonify({'error': 'Failed to get user data summary', 'details': str(e)}), 500

