# app.py (Updated with Profile Analysis)
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

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
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

# Utility Functions
def validate_email(email):
    pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    return re.match(pattern, email) is not None

def auth_required(f):
    """Decorator to require user ID authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return jsonify({'error': 'User ID required in X-User-ID header'}), 401
        
        # Verify user exists in database
        if db:
            try:
                doc_ref = db.collection('users').document(user_id)
                doc = doc_ref.get()
                if not doc.exists:
                    return jsonify({'error': 'Invalid user ID'}), 401
            except Exception as e:
                return jsonify({'error': 'User verification failed'}), 401
        
        request.user_id = user_id
        return f(*args, **kwargs)
    
    return decorated

# Import and register blueprints
try:
    from routes.auth_routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    print("✓ Auth routes loaded")
except ImportError as e:
    print(f"✗ Auth routes failed: {e}")
    auth_bp = None

try:
    from routes.user_routes import user_bp
    app.register_blueprint(user_bp, url_prefix='/api/user')
    print("✓ User routes loaded")
except ImportError as e:
    print(f"✗ User routes failed: {e}")
    user_bp = None

try:
    from routes.resume_routes import resume_bp
    app.register_blueprint(resume_bp, url_prefix='/api/resume')
    print("✓ Resume routes loaded")
except ImportError as e:
    print(f"✗ Resume routes failed: {e}")
    resume_bp = None

# NEW: Import and register profile analysis blueprint
try:
    from routes.profile_analysis_routes import profile_analysis_bp
    app.register_blueprint(profile_analysis_bp, url_prefix='/api/profile-analysis')
    print("✓ Profile analysis routes loaded")
except ImportError as e:
    print(f"✗ Profile analysis routes failed: {e}")
    profile_analysis_bp = None

# Update the status endpoint
@app.route('/api/status', methods=['GET'])
def api_status():
    try:
        stats = {
            'api_status': 'healthy',
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'database_connected': db is not None,
            'features_available': {
                'authentication': auth_bp is not None,
                'user_management': user_bp is not None,
                'resume_processing': resume_bp is not None,
                'profile_analysis': profile_analysis_bp is not None  # NEW
            }
        }
        
        # Try to get statistics if available
        if resume_bp and db:
            try:
                from models.resume_model import ResumeModel
                from models.user_model import UserModel
                
                user_model = UserModel(db)
                resume_model = ResumeModel(db)
                
                user_stats = user_model.get_user_statistics()
                resume_stats = resume_model.get_processing_statistics()
                
                stats.update({
                    'user_statistics': user_stats,
                    'resume_statistics': resume_stats
                })
            except Exception as e:
                stats['statistics_error'] = str(e)
        
        # NEW: Try to get profile analysis statistics
        if profile_analysis_bp and db:
            try:
                from models.profile_analysis_model import ProfileAnalysisModel
                
                analysis_model = ProfileAnalysisModel(db)
                analysis_stats = analysis_model.get_analysis_statistics()
                
                stats['profile_analysis_statistics'] = analysis_stats
            except Exception as e:
                stats['profile_analysis_error'] = str(e)
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Status check error: {e}")
        return jsonify({
            'api_status': 'error',
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'error': str(e)
        }), 500

# Basic Routes
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        'message': 'Skill Buddy API is running',
        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'healthy',
        'version': '2.0.0',  # Updated version
        'features': [
            'Resume Processing',
            'User Management', 
            'LinkedIn Profile Analysis',  # NEW
            'GitHub Profile Analysis'     # NEW
        ]
    })

# Test authentication endpoint
@app.route('/api/test-auth', methods=['GET'])
@auth_required
def test_auth():
    return jsonify({
        'message': 'Authentication successful',
        'user_id': request.user_id,
        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()
    })

# NEW: Profile analysis test endpoint
@app.route('/api/test-profile-analysis', methods=['GET'])
@auth_required
def test_profile_analysis():
    """Test endpoint to check if profile analysis features are working"""
    try:
        claude_api_key = os.environ.get('CLAUDE_API_KEY')
        github_token = os.environ.get('GITHUB_TOKEN')
        
        return jsonify({
            'message': 'Profile analysis features test',
            'user_id': request.user_id,
            'claude_api_configured': bool(claude_api_key),
            'github_token_configured': bool(github_token),
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'features_status': {
                'linkedin_analysis': profile_analysis_bp is not None,
                'github_analysis': profile_analysis_bp is not None,
                'claude_integration': bool(claude_api_key)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Profile analysis test error: {e}")
        return jsonify({
            'error': 'Profile analysis test failed',
            'details': str(e)
        }), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(429)
def rate_limit_handler(e):
    return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print("=== Skill Buddy API Starting ===")
    print(f"Port: {port}")
    print(f"Debug: {debug}")
    print("Features:")
    print("  ✓ Resume Processing")
    print("  ✓ User Management")
    print("  ✓ LinkedIn Profile Analysis")  # NEW
    print("  ✓ GitHub Profile Analysis")    # NEW
    print("================================")
    
    app.run(host='0.0.0.0', port=port, debug=debug)