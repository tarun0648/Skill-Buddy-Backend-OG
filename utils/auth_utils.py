# utils/auth_utils.py
import jwt
import datetime
from functools import wraps
from flask import request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
import logging

# Import cache service
from services.redis_cache_service import cache, CacheKeys, CacheTTL

logger = logging.getLogger(__name__)
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
    """Decorator to require user ID authentication with caching"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return jsonify({'error': 'User ID required in X-User-ID header'}), 401
        
        # Check cache first for user validation
        cache_key = cache.generate_cache_key(CacheKeys.USER_PROFILE, user_id, 'validation')
        cached_validation = cache.get(cache_key)
        
        if cached_validation is None:
            # Verify user exists in database
            from app import db  # Import db from app
            if db:
                try:
                    doc_ref = db.collection('users').document(user_id)
                    doc = doc_ref.get()
                    if not doc.exists:
                        return jsonify({'error': 'Invalid user ID'}), 401
                    
                    # Cache the validation result
                    cache.set(cache_key, {'valid': True}, CacheTTL.MEDIUM)
                    
                except Exception as e:
                    return jsonify({'error': 'User verification failed'}), 401
        
        request.user_id = user_id
        return f(*args, **kwargs)
    
    return decorated