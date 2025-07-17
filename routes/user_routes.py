# routes/user_routes.py - Fixed with Redis Cache Integration
from flask import Blueprint, request, jsonify
from config.firebase_config import firebase_config
from models.user_model import UserModel
from utils.validation import Validator
from services.email_service import email_service
from services.redis_cache_service import cache, CacheKeys, CacheTTL, cache_result, invalidate_cache_pattern
import logging
from datetime import datetime
import os
from functools import wraps

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
    """Local auth decorator for user routes with caching"""
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
                    logger.error(f"User verification error: {e}")
                    return jsonify({'error': 'User verification failed'}), 401
        
        request.user_id = user_id
        return f(*args, **kwargs)
    
    return decorated

@user_bp.route('/profile', methods=['GET'])
@auth_required
def get_profile():
    """Get user profile endpoint with caching"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        
        # Check cache first
        cache_key = cache.generate_cache_key(CacheKeys.USER_PROFILE, user_id)
        cached_profile = cache.get(cache_key)
        
        if cached_profile:
            logger.info(f"Profile cache hit for user: {user_id}")
            return jsonify(cached_profile), 200
        
        # Fetch from database
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
                'phone': '',
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
        
        response_data = {'user': safe_user_data}
        
        # Cache the profile data
        cache.set(cache_key, response_data, CacheTTL.USER_PROFILE)
        logger.info(f"Profile cached for user: {user_id}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Get profile error: {str(e)}")
        return jsonify({'error': 'Failed to get profile', 'details': str(e)}), 500

@user_bp.route('/profile', methods=['PUT'])
@auth_required
def update_profile():
    """Update user profile endpoint with cache invalidation"""
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
        
        # Invalidate specific cache entries
        profile_cache_key = cache.generate_cache_key(CacheKeys.USER_PROFILE, user_id)
        stats_cache_key = cache.generate_cache_key(CacheKeys.USER_STATS, user_id)
        settings_cache_key = cache.generate_cache_key(CacheKeys.USER_SETTINGS, user_id)
        
        cache.delete(profile_cache_key)
        cache.delete(stats_cache_key)
        cache.delete(settings_cache_key)
        
        # Also invalidate validation cache
        validation_cache_key = cache.generate_cache_key(CacheKeys.USER_PROFILE, user_id, 'validation')
        cache.delete(validation_cache_key)
        
        # Get updated user data
        updated_user = user_model.get_user_by_id(user_id)
        
        logger.info(f"Profile updated and cache invalidated for user: {user_id}")
        
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

@user_bp.route('/profile/links', methods=['PUT'])
@auth_required
def update_profile_links():
    """Update GitHub and LinkedIn links with cache invalidation"""
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
        
        # Invalidate cache
        profile_cache_key = cache.generate_cache_key(CacheKeys.USER_PROFILE, user_id)
        cache.delete(profile_cache_key)
        
        # Also invalidate any LinkedIn/GitHub profile caches
        if 'github_link' in data:
            github_cache_key = cache.generate_cache_key(CacheKeys.GITHUB_PROFILE, user_id)
            cache.delete(github_cache_key)
        
        if 'linkedin_link' in data:
            linkedin_cache_key = cache.generate_cache_key(CacheKeys.LINKEDIN_PROFILE, user_id)
            cache.delete(linkedin_cache_key)
        
        # Get updated user data
        updated_user = user_model.get_user_by_id(user_id)
        
        logger.info(f"Profile links updated and cache invalidated for user: {user_id}")
        
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

@user_bp.route('/profile/completion', methods=['GET'])
@auth_required
def get_profile_completion():
    """Get profile completion status with caching"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        
        # Check cache first
        cache_key = cache.generate_cache_key(CacheKeys.USER_PROFILE, user_id, 'completion')
        cached_completion = cache.get(cache_key)
        
        if cached_completion:
            logger.info(f"Profile completion cache hit for user: {user_id}")
            return jsonify(cached_completion), 200
        
        user = user_model.get_user_by_id(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        profile = user.get('profile', {})
        completion_status = profile.get('completion_status', 0)
        
        # Get next steps based on completion system
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
        
        response_data = {
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
        }
        
        # Cache the completion data
        cache.set(cache_key, response_data, CacheTTL.USER_PROFILE)
        logger.info(f"Profile completion cached for user: {user_id}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Get profile completion error: {str(e)}")
        return jsonify({'error': 'Failed to get profile completion', 'details': str(e)}), 500

@user_bp.route('/settings', methods=['GET'])
@auth_required
def get_user_settings():
    """Get user settings with caching"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        
        # Check cache first
        cache_key = cache.generate_cache_key(CacheKeys.USER_SETTINGS, user_id)
        cached_settings = cache.get(cache_key)
        
        if cached_settings:
            logger.info(f"Settings cache hit for user: {user_id}")
            return jsonify(cached_settings), 200
        
        # Fetch from database
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
        
        response_data = {'settings': settings}
        
        # Cache the settings
        cache.set(cache_key, response_data, CacheTTL.USER_SETTINGS)
        logger.info(f"Settings cached for user: {user_id}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Get settings error: {str(e)}")
        return jsonify({'error': 'Failed to get settings', 'details': str(e)}), 500

@user_bp.route('/settings', methods=['PUT'])
@auth_required
def update_user_settings():
    """Update user settings with cache invalidation"""
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
        
        # Invalidate settings cache
        settings_cache_key = cache.generate_cache_key(CacheKeys.USER_SETTINGS, user_id)
        cache.delete(settings_cache_key)
        
        # Get updated settings
        updated_user = user_model.get_user_by_id(user_id)
        updated_settings = updated_user.get('settings', {})
        updated_settings['email_service_enabled'] = email_service.enabled
        
        logger.info(f"Settings updated and cache invalidated for user: {user_id}")
        
        return jsonify({
            'message': 'Settings updated successfully',
            'settings': updated_settings
        }), 200
        
    except Exception as e:
        logger.error(f"Settings update error: {str(e)}")
        return jsonify({'error': 'Settings update failed', 'details': str(e)}), 500

@user_bp.route('/xp', methods=['GET'])
@auth_required
def get_user_xp():
    """Get user XP and level information with caching"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        
        # Check cache first
        cache_key = cache.generate_cache_key(CacheKeys.USER_STATS, user_id, 'xp')
        cached_xp = cache.get(cache_key)
        
        if cached_xp:
            logger.info(f"XP cache hit for user: {user_id}")
            return jsonify(cached_xp), 200
        
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
        
        response_data = {
            'total_xp': total_xp,
            'level': xp_data.get('level', 1),
            'badges': xp_data.get('badges', []),
            'level_progress': level_progress
        }
        
        # Cache the XP data
        cache.set(cache_key, response_data, CacheTTL.USER_STATS)
        logger.info(f"XP data cached for user: {user_id}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Get user XP error: {str(e)}")
        return jsonify({'error': 'Failed to get XP data', 'details': str(e)}), 500

@user_bp.route('/resumes', methods=['GET'])
@auth_required
def get_user_resumes():
    """Get all resumes for the authenticated user with caching"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        
        # Get query parameters for filtering/pagination
        include_details = request.args.get('details', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 50))  # Default limit of 50
        
        # Generate cache key based on parameters
        cache_key = cache.generate_cache_key(
            CacheKeys.USER_RESUMES, 
            user_id, 
            f"details:{include_details}",
            f"limit:{limit}"
        )
        
        # Check cache first
        cached_resumes = cache.get(cache_key)
        if cached_resumes:
            logger.info(f"Resumes cache hit for user: {user_id}")
            return jsonify(cached_resumes), 200
        
        # Import resume model
        from models.resume_model import ResumeModel
        resume_model = ResumeModel(db)
        
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
                # Invalidate profile cache when resume status changes
                profile_cache_key = cache.generate_cache_key(CacheKeys.USER_PROFILE, user_id)
                cache.delete(profile_cache_key)
        
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
        
        # Cache the response
        cache.set(cache_key, response_data, CacheTTL.USER_RESUMES)
        logger.info(f"Resumes cached for user: {user_id}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error getting user resumes: {e}")
        return jsonify({'error': 'Failed to get resumes', 'details': str(e)}), 500

@user_bp.route('/resumes/statistics', methods=['GET'])
@auth_required
def get_user_resume_statistics():
    """Get detailed resume statistics for the user with caching"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        
        # Check cache first
        cache_key = cache.generate_cache_key(CacheKeys.USER_STATS, user_id, 'resume_stats')
        cached_stats = cache.get(cache_key)
        
        if cached_stats:
            logger.info(f"Resume statistics cache hit for user: {user_id}")
            return jsonify(cached_stats), 200
        
        # Import resume model
        from models.resume_model import ResumeModel
        resume_model = ResumeModel(db)
        
        # Get statistics
        statistics = resume_model.get_user_resume_statistics(user_id)
        
        # Add additional computed statistics
        statistics['average_file_size_mb'] = round(
            statistics['total_size_mb'] / statistics['total_resumes'], 2
        ) if statistics['total_resumes'] > 0 else 0
        
        response_data = {'statistics': statistics}
        
        # Cache the statistics
        cache.set(cache_key, response_data, CacheTTL.USER_STATS)
        logger.info(f"Resume statistics cached for user: {user_id}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error getting resume statistics: {e}")
        return jsonify({'error': 'Failed to get resume statistics', 'details': str(e)}), 500

@user_bp.route('/sso/linkedin/data', methods=['GET'])
@auth_required
def get_linkedin_data():
    """Get LinkedIn profile data for the authenticated user with caching"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
        
        user_id = request.user_id
        
        # Check cache first
        cache_key = cache.generate_cache_key(CacheKeys.LINKEDIN_PROFILE, user_id, 'data')
        cached_data = cache.get(cache_key)
        
        if cached_data:
            logger.info(f"LinkedIn data cache hit for user: {user_id}")
            return jsonify(cached_data), 200
        
        user = user_model.get_user_by_id(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        linkedin_data = user.get('linkedin_profile_data')
        
        if not linkedin_data:
            response_data = {
                'message': 'No LinkedIn data found',
                'connected': False
            }
        else:
            response_data = {
                'connected': True,
                'data': linkedin_data,
                'last_updated': linkedin_data.get('fetched_at')
            }
        
        # Cache the LinkedIn data
        cache.set(cache_key, response_data, CacheTTL.LINKEDIN_PROFILE)
        logger.info(f"LinkedIn data cached for user: {user_id}")
        
        return jsonify(response_data), 200 if linkedin_data else 404
        
    except Exception as e:
        logger.error(f"Error getting LinkedIn data: {e}")
        return jsonify({'error': 'Failed to get LinkedIn data'}), 500

@user_bp.route('/sso/github/data', methods=['GET'])
@auth_required
def get_github_data():
    """Get GitHub profile data for the authenticated user with caching"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
        
        user_id = request.user_id
        
        # Check cache first
        cache_key = cache.generate_cache_key(CacheKeys.GITHUB_PROFILE, user_id, 'data')
        cached_data = cache.get(cache_key)
        
        if cached_data:
            logger.info(f"GitHub data cache hit for user: {user_id}")
            return jsonify(cached_data), 200
        
        user = user_model.get_user_by_id(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        github_data = user.get('github_profile_data')
        
        if not github_data:
            response_data = {
                'message': 'No GitHub data found',
                'connected': False
            }
        else:
            response_data = {
                'connected': True,
                'data': github_data,
                'last_updated': github_data.get('fetched_at')
            }
        
        # Cache the GitHub data
        cache.set(cache_key, response_data, CacheTTL.GITHUB_PROFILE)
        logger.info(f"GitHub data cached for user: {user_id}")
        
        return jsonify(response_data), 200 if github_data else 404
        
    except Exception as e:
        logger.error(f"Error getting GitHub data: {e}")
        return jsonify({'error': 'Failed to get GitHub data'}), 500

@user_bp.route('/sso/data/export', methods=['GET'])
@auth_required
def export_sso_data():
    """Export all SSO data for the authenticated user with caching"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
        
        user_id = request.user_id
        
        # Check cache first
        cache_key = cache.generate_cache_key(CacheKeys.USER_PROFILE, user_id, 'sso_export')
        cached_export = cache.get(cache_key)
        
        if cached_export:
            logger.info(f"SSO export cache hit for user: {user_id}")
            return jsonify(cached_export), 200
        
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
        
        # Cache the export data
        cache.set(cache_key, export_data, CacheTTL.LONG)
        logger.info(f"SSO export data cached for user: {user_id}")
        
        return jsonify(export_data), 200
        
    except Exception as e:
        logger.error(f"Error exporting SSO data: {e}")
        return jsonify({'error': 'Failed to export SSO data'}), 500

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

# Cache management endpoints
@user_bp.route('/cache/clear', methods=['POST'])
@auth_required
def clear_user_cache():
    """Clear all cache entries for the authenticated user"""
    try:
        user_id = request.user_id
        
        # Clear all user-related cache entries
        cache_patterns = [
            f"{CacheKeys.USER_PROFILE}:{user_id}*",
            f"{CacheKeys.USER_RESUMES}:{user_id}*",
            f"{CacheKeys.USER_STATS}:{user_id}*",
            f"{CacheKeys.USER_SETTINGS}:{user_id}*",
            f"{CacheKeys.GITHUB_PROFILE}:{user_id}*",
            f"{CacheKeys.LINKEDIN_PROFILE}:{user_id}*"
        ]
        
        total_deleted = 0
        for pattern in cache_patterns:
            deleted = cache.delete_pattern(pattern)
            total_deleted += deleted
        
        logger.info(f"Cleared {total_deleted} cache entries for user: {user_id}")
        
        return jsonify({
            'message': 'User cache cleared successfully',
            'entries_deleted': total_deleted
        }), 200
        
    except Exception as e:
        logger.error(f"Clear cache error: {str(e)}")
        return jsonify({'error': 'Failed to clear cache', 'details': str(e)}), 500

@user_bp.route('/cache/status', methods=['GET'])
@auth_required
def get_cache_status():
    """Get cache status for the authenticated user"""
    try:
        user_id = request.user_id
        
        # Check various cache keys
        cache_keys_to_check = [
            (CacheKeys.USER_PROFILE, 'profile'),
            (CacheKeys.USER_RESUMES, 'resumes'),
            (CacheKeys.USER_STATS, 'stats'),
            (CacheKeys.USER_SETTINGS, 'settings'),
            (CacheKeys.GITHUB_PROFILE, 'github_profile'),
            (CacheKeys.LINKEDIN_PROFILE, 'linkedin_profile')
        ]
        
        cache_status = {}
        for cache_key_prefix, name in cache_keys_to_check:
            cache_key = cache.generate_cache_key(cache_key_prefix, user_id)
            exists = cache.exists(cache_key)
            ttl = cache.get_ttl(cache_key) if exists else -1
            
            cache_status[name] = {
                'cached': exists,
                'ttl_seconds': ttl,
                'expires_in': f"{ttl // 60}m {ttl % 60}s" if ttl > 0 else 'Not cached'
            }
        
        # Get overall cache info
        cache_info = cache.get_cache_info()
        
        return jsonify({
            'user_cache_status': cache_status,
            'redis_info': cache_info,
            'user_id': user_id
        }), 200
        
    except Exception as e:
        logger.error(f"Get cache status error: {str(e)}")
        return jsonify({'error': 'Failed to get cache status', 'details': str(e)}), 500

@user_bp.route('/cache/warm-up', methods=['POST'])
@auth_required
def warm_up_user_cache():
    """Warm up cache for the authenticated user"""
    try:
        user_id = request.user_id
        
        warmed_items = []
        
        # Get user data once
        user_data = user_model.get_user_by_id(user_id)
        if not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        # Warm up user profile
        try:
            profile_key = cache.generate_cache_key(CacheKeys.USER_PROFILE, user_id)
            safe_user_data = {
                'id': user_id,
                'email': user_data.get('email'),
                'profile': user_data.get('profile', {}),
                'xp': user_data.get('xp', {}),
                'sso_provider': user_data.get('sso_provider', 'email'),
                'is_verified': user_data.get('is_verified', False),
                'created_at': user_data.get('created_at'),
                'last_login': user_data.get('last_login'),
                'settings': user_data.get('settings', {})
            }
            cache.set(profile_key, {'user': safe_user_data}, CacheTTL.USER_PROFILE)
            warmed_items.append('user_profile')
            
            # Warm up profile completion
            completion_key = cache.generate_cache_key(CacheKeys.USER_PROFILE, user_id, 'completion')
            profile = user_data.get('profile', {})
            completion_status = profile.get('completion_status', 0)
            completion_data = {
                'completion_status': completion_status,
                'is_complete': profile.get('is_profile_complete', False)
            }
            cache.set(completion_key, completion_data, CacheTTL.USER_PROFILE)
            warmed_items.append('profile_completion')
            
            # Warm up user settings
            settings_key = cache.generate_cache_key(CacheKeys.USER_SETTINGS, user_id)
            settings_data = user_data.get('settings', {})
            settings_data['email_service_enabled'] = email_service.enabled
            cache.set(settings_key, {'settings': settings_data}, CacheTTL.USER_SETTINGS)
            warmed_items.append('user_settings')
            
        except Exception as e:
            logger.warning(f"Failed to warm up user data: {e}")
        
        # Warm up XP data
        try:
            xp_key = cache.generate_cache_key(CacheKeys.USER_STATS, user_id, 'xp')
            xp_data = user_data.get('xp', {})
            total_xp = xp_data.get('total_xp', 0)
            current_level = (total_xp // 100) + 1
            xp_for_current_level = (current_level - 1) * 100
            xp_in_current_level = total_xp - xp_for_current_level
            
            xp_response = {
                'total_xp': total_xp,
                'level': xp_data.get('level', 1),
                'badges': xp_data.get('badges', []),
                'level_progress': {
                    'current_level_xp': xp_in_current_level,
                    'xp_needed_for_next_level': 100 - xp_in_current_level,
                    'progress_percentage': round((xp_in_current_level / 100) * 100, 1)
                }
            }
            cache.set(xp_key, xp_response, CacheTTL.USER_STATS)
            warmed_items.append('user_xp')
            
        except Exception as e:
            logger.warning(f"Failed to warm up XP data: {e}")
        
        # Warm up LinkedIn data if available
        try:
            linkedin_data = user_data.get('linkedin_profile_data')
            if linkedin_data:
                linkedin_key = cache.generate_cache_key(CacheKeys.LINKEDIN_PROFILE, user_id, 'data')
                linkedin_response = {
                    'connected': True,
                    'data': linkedin_data,
                    'last_updated': linkedin_data.get('fetched_at')
                }
                cache.set(linkedin_key, linkedin_response, CacheTTL.LINKEDIN_PROFILE)
                warmed_items.append('linkedin_data')
        except Exception as e:
            logger.warning(f"Failed to warm up LinkedIn data: {e}")
        
        # Warm up GitHub data if available
        try:
            github_data = user_data.get('github_profile_data')
            if github_data:
                github_key = cache.generate_cache_key(CacheKeys.GITHUB_PROFILE, user_id, 'data')
                github_response = {
                    'connected': True,
                    'data': github_data,
                    'last_updated': github_data.get('fetched_at')
                }
                cache.set(github_key, github_response, CacheTTL.GITHUB_PROFILE)
                warmed_items.append('github_data')
        except Exception as e:
            logger.warning(f"Failed to warm up GitHub data: {e}")
        
        logger.info(f"Warmed up {len(warmed_items)} cache items for user {user_id}")
        
        return jsonify({
            'message': 'Cache warm-up completed',
            'user_id': user_id,
            'warmed_items': warmed_items,
            'total_warmed': len(warmed_items)
        }), 200
        
    except Exception as e:
        logger.error(f"Cache warm-up error: {str(e)}")
        return jsonify({'error': 'Cache warm-up failed', 'details': str(e)}), 500