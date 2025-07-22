"""
Authentication Utilities - Helper functions for user authentication
"""

import jwt
import logging
from functools import wraps
from datetime import datetime, timedelta
from flask import request, jsonify, current_app, g
from firebase_admin import auth as firebase_auth
from config.settings import Config

logger = logging.getLogger(__name__)

def require_auth(f):
    """Decorator to require authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for user ID in headers (existing system compatibility)
        user_id = request.headers.get('X-User-ID')
        
        # Check for Authorization header (JWT token)
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            user_data = verify_jwt_token(token)
            if user_data:
                request.user_id = user_data.get('user_id')
                request.user_email = user_data.get('email')
                request.user_data = user_data
                return f(*args, **kwargs)
        
        # Check for Firebase ID token
        if auth_header and auth_header.startswith('Firebase '):
            firebase_token = auth_header.split(' ')[1]
            user_data = verify_firebase_token(firebase_token)
            if user_data:
                request.user_id = user_data.get('uid')
                request.user_email = user_data.get('email')
                request.user_data = user_data
                return f(*args, **kwargs)
        
        # Fallback to X-User-ID header (for backward compatibility)
        if user_id:
            request.user_id = user_id
            request.user_email = None
            request.user_data = {'user_id': user_id}
            return f(*args, **kwargs)
        
        return jsonify({
            'success': False,
            'error': 'Authentication required',
            'message': 'Please provide valid authentication credentials'
        }), 401
    
    return decorated_function

def optional_auth(f):
    """Decorator for optional authentication (sets user data if available)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        request.user_id = None
        request.user_email = None
        request.user_data = None
        
        # Try to authenticate but don't fail if not provided
        user_id = request.headers.get('X-User-ID')
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            user_data = verify_jwt_token(token)
            if user_data:
                request.user_id = user_data.get('user_id')
                request.user_email = user_data.get('email')
                request.user_data = user_data
        
        elif auth_header and auth_header.startswith('Firebase '):
            firebase_token = auth_header.split(' ')[1]
            user_data = verify_firebase_token(firebase_token)
            if user_data:
                request.user_id = user_data.get('uid')
                request.user_email = user_data.get('email')
                request.user_data = user_data
        
        elif user_id:
            request.user_id = user_id
            request.user_data = {'user_id': user_id}
        
        return f(*args, **kwargs)
    
    return decorated_function

def verify_jwt_token(token):
    """Verify JWT token and return user data"""
    try:
        payload = jwt.decode(
            token, 
            current_app.config['JWT_SECRET_KEY'], 
            algorithms=['HS256']
        )
        
        # Check if token is expired
        if 'exp' in payload and datetime.utcfromtimestamp(payload['exp']) < datetime.utcnow():
            logger.warning("JWT token expired")
            return None
        
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None
    except Exception as e:
        logger.error(f"JWT verification error: {e}")
        return None

def verify_firebase_token(id_token):
    """Verify Firebase ID token and return user data"""
    try:
        decoded_token = firebase_auth.verify_id_token(id_token)
        return {
            'uid': decoded_token['uid'],
            'email': decoded_token.get('email'),
            'name': decoded_token.get('name'),
            'picture': decoded_token.get('picture'),
            'email_verified': decoded_token.get('email_verified', False)
        }
    except Exception as e:
        logger.warning(f"Firebase token verification failed: {e}")
        return None

def generate_jwt_token(user_data):
    """Generate JWT token for user"""
    try:
        payload = {
            'user_id': user_data.get('user_id') or user_data.get('uid'),
            'email': user_data.get('email'),
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=current_app.config['JWT_EXPIRATION_HOURS'])
        }
        
        token = jwt.encode(
            payload,
            current_app.config['JWT_SECRET_KEY'],
            algorithm='HS256'
        )
        
        return token
        
    except Exception as e:
        logger.error(f"JWT generation error: {e}")
        return None

def get_current_user():
    """Get current authenticated user from request context"""
    return getattr(request, 'user_data', None)

def get_current_user_id():
    """Get current authenticated user ID from request context"""
    return getattr(request, 'user_id', None)

def is_authenticated():
    """Check if current request is authenticated"""
    return getattr(request, 'user_id', None) is not None

def require_admin(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
        
        user_data = get_current_user()
        if not user_data or not user_data.get('is_admin', False):
            return jsonify({
                'success': False,
                'error': 'Admin privileges required'
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_role(role):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not is_authenticated():
                return jsonify({
                    'success': False,
                    'error': 'Authentication required'
                }), 401
            
            user_data = get_current_user()
            user_roles = user_data.get('roles', []) if user_data else []
            
            if role not in user_roles and not user_data.get('is_admin', False):
                return jsonify({
                    'success': False,
                    'error': f'Role "{role}" required'
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def validate_password_strength(password):
    """Validate password strength"""
    errors = []
    
    if len(password) < current_app.config.get('PASSWORD_MIN_LENGTH', 8):
        errors.append(f"Password must be at least {current_app.config.get('PASSWORD_MIN_LENGTH', 8)} characters long")
    
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    
    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one number")
    
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Password must contain at least one special character")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }

def rate_limit_key(identifier=None):
    """Generate rate limit key for user"""
    if identifier:
        return f"rate_limit:{identifier}"
    
    user_id = get_current_user_id()
    if user_id:
        return f"rate_limit:user:{user_id}"
    
    # Fallback to IP address
    return f"rate_limit:ip:{request.remote_addr}"

def check_rate_limit(limit_per_hour=None, limit_per_day=None):
    """Check if user has exceeded rate limits"""
    if not current_app.config.get('RATE_LIMIT_ENABLED', True):
        return True
    
    # This would typically use Redis or another cache
    # For now, returning True (no rate limiting)
    # In production, implement with Redis/Memcached
    return True

def create_session_data(user_data):
    """Create session data for user"""
    return {
        'user_id': user_data.get('user_id') or user_data.get('uid'),
        'email': user_data.get('email'),
        'name': user_data.get('name'),
        'login_time': datetime.utcnow().isoformat(),
        'is_admin': user_data.get('is_admin', False),
        'roles': user_data.get('roles', [])
    }

def clear_session():
    """Clear user session"""
    for key in ['user_id', 'user_email', 'user_data']:
        if hasattr(request, key):
            delattr(request, key)

# Security helpers
def sanitize_user_data(data):
    """Sanitize user data before sending to client"""
    sensitive_fields = ['password', 'password_hash', 'salt', 'private_key', 'secret']
    
    if isinstance(data, dict):
        return {k: v for k, v in data.items() if k not in sensitive_fields}
    elif isinstance(data, list):
        return [sanitize_user_data(item) for item in data]
    else:
        return data

def log_auth_event(event_type, user_id=None, details=None):
    """Log authentication events for security monitoring"""
    log_data = {
        'event_type': event_type,
        'user_id': user_id or get_current_user_id(),
        'ip_address': request.remote_addr,
        'user_agent': request.headers.get('User-Agent'),
        'timestamp': datetime.utcnow().isoformat(),
        'details': details or {}
    }
    
    # In production, send to security monitoring system
    logger.info(f"Auth event: {event_type} for user {log_data['user_id']}")
    
    return log_data