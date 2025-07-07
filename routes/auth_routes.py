# routes/auth_routes.py
from flask import Blueprint, request, jsonify
from config.firebase_config import firebase_config
from models.user_model import UserModel
from utils.validation import Validator
from datetime import datetime
import logging

# Create blueprint
auth_bp = Blueprint('auth', __name__)

# Initialize components
db = firebase_config.get_db()
if db:
    user_model = UserModel(db)
else:
    user_model = None

logger = logging.getLogger(__name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """User registration endpoint"""
    try:
        print("[DEBUG] Registration request received")
        
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
            
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        print(f"[DEBUG] Registration data: {data}")
        
        # Validate input data
        validation_result = Validator.validate_user_registration(data)
        if not validation_result['valid']:
            return jsonify({'error': 'Validation failed', 'details': validation_result['errors']}), 400
        
        email = data['email'].lower().strip()
        password = data['password']
        
        # Check if user already exists
        existing_user = user_model.get_user_by_email(email)
        if existing_user:
            return jsonify({'error': 'User already exists'}), 409
        
        # Create user data
        user_data = {
            'email': email,
            'password': password,
            'name': data.get('name', ''),
            'sso_provider': 'email',
            'is_verified': False,
            'initial_xp': 0
        }
        
        # Create user
        user_id = user_model.create_user(user_data)
        print(f"[DEBUG] Created user with ID: {user_id}")
        
        # Get user data for response
        user = user_model.get_user_by_id(user_id)
        
        logger.info(f"User registered successfully: {email}")
        
        response_data = {
            'message': 'User registered successfully',
            'user_id': user_id,
            'user': {
                'id': user_id,
                'email': email,
                'profile': user.get('profile', {}) if user else {}
            }
        }
        
        print(f"[DEBUG] Registration response: {response_data}")
        return jsonify(response_data), 201
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        print(f"[DEBUG] Registration error: {str(e)}")
        return jsonify({'error': 'Registration failed', 'details': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        print("[DEBUG] Login request received")
        
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
            
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        print(f"[DEBUG] Login data: {data}")
        
        # Validate required fields
        required_fields = ['email', 'password']
        missing_fields = Validator.validate_required_fields(data, required_fields)
        if missing_fields:
            return jsonify({'error': f'Required fields missing: {", ".join(missing_fields)}'}), 400
        
        email = data['email'].lower().strip()
        password = data['password']
        
        # Find user
        user = user_model.get_user_by_email(email)
        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        print(f"[DEBUG] Found user: {user['id']}")
        
        # Check if user uses email authentication
        if user.get('sso_provider') != 'email':
            return jsonify({'error': 'Please use Google Sign-In for this account'}), 400
        
        # Verify password
        from werkzeug.security import check_password_hash
        if not check_password_hash(user.get('password', ''), password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Update last login
        user_model.update_user(user['id'], {'last_login': datetime.utcnow()})
        
        logger.info(f"User logged in: {email}")
        
        response_data = {
            'message': 'Login successful',
            'user_id': user['id'],
            'user': {
                'id': user['id'],
                'email': email,
                'profile': user.get('profile', {})
            }
        }
        
        print(f"[DEBUG] Login response: {response_data}")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        print(f"[DEBUG] Login error: {str(e)}")
        return jsonify({'error': 'Login failed', 'details': str(e)}), 500

@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    """Change user password endpoint"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
            
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        user_id = data.get('user_id')
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not user_id or not current_password or not new_password:
            return jsonify({'error': 'User ID, current password and new password are required'}), 400
        
        # Validate new password
        password_validation = Validator.validate_password(new_password)
        if not password_validation['valid']:
            return jsonify({'error': password_validation['message']}), 400
        
        # Get user
        user = user_model.get_user_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if user uses email authentication
        if user.get('sso_provider') != 'email':
            return jsonify({'error': 'Cannot change password for SSO accounts'}), 400
        
        # Verify current password
        from werkzeug.security import check_password_hash, generate_password_hash
        if not check_password_hash(user.get('password', ''), current_password):
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Update password
        new_password_hash = generate_password_hash(new_password)
        success = user_model.update_user(user_id, {'password': new_password_hash})
        
        if not success:
            return jsonify({'error': 'Failed to update password'}), 500
        
        logger.info(f"Password changed for user: {user_id}")
        
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        logger.error(f"Change password error: {str(e)}")
        return jsonify({'error': 'Failed to change password', 'details': str(e)}), 500