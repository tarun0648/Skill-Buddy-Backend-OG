# models/social_model.py (COMPLETELY FIXED - FULL DATA RETURN)
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
import uuid
from firebase_admin import firestore

logger = logging.getLogger(__name__)

class SocialModel:
    """Social media data model for Firestore operations - COMPLETELY FIXED"""
    
    def __init__(self, db):
        self.db = db
        self.posts_collection = 'social_posts'
        self.replies_collection = 'social_replies'
        self.likes_collection = 'social_likes'
    
    def create_post(self, user_id: str, content: str, category: str = 'general', 
                    tags: List[str] = None, is_anonymous: bool = False) -> str:
        """Create a new post"""
        try:
            post_id = str(uuid.uuid4())
            
            # Get user info for display
            user_info = self._get_user_display_info(user_id, is_anonymous)
            
            post_data = {
                'post_id': post_id,
                'user_id': user_id,
                'content': content,
                'category': category,
                'tags': tags or [],
                'is_anonymous': is_anonymous,
                'user_info': user_info,
                'like_count': 0,
                'reply_count': 0,
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'is_active': True
            }
            
            # Add to Firestore
            doc_ref = self.db.collection(self.posts_collection).document(post_id)
            doc_ref.set(post_data)
            
            logger.info(f"Created post: {post_id} by user: {user_id}")
            return post_id
            
        except Exception as e:
            logger.error(f"Error creating post: {e}")
            raise Exception(f"Failed to create post: {str(e)}")
    
    def get_post_by_id(self, post_id: str) -> Optional[Dict[str, Any]]:
        """Get a post by ID with ALL required fields"""
        try:
            doc_ref = self.db.collection(self.posts_collection).document(post_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                logger.warning(f"Post not found: {post_id}")
                return None
            
            # Get raw data from Firestore
            post_data = doc.to_dict()
            
            # Ensure post_data is not None
            if not post_data:
                logger.error(f"Post data is None for post: {post_id}")
                return None
            
            # Add document ID
            post_data['id'] = post_id
            
            # Ensure ALL required fields are present with proper defaults
            post_data['post_id'] = post_data.get('post_id', post_id)
            post_data['user_id'] = post_data.get('user_id', '')
            post_data['content'] = post_data.get('content', '')
            post_data['category'] = post_data.get('category', 'general')
            post_data['tags'] = post_data.get('tags', [])
            post_data['is_anonymous'] = post_data.get('is_anonymous', False)
            post_data['like_count'] = int(post_data.get('like_count', 0))
            post_data['reply_count'] = int(post_data.get('reply_count', 0))
            post_data['is_active'] = post_data.get('is_active', True)
            
            # Ensure user_info is present and complete
            user_info = post_data.get('user_info', {})
            if not isinstance(user_info, dict):
                user_info = {}
            
            post_data['user_info'] = {
                'name': user_info.get('name', 'User'),
                'profession': user_info.get('profession', ''),
                'profile_picture': user_info.get('profile_picture', '')
            }
            
            # Convert timestamps to readable format
            self._convert_timestamps(post_data)
            
            logger.info(f"Successfully retrieved post: {post_id}")
            return post_data
            
        except Exception as e:
            logger.error(f"Error getting post by ID {post_id}: {e}")
            return None
    
    def get_posts(self, limit: int = 10, page: int = 1, category: str = None, 
                  tag: str = None) -> List[Dict[str, Any]]:
        """Get posts with ALL fields included"""
        try:
            logger.info(f"Getting posts: limit={limit}, page={page}, category={category}, tag={tag}")
            
            # Start with base query
            query = self.db.collection(self.posts_collection)
            
            # Add filters
            query = query.where('is_active', '==', True)
            
            if category and category.strip():
                query = query.where('category', '==', category.strip())
                logger.info(f"Added category filter: {category}")
            
            if tag and tag.strip():
                query = query.where('tags', 'array_contains', tag.strip())
                logger.info(f"Added tag filter: {tag}")
            
            # Order by creation time (newest first)
            query = query.order_by('created_at', direction=firestore.Query.DESCENDING)
            
            # Apply pagination
            offset = (page - 1) * limit
            if offset > 0:
                query = query.offset(offset)
            
            # Apply limit
            query = query.limit(limit)
            
            # Execute query
            docs = query.get()
            posts = []
            
            logger.info(f"Found {len(docs)} posts from Firestore")
            
            for doc in docs:
                post_data = doc.to_dict()
                
                if not post_data:
                    logger.warning(f"Skipping post with no data: {doc.id}")
                    continue
                
                # Add document ID
                post_data['id'] = doc.id
                
                # Ensure ALL required fields are present
                post_data['post_id'] = post_data.get('post_id', doc.id)
                post_data['user_id'] = post_data.get('user_id', '')
                post_data['content'] = post_data.get('content', '')
                post_data['category'] = post_data.get('category', 'general')
                post_data['tags'] = post_data.get('tags', [])
                post_data['is_anonymous'] = post_data.get('is_anonymous', False)
                post_data['like_count'] = int(post_data.get('like_count', 0))
                post_data['reply_count'] = int(post_data.get('reply_count', 0))
                post_data['is_active'] = post_data.get('is_active', True)
                
                # Ensure user_info is complete
                user_info = post_data.get('user_info', {})
                if not isinstance(user_info, dict):
                    user_info = {}
                
                post_data['user_info'] = {
                    'name': user_info.get('name', 'User'),
                    'profession': user_info.get('profession', ''),
                    'profile_picture': user_info.get('profile_picture', '')
                }
                
                # Convert timestamps
                self._convert_timestamps(post_data)
                
                posts.append(post_data)
            
            logger.info(f"Successfully processed {len(posts)} posts")
            return posts
            
        except Exception as e:
            logger.error(f"Error getting posts: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_user_posts(self, user_id: str, limit: int = 10, page: int = 1) -> List[Dict[str, Any]]:
        """Get posts by a specific user with ALL fields"""
        try:
            logger.info(f"Getting user posts: user_id={user_id}, limit={limit}, page={page}")
            
            query = self.db.collection(self.posts_collection)\
                .where('user_id', '==', user_id)\
                .where('is_active', '==', True)\
                .order_by('created_at', direction=firestore.Query.DESCENDING)
            
            # Apply pagination
            offset = (page - 1) * limit
            if offset > 0:
                query = query.offset(offset)
            
            query = query.limit(limit)
            
            docs = query.get()
            posts = []
            
            logger.info(f"Found {len(docs)} user posts from Firestore")
            
            for doc in docs:
                post_data = doc.to_dict()
                
                if not post_data:
                    continue
                
                # Add document ID
                post_data['id'] = doc.id
                
                # Ensure ALL required fields
                post_data['post_id'] = post_data.get('post_id', doc.id)
                post_data['user_id'] = post_data.get('user_id', user_id)
                post_data['content'] = post_data.get('content', '')
                post_data['category'] = post_data.get('category', 'general')
                post_data['tags'] = post_data.get('tags', [])
                post_data['is_anonymous'] = post_data.get('is_anonymous', False)
                post_data['like_count'] = int(post_data.get('like_count', 0))
                post_data['reply_count'] = int(post_data.get('reply_count', 0))
                post_data['is_active'] = post_data.get('is_active', True)
                
                # Ensure user_info
                user_info = post_data.get('user_info', {})
                if not isinstance(user_info, dict):
                    user_info = {}
                
                post_data['user_info'] = {
                    'name': user_info.get('name', 'User'),
                    'profession': user_info.get('profession', ''),
                    'profile_picture': user_info.get('profile_picture', '')
                }
                
                # Convert timestamps
                self._convert_timestamps(post_data)
                
                posts.append(post_data)
            
            logger.info(f"Successfully processed {len(posts)} user posts")
            return posts
            
        except Exception as e:
            logger.error(f"Error getting user posts: {e}")
            return []
    
    def toggle_post_like(self, post_id: str, user_id: str) -> bool:
        """Toggle like on a post"""
        try:
            like_id = f"{post_id}_{user_id}"
            like_doc_ref = self.db.collection(self.likes_collection).document(like_id)
            like_doc = like_doc_ref.get()
            
            post_ref = self.db.collection(self.posts_collection).document(post_id)
            
            if like_doc.exists:
                # Unlike the post
                like_doc_ref.delete()
                post_ref.update({'like_count': firestore.Increment(-1)})
                logger.info(f"User {user_id} unliked post {post_id}")
                return False
            else:
                # Like the post
                like_data = {
                    'post_id': post_id,
                    'user_id': user_id,
                    'created_at': firestore.SERVER_TIMESTAMP
                }
                like_doc_ref.set(like_data)
                post_ref.update({'like_count': firestore.Increment(1)})
                logger.info(f"User {user_id} liked post {post_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error toggling post like: {e}")
            raise Exception(f"Failed to toggle like: {str(e)}")
    
    def get_post_like_count(self, post_id: str) -> int:
        """Get the number of likes for a post"""
        try:
            post = self.get_post_by_id(post_id)
            return post.get('like_count', 0) if post else 0
        except Exception as e:
            logger.error(f"Error getting post like count: {e}")
            return 0
    
    def create_reply(self, post_id: str, user_id: str, text: str, 
                     is_anonymous: bool = False) -> str:
        """Create a reply to a post"""
        try:
            reply_id = str(uuid.uuid4())
            
            # Get user info for display
            user_info = self._get_user_display_info(user_id, is_anonymous)
            
            reply_data = {
                'reply_id': reply_id,
                'post_id': post_id,
                'user_id': user_id,
                'text': text,
                'is_anonymous': is_anonymous,
                'user_info': user_info,
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'is_active': True
            }
            
            # Use transaction to ensure consistency
            @firestore.transactional
            def update_reply_count(transaction):
                # Add reply
                reply_ref = self.db.collection(self.replies_collection).document(reply_id)
                transaction.set(reply_ref, reply_data)
                
                # Update post reply count
                post_ref = self.db.collection(self.posts_collection).document(post_id)
                transaction.update(post_ref, {
                    'reply_count': firestore.Increment(1),
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
            
            transaction = self.db.transaction()
            update_reply_count(transaction)
            
            logger.info(f"Created reply: {reply_id} for post: {post_id}")
            return reply_id
            
        except Exception as e:
            logger.error(f"Error creating reply: {e}")
            raise Exception(f"Failed to create reply: {str(e)}")
    
    def get_reply_by_id(self, reply_id: str) -> Optional[Dict[str, Any]]:
        """Get a reply by ID with ALL fields"""
        try:
            doc_ref = self.db.collection(self.replies_collection).document(reply_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
            
            reply_data = doc.to_dict()
            if not reply_data:
                return None
            
            # Add document ID
            reply_data['id'] = reply_id
            
            # Ensure required fields
            reply_data['reply_id'] = reply_data.get('reply_id', reply_id)
            reply_data['post_id'] = reply_data.get('post_id', '')
            reply_data['user_id'] = reply_data.get('user_id', '')
            reply_data['text'] = reply_data.get('text', '')
            reply_data['is_anonymous'] = reply_data.get('is_anonymous', False)
            reply_data['is_active'] = reply_data.get('is_active', True)
            
            # Ensure user_info
            user_info = reply_data.get('user_info', {})
            if not isinstance(user_info, dict):
                user_info = {}
            
            reply_data['user_info'] = {
                'name': user_info.get('name', 'User'),
                'profession': user_info.get('profession', ''),
                'profile_picture': user_info.get('profile_picture', '')
            }
            
            self._convert_timestamps(reply_data)
            return reply_data
            
        except Exception as e:
            logger.error(f"Error getting reply by ID: {e}")
            return None
    
    def get_post_replies(self, post_id: str) -> List[Dict[str, Any]]:
        """Get all replies for a post with ALL fields"""
        try:
            logger.info(f"Getting replies for post: {post_id}")
            
            query = self.db.collection(self.replies_collection)\
                .where('post_id', '==', post_id)\
                .where('is_active', '==', True)\
                .order_by('created_at', direction=firestore.Query.ASCENDING)
            
            docs = query.get()
            replies = []
            
            logger.info(f"Found {len(docs)} replies from Firestore")
            
            for doc in docs:
                reply_data = doc.to_dict()
                
                if not reply_data:
                    continue
                
                # Add document ID
                reply_data['id'] = doc.id
                
                # Ensure required fields
                reply_data['reply_id'] = reply_data.get('reply_id', doc.id)
                reply_data['post_id'] = reply_data.get('post_id', post_id)
                reply_data['user_id'] = reply_data.get('user_id', '')
                reply_data['text'] = reply_data.get('text', '')
                reply_data['is_anonymous'] = reply_data.get('is_anonymous', False)
                reply_data['is_active'] = reply_data.get('is_active', True)
                
                # Ensure user_info
                user_info = reply_data.get('user_info', {})
                if not isinstance(user_info, dict):
                    user_info = {}
                
                reply_data['user_info'] = {
                    'name': user_info.get('name', 'User'),
                    'profession': user_info.get('profession', ''),
                    'profile_picture': user_info.get('profile_picture', '')
                }
                
                self._convert_timestamps(reply_data)
                replies.append(reply_data)
            
            logger.info(f"Successfully processed {len(replies)} replies")
            return replies
            
        except Exception as e:
            logger.error(f"Error getting post replies: {e}")
            return []
    
    def delete_post(self, post_id: str) -> bool:
        """Soft delete a post"""
        try:
            post_ref = self.db.collection(self.posts_collection).document(post_id)
            post_ref.update({
                'is_active': False,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"Deleted post: {post_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting post: {e}")
            return False
    
    def delete_reply(self, reply_id: str) -> bool:
        """Soft delete a reply"""
        try:
            # Get reply to update post count
            reply = self.get_reply_by_id(reply_id)
            if not reply:
                return False
            
            @firestore.transactional
            def update_reply_deletion(transaction):
                # Soft delete reply
                reply_ref = self.db.collection(self.replies_collection).document(reply_id)
                transaction.update(reply_ref, {
                    'is_active': False,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
                
                # Update post reply count
                post_ref = self.db.collection(self.posts_collection).document(reply['post_id'])
                transaction.update(post_ref, {
                    'reply_count': firestore.Increment(-1),
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
            
            transaction = self.db.transaction()
            update_reply_deletion(transaction)
            
            logger.info(f"Deleted reply: {reply_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting reply: {e}")
            return False
    
    def get_user_activity_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user's social activity statistics"""
        try:
            # Count posts
            posts_query = self.db.collection(self.posts_collection)\
                .where('user_id', '==', user_id)\
                .where('is_active', '==', True)
            posts_count = len(posts_query.get())
            
            # Count replies
            replies_query = self.db.collection(self.replies_collection)\
                .where('user_id', '==', user_id)\
                .where('is_active', '==', True)
            replies_count = len(replies_query.get())
            
            # Count likes received
            likes_received = 0
            user_posts = posts_query.get()
            for post_doc in user_posts:
                post_data = post_doc.to_dict()
                likes_received += post_data.get('like_count', 0)
            
            return {
                'posts_count': posts_count,
                'replies_count': replies_count,
                'likes_received': likes_received,
                'total_interactions': posts_count + replies_count
            }
            
        except Exception as e:
            logger.error(f"Error getting user activity stats: {e}")
            return {
                'posts_count': 0,
                'replies_count': 0,
                'likes_received': 0,
                'total_interactions': 0
            }
    
    def _get_user_display_info(self, user_id: str, is_anonymous: bool = False) -> Dict[str, Any]:
        """Get user display information"""
        try:
            if is_anonymous:
                return {
                    'name': 'Anonymous',
                    'profile_picture': '',
                    'profession': ''
                }
            
            # Get user from users collection
            user_doc = self.db.collection('users').document(user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                profile = user_data.get('profile', {})
                
                return {
                    'name': profile.get('name', 'User'),
                    'profile_picture': profile.get('profile_picture', ''),
                    'profession': profile.get('profession', '')
                }
            
            return {
                'name': 'User',
                'profile_picture': '',
                'profession': ''
            }
            
        except Exception as e:
            logger.error(f"Error getting user display info: {e}")
            return {
                'name': 'User',
                'profile_picture': '',
                'profession': ''
            }
    
    def _convert_timestamps(self, data: Dict[str, Any]):
        """Convert Firestore timestamps to ISO strings"""
        timestamp_fields = ['created_at', 'updated_at']
        for field in timestamp_fields:
            if field in data and data[field]:
                try:
                    if hasattr(data[field], 'isoformat'):
                        data[field] = data[field].isoformat()
                    elif hasattr(data[field], 'timestamp'):
                        # Handle Firestore timestamp
                        data[field] = datetime.fromtimestamp(data[field].timestamp()).isoformat()
                    else:
                        data[field] = str(data[field])
                except Exception as e:
                    logger.warning(f"Error converting timestamp for field {field}: {e}")
                    data[field] = str(data[field])
    
    def get_social_statistics(self) -> Dict[str, Any]:
        """Get global social platform statistics"""
        try:
            # Count total posts
            posts_query = self.db.collection(self.posts_collection)\
                .where('is_active', '==', True)
            total_posts = len(posts_query.get())
            
            # Count total replies
            replies_query = self.db.collection(self.replies_collection)\
                .where('is_active', '==', True)
            total_replies = len(replies_query.get())
            
            # Count total likes
            likes_query = self.db.collection(self.likes_collection)
            total_likes = len(likes_query.get())
            
            return {
                'total_posts': total_posts,
                'total_replies': total_replies,
                'total_likes': total_likes,
                'total_interactions': total_posts + total_replies + total_likes
            }
            
        except Exception as e:
            logger.error(f"Error getting social statistics: {e}")
            return {
                'total_posts': 0,
                'total_replies': 0,
                'total_likes': 0,
                'total_interactions': 0
            }