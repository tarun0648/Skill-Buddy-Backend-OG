"""
Validation Utilities - Helper functions for data validation
"""

import re
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
    """Validate that all required fields are present in data"""
    if not isinstance(data, dict):
        return {
            'valid': False,
            'message': 'Invalid data format - expected object',
            'missing_fields': required_fields
        }
    
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == '':
            missing_fields.append(field)
    
    if missing_fields:
        return {
            'valid': False,
            'message': f'Missing required fields: {", ".join(missing_fields)}',
            'missing_fields': missing_fields
        }
    
    return {
        'valid': True,
        'message': 'All required fields present',
        'missing_fields': []
    }

def validate_email(email: str) -> Dict[str, Any]:
    """Validate email format"""
    if not email or not isinstance(email, str):
        return {'valid': False, 'message': 'Email is required'}
    
    email = email.strip().lower()
    
    # RFC 5322 compliant email regex (simplified)
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        return {'valid': False, 'message': 'Invalid email format'}
    
    if len(email) > 254:  # RFC 5321 limit
        return {'valid': False, 'message': 'Email address too long'}
    
    return {'valid': True, 'message': 'Valid email', 'email': email}

def validate_phone_number(phone: str) -> Dict[str, Any]:
    """Validate phone number format"""
    if not phone or not isinstance(phone, str):
        return {'valid': False, 'message': 'Phone number is required'}
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # Check if it's a valid length (10-15 digits)
    if len(digits_only) < 10 or len(digits_only) > 15:
        return {'valid': False, 'message': 'Phone number must be 10-15 digits'}
    
    # Format as international number
    if not phone.startswith('+'):
        if len(digits_only) == 10:
            formatted_phone = f"+1{digits_only}"  # Assume US number
        else:
            formatted_phone = f"+{digits_only}"
    else:
        formatted_phone = f"+{digits_only}"
    
    return {'valid': True, 'message': 'Valid phone number', 'phone': formatted_phone}

def validate_json_data(data: str) -> Dict[str, Any]:
    """Validate and parse JSON data"""
    if not data:
        return {'valid': False, 'message': 'JSON data is required'}
    
    try:
        parsed_data = json.loads(data) if isinstance(data, str) else data
        return {'valid': True, 'message': 'Valid JSON', 'data': parsed_data}
    except json.JSONDecodeError as e:
        return {'valid': False, 'message': f'Invalid JSON format: {str(e)}'}

def validate_url(url: str) -> Dict[str, Any]:
    """Validate URL format"""
    if not url or not isinstance(url, str):
        return {'valid': False, 'message': 'URL is required'}
    
    url = url.strip()
    
    # URL regex pattern
    url_pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
    
    if not re.match(url_pattern, url):
        return {'valid': False, 'message': 'Invalid URL format'}
    
    if len(url) > 2048:  # URL length limit
        return {'valid': False, 'message': 'URL too long'}
    
    return {'valid': True, 'message': 'Valid URL', 'url': url}

def validate_interview_role(role: str) -> Dict[str, Any]:
    """Validate interview role"""
    from config.settings import Config
    
    if not role or not isinstance(role, str):
        return {'valid': False, 'message': 'Role is required'}
    
    valid_roles = Config.INTERVIEW_ROLES
    
    if role not in valid_roles:
        return {
            'valid': False, 
            'message': f'Invalid role. Must be one of: {", ".join(valid_roles)}'
        }
    
    return {'valid': True, 'message': 'Valid role', 'role': role}

def validate_interview_level(level: str) -> Dict[str, Any]:
    """Validate interview level"""
    from config.settings import Config
    
    if not level or not isinstance(level, str):
        return {'valid': False, 'message': 'Level is required'}
    
    valid_levels = list(Config.INTERVIEW_LEVELS.keys())
    
    if level not in valid_levels:
        return {
            'valid': False,
            'message': f'Invalid level. Must be one of: {", ".join(valid_levels)}'
        }
    
    return {'valid': True, 'message': 'Valid level', 'level': level}

def validate_interview_category(category: str) -> Dict[str, Any]:
    """Validate interview category"""
    from config.settings import Config
    
    if not category or not isinstance(category, str):
        return {'valid': False, 'message': 'Category is required'}
    
    valid_categories = Config.INTERVIEW_CATEGORIES
    
    if category not in valid_categories:
        return {
            'valid': False,
            'message': f'Invalid category. Must be one of: {", ".join(valid_categories)}'
        }
    
    return {'valid': True, 'message': 'Valid category', 'category': category}

def validate_session_id(session_id: str) -> Dict[str, Any]:
    """Validate session ID format"""
    if not session_id or not isinstance(session_id, str):
        return {'valid': False, 'message': 'Session ID is required'}
    
    session_id = session_id.strip()
    
    # Session ID should be alphanumeric and reasonable length
    if not re.match(r'^[a-zA-Z0-9_-]{8,64}$', session_id):
        return {'valid': False, 'message': 'Invalid session ID format'}
    
    return {'valid': True, 'message': 'Valid session ID', 'session_id': session_id}

def validate_user_id(user_id: str) -> Dict[str, Any]:
    """Validate user ID format"""
    if not user_id or not isinstance(user_id, str):
        return {'valid': False, 'message': 'User ID is required'}
    
    user_id = user_id.strip()
    
    # User ID should be alphanumeric and reasonable length
    if not re.match(r'^[a-zA-Z0-9_-]{3,64}$', user_id):
        return {'valid': False, 'message': 'Invalid user ID format'}
    
    return {'valid': True, 'message': 'Valid user ID', 'user_id': user_id}

