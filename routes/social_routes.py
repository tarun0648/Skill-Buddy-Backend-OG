# routes/social_routes.py (DEBUG VERSION - FULL DATA RETURN)
from flask import Blueprint, request, jsonify
from config.firebase_config import firebase_config
from models.social_model import SocialModel
import logging
from datetime import datetime
import uuid
import json

# Create blueprint
social_bp = Blueprint('social', __name__)

# Initialize components
db = firebase_config.get_db()
if db:
    social_model = SocialModel(db)
else:
    social_model = None

logger = logging.getLogger(__name__)

def auth_required(f):
    """Local auth decorator for social routes"""
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

@social_bp.route('/posts', methods=['POST'])
@auth_required
def create_post():
    """Create a new post"""
    try:
        if not social_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        data = request.get_json()
        
        logger.info(f"Creating post for user: {user_id} with data: {data}")
        
        if not data or 'content' not in data:
            return jsonify({'error': 'Content is required'}), 400
        
        content = data['content'].strip()
        if not content:
            return jsonify({'error': 'Content cannot be empty'}), 400
        
        # Optional fields
        category = data.get('category', 'general')
        tags = data.get('tags', [])
        is_anonymous = data.get('is_anonymous', False)
        
        logger.info(f"Post details: category={category}, tags={tags}, anonymous={is_anonymous}")
        
        # Create post
        post_id = social_model.create_post(
            user_id=user_id,
            content=content,
            category=category,
            tags=tags,
            is_anonymous=is_anonymous
        )
        
        logger.info(f"Post created with ID: {post_id}")
        
        # Get the created post
        post = social_model.get_post_by_id(post_id)
        
        logger.info(f"Retrieved created post: {post}")
        
        if not post:
            return jsonify({'error': 'Failed to retrieve created post'}), 500
        
        return jsonify({
            'success': True,
            'message': 'Post created successfully',
            'post': post
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating post: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to create post', 'details': str(e)}), 500

@social_bp.route('/posts', methods=['GET'])
@auth_required
def get_posts():
    """Get posts with pagination and filtering"""
    try:
        if not social_model:
            return jsonify({'error': 'Database not available'}), 500
        
        logger.info(f"Getting posts with query params: {dict(request.args)}")
        
        # Query parameters with validation
        try:
            page = max(1, int(request.args.get('page', 1)))
            limit = min(50, max(1, int(request.args.get('limit', 10))))
        except ValueError:
            return jsonify({'error': 'Invalid page or limit parameter'}), 400
        
        category = request.args.get('category')
        tag = request.args.get('tag')
        user_posts_only = request.args.get('user_only', 'false').lower() == 'true'
        
        logger.info(f"Query params: page={page}, limit={limit}, category={category}, tag={tag}, user_only={user_posts_only}")
        
        # Get posts
        if user_posts_only:
            posts = social_model.get_user_posts(request.user_id, limit, page)
            logger.info(f"Got {len(posts)} user posts")
        else:
            posts = social_model.get_posts(limit, page, category, tag)
            logger.info(f"Got {len(posts)} general posts")
        
        # Log first post for debugging
        if posts:
            logger.info(f"First post data: {json.dumps(posts[0], indent=2, default=str)}")
        else:
            logger.warning("No posts returned from model")
        
        response_data = {
            'success': True,
            'posts': posts,
            'pagination': {
                'page': page,
                'limit': limit,
                'has_more': len(posts) == limit,
                'count': len(posts)
            },
            'filters': {
                'category': category,
                'tag': tag,
                'user_only': user_posts_only
            },
            'debug': {
                'total_returned': len(posts),
                'query_executed': True,
                'user_id': request.user_id
            }
        }
        
        logger.info(f"Returning response with {len(posts)} posts")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error getting posts: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to get posts', 'details': str(e)}), 500

@social_bp.route('/posts/<post_id>', methods=['GET'])
@auth_required
def get_post(post_id):
    """Get a specific post with replies - FULL DEBUG VERSION"""
    try:
        if not social_model:
            return jsonify({'error': 'Database not available'}), 500
        
        logger.info(f"Getting post: {post_id}")
        
        # Get the post
        post = social_model.get_post_by_id(post_id)
        
        if not post:
            logger.warning(f"Post not found: {post_id}")
            return jsonify({'error': 'Post not found'}), 404
        
        logger.info(f"Retrieved post: {json.dumps(post, indent=2, default=str)}")
        
        # Get replies for this post
        replies = social_model.get_post_replies(post_id)
        logger.info(f"Retrieved {len(replies)} replies for post {post_id}")
        
        if replies:
            logger.info(f"First reply: {json.dumps(replies[0], indent=2, default=str)}")
        
        # Update the post with replies
        post['replies'] = replies
        post['reply_count'] = len(replies)  # Ensure count matches actual replies
        
        logger.info(f"Final post data with replies: {json.dumps(post, indent=2, default=str)}")
        
        response_data = {
            'success': True,
            'post': post,
            'debug': {
                'post_id': post_id,
                'replies_count': len(replies),
                'post_fields': list(post.keys()),
                'has_user_info': 'user_info' in post,
                'user_info_complete': isinstance(post.get('user_info'), dict) and 'name' in post.get('user_info', {})
            }
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error getting post: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to get post', 'details': str(e)}), 500

@social_bp.route('/posts/<post_id>/replies', methods=['POST'])
@auth_required
def add_reply(post_id):
    """Add a reply to a post"""
    try:
        if not social_model:
            return jsonify({'error': 'Database not available'}), 500
        
        user_id = request.user_id
        data = request.get_json()
        
        logger.info(f"Adding reply to post {post_id} by user {user_id} with data: {data}")
        
        if not data or 'text' not in data:
            return jsonify({'error': 'Reply text is required'}), 400
        
        text = data['text'].strip()
        if not text:
            return jsonify({'error': 'Reply text cannot be empty'}), 400
        
        # Check if post exists
        post = social_model.get_post_by_id(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        is_anonymous = data.get('is_anonymous', False)
        
        logger.info(f"Creating reply: text='{text}', anonymous={is_anonymous}")
        
        # Create reply
        reply_id = social_model.create_reply(
            post_id=post_id,
            user_id=user_id,
            text=text,
            is_anonymous=is_anonymous
        )
        
        logger.info(f"Reply created with ID: {reply_id}")
        
        # Get the created reply
        reply = social_model.get_reply_by_id(reply_id)
        
        logger.info(f"Retrieved created reply: {json.dumps(reply, indent=2, default=str)}")
        
        return jsonify({
            'success': True,
            'message': 'Reply added successfully',
            'reply': reply
        }), 201
        
    except Exception as e:
        logger.error(f"Error adding reply: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to add reply', 'details': str(e)}), 500

@social_bp.route('/posts/<post_id>/replies', methods=['GET'])
@auth_required
def get_replies(post_id):
    """Get replies for a post"""
    try:
        if not social_model:
            return jsonify({'error': 'Database not available'}), 500
        
        logger.info(f"Getting replies for post: {post_id}")
        
        # Check if post exists
        post = social_model.get_post_by_id(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        replies = social_model.get_post_replies(post_id)
        logger.info(f"Retrieved {len(replies)} replies")
        
        if replies:
            logger.info(f"Sample reply data: {json.dumps(replies[0], indent=2, default=str)}")
        
        response_data = {
            'success': True,
            'replies': replies,
            'count': len(replies),
            'debug': {
                'post_id': post_id,
                'replies_found': len(replies),
                'post_exists': True
            }
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error getting replies: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to get replies', 'details': str(e)}), 500

@social_bp.route('/posts/<post_id>/like', methods=['POST'])
@auth_required
def like_post(post_id):
    """Like or unlike a post"""
    try:
        if not social_model:
            return jsonify({'error': 'Database not available'}), 500
        
        user_id = request.user_id
        logger.info(f"User {user_id} toggling like on post {post_id}")
        
        # Check if post exists
        post = social_model.get_post_by_id(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        # Toggle like
        liked = social_model.toggle_post_like(post_id, user_id)
        
        # Get updated like count
        like_count = social_model.get_post_like_count(post_id)
        
        logger.info(f"Like toggled: liked={liked}, new count={like_count}")
        
        return jsonify({
            'success': True,
            'liked': liked,
            'like_count': like_count,
            'message': 'Post liked' if liked else 'Post unliked'
        }), 200
        
    except Exception as e:
        logger.error(f"Error liking post: {e}")
        return jsonify({'error': 'Failed to like post', 'details': str(e)}), 500

@social_bp.route('/user/posts', methods=['GET'])
@auth_required
def get_user_posts():
    """Get posts by the authenticated user"""
    try:
        if not social_model:
            return jsonify({'error': 'Database not available'}), 500
        
        user_id = request.user_id
        logger.info(f"Getting posts for user: {user_id}")
        
        # Query parameters
        try:
            page = max(1, int(request.args.get('page', 1)))
            limit = min(50, max(1, int(request.args.get('limit', 10))))
        except ValueError:
            return jsonify({'error': 'Invalid page or limit parameter'}), 400
        
        posts = social_model.get_user_posts(user_id, limit, page)
        logger.info(f"Retrieved {len(posts)} user posts")
        
        if posts:
            logger.info(f"Sample user post: {json.dumps(posts[0], indent=2, default=str)}")
        
        response_data = {
            'success': True,
            'posts': posts,
            'pagination': {
                'page': page,
                'limit': limit,
                'has_more': len(posts) == limit,
                'count': len(posts)
            },
            'user_id': user_id,
            'debug': {
                'query_user_id': user_id,
                'posts_found': len(posts)
            }
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error getting user posts: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to get user posts', 'details': str(e)}), 500

@social_bp.route('/user/activity', methods=['GET'])
@auth_required
def get_user_activity():
    """Get user's social activity statistics"""
    try:
        if not social_model:
            return jsonify({'error': 'Database not available'}), 500
        
        user_id = request.user_id
        activity = social_model.get_user_activity_stats(user_id)
        
        return jsonify({
            'success': True,
            'activity': activity,
            'user_id': user_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting user activity: {e}")
        return jsonify({'error': 'Failed to get user activity', 'details': str(e)}), 500

@social_bp.route('/categories', methods=['GET'])
@auth_required
def get_categories():
    """Get available post categories"""
    try:
        categories = [
            'general',
            'career_advice',
            'technical_help',
            'networking',
            'job_opportunities',
            'study_groups',
            'project_collaboration',
            'achievements',
            'questions',
            'announcements'
        ]
        
        return jsonify({
            'success': True,
            'categories': categories
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        return jsonify({'error': 'Failed to get categories', 'details': str(e)}), 500

# DEBUG ENDPOINTS
@social_bp.route('/debug/firestore-test', methods=['GET'])
@auth_required
def debug_firestore_test():
    """Test Firestore connection and data structure"""
    try:
        if not social_model:
            return jsonify({'error': 'Database not available'}), 500
        
        logger.info("Testing Firestore connection and data structure")
        
        # Test collections exist
        posts_collection = db.collection('social_posts')
        replies_collection = db.collection('social_replies')
        likes_collection = db.collection('social_likes')
        
        # Count documents
        posts_count = len(posts_collection.limit(1).get())
        replies_count = len(replies_collection.limit(1).get())
        likes_count = len(likes_collection.limit(1).get())
        
        # Get sample documents
        sample_post = None
        sample_reply = None
        
        posts_sample = posts_collection.limit(1).get()
        if posts_sample:
            sample_post = posts_sample[0].to_dict()
            sample_post['doc_id'] = posts_sample[0].id
        
        replies_sample = replies_collection.limit(1).get()
        if replies_sample:
            sample_reply = replies_sample[0].to_dict()
            sample_reply['doc_id'] = replies_sample[0].id
        
        debug_info = {
            'firestore_connected': True,
            'collections_exist': {
                'posts': posts_count >= 0,
                'replies': replies_count >= 0,
                'likes': likes_count >= 0
            },
            'document_counts': {
                'posts_exist': posts_count > 0,
                'replies_exist': replies_count > 0,
                'likes_exist': likes_count > 0
            },
            'sample_data': {
                'sample_post': sample_post,
                'sample_reply': sample_reply
            },
            'model_methods_available': {
                'get_posts': hasattr(social_model, 'get_posts'),
                'get_post_by_id': hasattr(social_model, 'get_post_by_id'),
                'create_post': hasattr(social_model, 'create_post'),
                'get_post_replies': hasattr(social_model, 'get_post_replies')
            }
        }
        
        return jsonify({
            'success': True,
            'debug_info': debug_info
        }), 200
        
    except Exception as e:
        logger.error(f"Error in Firestore test: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Firestore test failed', 'details': str(e)}), 500

@social_bp.route('/debug/create-test-post', methods=['POST'])
@auth_required
def debug_create_test_post():
    """Create a test post for debugging"""
    try:
        if not social_model:
            return jsonify({'error': 'Database not available'}), 500
        
        user_id = request.user_id
        
        # Create test post
        test_content = f"Test post created at {datetime.now().isoformat()} by user {user_id}"
        
        post_id = social_model.create_post(
            user_id=user_id,
            content=test_content,
            category='general',
            tags=['test', 'debug'],
            is_anonymous=False
        )
        
        # Retrieve the created post
        created_post = social_model.get_post_by_id(post_id)
        
        return jsonify({
            'success': True,
            'message': 'Test post created',
            'post_id': post_id,
            'created_post': created_post
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating test post: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to create test post', 'details': str(e)}), 500

@social_bp.route('/debug/raw-firestore/<post_id>', methods=['GET'])
@auth_required
def debug_raw_firestore_data(post_id):
    """Get raw Firestore data for a post"""
    try:
        if not db:
            return jsonify({'error': 'Database not available'}), 500
        
        # Get raw document from Firestore
        doc_ref = db.collection('social_posts').document(post_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return jsonify({'error': 'Post not found in Firestore'}), 404
        
        raw_data = doc.to_dict()
        
        # Get raw replies
        replies_query = db.collection('social_replies').where('post_id', '==', post_id)
        replies_docs = replies_query.get()
        raw_replies = [reply_doc.to_dict() for reply_doc in replies_docs]
        
        return jsonify({
            'success': True,
            'raw_post_data': raw_data,
            'raw_replies': raw_replies,
            'doc_id': doc.id,
            'replies_count': len(raw_replies)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting raw Firestore data: {e}")
        return jsonify({'error': 'Failed to get raw data', 'details': str(e)}), 500