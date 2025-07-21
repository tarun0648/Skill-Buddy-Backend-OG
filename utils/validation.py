# utils/validation.py (UPDATED - No Name Required)
import re
from typing import Dict, Any, List
from flask import jsonify

class ValidationError(Exception):
    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(self.message)

class Validator:
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        if not email:
            return False
        pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        return re.match(pattern, email.lower().strip()) is not None
    
    @staticmethod
    def validate_password(password: str) -> Dict[str, Any]:
        """Validate password strength"""
        if not password:
            return {'valid': False, 'message': 'Password is required'}
        
        if len(password) < 6:
            return {'valid': False, 'message': 'Password must be at least 6 characters long'}
        
        # Optional: Add more password strength requirements
        # if not re.search(r'[A-Z]', password):
        #     return {'valid': False, 'message': 'Password must contain at least one uppercase letter'}
        
        # if not re.search(r'[a-z]', password):
        #     return {'valid': False, 'message': 'Password must contain at least one lowercase letter'}
        
        # if not re.search(r'\d', password):
        #     return {'valid': False, 'message': 'Password must contain at least one number'}
        
        return {'valid': True, 'message': 'Password is valid'}
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> List[str]:
        """Validate that required fields are present"""
        missing_fields = []
        for field in required_fields:
            if field not in data or not data[field] or (isinstance(data[field], str) and not data[field].strip()):
                missing_fields.append(field)
        return missing_fields
    
    @staticmethod
    def validate_user_registration(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate user registration data - UPDATED: Name is optional"""
        errors = {}
        
        # Only email and password are required now
        required_fields = ['email', 'password']
        missing_fields = Validator.validate_required_fields(data, required_fields)
        
        if missing_fields:
            errors['missing_fields'] = f"Required fields missing: {', '.join(missing_fields)}"
        
        email = data.get('email', '').lower().strip()
        if email and not Validator.validate_email(email):
            errors['email'] = 'Invalid email format'
        
        password = data.get('password', '')
        if password:
            password_validation = Validator.validate_password(password)
            if not password_validation['valid']:
                errors['password'] = password_validation['message']
        
        # Name is optional - no validation needed
        # Just check if it's reasonable length if provided
        name = data.get('name', '')
        if name and len(name.strip()) > 100:
            errors['name'] = 'Name must be less than 100 characters'
        
        return {'valid': len(errors) == 0, 'errors': errors}
    
    @staticmethod
    def validate_profile_update(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate profile update data"""
        errors = {}
        
        # Name validation - optional
        name = data.get('name', '')
        if name and len(name.strip()) > 100:
            errors['name'] = 'Name must be less than 100 characters'
        
        # Email validation - if provided
        email = data.get('college_email', '')
        if email and not Validator.validate_email(email):
            errors['college_email'] = 'Invalid email format'
        
        # Profession validation - if provided
        profession = data.get('profession', '')
        if profession:
            valid_professions = ['Student', 'Graduate', 'Post Graduate', 'Professional', 'Switch Career']
            if profession not in valid_professions:
                errors['profession'] = f'Profession must be one of: {", ".join(valid_professions)}'
        
        # Career choices validation - if provided
        career_choices = data.get('career_choices', [])
        if career_choices:
            if not isinstance(career_choices, list):
                errors['career_choices'] = 'Career choices must be a list'
            elif len(career_choices) > 3:
                errors['career_choices'] = 'Maximum 3 career choices allowed'
        
        # URL validation for links - if provided
        github_link = data.get('github_link', '')
        if github_link and not github_link.strip():
            # Allow empty strings
            pass
        elif github_link and not (github_link.startswith('http://') or github_link.startswith('https://') or github_link.startswith('github.com')):
            errors['github_link'] = 'Invalid GitHub URL format'
        
        linkedin_link = data.get('linkedin_link', '')
        if linkedin_link and not linkedin_link.strip():
            # Allow empty strings
            pass
        elif linkedin_link and not (linkedin_link.startswith('http://') or linkedin_link.startswith('https://') or 'linkedin.com' in linkedin_link):
            errors['linkedin_link'] = 'Invalid LinkedIn URL format'
        
        return {'valid': len(errors) == 0, 'errors': errors}
    
    @staticmethod
    def validate_name_optional(name: str) -> Dict[str, Any]:
        """Validate name field - optional but with constraints if provided"""
        if not name or not name.strip():
            return {'valid': True, 'message': 'Name is optional'}
        
        name = name.strip()
        
        if len(name) < 2:
            return {'valid': False, 'message': 'Name must be at least 2 characters if provided'}
        
        if len(name) > 100:
            return {'valid': False, 'message': 'Name must be less than 100 characters'}
        
        # Check for reasonable characters (letters, spaces, hyphens, apostrophes)
        if not re.match(r"^[a-zA-Z\s\-'\.]+$", name):
            return {'valid': False, 'message': 'Name contains invalid characters'}
        
        return {'valid': True, 'message': 'Name is valid'}
    
    @staticmethod
    def create_validation_response(errors: Dict[str, str]) -> tuple:
        """Create a standardized validation error response"""
        return jsonify({'error': 'Validation failed', 'details': errors}), 400