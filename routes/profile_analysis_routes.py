# routes/profile_analysis_routes.py - Fixed with Redis Caching
from flask import Blueprint, request, jsonify
from functools import wraps
import logging
from datetime import datetime

# Import cache service
from services.redis_cache_service import cache, CacheKeys, CacheTTL, cache_result, invalidate_cache_pattern

logger = logging.getLogger(__name__)

profile_analysis_bp = Blueprint('profile_analysis', __name__)

# Global variables (will be set when blueprint is registered)
profile_analysis_model = None
user_model = None
db = None
email_service = None

def init_profile_analysis_routes(profile_analysis_model_instance, user_model_instance, db_instance, email_service_instance):
    """Initialize profile analysis routes with model instances"""
    global profile_analysis_model, user_model, db, email_service
    profile_analysis_model = profile_analysis_model_instance
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

@profile_analysis_bp.route('/linkedin', methods=['POST'])
@auth_required
def analyze_linkedin_profile():
    """Analyze LinkedIn profile with cache invalidation"""
    try:
        if not profile_analysis_model:
            return jsonify({'error': 'Profile analysis service not available'}), 500
        
        user_id = request.user_id
        data = request.get_json()
        
        if not data or 'linkedin_url' not in data:
            return jsonify({'error': 'LinkedIn URL is required'}), 400
        
        linkedin_url = data['linkedin_url'].strip()
        if not linkedin_url:
            return jsonify({'error': 'LinkedIn URL cannot be empty'}), 400
        
        # Get user profile for context
        user_data = user_model.get_user_by_id(user_id) if user_model else None
        
        # Create analysis record
        analysis_data = {
            'user_id': user_id,
            'analysis_type': 'linkedin',
            'linkedin_url': linkedin_url,
            'user_profile_context': user_data.get('profile', {}) if user_data else {}
        }
        
        analysis_id = profile_analysis_model.create_analysis_record(analysis_data)
        
        # Invalidate profile analysis caches
        cache_patterns = [
            f"{CacheKeys.PROFILE_ANALYSIS}:{user_id}*",
            f"{CacheKeys.PROFILE_ANALYSIS_RESULTS}:{user_id}*",
            f"{CacheKeys.LINKEDIN_PROFILE}:{user_id}*"
        ]
        
        for pattern in cache_patterns:
            cache.delete_pattern(pattern)
        
        # Start analysis asynchronously
        try:
            from services.profile_analyzer import ProfileAnalyzer
            analyzer = ProfileAnalyzer(db, email_service)
            analyzer.analyze_linkedin_profile_async(analysis_id, linkedin_url)
            
            logger.info(f"LinkedIn analysis started for user: {user_id}, analysis: {analysis_id}")
            
        except Exception as e:
            logger.error(f"LinkedIn analysis failed to start: {e}")
            profile_analysis_model.update_analysis_status(analysis_id, 'failed', str(e))
        
        return jsonify({
            'message': 'LinkedIn analysis started',
            'analysis_id': analysis_id,
            'status': 'processing'
        }), 201
        
    except Exception as e:
        logger.error(f"LinkedIn analysis error: {str(e)}")
        return jsonify({'error': 'LinkedIn analysis failed', 'details': str(e)}), 500

