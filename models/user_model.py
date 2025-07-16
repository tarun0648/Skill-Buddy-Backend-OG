# models/user_model.py (UPDATED with Phone Number Support)
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
from firebase_admin import firestore

logger = logging.getLogger(__name__)

class UserModel:
    """User data model for Firestore operations with phone support"""
    
    def __init__(self, db):
        self.db = db
        self.collection_name = 'users'
    
    def create_user(self, user_data: Dict[str, Any]) -> str:
        """Create a new user in Firestore with phone or email"""
        try:
            from werkzeug.security import generate_password_hash
            
            # Determine authentication method
            is_phone_auth = 'phone' in user_data
            is_email_auth = 'email' in user_data
            
            user_doc = {
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
                },
                # Password reset fields
                'password_reset_token': None,
                'password_reset_expires': None,
                'password_reset_requested_at': None,
                'password_changed_at': None
            }
            
            # Add email if provided
            if is_email_auth and user_data.get('email'):
                user_doc['email'] = user_data['email'].lower().strip()
            
            # Add phone if provided
            if is_phone_auth and user_data.get('phone'):
                user_doc['phone'] = user_data['phone']
                # Also add to profile for easy access
                user_doc['profile']['phone'] = user_data['phone']
            
            # Add password hash if provided (for email authentication)
            if 'password' in user_data:
                user_doc['password'] = generate_password_hash(user_data['password'])
            
            # Add Google ID if provided
            if 'google_id' in user_data:
                user_doc['google_id'] = user_data['google_id']
            
            # Add user to Firestore
            doc_ref = self.db.collection(self.collection_name).add(user_doc)
            user_id = doc_ref[1].id
            
            logger.info(f"Created user: {user_id} with auth method: {user_data.get('sso_provider')}")
            return user_id
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise Exception(f"Failed to create user: {str(e)}")
    
    def get_user_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Get user by phone number"""
        try:
            query = self.db.collection(self.collection_name).where('phone', '==', phone).limit(1)
            docs = query.get()
            
            if docs:
                doc = docs[0]
                user_data = doc.to_dict()
                user_data['id'] = doc.id
                
                # Convert Firebase timestamps
                timestamp_fields = ['created_at', 'last_login', 'password_reset_expires', 'password_reset_requested_at', 'password_changed_at']
                for field in timestamp_fields:
                    if user_data.get(field):
                        if hasattr(user_data[field], 'isoformat'):
                            user_data[field] = user_data[field].isoformat()
                        else:
                            user_data[field] = str(user_data[field])
                
                return user_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by phone: {e}")
            return None
    
    def get_user_by_reset_token(self, hashed_token: str) -> Optional[Dict[str, Any]]:
        """Get user by password reset token"""
        try:
            # Query users collection for the reset token
            query = self.db.collection(self.collection_name).where('password_reset_token', '==', hashed_token).limit(1)
            docs = query.get()
            
            if docs:
                doc = docs[0]
                user_data = doc.to_dict()
                user_data['id'] = doc.id
                
                # Convert Firebase timestamps
                timestamp_fields = ['created_at', 'last_login', 'password_reset_expires', 'password_reset_requested_at', 'password_changed_at']
                for field in timestamp_fields:
                    if user_data.get(field):
                        if hasattr(user_data[field], 'isoformat'):
                            user_data[field] = user_data[field].isoformat()
                        else:
                            user_data[field] = str(user_data[field])
                
                return user_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by reset token: {e}")
            return None
    
    def calculate_profile_completion(self, profile: Dict[str, Any]) -> int:
        """Calculate profile completion percentage based on new requirements - FIXED"""
        completion = 0
        
        # Debug logging
        logger.debug(f"Calculating completion for profile: {profile}")
        
        # Basic profile steps (55% total)
        if profile.get('name') and str(profile.get('name')).strip():
            completion += 10  # 10%
            logger.debug("Added 10% for name")
        
        if profile.get('profession') and str(profile.get('profession')).strip():
            completion += 10  # 10%
            logger.debug("Added 10% for profession")
        
        career_choices = profile.get('career_choices', [])
        if career_choices and isinstance(career_choices, list) and len(career_choices) > 0:
            # Check if any choice is not empty
            valid_choices = [choice for choice in career_choices if choice and str(choice).strip()]
            if valid_choices:
                completion += 10  # 10%
                logger.debug("Added 10% for career choices")
        
        if profile.get('college_name') and str(profile.get('college_name')).strip():
            completion += 10  # 10%
            logger.debug("Added 10% for college name")
        
        if profile.get('college_email') and str(profile.get('college_email')).strip():
            completion += 15  # 15% (Total basic: 55%)
            logger.debug("Added 15% for college email")
        
        # Additional profile elements (45% total)
        github_link = profile.get('github_link', '')
        if github_link and str(github_link).strip() and str(github_link).strip() != '':
            completion += 15  # 15%
            logger.debug(f"Added 15% for GitHub link: {github_link}")
        
        linkedin_link = profile.get('linkedin_link', '')
        if linkedin_link and str(linkedin_link).strip() and str(linkedin_link).strip() != '':
            completion += 15  # 15%
            logger.debug(f"Added 15% for LinkedIn link: {linkedin_link}")
        
        if profile.get('has_resume') is True:
            completion += 15  # 15%
            logger.debug("Added 15% for resume")
        
        final_completion = min(completion, 100)
        logger.debug(f"Final completion percentage: {final_completion}")
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
                timestamp_fields = ['created_at', 'last_login', 'password_reset_expires', 'password_reset_requested_at', 'password_changed_at']
                for field in timestamp_fields:
                    if user_data.get(field):
                        if hasattr(user_data[field], 'isoformat'):
                            user_data[field] = user_data[field].isoformat()
                        else:
                            user_data[field] = str(user_data[field])
                    
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
                timestamp_fields = ['created_at', 'last_login', 'password_reset_expires', 'password_reset_requested_at', 'password_changed_at']
                for field in timestamp_fields:
                    if user_data.get(field):
                        if hasattr(user_data[field], 'isoformat'):
                            user_data[field] = user_data[field].isoformat()
                        else:
                            user_data[field] = str(user_data[field])
                    
                return user_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    def get_user_by_identifier(self, identifier: str, identifier_type: str = 'auto') -> Optional[Dict[str, Any]]:
        """Get user by email or phone number (auto-detect or specify type)"""
        try:
            if identifier_type == 'auto':
                # Auto-detect based on format
                if '@' in identifier:
                    return self.get_user_by_email(identifier)
                elif any(char.isdigit() for char in identifier):
                    return self.get_user_by_phone(identifier)
                else:
                    return None
            elif identifier_type == 'email':
                return self.get_user_by_email(identifier)
            elif identifier_type == 'phone':
                return self.get_user_by_phone(identifier)
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting user by identifier: {e}")
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
    
    def update_user_phone(self, user_id: str, phone: str) -> bool:
        """Update user's phone number"""
        try:
            update_data = {
                'phone': phone,
                'profile.phone': phone,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            return self.update_user(user_id, update_data)
            
        except Exception as e:
            logger.error(f"Error updating user phone: {e}")
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
                    
                    # Send milestone email if major milestone reached
                    try:
                        from services.email_service import email_service
                        user_profile = user.get('profile', {})
                        user_name = user_profile.get('name', 'User')
                        user_email = user.get('email', '')
                        
                        # Send email for significant milestones (55%, 85%, 100%)
                        significant_milestones = [milestone for milestone in milestones if milestone in [55, 85, 100]]
                        if significant_milestones and email_service.enabled and user_email:
                            for milestone in significant_milestones:
                                milestone_xp = self.calculate_xp_bonus([milestone])
                                email_service.send_profile_completion_milestone_email(
                                    user_email, user_name, milestone, milestone_xp
                                )
                                logger.info(f"Milestone email sent for {milestone}% completion")
                    except Exception as e:
                        logger.error(f"Error sending milestone email: {e}")
            
            success = self.update_user(user_id, update_data)
            if success:
                logger.info(f"Successfully updated resume status for user {user_id}: {has_resume}, completion: {old_completion}% -> {new_completion}%")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating resume status: {e}")
            return False
    
    def update_profile_with_milestone_email(self, user_id: str, update_data: Dict[str, Any], old_completion: int) -> bool:
        """Update user profile and send milestone emails when appropriate"""
        try:
            # Update the user
            success = self.update_user(user_id, update_data)
            if not success:
                return False
            
            # Check for milestone emails
            new_completion = update_data.get('profile.completion_status')
            if new_completion and old_completion != new_completion:
                milestones = self.get_completion_milestones(old_completion, new_completion)
                
                # Send email for significant milestones
                significant_milestones = [m for m in milestones if m in [55, 85, 100]]
                if significant_milestones:
                    try:
                        from services.email_service import email_service
                        user = self.get_user_by_id(user_id)
                        if user and email_service.enabled:
                            user_profile = user.get('profile', {})
                            user_name = user_profile.get('name', 'User')
                            user_email = user.get('email', '')
                            
                            if user_email:
                                for milestone in significant_milestones:
                                    milestone_xp = self.calculate_xp_bonus([milestone])
                                    email_service.send_profile_completion_milestone_email(
                                        user_email, user_name, milestone, milestone_xp
                                    )
                                    logger.info(f"Milestone email sent for {milestone}% completion")
                    except Exception as e:
                        logger.error(f"Error sending milestone email: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating profile with milestone email: {e}")
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
    
    def verify_user_phone(self, user_id: str) -> bool:
        """Mark user's phone as verified"""
        try:
            update_data = {
                'is_verified': True,
                'phone_verified_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            return self.update_user(user_id, update_data)
            
        except Exception as e:
            logger.error(f"Error verifying user phone: {e}")
            return False
    
    def get_user_statistics(self) -> Dict[str, Any]:
        """Get user statistics"""
        try:
            total_users = len(self.db.collection(self.collection_name).where('is_active', '==', True).get())
            
            # Get users by authentication method
            email_users = len(self.db.collection(self.collection_name)
                             .where('is_active', '==', True)
                             .where('sso_provider', '==', 'email').get())
            
            phone_users = len(self.db.collection(self.collection_name)
                             .where('is_active', '==', True)
                             .where('sso_provider', '==', 'phone').get())
            
            google_users = len(self.db.collection(self.collection_name)
                              .where('is_active', '==', True)
                              .where('sso_provider', '==', 'google').get())
            
            return {
                'total_users': total_users,
                'active_users': total_users,
                'email_users': email_users,
                'phone_users': phone_users,
                'google_users': google_users,
                'verified_users': len(self.db.collection(self.collection_name)
                                     .where('is_active', '==', True)
                                     .where('is_verified', '==', True).get())
            }
        except Exception as e:
            logger.error(f"Error getting user statistics: {e}")
            return {
                'total_users': 0, 
                'active_users': 0,
                'email_users': 0,
                'phone_users': 0,
                'google_users': 0,
                'verified_users': 0
            }