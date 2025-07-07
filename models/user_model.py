# models/user_model.py
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
from firebase_admin import firestore

logger = logging.getLogger(__name__)

class UserModel:
    """User data model for Firestore operations"""
    
    def __init__(self, db):
        self.db = db
        self.collection_name = 'users'
    
    def create_user(self, user_data: Dict[str, Any]) -> str:
        """Create a new user in Firestore"""
        try:
            from werkzeug.security import generate_password_hash
            
            user_doc = {
                'email': user_data['email'].lower().strip(),
                'sso_provider': user_data.get('sso_provider', 'email'),
                'profile': {
                    'name': user_data.get('name', ''),
                    'profession': '',
                    'career_choices': [],
                    'college_name': '',
                    'college_email': '',
                    'completion_status': 0,
                    'is_profile_complete': False,
                    'profile_picture': user_data.get('profile_picture', ''),
                    'phone': ''
                },
                'is_active': True,
                'is_verified': user_data.get('is_verified', False),
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'last_login': None,
                'xp': {
                    'total_xp': user_data.get('initial_xp', 0),
                    'level': 1,
                    'badges': []
                },
                'settings': {
                    'notifications': True,
                    'email_updates': True,
                    'privacy_level': 'normal'
                }
            }
            
            # Add password hash if provided
            if 'password' in user_data:
                user_doc['password'] = generate_password_hash(user_data['password'])
            
            # Add Google ID if provided
            if 'google_id' in user_data:
                user_doc['google_id'] = user_data['google_id']
            
            # Add user to Firestore
            doc_ref = self.db.collection(self.collection_name).add(user_doc)
            user_id = doc_ref[1].id
            
            logger.info(f"Created user: {user_id}")
            return user_id
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise Exception(f"Failed to create user: {str(e)}")
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            doc_ref = self.db.collection(self.collection_name).document(user_id)
            doc = doc_ref.get()
            
            if doc.exists:
                user_data = doc.to_dict()
                user_data['id'] = user_id
                
                # Convert Firebase timestamps to ISO strings
                if user_data.get('created_at'):
                    user_data['created_at'] = user_data['created_at'].isoformat() if hasattr(user_data['created_at'], 'isoformat') else str(user_data['created_at'])
                if user_data.get('last_login'):
                    user_data['last_login'] = user_data['last_login'].isoformat() if hasattr(user_data['last_login'], 'isoformat') else str(user_data['last_login'])
                    
                return user_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        try:
            query = self.db.collection(self.collection_name).where('email', '==', email.lower().strip()).limit(1)
            docs = query.get()
            
            if docs:
                doc = docs[0]
                user_data = doc.to_dict()
                user_data['id'] = doc.id
                
                # Convert Firebase timestamps
                if user_data.get('created_at'):
                    user_data['created_at'] = user_data['created_at'].isoformat() if hasattr(user_data['created_at'], 'isoformat') else str(user_data['created_at'])
                if user_data.get('last_login'):
                    user_data['last_login'] = user_data['last_login'].isoformat() if hasattr(user_data['last_login'], 'isoformat') else str(user_data['last_login'])
                    
                return user_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    def update_user(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """Update user data"""
        try:
            # Always add updated timestamp
            update_data['updated_at'] = firestore.SERVER_TIMESTAMP
            
            doc_ref = self.db.collection(self.collection_name).document(user_id)
            doc_ref.update(update_data)
            
            logger.info(f"Updated user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return False
    
    def delete_user(self, user_id: str) -> bool:
        """Soft delete user"""
        try:
            update_data = {
                'is_active': False,
                'deleted_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            doc_ref = self.db.collection(self.collection_name).document(user_id)
            doc_ref.update(update_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False
    
    def get_user_statistics(self) -> Dict[str, Any]:
        """Get user statistics"""
        try:
            total_users = len(self.db.collection(self.collection_name).where('is_active', '==', True).get())
            return {
                'total_users': total_users,
                'active_users': total_users
            }
        except Exception as e:
            logger.error(f"Error getting user statistics: {e}")
            return {'total_users': 0, 'active_users': 0}