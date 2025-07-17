# app.py - Updated with Redis Cache Integration
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import firebase_admin
from firebase_admin import credentials, auth, firestore
from functools import wraps
import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash
import re
import logging

# Import Redis cache service
from services.redis_cache_service import cache, CacheKeys, CacheTTL

# Create required directories first
os.makedirs('logs', exist_ok=True)
os.makedirs('uploads', exist_ok=True)
os.makedirs('uploads/resumes', exist_ok=True)
os.makedirs('config', exist_ok=True)
os.makedirs('models', exist_ok=True)
os.makedirs('routes', exist_ok=True)
os.makedirs('utils', exist_ok=True)
os.makedirs('services', exist_ok=True)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# CORS configuration
CORS(app, origins=[
    "http://localhost:3000",
    "http://localhost:8081", 
    "http://172.20.10.7:8081",
    "exp://192.168.1.100:8081"
])

# Rate limiting with Redis backend
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["20000 per day", "5000 per hour"],
    storage_uri=os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
)

# Initialize Firebase Admin SDK
try:
    if os.path.exists('serviceAccountKey.json'):
        cred = credentials.Certificate('serviceAccountKey.json')
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("Firebase initialized successfully")
    else:
        print("Warning: serviceAccountKey.json not found. Some features may not work.")
        db = None
except Exception as e:
    print(f"Firebase initialization error: {e}")
    db = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Log Redis cache status
cache_info = cache.get_cache_info()
logger.info(f"Redis cache status: {cache_info}")

# Utility Functions
def validate_email(email):
    pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    return re.match(pattern, email) is not None

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

# Import and register blueprints
try:
    from routes.auth_routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    print("✓ Auth routes loaded (with Phone OTP support)")
except ImportError as e:
    print(f"✗ Auth routes failed: {e}")
    auth_bp = None

try:
    from routes.user_routes import user_bp, init_user_routes
    app.register_blueprint(user_bp, url_prefix='/api/user')
    print("✓ User routes loaded (with Redis caching)")
except ImportError as e:
    print(f"✗ User routes failed: {e}")
    user_bp = None

try:
    from routes.resume_routes import resume_bp, init_resume_routes
    app.register_blueprint(resume_bp, url_prefix='/api/resume')
    print("✓ Resume routes loaded (with Redis caching)")
except ImportError as e:
    print(f"✗ Resume routes failed: {e}")
    resume_bp = None

try:
    from routes.profile_analysis_routes import profile_analysis_bp, init_profile_analysis_routes
    app.register_blueprint(profile_analysis_bp, url_prefix='/api/profile-analysis')
    print("✓ Profile analysis routes loaded (with Redis caching)")
except ImportError as e:
    print(f"✗ Profile analysis routes failed: {e}")
    profile_analysis_bp = None

try:
    from routes.portfolio_analysis_routes import portfolio_analysis_bp, init_portfolio_analysis_routes
    app.register_blueprint(portfolio_analysis_bp, url_prefix='/api/portfolio-analysis')
    print("✓ Portfolio analysis routes loaded (with Redis caching)")
except ImportError as e:
    print(f"✗ Portfolio analysis routes failed: {e}")
    portfolio_analysis_bp = None

try:
    from routes.community_routes import community_bp, init_community_routes
    app.register_blueprint(community_bp, url_prefix='/api/community')
    print("✓ Community platform routes loaded (with Redis caching)")
except ImportError as e:
    print(f"✗ Community routes failed: {e}")
    community_bp = None

