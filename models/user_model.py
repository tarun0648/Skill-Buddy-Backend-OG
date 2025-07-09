# models/user_model.py (FIXED)
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
                    'github_link': '',
                    'linkedin_link': '',
                    'completion_status': 0,
                    'is_profile_complete': False,
                    'profile_picture': user_data.get('profile_picture', ''),
                    'phone': '',
                    'has_resume': False  # Track if user has uploaded resume
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
    
    def calculate_profile_completion(self, profile: Dict[str, Any]) -> int:
        """Calculate profile completion percentage based on new requirements - FIXED"""
        completion = 0
        
        # Debug logging
        logger.info(f"Calculating completion for profile: {profile}")
        
        # Basic profile steps (55% total)
        if profile.get('name') and str(profile.get('name')).strip():
            completion += 10  # 10%
            logger.info("Added 10% for name")
        
        if profile.get('profession') and str(profile.get('profession')).strip():
            completion += 10  # 10%
            logger.info("Added 10% for profession")
        
        career_choices = profile.get('career_choices', [])
        if career_choices and isinstance(career_choices, list) and len(career_choices) > 0:
            # Check if any choice is not empty
            valid_choices = [choice for choice in career_choices if choice and str(choice).strip()]
            if valid_choices:
                completion += 10  # 10%
                logger.info("Added 10% for career choices")
        
        if profile.get('college_name') and str(profile.get('college_name')).strip():
            completion += 10  # 10%
            logger.info("Added 10% for college name")
        
        if profile.get('college_email') and str(profile.get('college_email')).strip():
            completion += 15  # 15% (Total basic: 55%)
            logger.info("Added 15% for college email")
        
        # Additional profile elements (45% total)
        github_link = profile.get('github_link', '')
        if github_link and str(github_link).strip() and str(github_link).strip() != '':
            completion += 15  # 15%
            logger.info(f"Added 15% for GitHub link: {github_link}")
        
        linkedin_link = profile.get('linkedin_link', '')
        if linkedin_link and str(linkedin_link).strip() and str(linkedin_link).strip() != '':
            completion += 15  # 15%
            logger.info(f"Added 15% for LinkedIn link: {linkedin_link}")
        
        if profile.get('has_resume') is True:
            completion += 15  # 15%
            logger.info("Added 15% for resume")
        
        final_completion = min(completion, 100)
        logger.info(f"Final completion percentage: {final_completion}")
        return final_completion
    
    def get_completion_milestones(self, old_completion: int, new_completion: int) -> List[int]:
        """Get milestones that were just reached"""
        milestones = [10, 20, 30, 40, 55, 70, 85, 100]
        reached = []
        
        for milestone in milestones:
            if old_completion < milestone <= new_completion:
                reached.append(milestone)
        
        return reached
    
    def calculate_xp_bonus(self, milestones: List[int]) -> int:
        """Calculate XP bonus for reached milestones"""
        xp_bonus = 0
        milestone_rewards = {
            10: 5,   # Name
            20: 5,   # Profession
            30: 5,   # Career choices
            40: 5,   # College name
            55: 15,  # College email (basic profile complete)
            70: 15,  # GitHub or LinkedIn added
            85: 15,  # Both GitHub and LinkedIn, or Resume added
            100: 50  # Complete profile
        }
        
        for milestone in milestones:
            xp_bonus += milestone_rewards.get(milestone, 0)
        
        return xp_bonus
    
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
    
    def update_resume_status(self, user_id: str, has_resume: bool) -> bool:
        """Update user's resume status and recalculate completion"""
        try:
            logger.info(f"Updating resume status for user {user_id}: {has_resume}")
            
            # Get current user to recalculate completion
            user = self.get_user_by_id(user_id)
            if not user:
                logger.error(f"User {user_id} not found")
                return False
            
            current_profile = user.get('profile', {})
            old_completion = current_profile.get('completion_status', 0)
            
            # Update the profile with new resume status
            current_profile['has_resume'] = has_resume
            
            # Recalculate completion
            new_completion = self.calculate_profile_completion(current_profile)
            
            update_data = {
                'profile.has_resume': has_resume,
                'profile.completion_status': new_completion,
                'profile.is_profile_complete': new_completion == 100,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            # Calculate XP bonus for milestones
            milestones = self.get_completion_milestones(old_completion, new_completion)
            if milestones:
                xp_bonus = self.calculate_xp_bonus(milestones)
                if xp_bonus > 0:
                    current_xp = user.get('xp', {}).get('total_xp', 0)
                    new_total_xp = current_xp + xp_bonus
                    new_level = (new_total_xp // 100) + 1
                    
                    update_data['xp.total_xp'] = new_total_xp
                    update_data['xp.level'] = new_level
                    
                    logger.info(f"XP bonus awarded: {xp_bonus}, new total: {new_total_xp}")
            
            success = self.update_user(user_id, update_data)
            if success:
                logger.info(f"Successfully updated resume status for user {user_id}: {has_resume}, completion: {old_completion}% -> {new_completion}%")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating resume status: {e}")
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