# models/community_model.py (FIXED - Index Compatible)
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
import uuid
from firebase_admin import firestore

logger = logging.getLogger(__name__)

class CommunityModel:
    """Community platform data model for Firestore operations - FIXED for index compatibility"""
    
    def __init__(self, db):
        self.db = db
        self.posts_collection = 'community_posts'
    
    def create_post(self, user_id: str, user_data: Dict[str, Any], content: str) -> str:
        """Create a new community post"""
        try:
            post_id = str(uuid.uuid4())
            user_profile = user_data.get('profile', {})
            
            post_data = {
                'post_id': post_id,
                'content': content,
                'user_id': user_id,
                'user_name': user_profile.get('name', 'Anonymous User'),
                'user_profession': user_profile.get('profession', 'Student'),
                'user_profile_picture': user_profile.get('profile_picture', ''),
                'timestamp': datetime.now().isoformat(),
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'likes': {},  # Will store user_id: user_info for likes
                'likes_count': 0,
                'replies': {},  # Will store reply_id: reply_data
                'replies_count': 0,
                'is_active': True,
                'tags': [],  # For future categorization
                'visibility': 'public'  # public, private, friends
            }
            
            # Store in Firestore
            doc_ref = self.db.collection(self.posts_collection).document(post_id)
            doc_ref.set(post_data)
            
            logger.info(f"Post created: {post_id} by user: {user_id}")
            return post_id
            
        except Exception as e:
            logger.error(f"Error creating post: {e}")
            raise Exception(f"Failed to create post: {str(e)}")
    
    def get_post_by_id(self, post_id: str) -> Optional[Dict[str, Any]]:
        """Get post by ID"""
        try:
            doc_ref = self.db.collection(self.posts_collection).document(post_id)
            doc = doc_ref.get()
            
            if doc.exists:
                post_data = doc.to_dict()
                post_data['id'] = post_id
                
                # Convert Firebase timestamps to ISO strings
                for field in ['created_at', 'updated_at']:
                    if post_data.get(field):
                        post_data[field] = post_data[field].isoformat() if hasattr(post_data[field], 'isoformat') else str(post_data[field])
                
                return post_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting post by ID: {e}")
            return None
    
    def get_posts(self, limit: int = 20, offset: int = 0, user_id: str = None) -> List[Dict[str, Any]]:
        """Get posts with pagination - FIXED to avoid composite index requirement"""
        try:
            # OPTION 1: Simple query without ordering (fastest, no index needed)
            if user_id:
                # For user-specific posts, use simple query
                query = self.db.collection(self.posts_collection)\
                    .where(filter=firestore.FieldFilter('user_id', '==', user_id))\
                    .where(filter=firestore.FieldFilter('is_active', '==', True))\
                    .limit(limit)
            else:
                # For all posts, get all active posts and sort in Python
                query = self.db.collection(self.posts_collection)\
                    .where(filter=firestore.FieldFilter('is_active', '==', True))\
                    .limit(limit * 2)  # Get more to sort and slice
            
            docs = query.get()
            posts = []
            
            for doc in docs:
                post_data = doc.to_dict()
                post_data['id'] = doc.id
                
                # Convert Firebase timestamps
                for field in ['created_at', 'updated_at']:
                    if post_data.get(field):
                        if hasattr(post_data[field], 'isoformat'):
                            post_data[field] = post_data[field].isoformat()
                        else:
                            post_data[field] = str(post_data[field])
                
                posts.append(post_data)
            
            # Sort by timestamp in Python (newest first)
            posts.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # Apply pagination in Python
            start_idx = offset
            end_idx = start_idx + limit
            paginated_posts = posts[start_idx:end_idx]
            
            return paginated_posts
            
        except Exception as e:
            logger.error(f"Error getting posts: {e}")
            return []
    
    def add_like(self, post_id: str, user_id: str, user_data: Dict[str, Any]) -> bool:
        """Add or remove like from a post"""
        try:
            doc_ref = self.db.collection(self.posts_collection).document(post_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return False
            
            post_data = doc.to_dict()
            likes = post_data.get('likes', {})
            user_profile = user_data.get('profile', {})
            
            # Toggle like
            if user_id in likes:
                # Remove like
                del likes[user_id]
                action = 'unliked'
            else:
                # Add like
                likes[user_id] = {
                    'user_name': user_profile.get('name', 'Anonymous'),
                    'user_profession': user_profile.get('profession', 'Student'),
                    'timestamp': datetime.now().isoformat()
                }
                action = 'liked'
            
            # Update post
            update_data = {
                'likes': likes,
                'likes_count': len(likes),
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            doc_ref.update(update_data)
            logger.info(f"User {user_id} {action} post {post_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error toggling like: {e}")
            return False
    
    def add_reply(self, post_id: str, user_id: str, user_data: Dict[str, Any], reply_text: str) -> Optional[str]:
        """Add a reply to a post"""
        try:
            doc_ref = self.db.collection(self.posts_collection).document(post_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
            
            post_data = doc.to_dict()
            replies = post_data.get('replies', {})
            user_profile = user_data.get('profile', {})
            
            # Create new reply
            reply_id = f"reply_{uuid.uuid4().hex}"
            reply_data = {
                'reply_id': reply_id,
                'text': reply_text,
                'user_id': user_id,
                'user_name': user_profile.get('name', 'Anonymous User'),
                'user_profession': user_profile.get('profession', 'Student'),
                'user_profile_picture': user_profile.get('profile_picture', ''),
                'timestamp': datetime.now().isoformat(),
                'created_at': datetime.now().isoformat(),
                'likes': {},  # Replies can also be liked
                'likes_count': 0
            }
            
            # Add reply to post
            replies[reply_id] = reply_data
            
            # Update post
            update_data = {
                'replies': replies,
                'replies_count': len(replies),
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            doc_ref.update(update_data)
            logger.info(f"User {user_id} replied to post {post_id}")
            
            return reply_id
            
        except Exception as e:
            logger.error(f"Error adding reply: {e}")
            return None
    
    def delete_post(self, post_id: str, user_id: str) -> bool:
        """Soft delete a post (only by author)"""
        try:
            doc_ref = self.db.collection(self.posts_collection).document(post_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return False
            
            post_data = doc.to_dict()
            
            # Check if user is the author
            if post_data.get('user_id') != user_id:
                return False
            
            # Soft delete
            update_data = {
                'is_active': False,
                'deleted_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            doc_ref.update(update_data)
            logger.info(f"User {user_id} deleted post {post_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting post: {e}")
            return False
    
    def delete_reply(self, post_id: str, reply_id: str, user_id: str) -> bool:
        """Delete a reply (only by author)"""
        try:
            doc_ref = self.db.collection(self.posts_collection).document(post_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return False
            
            post_data = doc.to_dict()
            replies = post_data.get('replies', {})
            
            # Check if reply exists
            if reply_id not in replies:
                return False
            
            reply_data = replies[reply_id]
            
            # Check if user is the author of the reply
            if reply_data.get('user_id') != user_id:
                return False
            
            # Remove reply
            del replies[reply_id]
            
            # Update post
            update_data = {
                'replies': replies,
                'replies_count': len(replies),
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            doc_ref.update(update_data)
            logger.info(f"User {user_id} deleted reply {reply_id} from post {post_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting reply: {e}")
            return False
    
    def get_user_posts(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all posts by a specific user - FIXED to avoid composite index"""
        try:
            # Use simple query without ordering
            query = self.db.collection(self.posts_collection)\
                .where(filter=firestore.FieldFilter('user_id', '==', user_id))\
                .where(filter=firestore.FieldFilter('is_active', '==', True))\
                .limit(limit)
            
            docs = query.get()
            posts = []
            
            for doc in docs:
                post_data = doc.to_dict()
                post_data['id'] = doc.id
                
                # Convert Firebase timestamps
                for field in ['created_at', 'updated_at']:
                    if post_data.get(field):
                        if hasattr(post_data[field], 'isoformat'):
                            post_data[field] = post_data[field].isoformat()
                        else:
                            post_data[field] = str(post_data[field])
                
                posts.append(post_data)
            
            # Sort by timestamp in Python (newest first)
            posts.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            return posts
            
        except Exception as e:
            logger.error(f"Error getting user posts: {e}")
            return []
    
    def get_community_statistics(self) -> Dict[str, Any]:
        """Get community platform statistics"""
        try:
            # Use simple query without complex conditions
            posts_ref = self.db.collection(self.posts_collection)\
                .where(filter=firestore.FieldFilter('is_active', '==', True))
            posts_docs = posts_ref.get()
            
            total_posts = len(posts_docs)
            total_likes = 0
            total_replies = 0
            active_users = set()
            
            for doc in posts_docs:
                post_data = doc.to_dict()
                total_likes += post_data.get('likes_count', 0)
                total_replies += post_data.get('replies_count', 0)
                active_users.add(post_data.get('user_id'))
            
            return {
                'total_posts': total_posts,
                'total_likes': total_likes,
                'total_replies': total_replies,
                'active_users': len(active_users),
                'average_likes_per_post': round(total_likes / max(total_posts, 1), 2),
                'average_replies_per_post': round(total_replies / max(total_posts, 1), 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting community statistics: {e}")
            return {
                'total_posts': 0,
                'total_likes': 0,
                'total_replies': 0,
                'active_users': 0,
                'average_likes_per_post': 0,
                'average_replies_per_post': 0
            }
    
    def search_posts(self, search_term: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search posts by content - SIMPLIFIED to avoid index issues"""
        try:
            # Get all active posts and filter in Python
            query = self.db.collection(self.posts_collection)\
                .where(filter=firestore.FieldFilter('is_active', '==', True))\
                .limit(limit * 3)  # Get more to filter
            
            docs = query.get()
            posts = []
            
            search_term_lower = search_term.lower()
            
            for doc in docs:
                post_data = doc.to_dict()
                
                # Basic text search in content and user name
                if (search_term_lower in post_data.get('content', '').lower() or
                    search_term_lower in post_data.get('user_name', '').lower()):
                    
                    post_data['id'] = doc.id
                    
                    # Convert Firebase timestamps
                    for field in ['created_at', 'updated_at']:
                        if post_data.get(field):
                            if hasattr(post_data[field], 'isoformat'):
                                post_data[field] = post_data[field].isoformat()
                            else:
                                post_data[field] = str(post_data[field])
                    
                    posts.append(post_data)
                    
                    if len(posts) >= limit:
                        break
            
            # Sort by timestamp in Python
            posts.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            return posts
            
        except Exception as e:
            logger.error(f"Error searching posts: {e}")
            return []
    
    def get_trending_posts(self, limit: int = 10, days: int = 7) -> List[Dict[str, Any]]:
        """Get trending posts based on engagement - SIMPLIFIED"""
        try:
            from datetime import timedelta
            
            # Get recent posts without complex date filtering to avoid index issues
            query = self.db.collection(self.posts_collection)\
                .where(filter=firestore.FieldFilter('is_active', '==', True))\
                .limit(limit * 3)  # Get more to calculate trending
            
            docs = query.get()
            posts = []
            
            # Calculate date threshold
            threshold_date = datetime.now() - timedelta(days=days)
            
            for doc in docs:
                post_data = doc.to_dict()
                
                # Check if post is recent (simple timestamp comparison)
                timestamp_str = post_data.get('timestamp', '')
                try:
                    if timestamp_str:
                        post_date = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00').replace('+00:00', ''))
                        if post_date < threshold_date:
                            continue
                except:
                    # If timestamp parsing fails, include the post
                    pass
                
                # Calculate engagement score
                likes_count = post_data.get('likes_count', 0)
                replies_count = post_data.get('replies_count', 0)
                engagement_score = (likes_count * 1) + (replies_count * 2)  # Replies worth more
                
                post_data['id'] = doc.id
                post_data['engagement_score'] = engagement_score
                
                # Convert Firebase timestamps
                for field in ['created_at', 'updated_at']:
                    if post_data.get(field):
                        if hasattr(post_data[field], 'isoformat'):
                            post_data[field] = post_data[field].isoformat()
                        else:
                            post_data[field] = str(post_data[field])
                
                posts.append(post_data)
            
            # Sort by engagement score
            posts.sort(key=lambda x: x.get('engagement_score', 0), reverse=True)
            
            return posts[:limit]
            
        except Exception as e:
            logger.error(f"Error getting trending posts: {e}")
            return []