# routes/portfolio_analysis_routes.py - Fixed with Redis Caching
from flask import Blueprint, request, jsonify
from functools import wraps
import logging
from datetime import datetime

# Import cache service
from services.redis_cache_service import cache, CacheKeys, CacheTTL, cache_result, invalidate_cache_pattern

logger = logging.getLogger(__name__)

portfolio_analysis_bp = Blueprint('portfolio_analysis', __name__)

# Global variables (will be set when blueprint is registered)
portfolio_analysis_model = None
user_model = None
db = None
email_service = None

def init_portfolio_analysis_routes(portfolio_analysis_model_instance, user_model_instance, db_instance, email_service_instance):
    """Initialize portfolio analysis routes with model instances"""
    global portfolio_analysis_model, user_model, db, email_service
    portfolio_analysis_model = portfolio_analysis_model_instance
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

@portfolio_analysis_bp.route('/analyze', methods=['POST'])
@auth_required
def analyze_portfolio():
    """Analyze portfolio website with cache invalidation"""
    try:
        if not portfolio_analysis_model:
            return jsonify({'error': 'Portfolio analysis service not available'}), 500
        
        user_id = request.user_id
        data = request.get_json()
        
        if not data or 'portfolio_url' not in data:
            return jsonify({'error': 'Portfolio URL is required'}), 400
        
        portfolio_url = data['portfolio_url'].strip()
        if not portfolio_url:
            return jsonify({'error': 'Portfolio URL cannot be empty'}), 400
        
        # Validate URL format
        if not portfolio_url.startswith(('http://', 'https://')):
            portfolio_url = 'https://' + portfolio_url
        
        # Get user profile for context
        user_data = user_model.get_user_by_id(user_id) if user_model else None
        
        # Create analysis record
        analysis_data = {
            'user_id': user_id,
            'analysis_type': 'portfolio',
            'portfolio_url': portfolio_url,
            'user_profile_context': user_data.get('profile', {}) if user_data else {}
        }
        
        analysis_id = portfolio_analysis_model.create_analysis_record(analysis_data)
        
        # Invalidate portfolio analysis caches
        cache_patterns = [
            f"{CacheKeys.PORTFOLIO_ANALYSIS}:{user_id}*",
            f"{CacheKeys.PORTFOLIO_ANALYSIS_RESULTS}:{user_id}*"
        ]
        
        for pattern in cache_patterns:
            cache.delete_pattern(pattern)
        
        # Start analysis asynchronously
        try:
            from services.portfolio_analyzer import PortfolioAnalyzer
            analyzer = PortfolioAnalyzer(db, email_service)
            analyzer.analyze_portfolio_async(analysis_id, portfolio_url)
            
            logger.info(f"Portfolio analysis started for user: {user_id}, analysis: {analysis_id}")
            
        except Exception as e:
            logger.error(f"Portfolio analysis failed to start: {e}")
            portfolio_analysis_model.update_analysis_status(analysis_id, 'failed', str(e))
        
        return jsonify({
            'message': 'Portfolio analysis started',
            'analysis_id': analysis_id,
            'status': 'processing'
        }), 201
        
    except Exception as e:
        logger.error(f"Portfolio analysis error: {str(e)}")
        return jsonify({'error': 'Portfolio analysis failed', 'details': str(e)}), 500

