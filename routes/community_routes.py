# routes/community_routes.py (FIXED)
from flask import Blueprint, request, jsonify
from config.firebase_config import firebase_config
from models.user_model import UserModel
from models.community_model import CommunityModel
import uuid
from datetime import datetime
import logging

# Create blueprint
community_bp = Blueprint('community', __name__)

# Initialize components
db = firebase_config.get_db()
if db:
    user_model = UserModel(db)
    community_model = CommunityModel(db)
else:
    user_model = None
    community_model = None

logger = logging.getLogger(__name__)

def auth_required(f):
    """Local auth decorator for community routes"""
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

# Create a new post
@community_bp.route('/posts', methods=['POST'])
@auth_required
def create_post():
    """Create a new community post"""
    try:
        if not user_model or not community_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        data = request.get_json()

        if not data or 'content' not in data:
            return jsonify({
                'success': False,
                'error': 'Content field is required'
            }), 400

        content = data['content'].strip()
        if not content:
            return jsonify({
                'success': False,
                'error': 'Content cannot be empty'
            }), 400

        # Get user info for post metadata
        user = user_model.get_user_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Create post using community model
        post_id = community_model.create_post(user_id, user, content)

        # Get the created post data
        post_data = community_model.get_post_by_id(post_id)

        logger.info(f"Post created by user {user_id}: {post_id}")

        return jsonify({
            'success': True,
            'message': 'Post created successfully',
            'data': post_data
        }), 201

    except Exception as e:
        logger.error(f"Error creating post: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to create post',
            'details': str(e)
        }), 500

# Get all posts with pagination
@community_bp.route('/posts', methods=['GET'])
@auth_required
def get_posts():
    """Get community posts with pagination"""
    try:
        if not community_model:
            return jsonify({'error': 'Database not available'}), 500

        # Get query parameters
        limit = int(request.args.get('limit', 20))  # Default 20 posts
        page = int(request.args.get('page', 1))
        
        # Calculate offset
        offset = (page - 1) * limit

        # Get posts using community model
        posts = community_model.get_posts(limit=limit, offset=offset)

        return jsonify({
            'success': True,
            'data': {
                'posts': posts,
                'page': page,
                'limit': limit,
                'total_posts': len(posts)
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting posts: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get posts',
            'details': str(e)
        }), 500

# Get a specific post with its likes and replies
@community_bp.route('/posts/<post_id>', methods=['GET'])
@auth_required
def get_post(post_id):
    """Get a specific post with all its data"""
    try:
        if not community_model:
            return jsonify({'error': 'Database not available'}), 500

        # Get post using community model
        post_data = community_model.get_post_by_id(post_id)

        if not post_data:
            return jsonify({
                'success': False,
                'error': 'Post not found'
            }), 404

        return jsonify({
            'success': True,
            'data': post_data
        }), 200

    except Exception as e:
        logger.error(f"Error getting post {post_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get post',
            'details': str(e)
        }), 500

# Add like to a post
@community_bp.route('/posts/<post_id>/like', methods=['POST'])
@auth_required
def add_like(post_id):
    """Add or remove like from a post"""
    try:
        if not user_model or not community_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        
        # Get user info
        user = user_model.get_user_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Toggle like using community model
        success = community_model.add_like(post_id, user_id, user)

        if not success:
            return jsonify({
                'success': False,
                'error': 'Post not found'
            }), 404

        # Get updated post data
        post_data = community_model.get_post_by_id(post_id)
        user_liked = user_id in post_data.get('likes', {})
        action = 'liked' if user_liked else 'unliked'

        logger.info(f"User {user_id} {action} post {post_id}")

        return jsonify({
            'success': True,
            'message': f'Post {action} successfully',
            'data': {
                'post_id': post_id,
                'action': action,
                'likes_count': post_data.get('likes_count', 0),
                'user_liked': user_liked
            }
        }), 200

    except Exception as e:
        logger.error(f"Error toggling like for post {post_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to toggle like',
            'details': str(e)
        }), 500

# Add reply to a post
@community_bp.route('/posts/<post_id>/replies', methods=['POST'])
@auth_required
def add_reply(post_id):
    """Add a reply to a post"""
    try:
        if not user_model or not community_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        data = request.get_json()

        if not data or 'text' not in data:
            return jsonify({
                'success': False,
                'error': 'Reply text is required'
            }), 400

        reply_text = data['text'].strip()
        if not reply_text:
            return jsonify({
                'success': False,
                'error': 'Reply text cannot be empty'
            }), 400

        # Get user info
        user = user_model.get_user_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Add reply using community model
        reply_id = community_model.add_reply(post_id, user_id, user, reply_text)

        if not reply_id:
            return jsonify({
                'success': False,
                'error': 'Post not found'
            }), 404

        # Get updated post data
        post_data = community_model.get_post_by_id(post_id)
        reply_data = post_data.get('replies', {}).get(reply_id)

        logger.info(f"User {user_id} replied to post {post_id}")

        return jsonify({
            'success': True,
            'message': 'Reply added successfully',
            'data': {
                'post_id': post_id,
                'reply': reply_data,
                'replies_count': post_data.get('replies_count', 0)
            }
        }), 201

    except Exception as e:
        logger.error(f"Error adding reply to post {post_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to add reply',
            'details': str(e)
        }), 500

