# routes/user_routes.py
from flask import Blueprint, request, jsonify
from config.firebase_config import firebase_config
from models.user_model import UserModel
from utils.validation import Validator
import logging
from datetime import datetime

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
                'completion_status': 0,
                'is_profile_complete': False,
                'profile_picture': ''
            }),
            'xp': user.get('xp', {
                'total_xp': 0,
                'level': 1,
                'badges': []
            }),
            'sso_provider': user.get('sso_provider', 'email'),
            'is_verified': user.get('is_verified', False),
            'created_at': user.get('created_at'),
            'last_login': user.get('last_login')
        }
        
        return jsonify({'user': safe_user_data}), 200
        
    except Exception as e:
        logger.error(f"Get profile error: {str(e)}")
        return jsonify({'error': 'Failed to get profile', 'details': str(e)}), 500

@user_bp.route('/profile', methods=['PUT'])
@auth_required
def update_profile():
    """Update user profile endpoint"""
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
        current_completion = current_profile.get('completion_status', 0)
        
        # Prepare update data
        update_data = {}
        new_completion = current_completion
        
        # Handle each profile field
        if 'name' in data and data['name'] and data['name'].strip():
            update_data['profile.name'] = data['name'].strip()
            if not current_profile.get('name'):
                new_completion = max(new_completion, 25)
        
        if 'profession' in data and data['profession']:
            valid_professions = ['Student', 'Graduate', 'Post Graduate', 'Professional', 'Switch Career']
            if data['profession'] in valid_professions:
                update_data['profile.profession'] = data['profession']
                if not current_profile.get('profession'):
                    new_completion = max(new_completion, 50)
        
        if 'career_choices' in data and isinstance(data['career_choices'], list):
            # Limit to 3 choices
            career_choices = data['career_choices'][:3]
            update_data['profile.career_choices'] = career_choices
            if not current_profile.get('career_choices') and career_choices:
                new_completion = max(new_completion, 75)
        
        if 'college_name' in data and data['college_name'] and data['college_name'].strip():
            update_data['profile.college_name'] = data['college_name'].strip()
            if not current_profile.get('college_name'):
                new_completion = max(new_completion, 90)
        
        if 'college_email' in data and data['college_email'] and data['college_email'].strip():
            college_email = data['college_email'].lower().strip()
            if Validator.validate_email(college_email):
                update_data['profile.college_email'] = college_email
                new_completion = 100
        
        if 'phone' in data and data['phone']:
            update_data['profile.phone'] = data['phone'].strip()
        
        if 'profile_picture' in data:
            update_data['profile.profile_picture'] = data['profile_picture']
        
        # Update completion status if changed
        if new_completion > current_completion:
            update_data['profile.completion_status'] = new_completion
            update_data['profile.is_profile_complete'] = new_completion == 100
            
            # Calculate XP bonus
            xp_bonus = 0
            milestones = {25: 10, 50: 15, 75: 20, 100: 50}
            
            for milestone, bonus in milestones.items():
                if current_completion < milestone <= new_completion:
                    xp_bonus += bonus
            
            if xp_bonus > 0:
                current_xp = current_user.get('xp', {}).get('total_xp', 0)
                new_total_xp = current_xp + xp_bonus
                new_level = (new_total_xp // 100) + 1
                
                update_data['xp.total_xp'] = new_total_xp
                update_data['xp.level'] = new_level
        
        # Apply updates
        if update_data:
            success = user_model.update_user(user_id, update_data)
            if not success:
                return jsonify({'error': 'Failed to update profile'}), 500
        
        # Get updated user data
        updated_user = user_model.get_user_by_id(user_id)
        
        logger.info(f"Profile updated for user: {user_id}")
        
        return jsonify({
            'message': 'Profile updated successfully',
            'profile': updated_user.get('profile', {}),
            'xp': updated_user.get('xp', {}),
            'completion_status': updated_user.get('profile', {}).get('completion_status', 0)
        }), 200
        
    except Exception as e:
        logger.error(f"Profile update error: {str(e)}")
        return jsonify({'error': 'Profile update failed', 'details': str(e)}), 500

# Add this updated endpoint to routes/user_routes.py

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
    """Get profile completion status"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        user = user_model.get_user_by_id(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        profile = user.get('profile', {})
        completion_status = profile.get('completion_status', 0)
        
        # Get next steps
        next_steps = []
        if completion_status < 25 or not profile.get('name'):
            next_steps.append({'step': 'name', 'description': 'Add your name', 'completion': 25})
        if completion_status < 50 or not profile.get('profession'):
            next_steps.append({'step': 'profession', 'description': 'Select your profession', 'completion': 50})
        if completion_status < 75 or not profile.get('career_choices'):
            next_steps.append({'step': 'career_choices', 'description': 'Choose your career interests', 'completion': 75})
        if completion_status < 100 or not profile.get('college_name') or not profile.get('college_email'):
            next_steps.append({'step': 'college_info', 'description': 'Add your education details', 'completion': 100})
        
        return jsonify({
            'completion_status': completion_status,
            'is_complete': profile.get('is_profile_complete', False),
            'next_steps': next_steps
        }), 200
        
    except Exception as e:
        logger.error(f"Get profile completion error: {str(e)}")
        return jsonify({'error': 'Failed to get profile completion', 'details': str(e)}), 500