@portfolio_analysis_bp.route('/results', methods=['GET'])
@auth_required
def get_portfolio_analysis_results():
    """Get all portfolio analysis results with caching"""
    try:
        if not portfolio_analysis_model:
            return jsonify({'error': 'Portfolio analysis service not available'}), 500
        
        user_id = request.user_id
        
        # Get query parameters
        include_details = request.args.get('details', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 20))
        status = request.args.get('status')  # completed, processing, failed
        
        # Generate cache key
        cache_key = cache.generate_cache_key(
            CacheKeys.PORTFOLIO_ANALYSIS_RESULTS, 
            user_id, 
            f"details:{include_details}",
            f"limit:{limit}",
            f"status:{status or 'all'}"
        )
        
        # Check cache first
        cached_results = cache.get(cache_key)
        if cached_results:
            logger.info(f"Portfolio analysis results cache hit for user: {user_id}")
            return jsonify(cached_results), 200
        
        # Get from database
        try:
            if include_details:
                analyses = portfolio_analysis_model.get_user_analyses(user_id, 'portfolio')
            else:
                analyses = portfolio_analysis_model.get_user_analysis_summary(user_id)
        except Exception as e:
            logger.warning(f"Failed to get portfolio analyses: {e}")
            analyses = []
        
        # Filter by status if specified
        if status:
            analyses = [a for a in analyses if a.get('status') == status]
        
        # Apply limit
        if limit and len(analyses) > limit:
            analyses = analyses[:limit]
        
        # Get statistics
        try:
            stats = portfolio_analysis_model.get_user_analysis_statistics(user_id)
        except Exception as e:
            logger.warning(f"Failed to get portfolio analysis stats: {e}")
            stats = {}
        
        response_data = {
            'analyses': analyses,
            'statistics': stats,
            'meta': {
                'total_count': len(analyses),
                'includes_details': include_details,
                'limit_applied': limit,
                'status_filter': status
            }
        }
        
        # Cache the results
        cache.set(cache_key, response_data, CacheTTL.PORTFOLIO_ANALYSIS)
        logger.info(f"Portfolio analysis results cached for user: {user_id}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Get portfolio analysis results error: {str(e)}")
        return jsonify({'error': 'Failed to get portfolio analysis results', 'details': str(e)}), 500

@portfolio_analysis_bp.route('/results/<analysis_id>', methods=['GET'])
@auth_required
def get_single_portfolio_analysis_result(analysis_id):
    """Get single portfolio analysis result with caching"""
    try:
        if not portfolio_analysis_model:
            return jsonify({'error': 'Portfolio analysis service not available'}), 500
        
        user_id = request.user_id
        
        # Check cache first
        cache_key = cache.generate_cache_key(CacheKeys.PORTFOLIO_ANALYSIS_RESULTS, user_id, analysis_id)
        cached_result = cache.get(cache_key)
        
        if cached_result:
            logger.info(f"Single portfolio analysis result cache hit for analysis: {analysis_id}")
            return jsonify(cached_result), 200
        
        # Get from database
        analysis = portfolio_analysis_model.get_analysis_by_id(analysis_id)
        if not analysis:
            return jsonify({'error': 'Analysis not found'}), 404
        
        # Verify ownership
        if analysis.get('user_id') != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Cache the result
        cache.set(cache_key, analysis, CacheTTL.PORTFOLIO_ANALYSIS)
        logger.info(f"Single portfolio analysis result cached for analysis: {analysis_id}")
        
        return jsonify(analysis), 200
        
    except Exception as e:
        logger.error(f"Get single portfolio analysis result error: {str(e)}")
        return jsonify({'error': 'Failed to get analysis result', 'details': str(e)}), 500

@portfolio_analysis_bp.route('/suggestions/<analysis_id>', methods=['GET'])
@auth_required
def get_portfolio_analysis_suggestions(analysis_id):
    """Get portfolio analysis suggestions with caching"""
    try:
        if not portfolio_analysis_model:
            return jsonify({'error': 'Portfolio analysis service not available'}), 500
        
        user_id = request.user_id
        
        # Check cache first
        cache_key = cache.generate_cache_key(CacheKeys.PORTFOLIO_ANALYSIS_SUGGESTIONS, user_id, analysis_id)
        cached_suggestions = cache.get(cache_key)
        
        if cached_suggestions:
            logger.info(f"Portfolio analysis suggestions cache hit for analysis: {analysis_id}")
            return jsonify(cached_suggestions), 200
        
        # Get from database
        analysis = portfolio_analysis_model.get_analysis_by_id(analysis_id)
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
            suggestions = portfolio_analysis_model.get_analysis_suggestions(analysis_id)
        except Exception as e:
            logger.warning(f"Failed to get portfolio suggestions: {e}")
            suggestions = None
        
        if not suggestions:
            return jsonify({'error': 'Suggestions not found'}), 404
        
        # Cache the suggestions
        cache.set(cache_key, suggestions, CacheTTL.PORTFOLIO_ANALYSIS)
        logger.info(f"Portfolio analysis suggestions cached for analysis: {analysis_id}")
        
        return jsonify(suggestions), 200
        
    except Exception as e:
        logger.error(f"Get portfolio analysis suggestions error: {str(e)}")
        return jsonify({'error': 'Failed to get suggestions', 'details': str(e)}), 500

