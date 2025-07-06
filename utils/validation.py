# utils/validation.py
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
        """Validate user registration data"""
        errors = {}
        
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
        
        return {'valid': len(errors) == 0, 'errors': errors}
    
    @staticmethod
    def validate_profile_update(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate profile update data"""
        # For now, just return valid
        return {'valid': True, 'errors': {}}
    
    @staticmethod
    def create_validation_response(errors: Dict[str, str]) -> tuple:
        """Create a standardized validation error response"""
        return jsonify({'error': 'Validation failed', 'details': errors}), 400