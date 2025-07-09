# config/settings.py
import os
from datetime import timedelta

class Config:
    """Base configuration class"""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    DEBUG = FLASK_ENV == 'development'
    
    # JWT Configuration
    JWT_SECRET = os.environ.get('JWT_SECRET', 'your-jwt-secret-key')
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', 24))
    REFRESH_TOKEN_EXPIRATION_DAYS = int(os.environ.get('REFRESH_TOKEN_EXPIRATION_DAYS', 7))
    
    # Firebase Configuration
    FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID')
    FIREBASE_PRIVATE_KEY_ID = os.environ.get('FIREBASE_PRIVATE_KEY_ID')
    FIREBASE_PRIVATE_KEY = os.environ.get('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n')
    FIREBASE_CLIENT_EMAIL = os.environ.get('FIREBASE_CLIENT_EMAIL')
    FIREBASE_CLIENT_ID = os.environ.get('FIREBASE_CLIENT_ID')
    
    # Google OAuth Configuration
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    
    # CORS Configuration
    CORS_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:8081", 
        "http://172.20.10.7:8081",
        "exp://192.168.1.100:8081"
    ]
    
    # Rate Limiting Configuration
    RATE_LIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')
    DEFAULT_RATE_LIMITS = ["200 per day", "50 per hour"]
    
    # Email Configuration (for future use)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s %(levelname)s %(name)s %(message)s'
    
    # Security Configuration
    BCRYPT_LOG_ROUNDS = int(os.environ.get('BCRYPT_LOG_ROUNDS', 12))
    
    # File Upload Configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}
    
    # UPDATED Profile Configuration
    PROFILE_COMPLETION_STEPS = {
        'name': 10,           # 10%
        'profession': 10,     # 10%
        'career_choices': 10, # 10%
        'college_name': 10,   # 10%
        'college_email': 15,  # 15% (Total basic profile: 55%)
        'github_link': 15,    # 15%
        'linkedin_link': 15,  # 15%
        'resume_uploaded': 15 # 15%
        # Total: 100%
    }
    
    # XP System Configuration - Updated for new completion system
    XP_REWARDS = {
        'registration': 10,
        'google_signin': 10,
        'profile_step_10': 5,   # Name
        'profile_step_20': 5,   # Profession
        'profile_step_30': 5,   # Career choices
        'profile_step_40': 5,   # College name
        'profile_step_55': 15,  # College email (basic profile complete)
        'github_linked': 15,    # GitHub link added
        'linkedin_linked': 15,  # LinkedIn link added
        'resume_uploaded': 15,  # Resume uploaded
        'profile_complete': 50, # Full profile complete (100%)
        'first_interview': 100,
        'interview_complete': 50,
        'daily_login': 5
    }
    
    # Interview Configuration (for future use)
    INTERVIEW_TIME_LIMIT = int(os.environ.get('INTERVIEW_TIME_LIMIT', 1800))  # 30 minutes
    MAX_QUESTIONS_PER_INTERVIEW = int(os.environ.get('MAX_QUESTIONS_PER_INTERVIEW', 10))
    
    # Cache Configuration
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'simple')
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', 300))
    
    @staticmethod
    def init_app(app):
        """Initialize application with configuration"""
        pass

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    FLASK_ENV = 'development'
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    FLASK_ENV = 'production'
    LOG_LEVEL = 'INFO'
    
    # Override with production values
    CORS_ORIGINS = [os.environ.get('FRONTEND_URL', 'https://your-frontend-domain.com')]

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    JWT_EXPIRATION_HOURS = 1  # Shorter expiration for testing

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}