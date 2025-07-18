# utils/file_utils.py
import os
import uuid
import hashlib
from werkzeug.utils import secure_filename
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

def allowed_file(filename: str, allowed_extensions: set) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def generate_unique_filename(original_filename: str) -> str:
    """Generate a unique filename while preserving the extension"""
    filename, ext = os.path.splitext(secure_filename(original_filename))
    unique_id = str(uuid.uuid4())
    return f"{filename}_{unique_id}{ext}"

def save_uploaded_file(file, upload_folder: str, allowed_extensions: set) -> Tuple[Optional[str], Optional[str]]:
    """Save uploaded file to the specified folder"""
    try:
        if not file or file.filename == '':
            return None, "No file selected"
        
        if not allowed_file(file.filename, allowed_extensions):
            return None, f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
        
        # Generate unique filename
        unique_filename = generate_unique_filename(file.filename)
        file_path = os.path.join(upload_folder, unique_filename)
        
        # Create directory if it doesn't exist
        os.makedirs(upload_folder, exist_ok=True)
        
        # Save file
        file.save(file_path)
        
        logger.info(f"File saved successfully: {file_path}")
        return file_path, None
        
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        return None, f"Error saving file: {str(e)}"

def get_file_size(file_path: str) -> int:
    """Get file size in bytes"""
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0

def calculate_file_hash(file_path: str) -> str:
    """Calculate MD5 hash of file"""
    try:
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating file hash: {e}")
        return ""

def delete_file(file_path: str) -> bool:
    """Delete file from filesystem"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"File deleted: {file_path}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        return False