# routes/community_routes.py - Updated with Redis Caching
from flask import Blueprint, request, jsonify
from functools import wraps
import logging
from datetime import datetime, timedelta

# Import cache service
from services.redis_cache_service import cache, CacheKeys, CacheTTL, cache_result, invalidate_cache_pattern

logger = logging.getLogger(__name__)

community_bp = Blueprint('community', __name__)

# Global variables (will be set when blueprint is registered)
community_model = None
user_model = None
db = None

def init_community_routes(community_model_instance, user_model_instance, db_instance):
    """Initialize community routes with model instances"""
    global community_model, user_model, db
    community_model = community_model_instance
    user_model = user_model_instance
    db = db_instance

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

@community_bp.route('/posts', methods=['POST'])
@auth_required
@invalidate_cache_pattern(f"{CacheKeys.COMMUNITY_POSTS}:*")
def create_post():
    """Create a new community post with cache invalidation"""
    try:
        if not community_model:
            return jsonify({'error': 'Community service not available'}), 500
        
        user_id = request.user_id
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['title', 'content']
        for field in required_fields:
            if field not in data or not data[field].strip():
                return jsonify({'error': f'{field} is required'}), 400
        
        # Get user profile for author information
        user_data = user_model.get_user_by_id(user_id) if user_model else None
        if not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        # Prepare post data
        post_data = {
            'title': data['title'].strip(),
            'content': data['content'].strip(),
            'author_id': user_id,
            'author_name': user_data.get('profile', {}).get('name', 'Anonymous'),
            'author_profession': user_data.get('profile', {}).get('profession', ''),
            'tags': data.get('tags', []),
            'category': data.get('category', 'general'),
            'created_at': datetime.utcnow()
        }
        
        # Create post
        post_id = community_model.create_post(post_data)
        
        # Invalidate community posts cache
        cache_patterns = [
            f"{CacheKeys.COMMUNITY_POSTS}:*",
            f"{CacheKeys.COMMUNITY_STATS}:*"
        ]
        
        for pattern in cache_patterns:
            cache.delete_pattern(pattern)
        
        logger.info(f"Post created and cache invalidated for user: {user_id}, post: {post_id}")
        
        return jsonify({
            'message': 'Post created successfully',
            'post_id': post_id
        }), 201
        
    except Exception as e:
        logger.error(f"Create post error: {str(e)}")
        return jsonify({'error': 'Post creation failed', 'details': str(e)}), 500

@community_bp.route('/posts', methods=['GET'])
@auth_required
def get_community_posts():
    """Get community posts with caching"""
    try:
        if not community_model:
            return jsonify({'error': 'Community service not available'}), 500
        
        # Get query parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        category = request.args.get('category')
        sort_by = request.args.get('sort_by', 'latest')  # latest, popular, oldest
        
        # Generate cache key
        cache_key = cache.generate_cache_key(
            CacheKeys.COMMUNITY_POSTS,
            f"page:{page}",
            f"limit:{limit}",
            f"category:{category or 'all'}",
            f"sort:{sort_by}"
        )
        
        # Check cache first
        cached_posts = cache.get(cache_key)
        if cached_posts:
            logger.info(f"Community posts cache hit for page: {page}")
            return jsonify(cached_posts), 200
        
        # Get from database
        posts = community_model.get_posts(
            page=page,
            limit=limit,
            category=category,
            sort_by=sort_by
        )
        
        # Get total count for pagination
        total_posts = community_model.get_total_posts_count(category)
        
        response_data = {
            'posts': posts,
            'pagination': {
                'current_page': page,
                'per_page': limit,
                'total_posts': total_posts,
                'total_pages': (total_posts + limit - 1) // limit,
                'has_next': page * limit < total_posts,
                'has_prev': page > 1
            },
            'filters': {
                'category': category,
                'sort_by': sort_by
            }
        }
        
        # Cache the results (shorter TTL for dynamic content)
        cache.set(cache_key, response_data, CacheTTL.COMMUNITY_POSTS)
        logger.info(f"Community posts cached for page: {page}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Get community posts error: {str(e)}")
        return jsonify({'error': 'Failed to get posts', 'details': str(e)}), 500