@portfolio_analysis_bp.route('/extracted-data/<analysis_id>', methods=['GET'])
@auth_required
def get_extracted_data(analysis_id):
    """Get extracted portfolio data with caching"""
    try:
        if not portfolio_analysis_model:
            return jsonify({'error': 'Portfolio analysis service not available'}), 500
        
        user_id = request.user_id
        
        # Check cache first
        cache_key = cache.generate_cache_key(CacheKeys.PORTFOLIO_ANALYSIS, user_id, analysis_id, 'extracted')
        cached_data = cache.get(cache_key)
        
        if cached_data:
            logger.info(f"Extracted data cache hit for analysis: {analysis_id}")
            return jsonify(cached_data), 200
        
        # Get from database
        analysis = portfolio_analysis_model.get_analysis_by_id(analysis_id)
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
        
        # Get extracted data
        try:
            extracted_data = portfolio_analysis_model.get_extracted_data(analysis_id)
        except Exception as e:
            logger.warning(f"Failed to get extracted data: {e}")
            extracted_data = None
        
        if not extracted_data:
            return jsonify({'error': 'Extracted data not found'}), 404
        
        # Cache the extracted data
        cache.set(cache_key, extracted_data, CacheTTL.PORTFOLIO_ANALYSIS)
        logger.info(f"Extracted data cached for analysis: {analysis_id}")
        
        return jsonify(extracted_data), 200
        
    except Exception as e:
        logger.error(f"Get extracted data error: {str(e)}")
        return jsonify({'error': 'Failed to get extracted data', 'details': str(e)}), 500

@portfolio_analysis_bp.route('/analyses', methods=['GET'])
@auth_required
def get_all_portfolio_analyses():
    """Get all portfolio analyses with caching"""
    try:
        if not portfolio_analysis_model:
            return jsonify({'error': 'Portfolio analysis service not available'}), 500
        
        user_id = request.user_id
        
        # Get query parameters
        status = request.args.get('status')  # completed, processing, failed
        limit = int(request.args.get('limit', 50))
        
        # Generate cache key
        cache_key = cache.generate_cache_key(
            CacheKeys.PORTFOLIO_ANALYSIS, 
            user_id, 
            'all',
            f"status:{status or 'all'}",
            f"limit:{limit}"
        )
        
        # Check cache first
        cached_analyses = cache.get(cache_key)
        if cached_analyses:
            logger.info(f"All portfolio analyses cache hit for user: {user_id}")
            return jsonify(cached_analyses), 200
        
        # Get from database
        try:
            analyses = portfolio_analysis_model.get_user_analyses(user_id, 'portfolio')
        except Exception as e:
            logger.warning(f"Failed to get user portfolio analyses: {e}")
            analyses = []
        
        # Filter by status if specified
        if status:
            analyses = [a for a in analyses if a.get('status') == status]
        
        # Apply limit
        if limit and len(analyses) > limit:
            analyses = analyses[:limit]
        
        # Get statistics
        try:
            stats = portfolio_analysis_model.get_user_analysis_statistics(user_id)
        except Exception as e:
            logger.warning(f"Failed to get portfolio analysis stats: {e}")
            stats = {}
        
        response_data = {
            'analyses': analyses,
            'statistics': stats,
            'filters': {
                'status': status,
                'limit': limit
            },
            'total_count': len(analyses)
        }
        
        # Cache the results
        cache.set(cache_key, response_data, CacheTTL.PORTFOLIO_ANALYSIS)
        logger.info(f"All portfolio analyses cached for user: {user_id}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Get all portfolio analyses error: {str(e)}")
        return jsonify({'error': 'Failed to get portfolio analyses', 'details': str(e)}), 500

