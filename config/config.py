# config/config.py
import os
from dotenv import load_dotenv

load_dotenv()

# API Keys configuration
CLAUDE_API_KEY = os.environ.get('CLAUDE_API_KEY')

# Validate API key
if CLAUDE_API_KEY and not CLAUDE_API_KEY.startswith('sk-ant-'):
    print("Warning: CLAUDE_API_KEY format appears incorrect. Should start with 'sk-ant-'")

# File upload configuration
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
RESUME_FOLDER = os.path.join(UPLOAD_FOLDER, 'resumes')
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'pdf'}

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESUME_FOLDER, exist_ok=True)

# Logging configuration
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)