def validate_text_length(text: str, min_length: int = 0, max_length: int = 1000, field_name: str = 'text') -> Dict[str, Any]:
    """Validate text length"""
    if text is None:
        if min_length > 0:
            return {'valid': False, 'message': f'{field_name} is required'}
        else:
            return {'valid': True, 'message': 'Valid (empty) text', 'text': ''}
    
    if not isinstance(text, str):
        return {'valid': False, 'message': f'{field_name} must be a string'}
    
    text_length = len(text.strip())
    
    if text_length < min_length:
        return {'valid': False, 'message': f'{field_name} must be at least {min_length} characters'}
    
    if text_length > max_length:
        return {'valid': False, 'message': f'{field_name} must be no more than {max_length} characters'}
    
    return {'valid': True, 'message': f'Valid {field_name}', 'text': text.strip()}

def validate_integer(value: Any, min_value: int = None, max_value: int = None, field_name: str = 'value') -> Dict[str, Any]:
    """Validate integer value"""
    if value is None:
        return {'valid': False, 'message': f'{field_name} is required'}
    
    try:
        int_value = int(value)
    except (ValueError, TypeError):
        return {'valid': False, 'message': f'{field_name} must be an integer'}
    
    if min_value is not None and int_value < min_value:
        return {'valid': False, 'message': f'{field_name} must be at least {min_value}'}
    
    if max_value is not None and int_value > max_value:
        return {'valid': False, 'message': f'{field_name} must be no more than {max_value}'}
    
    return {'valid': True, 'message': f'Valid {field_name}', 'value': int_value}

def validate_float(value: Any, min_value: float = None, max_value: float = None, field_name: str = 'value') -> Dict[str, Any]:
    """Validate float value"""
    if value is None:
        return {'valid': False, 'message': f'{field_name} is required'}
    
    try:
        float_value = float(value)
    except (ValueError, TypeError):
        return {'valid': False, 'message': f'{field_name} must be a number'}
    
    if min_value is not None and float_value < min_value:
        return {'valid': False, 'message': f'{field_name} must be at least {min_value}'}
    
    if max_value is not None and float_value > max_value:
        return {'valid': False, 'message': f'{field_name} must be no more than {max_value}'}
    
    return {'valid': True, 'message': f'Valid {field_name}', 'value': float_value}

def validate_boolean(value: Any, field_name: str = 'value') -> Dict[str, Any]:
    """Validate boolean value"""
    if value is None:
        return {'valid': False, 'message': f'{field_name} is required'}
    
    if isinstance(value, bool):
        return {'valid': True, 'message': f'Valid {field_name}', 'value': value}
    
    if isinstance(value, str):
        if value.lower() in ['true', '1', 'yes', 'on']:
            return {'valid': True, 'message': f'Valid {field_name}', 'value': True}
        elif value.lower() in ['false', '0', 'no', 'off']:
            return {'valid': True, 'message': f'Valid {field_name}', 'value': False}
    
    return {'valid': False, 'message': f'{field_name} must be a boolean value'}

def validate_datetime(value: Any, field_name: str = 'datetime') -> Dict[str, Any]:
    """Validate datetime value"""
    if value is None:
        return {'valid': False, 'message': f'{field_name} is required'}
    
    if isinstance(value, datetime):
        return {'valid': True, 'message': f'Valid {field_name}', 'value': value}
    
    if isinstance(value, str):
        # Try to parse ISO format
        try:
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return {'valid': True, 'message': f'Valid {field_name}', 'value': dt}
        except ValueError:
            pass
        
        # Try other common formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d',
            '%m/%d/%Y',
            '%d/%m/%Y'
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(value, fmt)
                return {'valid': True, 'message': f'Valid {field_name}', 'value': dt}
            except ValueError:
                continue
    
    return {'valid': False, 'message': f'{field_name} must be a valid datetime'}

def validate_choice(value: Any, choices: List[Any], field_name: str = 'value') -> Dict[str, Any]:
    """Validate that value is in allowed choices"""
    if value is None:
        return {'valid': False, 'message': f'{field_name} is required'}
    
    if value not in choices:
        return {
            'valid': False,
            'message': f'{field_name} must be one of: {", ".join(map(str, choices))}'
        }
    
    return {'valid': True, 'message': f'Valid {field_name}', 'value': value}

def validate_file_size(file_size: int, max_size: int = 16777216, field_name: str = 'file') -> Dict[str, Any]:
    """Validate file size (default max 16MB)"""
    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        return {'valid': False, 'message': f'{field_name} size must be less than {max_mb:.1f}MB'}
    
    return {'valid': True, 'message': f'Valid {field_name} size'}

def validate_file_extension(filename: str, allowed_extensions: List[str], field_name: str = 'file') -> Dict[str, Any]:
    """Validate file extension"""
    if not filename or '.' not in filename:
        return {'valid': False, 'message': f'{field_name} must have a valid extension'}
    
    extension = filename.rsplit('.', 1)[1].lower()
    
    if extension not in [ext.lower() for ext in allowed_extensions]:
        return {
            'valid': False,
            'message': f'{field_name} must have one of these extensions: {", ".join(allowed_extensions)}'
        }
    
    return {'valid': True, 'message': f'Valid {field_name} extension', 'extension': extension}

def sanitize_input(value: str, max_length: int = 1000) -> str:
    """Sanitize user input by removing potentially harmful content"""
    if not isinstance(value, str):
        return str(value)[:max_length]
    
    # Remove potentially harmful