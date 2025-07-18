# utils/auth_utils.py
import jwt
import datetime
from functools import wraps
from flask import request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash

class AuthUtils:
    
    @staticmethod
    def generate_tokens(user_id, secret_key=None, algorithm='HS256'):
        """Generate access and refresh tokens"""
        if not secret_key:
            secret_key = 'your-jwt-secret-key'
        
        now = datetime.datetime.now(datetime.timezone.utc)
        
        access_payload = {
            'user_id': user_id,
            'exp': now + datetime.timedelta(hours=24),
            'iat': now,
            'type': 'access'
        }
        
        refresh_payload = {
            'user_id': user_id,
            'exp': now + datetime.timedelta(days=7),
            'iat': now,
            'type': 'refresh'
        }
        
        access_token = jwt.encode(access_payload, secret_key, algorithm=algorithm)
        refresh_token = jwt.encode(refresh_payload, secret_key, algorithm=algorithm)
        
        return access_token, refresh_token
    
    @staticmethod
    def verify_token(token, secret_key=None, algorithm='HS256'):
        """Verify JWT token"""
        try:
            if not secret_key:
                secret_key = 'your-jwt-secret-key'
            
            payload = jwt.decode(token, secret_key, algorithms=[algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return {'error': 'Token has expired'}
        except jwt.InvalidTokenError:
            return {'error': 'Invalid token'}
        except Exception as e:
            return {'error': f'Token verification failed: {str(e)}'}
    
    @staticmethod
    def hash_password(password):
        """Hash a password"""
        return generate_password_hash(password)
    
    @staticmethod
    def check_password(password_hash, password):
        """Check password against hash"""
        return check_password_hash(password_hash, password)

def auth_required(f):
    """Decorator to require authentication - FIXED VERSION"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Get Authorization header
        auth_header = request.headers.get('Authorization')
        print(f"[DEBUG] Auth header received: {auth_header}")  # Debug log
        
        if not auth_header:
            print("[DEBUG] No Authorization header found")
            return jsonify({'error': 'No token provided'}), 401
        
        # Extract token
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]  # Remove 'Bearer ' prefix
            print(f"[DEBUG] Extracted token: {token[:20]}...")  # Debug log (first 20 chars)
        else:
            print("[DEBUG] Authorization header doesn't start with 'Bearer '")
            return jsonify({'error': 'Invalid token format'}), 401
        
        # Verify token
        payload = AuthUtils.verify_token(token)
        print(f"[DEBUG] Token verification result: {payload}")  # Debug log
        
        if 'error' in payload:
            print(f"[DEBUG] Token verification failed: {payload['error']}")
            return jsonify({'error': payload['error']}), 401
        
        if payload.get('type') != 'access':
            print(f"[DEBUG] Invalid token type: {payload.get('type')}")
            return jsonify({'error': 'Invalid token type'}), 401
        
        # Set user_id on request
        request.user_id = payload['user_id']
        print(f"[DEBUG] Authentication successful for user: {payload['user_id']}")
        
        return f(*args, **kwargs)
    
    return decorated