# app.py (Updated with Profile Completion System)
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

try:
    from routes.profile_analysis_routes import profile_analysis_bp
    app.register_blueprint(profile_analysis_bp, url_prefix='/api/profile-analysis')
    print("✓ Profile analysis routes loaded")
except ImportError as e:
    print(f"✗ Profile analysis routes failed: {e}")
    profile_analysis_bp = None

try:
    from routes.portfolio_analysis_routes import portfolio_analysis_bp
    app.register_blueprint(portfolio_analysis_bp, url_prefix='/api/portfolio-analysis')
    print("✓ Portfolio analysis routes loaded")
except ImportError as e:
    print(f"✗ Portfolio analysis routes failed: {e}")
    portfolio_analysis_bp = None

# Profile completion info endpoint
@app.route('/api/profile-completion/info', methods=['GET'])
def get_profile_completion_info():
    """Get information about profile completion system"""
    try:
        from utils.profile_completion_utils import ProfileCompletionManager
        
        return jsonify({
            'completion_system': {
                'basic_profile_percentage': 55,
                'additional_elements_percentage': 45,
                'total_percentage': 100
            },
            'steps': ProfileCompletionManager.COMPLETION_STEPS,
            'milestones': ProfileCompletionManager.get_milestones_info(),
            'xp_rewards': ProfileCompletionManager.XP_REWARDS
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting profile completion info: {e}")
        return jsonify({'error': 'Failed to get profile completion info'}), 500

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
                'profile_analysis': profile_analysis_bp is not None,
                'portfolio_analysis': portfolio_analysis_bp is not None,
                'profile_completion_system': True  # NEW
            },
            'profile_completion': {
                'basic_profile_required': 55,
                'github_link_bonus': 15,
                'linkedin_link_bonus': 15,
                'resume_upload_bonus': 15,
                'total_possible': 100
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
        
        # Try to get profile analysis statistics
        if profile_analysis_bp and db:
            try:
                from models.profile_analysis_model import ProfileAnalysisModel
                
                analysis_model = ProfileAnalysisModel(db)
                analysis_stats = analysis_model.get_analysis_statistics()
                
                stats['profile_analysis_statistics'] = analysis_stats
            except Exception as e:
                stats['profile_analysis_error'] = str(e)
        
        # Try to get portfolio analysis statistics
        if portfolio_analysis_bp and db:
            try:
                from models.portfolio_analysis_model import PortfolioAnalysisModel
                
                portfolio_model = PortfolioAnalysisModel(db)
                portfolio_stats = portfolio_model.get_analysis_statistics()
                
                stats['portfolio_analysis_statistics'] = portfolio_stats
            except Exception as e:
                stats['portfolio_analysis_error'] = str(e)
        
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
        'version': '3.1.0',  # Updated version for new completion system
        'features': [
            'Resume Processing',
            'User Management', 
            'LinkedIn Profile Analysis',
            'GitHub Profile Analysis',
            'Portfolio Website Analysis',
            'Enhanced Profile Completion System'  # NEW
        ],
        'profile_completion_system': {
            'basic_profile': '55% (Name, Profession, Career Choices, College Name & Email)',
            'github_link': '15% bonus',
            'linkedin_link': '15% bonus', 
            'resume_upload': '15% bonus',
            'total': '100% for complete profile'
        }
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

# Test profile completion endpoint
@app.route('/api/test-profile-completion', methods=['GET'])
@auth_required
def test_profile_completion():
    """Test endpoint to check profile completion system"""
    try:
        from utils.profile_completion_utils import ProfileCompletionManager
        
        # Mock profile data for testing
        test_profiles = [
            {
                'name': 'Test User',
                'description': 'Name only'
            },
            {
                'name': 'Test User',
                'profession': 'Student',
                'career_choices': ['Software Engineering'],
                'college_name': 'Test University',
                'college_email': 'test@university.edu',
                'description': 'Basic profile complete (55%)'
            },
            {
                'name': 'Test User',
                'profession': 'Student',
                'career_choices': ['Software Engineering'],
                'college_name': 'Test University',
                'college_email': 'test@university.edu',
                'github_link': 'https://github.com/testuser',
                'linkedin_link': 'https://linkedin.com/in/testuser',
                'has_resume': True,
                'description': 'Complete profile (100%)'
            }
        ]
        
        results = []
        for i, profile in enumerate(test_profiles):
            description = profile.pop('description')
            completion = ProfileCompletionManager.calculate_completion_percentage(profile)
            breakdown = ProfileCompletionManager.get_completion_breakdown(profile)
            next_steps = ProfileCompletionManager.get_next_steps(profile)
            
            results.append({
                'test_case': i + 1,
                'description': description,
                'profile': profile,
                'completion_percentage': completion,
                'breakdown': breakdown,
                'next_steps': next_steps
            })
        
        return jsonify({
            'message': 'Profile completion system test',
            'user_id': request.user_id,
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'test_results': results,
            'system_info': ProfileCompletionManager.get_milestones_info()
        }), 200
        
    except Exception as e:
        logger.error(f"Profile completion test error: {e}")
        return jsonify({
            'error': 'Profile completion test failed',
            'details': str(e)
        }), 500

# Test profile analysis endpoint
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
                'portfolio_analysis': portfolio_analysis_bp is not None,
                'claude_integration': bool(claude_api_key)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Profile analysis test error: {e}")
        return jsonify({
            'error': 'Profile analysis test failed',
            'details': str(e)
        }), 500

# Portfolio analysis test endpoint
@app.route('/api/test-portfolio-analysis', methods=['GET'])
@auth_required
def test_portfolio_analysis():
    """Test endpoint to check if portfolio analysis features are working"""
    try:
        claude_api_key = os.environ.get('CLAUDE_API_KEY')
        
        return jsonify({
            'message': 'Portfolio analysis features test',
            'user_id': request.user_id,
            'claude_api_configured': bool(claude_api_key),
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'features_status': {
                'portfolio_analysis': portfolio_analysis_bp is not None,
                'web_scraping': True,  # Built-in with requests and BeautifulSoup
                'claude_integration': bool(claude_api_key),
                'data_extraction': True
            },
            'supported_analysis': {
                'content_extraction': ['projects', 'skills', 'experience', 'education'],
                'technical_analysis': ['performance', 'seo', 'responsive_design'],
                'scoring_criteria': ['content_quality', 'technical_implementation', 'design_ux', 'professional_branding'],
                'improvement_suggestions': ['immediate_actions', 'content_improvements', 'technical_improvements']
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Portfolio analysis test error: {e}")
        return jsonify({
            'error': 'Portfolio analysis test failed',
            'details': str(e)
        }), 500
# Add this debug endpoint to app.py for testing

@app.route('/api/debug/profile-completion/<user_id>', methods=['GET'])
def debug_profile_completion(user_id):
    """Debug endpoint to check profile completion calculation"""
    try:
        if not db:
            return jsonify({'error': 'Database not available'}), 500
        
        # Get user data
        doc_ref = db.collection('users').document(user_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return jsonify({'error': 'User not found'}), 404
        
        user_data = doc.to_dict()
        profile = user_data.get('profile', {})
        
        # Import the completion manager
        from utils.profile_completion_utils import ProfileCompletionManager
        from models.user_model import UserModel
        
        user_model = UserModel(db)
        
        # Calculate completion using both methods
        util_completion = ProfileCompletionManager.calculate_completion_percentage(profile)
        model_completion = user_model.calculate_profile_completion(profile)
        stored_completion = profile.get('completion_status', 0)
        
        # Get detailed breakdown
        breakdown = ProfileCompletionManager.get_completion_breakdown(profile)
        next_steps = ProfileCompletionManager.get_next_steps(profile)
        
        # Check each field individually
        field_analysis = {}
        for field in ['name', 'profession', 'career_choices', 'college_name', 'college_email', 'github_link', 'linkedin_link', 'has_resume']:
            value = profile.get(field)
            field_analysis[field] = {
                'raw_value': value,
                'type': type(value).__name__,
                'string_value': str(value) if value is not None else 'None',
                'stripped_value': str(value).strip() if value is not None else '',
                'is_empty': not value or not str(value).strip() if field != 'has_resume' else not bool(value),
                'evaluation': 'PASS' if (
                    field == 'has_resume' and bool(value) or
                    field == 'career_choices' and value and isinstance(value, list) and len([c for c in value if c and str(c).strip()]) > 0 or
                    field not in ['has_resume', 'career_choices'] and value and str(value).strip()
                ) else 'FAIL'
            }
        
        return jsonify({
            'user_id': user_id,
            'profile_data': profile,
            'completion_calculations': {
                'utility_method': util_completion,
                'model_method': model_completion,
                'stored_value': stored_completion,
                'all_match': util_completion == model_completion == stored_completion
            },
            'field_analysis': field_analysis,
            'breakdown': breakdown,
            'next_steps': next_steps,
            'debug_info': {
                'profile_keys': list(profile.keys()),
                'has_all_fields': all(field in profile for field in ['name', 'profession', 'career_choices', 'college_name', 'college_email', 'github_link', 'linkedin_link', 'has_resume'])
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Debug profile completion error: {e}")
        return jsonify({'error': 'Debug failed', 'details': str(e)}), 500

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
    print("  ✓ LinkedIn Profile Analysis")
    print("  ✓ GitHub Profile Analysis")
    print("  ✓ Portfolio Website Analysis")
    print("  ✓ Enhanced Profile Completion System")
    print("")
    print("Profile Completion System:")
    print("  • Basic Profile (55%): Name, Profession, Career Choices, College Info")
    print("  • GitHub Link (+15%)")
    print("  • LinkedIn Link (+15%)")
    print("  • Resume Upload (+15%)")
    print("  • Total: 100%")
    print("================================")
    
    app.run(host='0.0.0.0', port=port, debug=debug)