@portfolio_analysis_bp.route('/user/portfolios', methods=['GET'])
@auth_required
def get_user_portfolios():
    """Get user's portfolio URLs with caching"""
    try:
        if not portfolio_analysis_model:
            return jsonify({'error': 'Portfolio analysis service not available'}), 500
        
        user_id = request.user_id
        
        # Check cache first
        cache_key = cache.generate_cache_key(CacheKeys.PORTFOLIO_ANALYSIS, user_id, 'portfolios')
        cached_portfolios = cache.get(cache_key)
        
        if cached_portfolios:
            logger.info(f"User portfolios cache hit for user: {user_id}")
            return jsonify(cached_portfolios), 200
        
        # Get from database
        try:
            analyses = portfolio_analysis_model.get_user_analyses(user_id, 'portfolio')
        except Exception as e:
            logger.warning(f"Failed to get user portfolio analyses: {e}")
            analyses = []
        
        # Extract unique portfolio URLs
        portfolios = {}
        for analysis in analyses:
            portfolio_url = analysis.get('portfolio_url')
            if portfolio_url:
                if portfolio_url not in portfolios:
                    portfolios[portfolio_url] = {
                        'url': portfolio_url,
                        'analyses': [],
                        'latest_analysis': None,
                        'total_analyses': 0
                    }
                
                portfolios[portfolio_url]['analyses'].append({
                    'id': analysis.get('id'),
                    'status': analysis.get('status'),
                    'created_at': analysis.get('created_at'),
                    'score': analysis.get('score')
                })
                
                portfolios[portfolio_url]['total_analyses'] += 1
                
                # Set latest analysis
                if not portfolios[portfolio_url]['latest_analysis'] or \
                   analysis.get('created_at', '') > portfolios[portfolio_url]['latest_analysis'].get('created_at', ''):
                    portfolios[portfolio_url]['latest_analysis'] = analysis
        
        # Sort analyses within each portfolio
        for portfolio_data in portfolios.values():
            portfolio_data['analyses'].sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # Convert to list and sort by latest analysis
        portfolios_list = list(portfolios.values())
        portfolios_list.sort(key=lambda x: x.get('latest_analysis', {}).get('created_at', ''), reverse=True)
        
        response_data = {
            'portfolios': portfolios_list,
            'total_unique_portfolios': len(portfolios_list),
            'total_analyses': len(analyses)
        }
        
        # Cache the portfolios
        cache.set(cache_key, response_data, CacheTTL.PORTFOLIO_ANALYSIS)
        logger.info(f"User portfolios cached for user: {user_id}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Get user portfolios error: {str(e)}")
        return jsonify({'error': 'Failed to get user portfolios', 'details': str(e)}), 500

@portfolio_analysis_bp.route('/reanalyze/<analysis_id>', methods=['POST'])
@auth_required
def reanalyze_portfolio(analysis_id):
    """Reanalyze portfolio with cache invalidation"""
    try:
        if not portfolio_analysis_model:
            return jsonify({'error': 'Portfolio analysis service not available'}), 500
        
        user_id = request.user_id
        
        # Get analysis data
        analysis = portfolio_analysis_model.get_analysis_by_id(analysis_id)
        if not analysis:
            return jsonify({'error': 'Analysis not found'}), 404
        
        # Verify ownership
        if analysis.get('user_id') != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Update status to processing
        portfolio_analysis_model.update_analysis_status(analysis_id, 'processing')
        
        # Invalidate all related caches
        cache_patterns = [
            f"{CacheKeys.PORTFOLIO_ANALYSIS}:{user_id}*",
            f"{CacheKeys.PORTFOLIO_ANALYSIS_RESULTS}:{user_id}*",
            f"{CacheKeys.PORTFOLIO_ANALYSIS_SUGGESTIONS}:{user_id}*"
        ]
        
        for pattern in cache_patterns:
            cache.delete_pattern(pattern)
        
        # Start reanalysis
        try:
            from services.portfolio_analyzer import PortfolioAnalyzer
            analyzer = PortfolioAnalyzer(db, email_service)
            analyzer.analyze_portfolio_async(analysis_id, analysis.get('portfolio_url'), reanalyze=True)
            
            logger.info(f"Portfolio reanalysis started for analysis: {analysis_id}")
            
        except Exception as e:
            logger.error(f"Portfolio reanalysis failed to start: {e}")
            portfolio_analysis_model.update_analysis_status(analysis_id, 'failed', str(e))
        
        return jsonify({
            'message': 'Portfolio reanalysis started',
            'analysis_id': analysis_id,
            'status': 'processing'
        }), 200
        
    except Exception as e:
        logger.error(f"Portfolio reanalyze error: {str(e)}")
        return jsonify({'error': 'Portfolio reanalysis failed', 'details': str(e)}), 500

