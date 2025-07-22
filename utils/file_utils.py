"""
File Utilities - Helper functions for file handling and uploads
"""

import os
import uuid
import mimetypes
from datetime import datetime
from typing import List, Optional, Dict, Any
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
import logging

logger = logging.getLogger(__name__)

def allowed_file(filename: str, allowed_extensions: List[str]) -> bool:
    """Check if file has an allowed extension"""
    if not filename or '.' not in filename:
        return False
    
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in [ext.lower() for ext in allowed_extensions]

def get_file_extension(filename: str) -> Optional[str]:
    """Get file extension from filename"""
    if not filename or '.' not in filename:
        return None
    return filename.rsplit('.', 1)[1].lower()

def generate_unique_filename(original_filename: str, prefix: str = '') -> str:
    """Generate a unique filename while preserving the original extension"""
    if not original_filename:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"{prefix}{timestamp}_{uuid.uuid4().hex[:8]}"
    
    # Get the extension
    extension = get_file_extension(original_filename)
    
    # Generate unique name
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    unique_id = uuid.uuid4().hex[:8]
    
    if extension:
        if prefix:
            return f"{prefix}_{timestamp}_{unique_id}.{extension}"
        else:
            return f"{timestamp}_{unique_id}.{extension}"
    else:
        if prefix:
            return f"{prefix}_{timestamp}_{unique_id}"
        else:
            return f"{timestamp}_{unique_id}"

def save_upload_file(file: FileStorage, filename: str = None, upload_folder: str = 'uploads') -> str:
    """Save uploaded file to specified folder"""
    try:
        # Create upload folder if it doesn't exist
        os.makedirs(upload_folder, exist_ok=True)
        
        # Generate filename if not provided
        if not filename:
            filename = generate_unique_filename(file.filename)
        else:
            filename = secure_filename(filename)
        
        # Full file path
        filepath = os.path.join(upload_folder, filename)
        
        # Save the file
        file.save(filepath)
        
        logger.info(f"File saved: {filepath}")
        return filepath
        
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise Exception(f"Failed to save file: {e}")