# Initialize models and services
try:
    from models.user_model import UserModel
    from models.resume_model import ResumeModel
    from models.profile_analysis_model import ProfileAnalysisModel
    from models.portfolio_analysis_model import PortfolioAnalysisModel
    from models.community_model import CommunityModel
    from services.email_service import EmailService
    
    # Initialize models
    user_model = UserModel(db) if db else None
    resume_model = ResumeModel(db) if db else None
    profile_analysis_model = ProfileAnalysisModel(db) if db else None
    portfolio_analysis_model = PortfolioAnalysisModel(db) if db else None
    community_model = CommunityModel(db) if db else None
    email_service = EmailService()
    
    # Initialize route handlers with models
    if user_bp and user_model:
        init_user_routes(user_model, db, email_service)
    
    if resume_bp and resume_model:
        init_resume_routes(resume_model, user_model, db, email_service)
    
    if profile_analysis_bp and profile_analysis_model:
        init_profile_analysis_routes(profile_analysis_model, user_model, db, email_service)
    
    if portfolio_analysis_bp and portfolio_analysis_model:
        init_portfolio_analysis_routes(portfolio_analysis_model, user_model, db, email_service)
    
    if community_bp and community_model:
        init_community_routes(community_model, user_model, db)
    
    print("✓ Models and services initialized with Redis caching")
    
except Exception as e:
    print(f"✗ Models initialization failed: {e}")
    user_model = None
    resume_model = None
    profile_analysis_model = None
    portfolio_analysis_model = None
    community_model = None
    email_service = None

# Global rate limiting
@app.before_request
def before_request():
    """Global rate limiting and cache warming"""
    # Skip rate limiting for health check
    if request.endpoint == 'health_check':
        return
    
    # Log request for monitoring
    logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")

# Health check endpoint with cache status
@app.route('/api/status', methods=['GET'])
def health_check():
    """Enhanced health check with cache status"""
    try:
        status = {
            'status': 'healthy',
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'services': {}
        }
        
        # Check Firebase
        if db:
            try:
                # Test Firebase connection
                test_doc = db.collection('health_check').document('test')
                test_doc.set({'timestamp': datetime.datetime.utcnow()})
                test_doc.delete()
                status['services']['firebase'] = 'healthy'
            except Exception as e:
                status['services']['firebase'] = f'error: {str(e)}'
        else:
            status['services']['firebase'] = 'not configured'
        
        # Check Redis cache
        cache_info = cache.get_cache_info()
        status['services']['redis'] = cache_info
        
        # Check email service
        try:
            email_status = email_service.get_service_status() if email_service else {'enabled': False}
            status['services']['email'] = email_status
        except Exception as e:
            status['services']['email'] = {'enabled': False, 'error': str(e)}
        
        # Check OTP service
        try:
            from services.otp_service import OTPService
            otp_service = OTPService()
            otp_debug = otp_service.get_debug_info()
            status['services']['otp'] = {
                'sms_enabled': otp_debug['sms_enabled'],
                'whatsapp_enabled': otp_debug['whatsapp_enabled'],
                'twilio_configured': otp_debug['twilio_configured'],
                'msg91_configured': otp_debug['msg91_configured']
            }
        except Exception as e:
            status['services']['otp'] = {'enabled': False, 'error': str(e)}
        
        # Try to get statistics if available
        if resume_bp and db:
            try:
                user_stats = user_model.get_user_statistics() if user_model else {}
                resume_stats = resume_model.get_processing_statistics() if resume_model else {}
                
                status.update({
                    'user_statistics': user_stats,
                    'resume_statistics': resume_stats
                })
            except Exception as e:
                status['statistics_error'] = str(e)
        
        # Try to get profile analysis statistics
        if profile_analysis_bp and db:
            try:
                analysis_stats = profile_analysis_model.get_analysis_statistics() if profile_analysis_model else {}
                status['profile_analysis_statistics'] = analysis_stats
            except Exception as e:
                status['profile_analysis_error'] = str(e)
        
        # Try to get portfolio analysis statistics
        if portfolio_analysis_bp and db:
            try:
                portfolio_stats = portfolio_analysis_model.get_analysis_statistics() if portfolio_analysis_model else {}
                status['portfolio_analysis_statistics'] = portfolio_stats
            except Exception as e:
                status['portfolio_analysis_error'] = str(e)
        
        # Try to get community statistics
        if community_bp and db:
            try:
                community_stats = community_model.get_community_statistics() if community_model else {}
                status['community_statistics'] = community_stats
            except Exception as e:
                status['community_error'] = str(e)
        
        return jsonify(status), 200
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.datetime.utcnow().isoformat()
        }), 500