@portfolio_analysis_bp.route('/delete/<analysis_id>', methods=['DELETE'])
@auth_required
def delete_portfolio_analysis(analysis_id):
    """Delete portfolio analysis with cache cleanup"""
    try:
        if not portfolio_analysis_model:
            return jsonify({'error': 'Portfolio analysis service not available'}), 500
        
        user_id = request.user_id
        
        # Get analysis data
        analysis = portfolio_analysis_model.get_analysis_by_id(analysis_id)
        if not analysis:
            return jsonify({'error': 'Analysis not found'}), 404
        
        # Verify ownership
        if analysis.get('user_id') != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Delete from database
        delete_result = portfolio_analysis_model.delete_analysis(analysis_id)
        
        if delete_result.get('success'):
            # Clean up all related cache entries
            cache_patterns = [
                f"{CacheKeys.PORTFOLIO_ANALYSIS}:{user_id}*",
                f"{CacheKeys.PORTFOLIO_ANALYSIS_RESULTS}:{user_id}*",
                f"{CacheKeys.PORTFOLIO_ANALYSIS_SUGGESTIONS}:{user_id}*"
            ]
            
            for pattern in cache_patterns:
                cache.delete_pattern(pattern)
            
            logger.info(f"Portfolio analysis deleted and cache cleaned for analysis: {analysis_id}")
            
            return jsonify({
                'message': 'Portfolio analysis deleted successfully',
                'analysis_id': analysis_id
            }), 200
        else:
            return jsonify({'error': 'Analysis deletion failed'}), 500
        
    except Exception as e:
        logger.error(f"Delete portfolio analysis error: {str(e)}")
        return jsonify({'error': 'Analysis deletion failed', 'details': str(e)}), 500

# Cache management endpoints
@portfolio_analysis_bp.route('/cache/clear', methods=['POST'])
@auth_required
def clear_portfolio_analysis_cache():
    """Clear all portfolio analysis cache entries for the authenticated user"""
    try:
        user_id = request.user_id
        
        # Clear all portfolio analysis related cache entries
        cache_patterns = [
            f"{CacheKeys.PORTFOLIO_ANALYSIS}:{user_id}*",
            f"{CacheKeys.PORTFOLIO_ANALYSIS_RESULTS}:{user_id}*",
            f"{CacheKeys.PORTFOLIO_ANALYSIS_SUGGESTIONS}:{user_id}*"
        ]
        
        total_deleted = 0
        for pattern in cache_patterns:
            deleted = cache.delete_pattern(pattern)
            total_deleted += deleted
        
        logger.info(f"Cleared {total_deleted} portfolio analysis cache entries for user: {user_id}")
        
        return jsonify({
            'message': 'Portfolio analysis cache cleared successfully',
            'entries_deleted': total_deleted
        }), 200
        
    except Exception as e:
        logger.error(f"Clear portfolio analysis cache error: {str(e)}")
        return jsonify({'error': 'Failed to clear cache', 'details': str(e)}), 500