# Get replies for a specific post
@community_bp.route('/posts/<post_id>/replies', methods=['GET'])
@auth_required
def get_replies(post_id):
    """Get all replies for a specific post"""
    try:
        if not community_model:
            return jsonify({'error': 'Database not available'}), 500

        # Get post data
        post_data = community_model.get_post_by_id(post_id)

        if not post_data:
            return jsonify({
                'success': False,
                'error': 'Post not found'
            }), 404

        replies = post_data.get('replies', {})
        
        # Convert replies dict to list and sort by timestamp
        replies_list = list(replies.values())
        replies_list.sort(key=lambda x: x.get('timestamp', ''), reverse=False)

        return jsonify({
            'success': True,
            'data': {
                'post_id': post_id,
                'replies': replies_list,
                'replies_count': len(replies_list)
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting replies for post {post_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get replies',
            'details': str(e)
        }), 500

# Delete a post (only by the author)
@community_bp.route('/posts/<post_id>', methods=['DELETE'])
@auth_required
def delete_post(post_id):
    """Delete a post (only by the author)"""
    try:
        if not community_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id

        # Delete post using community model
        success = community_model.delete_post(post_id, user_id)

        if not success:
            return jsonify({
                'success': False,
                'error': 'Post not found or you can only delete your own posts'
            }), 403

        logger.info(f"User {user_id} deleted post {post_id}")

        return jsonify({
            'success': True,
            'message': 'Post deleted successfully'
        }), 200

    except Exception as e:
        logger.error(f"Error deleting post {post_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete post',
            'details': str(e)
        }), 500

# Delete a reply (only by the author)
@community_bp.route('/posts/<post_id>/replies/<reply_id>', methods=['DELETE'])
@auth_required
def delete_reply(post_id, reply_id):
    """Delete a reply (only by the author)"""
    try:
        if not community_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id

        # Delete reply using community model
        success = community_model.delete_reply(post_id, reply_id, user_id)

        if not success:
            return jsonify({
                'success': False,
                'error': 'Reply not found or you can only delete your own replies'
            }), 403

        logger.info(f"User {user_id} deleted reply {reply_id} from post {post_id}")

        return jsonify({
            'success': True,
            'message': 'Reply deleted successfully'
        }), 200

    except Exception as e:
        logger.error(f"Error deleting reply {reply_id} from post {post_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete reply',
            'details': str(e)
        }), 500

# Get user's own posts
@community_bp.route('/my-posts', methods=['GET'])
@auth_required
def get_my_posts():
    """Get posts created by the authenticated user"""
    try:
        if not community_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id

        # Get user posts using community model
        posts = community_model.get_user_posts(user_id)

        return jsonify({
            'success': True,
            'data': {
                'posts': posts,
                'total_posts': len(posts)
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting user posts for {user_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get user posts',
            'details': str(e)
        }), 500

# Get community statistics
@community_bp.route('/stats', methods=['GET'])
@auth_required
def get_community_stats():
    """Get community platform statistics"""
    try:
        if not community_model:
            return jsonify({'error': 'Database not available'}), 500

        # Get statistics using community model
        stats = community_model.get_community_statistics()

        return jsonify({
            'success': True,
            'data': stats
        }), 200

    except Exception as e:
        logger.error(f"Error getting community stats: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get statistics',
            'details': str(e)
        }), 500

# Search posts
@community_bp.route('/search', methods=['GET'])
@auth_required
def search_posts():
    """Search posts by content"""
    try:
        if not community_model:
            return jsonify({'error': 'Database not available'}), 500

        search_term = request.args.get('q', '').strip()
        if not search_term:
            return jsonify({
                'success': False,
                'error': 'Search term is required'
            }), 400

        limit = int(request.args.get('limit', 20))

        # Search posts using community model
        posts = community_model.search_posts(search_term, limit)

        return jsonify({
            'success': True,
            'data': {
                'posts': posts,
                'search_term': search_term,
                'total_results': len(posts)
            }
        }), 200

    except Exception as e:
        logger.error(f"Error searching posts: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to search posts',
            'details': str(e)
        }), 500

# Get trending posts
@community_bp.route('/trending', methods=['GET'])
@auth_required
def get_trending_posts():
    """Get trending posts based on engagement"""
    try:
        if not community_model:
            return jsonify({'error': 'Database not available'}), 500

        limit = int(request.args.get('limit', 10))
        days = int(request.args.get('days', 7))

        # Get trending posts using community model
        posts = community_model.get_trending_posts(limit, days)

        return jsonify({
            'success': True,
            'data': {
                'posts': posts,
                'period_days': days,
                'total_trending': len(posts)
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting trending posts: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get trending posts',
            'details': str(e)
        }), 500