@profile_analysis_bp.route('/github', methods=['POST'])
@auth_required
def analyze_github_profile():
    """Analyze GitHub profile with cache invalidation"""
    try:
        if not profile_analysis_model:
            return jsonify({'error': 'Profile analysis service not available'}), 500
        
        user_id = request.user_id
        data = request.get_json()
        
        if not data or 'github_url' not in data:
            return jsonify({'error': 'GitHub URL is required'}), 400
        
        github_url = data['github_url'].strip()
        if not github_url:
            return jsonify({'error': 'GitHub URL cannot be empty'}), 400
        
        # Get user profile for context
        user_data = user_model.get_user_by_id(user_id) if user_model else None
        
        # Create analysis record
        analysis_data = {
            'user_id': user_id,
            'analysis_type': 'github',
            'github_url': github_url,
            'user_profile_context': user_data.get('profile', {}) if user_data else {}
        }
        
        analysis_id = profile_analysis_model.create_analysis_record(analysis_data)
        
        # Invalidate profile analysis caches
        cache_patterns = [
            f"{CacheKeys.PROFILE_ANALYSIS}:{user_id}*",
            f"{CacheKeys.PROFILE_ANALYSIS_RESULTS}:{user_id}*",
            f"{CacheKeys.GITHUB_PROFILE}:{user_id}*"
        ]
        
        for pattern in cache_patterns:
            cache.delete_pattern(pattern)
        
        # Start analysis asynchronously
        try:
            from services.profile_analyzer import ProfileAnalyzer
            analyzer = ProfileAnalyzer(db, email_service)
            analyzer.analyze_github_profile_async(analysis_id, github_url)
            
            logger.info(f"GitHub analysis started for user: {user_id}, analysis: {analysis_id}")
            
        except Exception as e:
            logger.error(f"GitHub analysis failed to start: {e}")
            profile_analysis_model.update_analysis_status(analysis_id, 'failed', str(e))
        
        return jsonify({
            'message': 'GitHub analysis started',
            'analysis_id': analysis_id,
            'status': 'processing'
        }), 201
        
    except Exception as e:
        logger.error(f"GitHub analysis error: {str(e)}")
        return jsonify({'error': 'GitHub analysis failed', 'details': str(e)}), 500

@profile_analysis_bp.route('/results', methods=['GET'])
@auth_required
def get_profile_analysis_results():
    """Get all profile analysis results with caching"""
    try:
        if not profile_analysis_model:
            return jsonify({'error': 'Profile analysis service not available'}), 500
        
        user_id = request.user_id
        
        # Get query parameters
        analysis_type = request.args.get('type')  # 'linkedin' or 'github'
        include_details = request.args.get('details', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 20))
        
        # Generate cache key
        cache_key = cache.generate_cache_key(
            CacheKeys.PROFILE_ANALYSIS_RESULTS, 
            user_id, 
            f"type:{analysis_type or 'all'}",
            f"details:{include_details}",
            f"limit:{limit}"
        )
        
        # Check cache first
        cached_results = cache.get(cache_key)
        if cached_results:
            logger.info(f"Profile analysis results cache hit for user: {user_id}")
            return jsonify(cached_results), 200
        
        # Get from database
        try:
            if include_details:
                analyses = profile_analysis_model.get_user_analyses(user_id, analysis_type)
            else:
                analyses = profile_analysis_model.get_user_analysis_summary(user_id, analysis_type)
        except Exception as e:
            logger.warning(f"Failed to get profile analyses: {e}")
            analyses = []
        
        # Apply limit
        if limit and len(analyses) > limit:
            analyses = analyses[:limit]
        
        # Get statistics
        try:
            stats = profile_analysis_model.get_user_analysis_statistics(user_id)
        except Exception as e:
            logger.warning(f"Failed to get profile analysis stats: {e}")
            stats = {}
        
        response_data = {
            'analyses': analyses,
            'statistics': stats,
            'meta': {
                'total_count': len(analyses),
                'analysis_type': analysis_type,
                'includes_details': include_details,
                'limit_applied': limit
            }
        }
        
        # Cache the results
        cache.set(cache_key, response_data, CacheTTL.PROFILE_ANALYSIS)
        logger.info(f"Profile analysis results cached for user: {user_id}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Get profile analysis results error: {str(e)}")
        return jsonify({'error': 'Failed to get profile analysis results', 'details': str(e)}), 500