# Cache management endpoints
@app.route('/api/cache/status', methods=['GET'])
@auth_required
def get_cache_status():
    """Get comprehensive cache status"""
    try:
        user_id = request.user_id
        
        # Get cache info
        cache_info = cache.get_cache_info()
        
        # Get user-specific cache status
        user_cache_patterns = [
            f"{CacheKeys.USER_PROFILE}:{user_id}*",
            f"{CacheKeys.USER_RESUMES}:{user_id}*",
            f"{CacheKeys.RESUME_ANALYSIS}:{user_id}*",
            f"{CacheKeys.PROFILE_ANALYSIS}:{user_id}*",
            f"{CacheKeys.PORTFOLIO_ANALYSIS}:{user_id}*"
        ]
        
        user_cache_count = 0
        for pattern in user_cache_patterns:
            keys = cache.get_keys_by_pattern(pattern)
            user_cache_count += len(keys)
        
        # Get global cache patterns
        global_cache_patterns = [
            f"{CacheKeys.COMMUNITY_POSTS}:*",
            f"{CacheKeys.COMMUNITY_STATS}:*",
            f"{CacheKeys.SYSTEM_STATS}:*"
        ]
        
        global_cache_count = 0
        for pattern in global_cache_patterns:
            keys = cache.get_keys_by_pattern(pattern)
            global_cache_count += len(keys)
        
        return jsonify({
            'cache_info': cache_info,
            'user_cache_entries': user_cache_count,
            'global_cache_entries': global_cache_count,
            'total_cache_entries': user_cache_count + global_cache_count,
            'user_id': user_id
        }), 200
        
    except Exception as e:
        logger.error(f"Get cache status error: {str(e)}")
        return jsonify({'error': 'Failed to get cache status', 'details': str(e)}), 500

@app.route('/api/cache/clear-all', methods=['POST'])
@auth_required
def clear_all_cache():
    """Clear all cache entries (admin only)"""
    try:
        user_id = request.user_id
        
        # You might want to add admin check here
        # For now, users can only clear their own cache
        
        # Clear all user-specific caches
        user_cache_patterns = [
            f"{CacheKeys.USER_PROFILE}:{user_id}*",
            f"{CacheKeys.USER_RESUMES}:{user_id}*",
            f"{CacheKeys.USER_STATS}:{user_id}*",
            f"{CacheKeys.USER_SETTINGS}:{user_id}*",
            f"{CacheKeys.RESUME_ANALYSIS}:{user_id}*",
            f"{CacheKeys.PROFILE_ANALYSIS}:{user_id}*",
            f"{CacheKeys.PORTFOLIO_ANALYSIS}:{user_id}*"
        ]
        
        total_deleted = 0
        for pattern in user_cache_patterns:
            deleted = cache.delete_pattern(pattern)
            total_deleted += deleted
        
        logger.info(f"Cleared {total_deleted} cache entries for user: {user_id}")
        
        return jsonify({
            'message': 'User cache cleared successfully',
            'entries_deleted': total_deleted
        }), 200
        
    except Exception as e:
        logger.error(f"Clear all cache error: {str(e)}")
        return jsonify({'error': 'Failed to clear cache', 'details': str(e)}), 500