@portfolio_analysis_bp.route('/cache/status', methods=['GET'])
@auth_required
def get_portfolio_analysis_cache_status():
    """Get cache status for portfolio analysis data"""
    try:
        user_id = request.user_id
        
        # Get user's portfolio analyses to check cache status
        try:
            analyses = portfolio_analysis_model.get_user_analysis_summary(user_id) if portfolio_analysis_model else []
        except Exception as e:
            logger.warning(f"Failed to get user portfolio analyses for cache status: {e}")
            analyses = []
        
        cache_status = {}
        for analysis in analyses:
            analysis_id = analysis.get('id')
            if analysis_id:
                cache_keys_to_check = [
                    (CacheKeys.PORTFOLIO_ANALYSIS_RESULTS, 'results'),
                    (CacheKeys.PORTFOLIO_ANALYSIS_SUGGESTIONS, 'suggestions'),
                    (CacheKeys.PORTFOLIO_ANALYSIS, 'extracted_data')
                ]
                
                analysis_cache_status = {}
                for cache_key_prefix, name in cache_keys_to_check:
                    if name == 'extracted_data':
                        cache_key = cache.generate_cache_key(cache_key_prefix, user_id, analysis_id, 'extracted')
                    else:
                        cache_key = cache.generate_cache_key(cache_key_prefix, user_id, analysis_id)
                    
                    exists = cache.exists(cache_key)
                    ttl = cache.get_ttl(cache_key) if exists else -1
                    
                    analysis_cache_status[name] = {
                        'cached': exists,
                        'ttl_seconds': ttl,
                        'expires_in': f"{ttl // 60}m {ttl % 60}s" if ttl > 0 else 'Not cached'
                    }
                
                cache_status[analysis_id] = {
                    'portfolio_url': analysis.get('portfolio_url', 'Unknown'),
                    'status': analysis.get('status', 'Unknown'),
                    'cache_status': analysis_cache_status
                }
        
        # Check portfolios list cache
        portfolios_cache_key = cache.generate_cache_key(CacheKeys.PORTFOLIO_ANALYSIS, user_id, 'portfolios')
        portfolios_exists = cache.exists(portfolios_cache_key)
        portfolios_ttl = cache.get_ttl(portfolios_cache_key) if portfolios_exists else -1
        
        return jsonify({
            'analysis_cache_status': cache_status,
            'portfolios_list_cache': {
                'cached': portfolios_exists,
                'ttl_seconds': portfolios_ttl,
                'expires_in': f"{portfolios_ttl // 60}m {portfolios_ttl % 60}s" if portfolios_ttl > 0 else 'Not cached'
            },
            'total_analyses': len(analyses),
            'user_id': user_id
        }), 200
        
    except Exception as e:
        logger.error(f"Get portfolio analysis cache status error: {str(e)}")
        return jsonify({'error': 'Failed to get cache status', 'details': str(e)}), 500

@portfolio_analysis_bp.route('/bulk-cache-refresh', methods=['POST'])
@auth_required
def bulk_cache_refresh():
    """Refresh cache for all user's portfolio analyses"""
    try:
        user_id = request.user_id
        
        # Get all user's completed analyses
        try:
            analyses = portfolio_analysis_model.get_user_analyses(user_id, 'portfolio') if portfolio_analysis_model else []
        except Exception as e:
            logger.warning(f"Failed to get user portfolio analyses for bulk refresh: {e}")
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
                    cache.generate_cache_key(CacheKeys.PORTFOLIO_ANALYSIS_RESULTS, user_id, analysis_id),
                    cache.generate_cache_key(CacheKeys.PORTFOLIO_ANALYSIS_SUGGESTIONS, user_id, analysis_id),
                    cache.generate_cache_key(CacheKeys.PORTFOLIO_ANALYSIS, user_id, analysis_id, 'extracted')
                ]
                
                for cache_key in cache_keys_to_refresh:
                    cache.delete(cache_key)
                
                refreshed_count += 1
                
            except Exception as e:
                errors.append(f"Analysis {analysis_id}: {str(e)}")
        
        # Also refresh portfolios list cache
        portfolios_cache_key = cache.generate_cache_key(CacheKeys.PORTFOLIO_ANALYSIS, user_id, 'portfolios')
        cache.delete(portfolios_cache_key)
        
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