@profile_analysis_bp.route('/results/<analysis_id>', methods=['GET'])
@auth_required
def get_single_profile_analysis_result(analysis_id):
    """Get single profile analysis result with caching"""
    try:
        if not profile_analysis_model:
            return jsonify({'error': 'Profile analysis service not available'}), 500
        
        user_id = request.user_id
        
        # Check cache first
        cache_key = cache.generate_cache_key(CacheKeys.PROFILE_ANALYSIS_RESULTS, user_id, analysis_id)
        cached_result = cache.get(cache_key)
        
        if cached_result:
            logger.info(f"Single profile analysis result cache hit for analysis: {analysis_id}")
            return jsonify(cached_result), 200
        
        # Get from database
        analysis = profile_analysis_model.get_analysis_by_id(analysis_id)
        if not analysis:
            return jsonify({'error': 'Analysis not found'}), 404
        
        # Verify ownership
        if analysis.get('user_id') != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Cache the result
        cache.set(cache_key, analysis, CacheTTL.PROFILE_ANALYSIS)
        logger.info(f"Single profile analysis result cached for analysis: {analysis_id}")
        
        return jsonify(analysis), 200
        
    except Exception as e:
        logger.error(f"Get single profile analysis result error: {str(e)}")
        return jsonify({'error': 'Failed to get analysis result', 'details': str(e)}), 500

@profile_analysis_bp.route('/suggestions/<analysis_id>', methods=['GET'])
@auth_required
def get_profile_analysis_suggestions(analysis_id):
    """Get profile analysis suggestions with caching"""
    try:
        if not profile_analysis_model:
            return jsonify({'error': 'Profile analysis service not available'}), 500
        
        user_id = request.user_id
        
        # Check cache first
        cache_key = cache.generate_cache_key(CacheKeys.PROFILE_ANALYSIS_SUGGESTIONS, user_id, analysis_id)
        cached_suggestions = cache.get(cache_key)
        
        if cached_suggestions:
            logger.info(f"Profile analysis suggestions cache hit for analysis: {analysis_id}")
            return jsonify(cached_suggestions), 200
        
        # Get from database
        analysis = profile_analysis_model.get_analysis_by_id(analysis_id)
        if not analysis:
            return jsonify({'error': 'Analysis not found'}), 404
        
        # Verify ownership
        if analysis.get('user_id') != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Check if analysis is complete
        if analysis.get('status') != 'completed':
            return jsonify({
                'error': 'Analysis not complete',
                'status': analysis.get('status', 'unknown')
            }), 202
        
        # Get suggestions
        try:
            suggestions = profile_analysis_model.get_analysis_suggestions(analysis_id)
        except Exception as e:
            logger.warning(f"Failed to get suggestions: {e}")
            suggestions = None
        
        if not suggestions:
            return jsonify({'error': 'Suggestions not found'}), 404
        
        # Cache the suggestions
        cache.set(cache_key, suggestions, CacheTTL.PROFILE_ANALYSIS)
        logger.info(f"Profile analysis suggestions cached for analysis: {analysis_id}")
        
        return jsonify(suggestions), 200
        
    except Exception as e:
        logger.error(f"Get profile analysis suggestions error: {str(e)}")
        return jsonify({'error': 'Failed to get suggestions', 'details': str(e)}), 500

