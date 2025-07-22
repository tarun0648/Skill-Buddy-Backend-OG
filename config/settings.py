"""
Application Configuration Settings - Enhanced with Interview System
"""

import os
from datetime import timedelta


class Config:
    """Base configuration class"""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'skill-buddy-secret-key-change-in-production')
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    
    # CORS Configuration
    CORS_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:8080", 
        "http://localhost:8081",
        "https://your-frontend-domain.com"
    ]
    
    # Rate Limiting
    RATE_LIMIT_ENABLED = os.environ.get('RATE_LIMIT_ENABLED', 'True').lower() == 'true'
    RATE_LIMIT_PER_DAY = int(os.environ.get('RATE_LIMIT_PER_DAY', 20000))
    RATE_LIMIT_PER_HOUR = int(os.environ.get('RATE_LIMIT_PER_HOUR', 5000))
    
    # File Upload Configuration
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
    ALLOWED_EXTENSIONS = {
        'resume': {'pdf', 'doc', 'docx'},
        'video': {'mp4', 'webm', 'avi', 'mov'},
        'image': {'png', 'jpg', 'jpeg', 'gif'}
    }
    
    # OpenAI Configuration (Interview System)
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    OPENAI_ASSISTANT_ID = os.environ.get('OPENAI_ASSISTANT_ID')
    
    # Interview Configuration
    INTERVIEW_MAX_QUESTIONS = int(os.environ.get('INTERVIEW_MAX_QUESTIONS', 8))
    INTERVIEW_MIN_QUESTIONS = int(os.environ.get('INTERVIEW_MIN_QUESTIONS', 5))
    INTERVIEW_TIME_LIMIT = int(os.environ.get('INTERVIEW_TIME_LIMIT', 1800))  # 30 minutes in seconds
    INTERVIEW_VAGUE_THRESHOLD = int(os.environ.get('INTERVIEW_VAGUE_THRESHOLD', 3))
    
    # JD Interview Configuration
    JD_INTERVIEW_MAX_QUESTIONS = int(os.environ.get('JD_INTERVIEW_MAX_QUESTIONS', 8))
    JD_INTERVIEW_MIN_QUESTIONS = int(os.environ.get('JD_INTERVIEW_MIN_QUESTIONS', 5))
    JD_ANALYSIS_MODEL = os.environ.get('JD_ANALYSIS_MODEL', 'gpt-3.5-turbo')
    
    # Authentication Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', SECRET_KEY)
    JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', 24))
    PASSWORD_MIN_LENGTH = int(os.environ.get('PASSWORD_MIN_LENGTH', 8))
    
    # Session Configuration
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'skillbuddy:'
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=JWT_EXPIRATION_HOURS)
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/app.log')
    LOG_MAX_BYTES = int(os.environ.get('LOG_MAX_BYTES', 10485760))  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', 5))
    
    # Email Configuration (for notifications, password reset, etc.)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@skillbuddy.com')
    
    # Background Task Configuration
    TASK_QUEUE_ENABLED = os.environ.get('TASK_QUEUE_ENABLED', 'True').lower() == 'true'
    TASK_TIMEOUT = int(os.environ.get('TASK_TIMEOUT', 300))  # 5 minutes
    MAX_CONCURRENT_TASKS = int(os.environ.get('MAX_CONCURRENT_TASKS', 5))
    
    # Analytics and Monitoring
    ANALYTICS_ENABLED = os.environ.get('ANALYTICS_ENABLED', 'False').lower() == 'true'
    SENTRY_DSN = os.environ.get('SENTRY_DSN')
    
    # Social Authentication (SSO)
    GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
    GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET')
    LINKEDIN_CLIENT_ID = os.environ.get('LINKEDIN_CLIENT_ID')
    LINKEDIN_CLIENT_SECRET = os.environ.get('LINKEDIN_CLIENT_SECRET')
    
    # Phone/SMS Configuration
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')
    
    # XP and Gamification System
    XP_REWARDS = {
        'profile_photo_upload': 10,
        'email_verified': 20,
        'phone_verified': 15,
        'github_linked': 15,
        'linkedin_linked': 15,
        'resume_uploaded': 15,
        'profile_complete': 50,
        'first_interview': 100,
        'interview_complete': 50,
        'daily_login': 5,
        'community_post': 20,
        'community_reply': 10,
        'community_like_received': 5
    }
    
    # Interview Question Categories
    INTERVIEW_CATEGORIES = [
        'Behavioral',
        'Technical',
        'Analytical',
        'Execution',
        'Strategic',
        'Leadership',
        'Communication',
        'Problem Solving'
    ]
    
    # Interview Difficulty Levels
    INTERVIEW_LEVELS = {
        'junior': 'Junior (0-2 years)',
        'mid': 'Mid-level (2-5 years)',
        'senior': 'Senior (5+ years)',
        'executive': 'Executive/Leadership'
    }
    
    # Supported Interview Roles
    INTERVIEW_ROLES = [
        'Software Engineer',
        'Engineering Lead',
        'Engineering Manager I',
        'Engineering Manager II',
        'Senior Engineering Manager',
        'Director of Engineering',
        'VP of Engineering',
        'CTO',
        'Product Manager',
        'Data Scientist',
        'UI/UX Designer',
        'DevOps Engineer',
        'QA Engineer',
        'Security Engineer'
    ]
    
    # File Storage Configuration
    STORAGE_TYPE = os.environ.get('STORAGE_TYPE', 'local')  # local, s3, gcs
    AWS_S3_BUCKET = os.environ.get('AWS_S3_BUCKET')
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
    
    # Google Cloud Storage
    GCS_BUCKET = os.environ.get('GCS_BUCKET')
    GCS_PROJECT_ID = os.environ.get('GCS_PROJECT_ID')
    
    # Cache Configuration
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'simple')
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', 300))
    REDIS_URL = os.environ.get('REDIS_URL')
    
    # API Versioning
    API_VERSION = os.environ.get('API_VERSION', 'v1')
    API_TITLE = 'Skill Buddy Backend API'
    API_DESCRIPTION = 'Backend API for Skill Buddy platform with interview system'
    
    # Feature Flags
    FEATURES = {
        'interview_system': os.environ.get('FEATURE_INTERVIEW_SYSTEM', 'True').lower() == 'true',
        'jd_interviews': os.environ.get('FEATURE_JD_INTERVIEWS', 'True').lower() == 'true',
        'video_upload': os.environ.get('FEATURE_VIDEO_UPLOAD', 'True').lower() == 'true',
        'community': os.environ.get('FEATURE_COMMUNITY', 'True').lower() == 'true',
        'profile_analysis': os.environ.get('FEATURE_PROFILE_ANALYSIS', 'True').lower() == 'true',
        'portfolio_analysis': os.environ.get('FEATURE_PORTFOLIO_ANALYSIS', 'True').lower() == 'true',
        'resume_analysis': os.environ.get('FEATURE_RESUME_ANALYSIS', 'True').lower() == 'true',
        'sso_authentication': os.environ.get('FEATURE_SSO_AUTH', 'True').lower() == 'true',
        'phone_authentication': os.environ.get('FEATURE_PHONE_AUTH', 'True').lower() == 'true'
    }
    
    @staticmethod
    def init_app(app):
        """Initialize application with configuration"""
        # Create necessary directories
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        
        # Validate OpenAI configuration if interview system is enabled
        if app.config['FEATURES']['interview_system']:
            if not app.config['OPENAI_API_KEY'] or not app.config['OPENAI_ASSISTANT_ID']:
                raise ValueError("OpenAI configuration is required for interview system")

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    FLASK_ENV = 'development'
    LOG_LEVEL = 'DEBUG'
    RATE_LIMIT_ENABLED = False
    SESSION_COOKIE_SECURE = False
    
    # Development-specific interview settings
    INTERVIEW_TIME_LIMIT = 3600  # 1 hour for development
    TASK_TIMEOUT = 600  # 10 minutes for development

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    FLASK_ENV = 'production'
    LOG_LEVEL = 'INFO'
    SESSION_COOKIE_SECURE = True
    
    # Override with production values
    CORS_ORIGINS = [
        os.environ.get('FRONTEND_URL', 'https://your-frontend-domain.com')
    ]
    
    # Production security settings
    RATE_LIMIT_ENABLED = True
    ANALYTICS_ENABLED = True
    
    # Stricter production settings
    PASSWORD_MIN_LENGTH = 12
    JWT_EXPIRATION_HOURS = 8  # Shorter in production

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    FLASK_ENV = 'testing'
    LOG_LEVEL = 'DEBUG'
    
    # Testing-specific settings
    JWT_EXPIRATION_HOURS = 1  # Short expiration for testing
    RATE_LIMIT_ENABLED = False
    TASK_QUEUE_ENABLED = False
    
    # Override interview settings for faster tests
    INTERVIEW_MAX_QUESTIONS = 3
    INTERVIEW_MIN_QUESTIONS = 2
    INTERVIEW_TIME_LIMIT = 300  # 5 minutes for testing

class StagingConfig(Config):
    """Staging configuration"""
    DEBUG = False
    FLASK_ENV = 'staging'
    LOG_LEVEL = 'INFO'
    
    # Staging-specific settings (similar to production but with some relaxed settings)
    RATE_LIMIT_PER_DAY = 50000  # Higher limits for testing
    ANALYTICS_ENABLED = False  # No analytics in staging

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'staging': StagingConfig,
    'default': DevelopmentConfig
}

def get_config(config_name=None):
    """Get configuration class"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    return config.get(config_name, DevelopmentConfig)