def delete_file(filepath: str) -> bool:
    """Delete a file from filesystem"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"File deleted: {filepath}")
            return True
        else:
            logger.warning(f"File not found for deletion: {filepath}")
            return False
    except Exception as e:
        logger.error(f"Failed to delete file {filepath}: {e}")
        return False

def get_file_info(filepath: str) -> Dict[str, Any]:
    """Get information about a file"""
    try:
        if not os.path.exists(filepath):
            return {'exists': False}
        
        stat = os.stat(filepath)
        filename = os.path.basename(filepath)
        extension = get_file_extension(filename)
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(filepath)
        
        return {
            'exists': True,
            'filename': filename,
            'filepath': filepath,
            'extension': extension,
            'size': stat.st_size,
            'size_mb': round(stat.st_size / (1024 * 1024), 2),
            'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'mime_type': mime_type
        }
    except Exception as e:
        logger.error(f"Failed to get file info for {filepath}: {e}")
        return {'exists': False, 'error': str(e)}

def validate_file_upload(file: FileStorage, allowed_extensions: List[str], 
                        max_size: int = 16777216) -> Dict[str, Any]:
    """Validate uploaded file"""
    if not file:
        return {'valid': False, 'message': 'No file provided'}
    
    if file.filename == '':
        return {'valid': False, 'message': 'No file selected'}
    
    # Check file extension
    if not allowed_file(file.filename, allowed_extensions):
        return {
            'valid': False,
            'message': f'Invalid file type. Allowed types: {", ".join(allowed_extensions)}'
        }
    
    # Check file size (if we can determine it)
    if hasattr(file, 'content_length') and file.content_length:
        if file.content_length > max_size:
            max_mb = max_size / (1024 * 1024)
            return {
                'valid': False,
                'message': f'File size too large. Maximum size: {max_mb:.1f}MB'
            }
    
    return {
        'valid': True,
        'message': 'File validation passed',
        'filename': file.filename,
        'extension': get_file_extension(file.filename)
    }

def create_directory_structure(base_path: str, user_id: str, category: str = None) -> str:
    """Create organized directory structure for user files"""
    try:
        # Create path like: uploads/users/{user_id}/{category}/
        if category:
            dir_path = os.path.join(base_path, 'users', user_id, category)
        else:
            dir_path = os.path.join(base_path, 'users', user_id)
        
        os.makedirs(dir_path, exist_ok=True)
        return dir_path
        
    except Exception as e:
        logger.error(f"Failed to create directory structure: {e}")
        raise Exception(f"Failed to create directory structure: {e}")

def cleanup_old_files(directory: str, days_old: int = 30) -> int:
    """Clean up files older than specified days"""
    try:
        if not os.path.exists(directory):
            return 0
        
        from datetime import timedelta
        cutoff_time = datetime.now() - timedelta(days=days_old)
        deleted_count = 0
        
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            
            if os.path.isfile(filepath):
                file_modified_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                
                if file_modified_time < cutoff_time:
                    if delete_file(filepath):
                        deleted_count += 1
        
        logger.info(f"Cleaned up {deleted_count} old files from {directory}")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Failed to cleanup old files: {e}")
        return 0

def get_directory_size(directory: str) -> Dict[str, Any]:
    """Get total size of directory and file count"""
    try:
        if not os.path.exists(directory):
            return {'size': 0, 'size_mb': 0, 'file_count': 0}
        
        total_size = 0
        file_count = 0
        
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
                    file_count += 1
        
        return {
            'size': total_size,
            'size_mb': round(total_size / (1024 * 1024), 2),
            'size_gb': round(total_size / (1024 * 1024 * 1024), 2),
            'file_count': file_count
        }
        
    except Exception as e:
        logger.error(f"Failed to get directory size: {e}")
        return {'size': 0, 'size_mb': 0, 'file_count': 0, 'error': str(e)}

def compress_file(filepath: str, compression_type: str = 'zip') -> Optional[str]:
    """Compress a file using specified compression type"""
    try:
        import zipfile
        import gzip
        
        if not os.path.exists(filepath):
            return None
        
        if compression_type == 'zip':
            compressed_path = f"{filepath}.zip"
            with zipfile.ZipFile(compressed_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(filepath, os.path.basename(filepath))
            
        elif compression_type == 'gzip':
            compressed_path = f"{filepath}.gz"
            with open(filepath, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    f_out.writelines(f_in)
        else:
            raise ValueError(f"Unsupported compression type: {compression_type}")
        
        logger.info(f"File compressed: {filepath} -> {compressed_path}")
        return compressed_path
        
    except Exception as e:
        logger.error(f"Failed to compress file {filepath}: {e}")
        return None

def extract_text_from_file(filepath: str) -> Optional[str]:
    """Extract text content from various file types"""
    try:
        extension = get_file_extension(filepath)
        
        if extension == 'txt':
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        
        elif extension == 'pdf':
            try:
                import PyPDF2
                with open(filepath, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = ''
                    for page in reader.pages:
                        text += page.extract_text()
                    return text
            except ImportError:
                logger.warning("PyPDF2 not installed, cannot extract PDF text")
                return None
        
        elif extension in ['doc', 'docx']:
            try:
                import docx
                doc = docx.Document(filepath)
                text = ''
                for paragraph in doc.paragraphs:
                    text += paragraph.text + '\n'
                return text
            except ImportError:
                logger.warning("python-docx not installed, cannot extract Word document text")
                return None
        
        else:
            logger.warning(f"Text extraction not supported for file type: {extension}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to extract text from {filepath}: {e}")
        return None

def move_file(source_path: str, destination_path: str) -> bool:
    """Move file from source to destination"""
    try:
        # Create destination directory if it doesn't exist
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        
        # Move the file
        os.rename(source_path, destination_path)
        
        logger.info(f"File moved: {source_path} -> {destination_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to move file {source_path} to {destination_path}: {e}")
        return False

def copy_file(source_path: str, destination_path: str) -> bool:
    """Copy file from source to destination"""
    try:
        import shutil
        
        # Create destination directory if it doesn't exist
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        
        # Copy the file
        shutil.copy2(source_path, destination_path)
        
        logger.info(f"File copied: {source_path} -> {destination_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to copy file {source_path} to {destination_path}: {e}")
        return False

def get_safe_filename(filename: str, max_length: int = 255) -> str:
    """Generate a safe filename for file system"""
    if not filename:
        return generate_unique_filename('')
    
    # Use werkzeug's secure_filename for basic safety
    safe_name = secure_filename(filename)
    
    # Additional safety measures
    # Remove any remaining special characters
    import re
    safe_name = re.sub(r'[^\w\s.-]', '', safe_name)
    
    # Replace spaces with underscores
    safe_name = safe_name.replace(' ', '_')
    
    # Limit length
    if len(safe_name) > max_length:
        extension = get_file_extension(safe_name)
        if extension:
            name_part = safe_name[:max_length - len(extension) - 1]
            safe_name = f"{name_part}.{extension}"
        else:
            safe_name = safe_name[:max_length]
    
    # Ensure we have a valid filename
    if not safe_name or safe_name in ['.', '..']:
        safe_name = generate_unique_filename('')
    
    return safe_name

# File type detection helpers
def is_image_file(filepath: str) -> bool:
    """Check if file is an image"""
    extension = get_file_extension(filepath)
    return extension in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg']

def is_video_file(filepath: str) -> bool:
    """Check if file is a video"""
    extension = get_file_extension(filepath)
    return extension in ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv']

def is_audio_file(filepath: str) -> bool:
    """Check if file is audio"""
    extension = get_file_extension(filepath)
    return extension in ['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a']

def is_document_file(filepath: str) -> bool:
    """Check if file is a document"""
    extension = get_file_extension(filepath)
    return extension in ['pdf', 'doc', 'docx', 'txt', 'rtf', 'odt']

def is_archive_file(filepath: str) -> bool:
    """Check if file is an archive"""
    extension = get_file_extension(filepath)
    return extension in ['zip', 'rar', '7z', 'tar', 'gz', 'bz2']

def get_file_size(filepath: str) -> int:
    """Get file size in bytes"""
    try:
        if not os.path.exists(filepath):
            return 0
        return os.path.getsize(filepath)
    except Exception as e:
        logger.error(f"Failed to get file size for {filepath}: {e}")
        return 0

def calculate_file_hash(filepath: str, algorithm: str = 'sha256') -> str:
    """Calculate file hash using specified algorithm"""
    try:
        import hashlib
        
        if not os.path.exists(filepath):
            return ""
        
        hash_obj = hashlib.new(algorithm)
        
        with open(filepath, 'rb') as f:
            # Read file in chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
        
    except Exception as e:
        logger.error(f"Failed to calculate file hash for {filepath}: {e}")
        return ""