@app.route('/api/cache/warm-up', methods=['POST'])
@auth_required
def warm_up_cache():
    """Warm up cache for the authenticated user"""
    try:
        user_id = request.user_id
        
        warmed_caches = []
        
        # Warm up user profile
        if user_model:
            try:
                user_data = user_model.get_user_by_id(user_id)
                if user_data:
                    profile_cache_key = cache.generate_cache_key(CacheKeys.USER_PROFILE, user_id)
                    cache.set(profile_cache_key, user_data, CacheTTL.USER_PROFILE)
                    warmed_caches.append('user_profile')
            except Exception as e:
                logger.warning(f"Failed to warm up user profile cache: {e}")
        
        # Warm up user stats
        if user_model:
            try:
                stats = user_model.get_user_statistics(user_id)
                stats_cache_key = cache.generate_cache_key(CacheKeys.USER_STATS, user_id)
                cache.set(stats_cache_key, stats, CacheTTL.USER_STATS)
                warmed_caches.append('user_stats')
            except Exception as e:
                logger.warning(f"Failed to warm up user stats cache: {e}")
        
        # Warm up recent resumes
        if resume_model:
            try:
                resumes = resume_model.get_user_resume_summary(user_id)
                if resumes:
                    resumes_cache_key = cache.generate_cache_key(CacheKeys.USER_RESUMES, user_id, 'details:false', 'limit:50')
                    cache.set(resumes_cache_key, {'resumes': resumes}, CacheTTL.USER_RESUMES)
                    warmed_caches.append('user_resumes')
            except Exception as e:
                logger.warning(f"Failed to warm up resumes cache: {e}")
        
        logger.info(f"Cache warm-up completed for user: {user_id}, warmed: {warmed_caches}")
        
        return jsonify({
            'message': 'Cache warm-up completed',
            'warmed_caches': warmed_caches
        }), 200
        
    except Exception as e:
        logger.error(f"Cache warm-up error: {str(e)}")
        return jsonify({'error': 'Cache warm-up failed', 'details': str(e)}), 500

# Test endpoints
@app.route('/api/test-auth', methods=['GET'])
@auth_required
def test_auth():
    """Test authentication with cache validation"""
    try:
        user_id = request.user_id
        
        # Get user data from cache if available
        cache_key = cache.generate_cache_key(CacheKeys.USER_PROFILE, user_id)
        cached_user = cache.get(cache_key)
        
        if cached_user:
            return jsonify({
                'message': 'Authentication successful',
                'user_id': user_id,
                'data_source': 'cache',
                'cached_user': cached_user
            }), 200
        else:
            # Get from database
            user_data = user_model.get_user_by_id(user_id) if user_model else None
            return jsonify({
                'message': 'Authentication successful',
                'user_id': user_id,
                'data_source': 'database',
                'user_exists': user_data is not None
            }), 200
        
    except Exception as e:
        logger.error(f"Test auth error: {str(e)}")
        return jsonify({'error': 'Authentication test failed', 'details': str(e)}), 500

@app.route('/api/info', methods=['GET'])
def get_app_info():
    """Get application information with cache status"""
    try:
        info = {
            'name': 'Skill Buddy API',
            'version': '1.0.0',
            'description': 'Enhanced API with Redis caching for resume and profile analysis',
            'features': [
                'User Authentication',
                'Resume Processing',
                'Profile Analysis (LinkedIn/GitHub)',
                'Portfolio Analysis',
                'Community Platform',
                'Redis Caching',
                'Real-time Notifications',
                'Rate Limiting'
            ],
            'cache_status': cache.get_cache_info(),
            'endpoints': {
                'auth': '/api/auth/*',
                'user': '/api/user/*',
                'resume': '/api/resume/*',
                'profile_analysis': '/api/profile-analysis/*',
                'portfolio_analysis': '/api/portfolio-analysis/*',
                'community': '/api/community/*',
                'cache_management': '/api/cache/*'
            }
        }
        
        return jsonify(info), 200
        
    except Exception as e:
        logger.error(f"Get app info error: {str(e)}")
        return jsonify({'error': 'Failed to get app info', 'details': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({'error': 'Rate limit exceeded', 'message': str(e)}), 429

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Starting Skill Buddy API with Redis Cache")
    print("=" * 50)
    print(f"✓ Redis Cache: {'Enabled' if cache.enabled else 'Disabled'}")
    print(f"✓ Firebase: {'Connected' if db else 'Not connected'}")
    print(f"✓ Email Service: {'Enabled' if email_service and email_service.enabled else 'Disabled'}")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)