@profile_analysis_bp.route('/quick-analyze', methods=['POST'])
@auth_required
def quick_analyze_profile():
    """Quick analysis of existing profile links with caching"""
    try:
        if not profile_analysis_model:
            return jsonify({'error': 'Profile analysis service not available'}), 500
        
        user_id = request.user_id
        
        # Check cache first for recent quick analysis
        cache_key = cache.generate_cache_key(CacheKeys.PROFILE_ANALYSIS, user_id, 'quick')
        cached_quick_analysis = cache.get(cache_key)
        
        if cached_quick_analysis:
            logger.info(f"Quick analysis cache hit for user: {user_id}")
            return jsonify(cached_quick_analysis), 200
        
        # Get user profile
        user_data = user_model.get_user_by_id(user_id) if user_model else None
        if not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        profile = user_data.get('profile', {})
        github_url = profile.get('github_link')
        linkedin_url = profile.get('linkedin_link')
        
        if not github_url and not linkedin_url:
            return jsonify({
                'error': 'No profile links found',
                'message': 'Please add GitHub or LinkedIn URL to your profile first'
            }), 400
        
        # Perform quick analysis
        quick_results = []
        
        if github_url:
            # Check if we have recent GitHub analysis
            github_cache_key = cache.generate_cache_key(CacheKeys.GITHUB_PROFILE, user_id, 'quick')
            github_result = cache.get(github_cache_key)
            
            if not github_result:
                # Perform quick GitHub analysis
                try:
                    from services.profile_analyzer import ProfileAnalyzer
                    analyzer = ProfileAnalyzer(db, email_service)
                    github_result = analyzer.quick_analyze_github(github_url)
                    cache.set(github_cache_key, github_result, CacheTTL.GITHUB_PROFILE)
                except Exception as e:
                    github_result = {'error': str(e), 'platform': 'github'}
            
            quick_results.append({
                'platform': 'github',
                'url': github_url,
                'result': github_result
            })
        
        if linkedin_url:
            # Check if we have recent LinkedIn analysis
            linkedin_cache_key = cache.generate_cache_key(CacheKeys.LINKEDIN_PROFILE, user_id, 'quick')
            linkedin_result = cache.get(linkedin_cache_key)
            
            if not linkedin_result:
                # Perform quick LinkedIn analysis
                try:
                    from services.profile_analyzer import ProfileAnalyzer
                    analyzer = ProfileAnalyzer(db, email_service)
                    linkedin_result = analyzer.quick_analyze_linkedin(linkedin_url)
                    cache.set(linkedin_cache_key, linkedin_result, CacheTTL.LINKEDIN_PROFILE)
                except Exception as e:
                    linkedin_result = {'error': str(e), 'platform': 'linkedin'}
            
            quick_results.append({
                'platform': 'linkedin',
                'url': linkedin_url,
                'result': linkedin_result
            })
        
        response_data = {
            'message': 'Quick analysis completed',
            'analyses': quick_results,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Cache the quick analysis results
        cache.set(cache_key, response_data, CacheTTL.SHORT)
        logger.info(f"Quick analysis cached for user: {user_id}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Quick analyze error: {str(e)}")
        return jsonify({'error': 'Quick analysis failed', 'details': str(e)}), 500

@profile_analysis_bp.route('/reanalyze/<analysis_id>', methods=['POST'])
@auth_required
def reanalyze_profile(analysis_id):
    """Reanalyze profile with cache invalidation"""
    try:
        if not profile_analysis_model:
            return jsonify({'error': 'Profile analysis service not available'}), 500
        
        user_id = request.user_id
        
        # Get analysis data
        analysis = profile_analysis_model.get_analysis_by_id(analysis_id)
        if not analysis:
            return jsonify({'error': 'Analysis not found'}), 404
        
        # Verify ownership
        if analysis.get('user_id') != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Update status to processing
        profile_analysis_model.update_analysis_status(analysis_id, 'processing')
        
        # Invalidate all related caches
        cache_patterns = [
            f"{CacheKeys.PROFILE_ANALYSIS}:{user_id}*",
            f"{CacheKeys.PROFILE_ANALYSIS_RESULTS}:{user_id}*",
            f"{CacheKeys.PROFILE_ANALYSIS_SUGGESTIONS}:{user_id}*"
        ]
        
        analysis_type = analysis.get('analysis_type')
        if analysis_type == 'github':
            cache_patterns.append(f"{CacheKeys.GITHUB_PROFILE}:{user_id}*")
        elif analysis_type == 'linkedin':
            cache_patterns.append(f"{CacheKeys.LINKEDIN_PROFILE}:{user_id}*")
        
        for pattern in cache_patterns:
            cache.delete_pattern(pattern)
        
        # Start reanalysis
        try:
            from services.profile_analyzer import ProfileAnalyzer
            analyzer = ProfileAnalyzer(db, email_service)
            
            if analysis_type == 'github':
                analyzer.analyze_github_profile_async(analysis_id, analysis.get('github_url'), reanalyze=True)
            elif analysis_type == 'linkedin':
                analyzer.analyze_linkedin_profile_async(analysis_id, analysis.get('linkedin_url'), reanalyze=True)
            
            logger.info(f"Profile reanalysis started for analysis: {analysis_id}")
            
        except Exception as e:
            logger.error(f"Profile reanalysis failed to start: {e}")
            profile_analysis_model.update_analysis_status(analysis_id, 'failed', str(e))
        
        return jsonify({
            'message': 'Profile reanalysis started',
            'analysis_id': analysis_id,
            'status': 'processing'
        }), 200
        
    except Exception as e:
        logger.error(f"Profile reanalyze error: {str(e)}")
        return jsonify({'error': 'Profile reanalysis failed', 'details': str(e)}), 500

@profile_analysis_bp.route('/delete/<analysis_id>', methods=['DELETE'])
@auth_required
def delete_profile_analysis(analysis_id):
    """Delete profile analysis with cache cleanup"""
    try:
        if not profile_analysis_model:
            return jsonify({'error': 'Profile analysis service not available'}), 500
        
        user_id = request.user_id
        
        # Get analysis data
        analysis = profile_analysis_model.get_analysis_by_id(analysis_id)
        if not analysis:
            return jsonify({'error': 'Analysis not found'}), 404
        
        # Verify ownership
        if analysis.get('user_id') != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Delete from database
        delete_result = profile_analysis_model.delete_analysis(analysis_id)
        
        if delete_result.get('success'):
            # Clean up all related cache entries
            cache_patterns = [
                f"{CacheKeys.PROFILE_ANALYSIS}:{user_id}*",
                f"{CacheKeys.PROFILE_ANALYSIS_RESULTS}:{user_id}*",
                f"{CacheKeys.PROFILE_ANALYSIS_SUGGESTIONS}:{user_id}*"
            ]
            
            analysis_type = analysis.get('analysis_type')
            if analysis_type == 'github':
                cache_patterns.append(f"{CacheKeys.GITHUB_PROFILE}:{user_id}*")
            elif analysis_type == 'linkedin':
                cache_patterns.append(f"{CacheKeys.LINKEDIN_PROFILE}:{user_id}*")
            
            for pattern in cache_patterns:
                cache.delete_pattern(pattern)
            
            logger.info(f"Profile analysis deleted and cache cleaned for analysis: {analysis_id}")
            
            return jsonify({
                'message': 'Profile analysis deleted successfully',
                'analysis_id': analysis_id
            }), 200
        else:
            return jsonify({'error': 'Analysis deletion failed'}), 500
        
    except Exception as e:
        logger.error(f"Delete profile analysis error: {str(e)}")
        return jsonify({'error': 'Analysis deletion failed', 'details': str(e)}), 500

@profile_analysis_bp.route('/analyses', methods=['GET'])
@auth_required
def get_all_profile_analyses():
    """Get all profile analyses with caching"""
    try:
        if not profile_analysis_model:
            return jsonify({'error': 'Profile analysis service not available'}), 500
        
        user_id = request.user_id
        
        # Get query parameters
        status = request.args.get('status')  # completed, processing, failed
        analysis_type = request.args.get('type')  # linkedin, github
        limit = int(request.args.get('limit', 50))
        
        # Generate cache key
        cache_key = cache.generate_cache_key(
            CacheKeys.PROFILE_ANALYSIS, 
            user_id, 
            'all',
            f"status:{status or 'all'}",
            f"type:{analysis_type or 'all'}",
            f"limit:{limit}"
        )
        
        # Check cache first
        cached_analyses = cache.get(cache_key)
        if cached_analyses:
            logger.info(f"All profile analyses cache hit for user: {user_id}")
            return jsonify(cached_analyses), 200
        
        # Get from database
        try:
            analyses = profile_analysis_model.get_user_analyses(user_id, analysis_type)
        except Exception as e:
            logger.warning(f"Failed to get user analyses: {e}")
            analyses = []
        
        # Filter by status if specified
        if status:
            analyses = [a for a in analyses if a.get('status') == status]
        
        # Apply limit
        if limit and len(analyses) > limit:
            analyses = analyses[:limit]
        
        # Get statistics
        try:
            stats = profile_analysis_model.get_user_analysis_statistics(user_id)
        except Exception as e:
            logger.warning(f"Failed to get analysis statistics: {e}")
            stats = {}
        
        response_data = {
            'analyses': analyses,
            'statistics': stats,
            'filters': {
                'status': status,
                'type': analysis_type,
                'limit': limit
            },
            'total_count': len(analyses)
        }
        
        # Cache the results
        cache.set(cache_key, response_data, CacheTTL.PROFILE_ANALYSIS)
        logger.info(f"All profile analyses cached for user: {user_id}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Get all profile analyses error: {str(e)}")
        return jsonify({'error': 'Failed to get profile analyses', 'details': str(e)}), 500

# Cache management endpoints
@profile_analysis_bp.route('/cache/clear', methods=['POST'])
@auth_required
def clear_profile_analysis_cache():
    """Clear all profile analysis cache entries for the authenticated user"""
    try:
        user_id = request.user_id
        
        # Clear all profile analysis related cache entries
        cache_patterns = [
            f"{CacheKeys.PROFILE_ANALYSIS}:{user_id}*",
            f"{CacheKeys.PROFILE_ANALYSIS_RESULTS}:{user_id}*",
            f"{CacheKeys.PROFILE_ANALYSIS_SUGGESTIONS}:{user_id}*",
            f"{CacheKeys.GITHUB_PROFILE}:{user_id}*",
            f"{CacheKeys.LINKEDIN_PROFILE}:{user_id}*"
        ]
        
        total_deleted = 0
        for pattern in cache_patterns:
            deleted = cache.delete_pattern(pattern)
            total_deleted += deleted
        
        logger.info(f"Cleared {total_deleted} profile analysis cache entries for user: {user_id}")
        
        return jsonify({
            'message': 'Profile analysis cache cleared successfully',
            'entries_deleted': total_deleted
        }), 200
        
    except Exception as e:
        logger.error(f"Clear profile analysis cache error: {str(e)}")
        return jsonify({'error': 'Failed to clear cache', 'details': str(e)}), 500

@profile_analysis_bp.route('/cache/status', methods=['GET'])
@auth_required
def get_profile_analysis_cache_status():
    """Get cache status for profile analysis data"""
    try:
        user_id = request.user_id
        
        # Get user's profile analyses to check cache status
        try:
            analyses = profile_analysis_model.get_user_analysis_summary(user_id) if profile_analysis_model else []
        except Exception as e:
            logger.warning(f"Failed to get user analyses for cache status: {e}")
            analyses = []
        
        cache_status = {}
        for analysis in analyses:
            analysis_id = analysis.get('id')
            if analysis_id:
                cache_keys_to_check = [
                    (CacheKeys.PROFILE_ANALYSIS_RESULTS, 'results'),
                    (CacheKeys.PROFILE_ANALYSIS_SUGGESTIONS, 'suggestions')
                ]
                
                analysis_cache_status = {}
                for cache_key_prefix, name in cache_keys_to_check:
                    cache_key = cache.generate_cache_key(cache_key_prefix, user_id, analysis_id)
                    exists = cache.exists(cache_key)
                    ttl = cache.get_ttl(cache_key) if exists else -1
                    
                    analysis_cache_status[name] = {
                        'cached': exists,
                        'ttl_seconds': ttl,
                        'expires_in': f"{ttl // 60}m {ttl % 60}s" if ttl > 0 else 'Not cached'
                    }
                
                cache_status[analysis_id] = {
                    'type': analysis.get('analysis_type', 'Unknown'),
                    'status': analysis.get('status', 'Unknown'),
                    'cache_status': analysis_cache_status
                }
        
        # Check quick analysis cache
        quick_cache_key = cache.generate_cache_key(CacheKeys.PROFILE_ANALYSIS, user_id, 'quick')
        quick_exists = cache.exists(quick_cache_key)
        quick_ttl = cache.get_ttl(quick_cache_key) if quick_exists else -1
        
        # Check platform-specific caches
        github_cache_key = cache.generate_cache_key(CacheKeys.GITHUB_PROFILE, user_id, 'quick')
        github_exists = cache.exists(github_cache_key)
        github_ttl = cache.get_ttl(github_cache_key) if github_exists else -1
        
        linkedin_cache_key = cache.generate_cache_key(CacheKeys.LINKEDIN_PROFILE, user_id, 'quick')
        linkedin_exists = cache.exists(linkedin_cache_key)
        linkedin_ttl = cache.get_ttl(linkedin_cache_key) if linkedin_exists else -1
        
        return jsonify({
            'analysis_cache_status': cache_status,
            'quick_analysis_cache': {
                'cached': quick_exists,
                'ttl_seconds': quick_ttl,
                'expires_in': f"{quick_ttl // 60}m {quick_ttl % 60}s" if quick_ttl > 0 else 'Not cached'
            },
            'platform_caches': {
                'github': {
                    'cached': github_exists,
                    'ttl_seconds': github_ttl,
                    'expires_in': f"{github_ttl // 60}m {github_ttl % 60}s" if github_ttl > 0 else 'Not cached'
                },
                'linkedin': {
                    'cached': linkedin_exists,
                    'ttl_seconds': linkedin_ttl,
                    'expires_in': f"{linkedin_ttl // 60}m {linkedin_ttl % 60}s" if linkedin_ttl > 0 else 'Not cached'
                }
            },
            'total_analyses': len(analyses),
            'user_id': user_id
        }), 200
        
    except Exception as e:
        logger.error(f"Get profile analysis cache status error: {str(e)}")
        return jsonify({'error': 'Failed to get cache status', 'details': str(e)}), 500

@profile_analysis_bp.route('/bulk-cache-refresh', methods=['POST'])
@auth_required
def bulk_cache_refresh():
    """Refresh cache for all user's profile analyses"""
    try:
        user_id = request.user_id
        
        # Get all user's completed analyses
        try:
            analyses = profile_analysis_model.get_user_analyses(user_id) if profile_analysis_model else []
        except Exception as e:
            logger.warning(f"Failed to get user analyses for bulk refresh: {e}")
            analyses = []
        
        completed_analyses = [a for a in analyses if a.get('status') == 'completed']
        
        refreshed_count = 0
        errors = []
        
        for analysis in completed_analyses:
            analysis_id = analysis.get('id')
            if not analysis_id:
                continue
                
            try:
                # Refresh each cache entry
                cache_keys_to_refresh = [
                    CacheKeys.PROFILE_ANALYSIS_RESULTS,
                    CacheKeys.PROFILE_ANALYSIS_SUGGESTIONS
                ]
                
                for cache_key_prefix in cache_keys_to_refresh:
                    cache_key = cache.generate_cache_key(cache_key_prefix, user_id, analysis_id)
                    cache.delete(cache_key)
                
                refreshed_count += 1
                
            except Exception as e:
                errors.append(f"Analysis {analysis_id}: {str(e)}")
        
        # Also refresh quick analysis and platform caches
        quick_cache_keys = [
            cache.generate_cache_key(CacheKeys.PROFILE_ANALYSIS, user_id, 'quick'),
            cache.generate_cache_key(CacheKeys.GITHUB_PROFILE, user_id, 'quick'),
            cache.generate_cache_key(CacheKeys.LINKEDIN_PROFILE, user_id, 'quick')
        ]
        
        for cache_key in quick_cache_keys:
            cache.delete(cache_key)
        
        logger.info(f"Bulk cache refresh completed for user: {user_id}, refreshed: {refreshed_count}")
        
        return jsonify({
            'message': 'Bulk cache refresh completed',
            'refreshed_analyses': refreshed_count,
            'total_analyses': len(completed_analyses),
            'errors': errors
        }), 200
        
    except Exception as e:
        logger.error(f"Bulk cache refresh error: {str(e)}")
        return jsonify({'error': 'Bulk cache refresh failed', 'details': str(e)}), 500