@community_bp.route('/posts/<post_id>', methods=['GET'])
@auth_required
def get_single_post(post_id):
    """Get single community post with caching"""
    try:
        if not community_model:
            return jsonify({'error': 'Community service not available'}), 500
        
        # Check cache first
        cache_key = cache.generate_cache_key(CacheKeys.COMMUNITY_POST, post_id)
        cached_post = cache.get(cache_key)
        
        if cached_post:
            logger.info(f"Single post cache hit for post: {post_id}")
            return jsonify(cached_post), 200
        
        # Get from database
        post = community_model.get_post_by_id(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        # Get replies
        replies = community_model.get_post_replies(post_id)
        
        # Combine post with replies
        post_data = {
            'post': post,
            'replies': replies,
            'reply_count': len(replies)
        }
        
        # Cache the post data
        cache.set(cache_key, post_data, CacheTTL.COMMUNITY_POST)
        logger.info(f"Single post cached for post: {post_id}")
        
        return jsonify(post_data), 200
        
    except Exception as e:
        logger.error(f"Get single post error: {str(e)}")
        return jsonify({'error': 'Failed to get post', 'details': str(e)}), 500

@community_bp.route('/posts/<post_id>/like', methods=['POST'])
@auth_required
@invalidate_cache_pattern(f"{CacheKeys.COMMUNITY_POST}:*")
def like_post(post_id):
    """Like/unlike a post with cache invalidation"""
    try:
        if not community_model:
            return jsonify({'error': 'Community service not available'}), 500
        
        user_id = request.user_id
        
        # Check if post exists
        post = community_model.get_post_by_id(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        # Toggle like
        result = community_model.toggle_post_like(post_id, user_id)
        
        # Invalidate post cache
        post_cache_key = cache.generate_cache_key(CacheKeys.COMMUNITY_POST, post_id)
        cache.delete(post_cache_key)
        
        # Also invalidate posts list cache
        cache.delete_pattern(f"{CacheKeys.COMMUNITY_POSTS}:*")
        
        logger.info(f"Post like toggled and cache invalidated for post: {post_id}, user: {user_id}")
        
        return jsonify({
            'message': 'Like toggled successfully',
            'liked': result.get('liked', False),
            'total_likes': result.get('total_likes', 0)
        }), 200
        
    except Exception as e:
        logger.error(f"Like post error: {str(e)}")
        return jsonify({'error': 'Like operation failed', 'details': str(e)}), 500

@community_bp.route('/posts/<post_id>/replies', methods=['POST'])
@auth_required
@invalidate_cache_pattern(f"{CacheKeys.COMMUNITY_POST}:*")
def add_reply(post_id):
    """Add a reply to a post with cache invalidation"""
    try:
        if not community_model:
            return jsonify({'error': 'Community service not available'}), 500
        
        user_id = request.user_id
        data = request.get_json()
        
        if not data or 'content' not in data or not data['content'].strip():
            return jsonify({'error': 'Reply content is required'}), 400
        
        # Check if post exists
        post = community_model.get_post_by_id(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        # Get user profile for author information
        user_data = user_model.get_user_by_id(user_id) if user_model else None
        if not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        # Prepare reply data
        reply_data = {
            'post_id': post_id,
            'content': data['content'].strip(),
            'author_id': user_id,
            'author_name': user_data.get('profile', {}).get('name', 'Anonymous'),
            'author_profession': user_data.get('profile', {}).get('profession', ''),
            'created_at': datetime.utcnow()
        }
        
        # Create reply
        reply_id = community_model.create_reply(reply_data)
        
        # Invalidate post cache (includes replies)
        post_cache_key = cache.generate_cache_key(CacheKeys.COMMUNITY_POST, post_id)
        cache.delete(post_cache_key)
        
        # Also invalidate posts list cache (for reply counts)
        cache.delete_pattern(f"{CacheKeys.COMMUNITY_POSTS}:*")
        
        logger.info(f"Reply added and cache invalidated for post: {post_id}, user: {user_id}")
        
        return jsonify({
            'message': 'Reply added successfully',
            'reply_id': reply_id
        }), 201
        
    except Exception as e:
        logger.error(f"Add reply error: {str(e)}")
        return jsonify({'error': 'Reply creation failed', 'details': str(e)}), 500

@community_bp.route('/posts/<post_id>/replies', methods=['GET'])
@auth_required
def get_post_replies(post_id):
    """Get replies for a post with caching"""
    try:
        if not community_model:
            return jsonify({'error': 'Community service not available'}), 500
        
        # Check cache first
        cache_key = cache.generate_cache_key(CacheKeys.COMMUNITY_REPLIES, post_id)
        cached_replies = cache.get(cache_key)
        
        if cached_replies:
            logger.info(f"Post replies cache hit for post: {post_id}")
            return jsonify(cached_replies), 200
        
        # Check if post exists
        post = community_model.get_post_by_id(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        # Get replies
        replies = community_model.get_post_replies(post_id)
        
        response_data = {
            'post_id': post_id,
            'replies': replies,
            'reply_count': len(replies)
        }
        
        # Cache the replies
        cache.set(cache_key, response_data, CacheTTL.COMMUNITY_POST)
        logger.info(f"Post replies cached for post: {post_id}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Get post replies error: {str(e)}")
        return jsonify({'error': 'Failed to get replies', 'details': str(e)}), 500

@community_bp.route('/posts/user', methods=['GET'])
@auth_required
def get_user_posts():
    """Get posts by the authenticated user with caching"""
    try:
        if not community_model:
            return jsonify({'error': 'Community service not available'}), 500
        
        user_id = request.user_id
        
        # Get query parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        
        # Generate cache key
        cache_key = cache.generate_cache_key(
            CacheKeys.COMMUNITY_POSTS,
            user_id,
            'user_posts',
            f"page:{page}",
            f"limit:{limit}"
        )
        
        # Check cache first
        cached_posts = cache.get(cache_key)
        if cached_posts:
            logger.info(f"User posts cache hit for user: {user_id}")
            return jsonify(cached_posts), 200
        
        # Get from database
        posts = community_model.get_user_posts(user_id, page, limit)
        total_posts = community_model.get_user_posts_count(user_id)
        
        response_data = {
            'posts': posts,
            'pagination': {
                'current_page': page,
                'per_page': limit,
                'total_posts': total_posts,
                'total_pages': (total_posts + limit - 1) // limit,
                'has_next': page * limit < total_posts,
                'has_prev': page > 1
            },
            'user_id': user_id
        }
        
        # Cache the results
        cache.set(cache_key, response_data, CacheTTL.COMMUNITY_POSTS)
        logger.info(f"User posts cached for user: {user_id}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Get user posts error: {str(e)}")
        return jsonify({'error': 'Failed to get user posts', 'details': str(e)}), 500

@community_bp.route('/my-posts', methods=['GET'])
@auth_required
def get_my_posts():
    """Get posts by the authenticated user (alias for user posts)"""
    return get_user_posts()

@community_bp.route('/stats', methods=['GET'])
@auth_required
def get_community_stats():
    """Get community statistics with caching"""
    try:
        if not community_model:
            return jsonify({'error': 'Community service not available'}), 500
        
        # Check cache first
        cache_key = cache.generate_cache_key(CacheKeys.COMMUNITY_STATS, 'global')
        cached_stats = cache.get(cache_key)
        
        if cached_stats:
            logger.info("Community stats cache hit")
            return jsonify(cached_stats), 200
        
        # Get from database
        stats = community_model.get_community_statistics()
        
        # Cache the stats
        cache.set(cache_key, stats, CacheTTL.COMMUNITY_STATS)
        logger.info("Community stats cached")
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Get community stats error: {str(e)}")
        return jsonify({'error': 'Failed to get community stats', 'details': str(e)}), 500

@community_bp.route('/posts/<post_id>', methods=['DELETE'])
@auth_required
@invalidate_cache_pattern(f"{CacheKeys.COMMUNITY_POST}:*")
def delete_post(post_id):
    """Delete a post with cache cleanup"""
    try:
        if not community_model:
            return jsonify({'error': 'Community service not available'}), 500
        
        user_id = request.user_id
        
        # Get post to verify ownership
        post = community_model.get_post_by_id(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        # Verify ownership
        if post.get('author_id') != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Delete post
        delete_result = community_model.delete_post(post_id)
        
        if delete_result.get('success'):
            # Clean up all related cache entries
            cache_patterns = [
                f"{CacheKeys.COMMUNITY_POST}:{post_id}*",
                f"{CacheKeys.COMMUNITY_POSTS}:*",
                f"{CacheKeys.COMMUNITY_REPLIES}:{post_id}*",
                f"{CacheKeys.COMMUNITY_STATS}:*"
            ]
            
            for pattern in cache_patterns:
                cache.delete_pattern(pattern)
            
            logger.info(f"Post deleted and cache cleaned for post: {post_id}")
            
            return jsonify({
                'message': 'Post deleted successfully',
                'post_id': post_id
            }), 200
        else:
            return jsonify({'error': 'Post deletion failed'}), 500
        
    except Exception as e:
        logger.error(f"Delete post error: {str(e)}")
        return jsonify({'error': 'Post deletion failed', 'details': str(e)}), 500

@community_bp.route('/posts/<post_id>/replies/<reply_id>', methods=['DELETE'])
@auth_required
@invalidate_cache_pattern(f"{CacheKeys.COMMUNITY_POST}:*")
def delete_reply(post_id, reply_id):
    """Delete a reply with cache cleanup"""
    try:
        if not community_model:
            return jsonify({'error': 'Community service not available'}), 500
        
        user_id = request.user_id
        
        # Get reply to verify ownership
        reply = community_model.get_reply_by_id(reply_id)
        if not reply:
            return jsonify({'error': 'Reply not found'}), 404
        
        # Verify ownership
        if reply.get('author_id') != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Delete reply
        delete_result = community_model.delete_reply(reply_id)
        
        if delete_result.get('success'):
            # Clean up related cache entries
            cache_patterns = [
                f"{CacheKeys.COMMUNITY_POST}:{post_id}*",
                f"{CacheKeys.COMMUNITY_REPLIES}:{post_id}*",
                f"{CacheKeys.COMMUNITY_POSTS}:*"  # For reply counts
            ]
            
            for pattern in cache_patterns:
                cache.delete_pattern(pattern)
            
            logger.info(f"Reply deleted and cache cleaned for reply: {reply_id}")
            
            return jsonify({
                'message': 'Reply deleted successfully',
                'reply_id': reply_id
            }), 200
        else:
            return jsonify({'error': 'Reply deletion failed'}), 500
        
    except Exception as e:
        logger.error(f"Delete reply error: {str(e)}")
        return jsonify({'error': 'Reply deletion failed', 'details': str(e)}), 500

# Cache management endpoints
@community_bp.route('/cache/clear', methods=['POST'])
@auth_required
def clear_community_cache():
    """Clear all community cache entries"""
    try:
        # Clear all community related cache entries
        cache_patterns = [
            f"{CacheKeys.COMMUNITY_POSTS}:*",
            f"{CacheKeys.COMMUNITY_POST}:*",
            f"{CacheKeys.COMMUNITY_REPLIES}:*",
            f"{CacheKeys.COMMUNITY_STATS}:*"
        ]
        
        total_deleted = 0
        for pattern in cache_patterns:
            deleted = cache.delete_pattern(pattern)
            total_deleted += deleted
        
        logger.info(f"Cleared {total_deleted} community cache entries")
        
        return jsonify({
            'message': 'Community cache cleared successfully',
            'entries_deleted': total_deleted
        }), 200
        
    except Exception as e:
        logger.error(f"Clear community cache error: {str(e)}")
        return jsonify({'error': 'Failed to clear cache', 'details': str(e)}), 500

@community_bp.route('/cache/status', methods=['GET'])
@auth_required
def get_community_cache_status():
    """Get cache status for community data"""
    try:
        # Check various cache keys
        cache_keys_to_check = [
            (f"{CacheKeys.COMMUNITY_STATS}:global", 'global_stats'),
            (f"{CacheKeys.COMMUNITY_POSTS}:page:1:limit:20:category:all:sort:latest", 'posts_page_1'),
            (f"{CacheKeys.COMMUNITY_POSTS}:{request.user_id}:user_posts:page:1:limit:20", 'user_posts')
        ]
        
        cache_status = {}
        for cache_key, name in cache_keys_to_check:
            exists = cache.exists(cache_key)
            ttl = cache.get_ttl(cache_key) if exists else -1
            
            cache_status[name] = {
                'cached': exists,
                'ttl_seconds': ttl,
                'expires_in': f"{ttl // 60}m {ttl % 60}s" if ttl > 0 else 'Not cached'
            }
        
        # Get sample of post caches
        if community_model:
            recent_posts = community_model.get_posts(page=1, limit=5)
            post_cache_status = {}
            
            for post in recent_posts[:3]:  # Check first 3 posts
                post_id = post.get('id')
                if post_id:
                    post_cache_key = cache.generate_cache_key(CacheKeys.COMMUNITY_POST, post_id)
                    exists = cache.exists(post_cache_key)
                    ttl = cache.get_ttl(post_cache_key) if exists else -1
                    
                    post_cache_status[post_id] = {
                        'title': post.get('title', 'Unknown')[:50],
                        'cached': exists,
                        'ttl_seconds': ttl,
                        'expires_in': f"{ttl // 60}m {ttl % 60}s" if ttl > 0 else 'Not cached'
                    }
            
            cache_status['sample_posts'] = post_cache_status
        
        return jsonify({
            'community_cache_status': cache_status,
            'user_id': request.user_id
        }), 200
        
    except Exception as e:
        logger.error(f"Get community cache status error: {str(e)}")
        return jsonify({'error': 'Failed to get cache status', 'details': str(e)}), 500

@community_bp.route('/bulk-cache-refresh', methods=['POST'])
@auth_required
def bulk_cache_refresh():
    """Refresh cache for community data"""
    try:
        # Clear all community caches to force refresh
        cache_patterns = [
            f"{CacheKeys.COMMUNITY_POSTS}:*",
            f"{CacheKeys.COMMUNITY_POST}:*",
            f"{CacheKeys.COMMUNITY_REPLIES}:*",
            f"{CacheKeys.COMMUNITY_STATS}:*"
        ]
        
        total_deleted = 0
        for pattern in cache_patterns:
            deleted = cache.delete_pattern(pattern)
            total_deleted += deleted
        
        logger.info(f"Bulk cache refresh completed, cleared {total_deleted} entries")
        
        return jsonify({
            'message': 'Bulk cache refresh completed',
            'entries_cleared': total_deleted
        }), 200
        
    except Exception as e:
        logger.error(f"Bulk cache refresh error: {str(e)}")
        return jsonify({'error': 'Bulk cache refresh failed', 'details': str(e)}), 500