# routes/auth_routes.py (UPDATED - Added Phone OTP Authentication)
from flask import Blueprint, request, jsonify
from config.firebase_config import firebase_config
from models.user_model import UserModel
from utils.validation import Validator
from services.email_service import email_service
from services.otp_service import otp_service
from datetime import datetime, timedelta
import logging
import secrets
import hashlib
from werkzeug.security import generate_password_hash
import os

# Create blueprint
auth_bp = Blueprint('auth', __name__)

# Initialize components
db = firebase_config.get_db()
if db:
    user_model = UserModel(db)
else:
    user_model = None

logger = logging.getLogger(__name__)

def generate_reset_token():
    """Generate a secure password reset token"""
    return secrets.token_urlsafe(32)

def hash_token(token):
    """Hash a token for secure storage"""
    return hashlib.sha256(token.encode()).hexdigest()

# ==================== EMAIL AUTHENTICATION ====================

@auth_bp.route('/register', methods=['POST'])
def register():
    """User registration endpoint with welcome email - NO NAME REQUIRED"""
    try:
        print("[DEBUG] Registration request received")
        
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
            
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        print(f"[DEBUG] Registration data: {data}")
        
        # Updated validation - only email and password required
        required_fields = ['email', 'password']
        missing_fields = Validator.validate_required_fields(data, required_fields)
        if missing_fields:
            return jsonify({'error': f'Required fields missing: {", ".join(missing_fields)}'}), 400
        
        # Validate email format
        email = data['email'].lower().strip()
        if not Validator.validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Validate password strength
        password = data['password']
        password_validation = Validator.validate_password(password)
        if not password_validation['valid']:
            return jsonify({'error': password_validation['message']}), 400
        
        # Name is optional now
        name = data.get('name', '').strip() if data.get('name') else ''
        
        # Check if user already exists
        existing_user = user_model.get_user_by_email(email)
        if existing_user:
            return jsonify({'error': 'User already exists'}), 409
        
        # Create user data
        user_data = {
            'email': email,
            'password': password,
            'name': name,  # Can be empty string
            'sso_provider': 'email',
            'is_verified': False,
            'initial_xp': 10  # Registration bonus
        }
        
        # Create user
        user_id = user_model.create_user(user_data)
        print(f"[DEBUG] Created user with ID: {user_id}")
        
        # Send welcome email (always attempt, even without name)
        email_sent = False
        try:
            if email_service.enabled:
                # Use email as display name if no name provided
                display_name = name if name else email.split('@')[0].title()
                email_sent = email_service.send_welcome_email(email, display_name)
                if email_sent:
                    logger.info(f"Welcome email sent to {email}")
                else:
                    logger.warning(f"Failed to send welcome email to {email}")
        except Exception as e:
            logger.error(f"Error sending welcome email: {e}")
            # Don't fail registration if email fails
        
        # Get user data for response
        user = user_model.get_user_by_id(user_id)
        
        logger.info(f"User registered successfully: {email}")
        
        response_data = {
            'message': 'User registered successfully',
            'user_id': user_id,
            'user': {
                'id': user_id,
                'email': email,
                'profile': user.get('profile', {}) if user else {}
            },
            'email_sent': email_sent
        }
        
        print(f"[DEBUG] Registration response: {response_data}")
        return jsonify(response_data), 201
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        print(f"[DEBUG] Registration error: {str(e)}")
        return jsonify({'error': 'Registration failed', 'details': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        print("[DEBUG] Login request received")
        
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
            
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        print(f"[DEBUG] Login data: {data}")
        
        # Validate required fields
        required_fields = ['email', 'password']
        missing_fields = Validator.validate_required_fields(data, required_fields)
        if missing_fields:
            return jsonify({'error': f'Required fields missing: {", ".join(missing_fields)}'}), 400
        
        email = data['email'].lower().strip()
        password = data['password']
        
        # Find user
        user = user_model.get_user_by_email(email)
        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        print(f"[DEBUG] Found user: {user['id']}")
        
        # Check if user uses email authentication
        if user.get('sso_provider') != 'email':
            return jsonify({'error': 'Please use Google Sign-In for this account'}), 400
        
        # Verify password
        from werkzeug.security import check_password_hash
        if not check_password_hash(user.get('password', ''), password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Update last login
        user_model.update_user(user['id'], {'last_login': datetime.utcnow()})
        
        logger.info(f"User logged in: {email}")
        
        response_data = {
            'message': 'Login successful',
            'user_id': user['id'],
            'user': {
                'id': user['id'],
                'email': email,
                'profile': user.get('profile', {})
            }
        }
        
        print(f"[DEBUG] Login response: {response_data}")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        print(f"[DEBUG] Login error: {str(e)}")
        return jsonify({'error': 'Login failed', 'details': str(e)}), 500

# ==================== PHONE OTP AUTHENTICATION ====================

@auth_bp.route('/phone/send-otp', methods=['POST'])
def send_phone_otp():
    """Send OTP to phone number for login/signup"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
            
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        phone = data.get('phone', '').strip()
        purpose = data.get('purpose', 'login')  # 'login' or 'signup'
        method = data.get('method', 'sms')  # 'sms' or 'whatsapp'
        
        if not phone:
            return jsonify({'error': 'Phone number is required'}), 400
        
        if purpose not in ['login', 'signup']:
            return jsonify({'error': 'Purpose must be either login or signup'}), 400
        
        if method not in ['sms', 'whatsapp']:
            return jsonify({'error': 'Method must be either sms or whatsapp'}), 400
        
        # Validate phone number
        if not otp_service.is_valid_phone_number(phone):
            return jsonify({'error': 'Invalid phone number format'}), 400
        
        formatted_phone = otp_service.format_phone_number(phone)
        
        # Check if user exists for login/signup flow
        existing_user = user_model.get_user_by_phone(formatted_phone)
        
        if purpose == 'login' and not existing_user:
            return jsonify({'error': 'No account found with this phone number. Please sign up first.'}), 404
        
        if purpose == 'signup' and existing_user:
            return jsonify({'error': 'Account already exists with this phone number. Please login instead.'}), 409
        
        # Send OTP
        success, message = otp_service.send_otp(formatted_phone, purpose, method)
        
        if success:
            logger.info(f"OTP sent for {purpose} to {formatted_phone} via {method}")
            return jsonify({
                'message': message,
                'phone': formatted_phone,
                'purpose': purpose,
                'method': method,
                'expires_in_minutes': otp_service.otp_expiry_minutes
            }), 200
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        logger.error(f"Send phone OTP error: {str(e)}")
        return jsonify({'error': 'Failed to send OTP', 'details': str(e)}), 500

@auth_bp.route('/phone/verify-otp', methods=['POST'])
def verify_phone_otp():
    """Verify OTP and complete login/signup"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
            
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        phone = data.get('phone', '').strip()
        otp = data.get('otp', '').strip()
        purpose = data.get('purpose', 'login')
        name = data.get('name', '').strip()  # For signup
        
        if not phone or not otp:
            return jsonify({'error': 'Phone number and OTP are required'}), 400
        
        if purpose not in ['login', 'signup']:
            return jsonify({'error': 'Purpose must be either login or signup'}), 400
        
        formatted_phone = otp_service.format_phone_number(phone)
        
        # Verify OTP
        otp_valid, otp_message = otp_service.verify_otp(formatted_phone, otp, purpose)
        
        if not otp_valid:
            return jsonify({'error': otp_message}), 400
        
        # OTP is valid, proceed with login/signup
        if purpose == 'signup':
            # Create new user account
            user_data = {
                'phone': formatted_phone,
                'name': name,
                'sso_provider': 'phone',
                'is_verified': True,  # Phone is already verified via OTP
                'initial_xp': 10  # Registration bonus
            }
            
            user_id = user_model.create_user(user_data)
            
            # Get user data for response
            user = user_model.get_user_by_id(user_id)
            
            logger.info(f"User registered successfully via phone: {formatted_phone}")
            
            return jsonify({
                'message': 'Account created and login successful',
                'user_id': user_id,
                'user': {
                    'id': user_id,
                    'phone': formatted_phone,
                    'profile': user.get('profile', {}) if user else {}
                },
                'is_new_user': True
            }), 201
            
        else:  # purpose == 'login'
            # Find existing user
            user = user_model.get_user_by_phone(formatted_phone)
            
            if not user:
                return jsonify({'error': 'Account not found'}), 404
            
            # Update last login
            user_model.update_user(user['id'], {'last_login': datetime.utcnow()})
            
            logger.info(f"User logged in via phone: {formatted_phone}")
            
            return jsonify({
                'message': 'Login successful',
                'user_id': user['id'],
                'user': {
                    'id': user['id'],
                    'phone': formatted_phone,
                    'profile': user.get('profile', {})
                },
                'is_new_user': False
            }), 200
            
    except Exception as e:
        logger.error(f"Verify phone OTP error: {str(e)}")
        return jsonify({'error': 'OTP verification failed', 'details': str(e)}), 500

@auth_bp.route('/phone/resend-otp', methods=['POST'])
def resend_phone_otp():
    """Resend OTP to phone number"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        phone = data.get('phone', '').strip()
        purpose = data.get('purpose', 'login')
        method = data.get('method', 'sms')
        
        if not phone:
            return jsonify({'error': 'Phone number is required'}), 400
        
        formatted_phone = otp_service.format_phone_number(phone)
        
        # Send new OTP
        success, message = otp_service.send_otp(formatted_phone, purpose, method)
        
        if success:
            logger.info(f"OTP resent for {purpose} to {formatted_phone} via {method}")
            return jsonify({
                'message': 'OTP resent successfully',
                'phone': formatted_phone,
                'method': method,
                'expires_in_minutes': otp_service.otp_expiry_minutes
            }), 200
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        logger.error(f"Resend phone OTP error: {str(e)}")
        return jsonify({'error': 'Failed to resend OTP', 'details': str(e)}), 500

# ==================== EXISTING EMAIL ENDPOINTS ====================

@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    """Change user password endpoint with email notification"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
            
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        user_id = data.get('user_id')
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not user_id or not current_password or not new_password:
            return jsonify({'error': 'User ID, current password and new password are required'}), 400
        
        # Validate new password
        password_validation = Validator.validate_password(new_password)
        if not password_validation['valid']:
            return jsonify({'error': password_validation['message']}), 400
        
        # Get user
        user = user_model.get_user_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if user uses email authentication
        if user.get('sso_provider') != 'email':
            return jsonify({'error': 'Cannot change password for SSO accounts'}), 400
        
        # Verify current password
        from werkzeug.security import check_password_hash, generate_password_hash
        if not check_password_hash(user.get('password', ''), current_password):
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Update password
        new_password_hash = generate_password_hash(new_password)
        success = user_model.update_user(user_id, {
            'password': new_password_hash,
            'password_changed_at': datetime.utcnow()
        })
        
        if not success:
            return jsonify({'error': 'Failed to update password'}), 500
        
        # Send password change notification email (non-blocking)
        email_sent = False
        try:
            user_profile = user.get('profile', {})
            user_name = user_profile.get('name', '')
            user_email = user.get('email', '')
            
            if email_service.enabled and user_email:
                # Use email as display name if no name in profile
                display_name = user_name if user_name else user_email.split('@')[0].title()
                email_sent = email_service.send_password_change_notification(user_email, display_name)
                if email_sent:
                    logger.info(f"Password change notification sent to {user_email}")
                else:
                    logger.warning(f"Failed to send password change notification to {user_email}")
        except Exception as e:
            logger.error(f"Error sending password change notification: {e}")
            # Don't fail password change if email fails
        
        logger.info(f"Password changed for user: {user_id}")
        
        return jsonify({
            'message': 'Password changed successfully',
            'email_sent': email_sent
        }), 200
        
    except Exception as e:
        logger.error(f"Change password error: {str(e)}")
        return jsonify({'error': 'Failed to change password', 'details': str(e)}), 500

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Initiate password reset process"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
            
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        email = data.get('email')
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        email = email.lower().strip()
        
        # Validate email format
        if not Validator.validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Find user
        user = user_model.get_user_by_email(email)
        if not user:
            # For security, don't reveal if email exists
            return jsonify({'message': 'If the email exists, a reset link has been sent'}), 200
        
        # Check if user uses email authentication
        if user.get('sso_provider') != 'email':
            return jsonify({'message': 'If the email exists, a reset link has been sent'}), 200
        
        # Generate reset token
        reset_token = generate_reset_token()
        hashed_token = hash_token(reset_token)
        
        # Set token expiration (1 hour)
        expiration_time = datetime.utcnow() + timedelta(hours=1)
        
        # Store reset token in user record
        success = user_model.update_user(user['id'], {
            'password_reset_token': hashed_token,
            'password_reset_expires': expiration_time,
            'password_reset_requested_at': datetime.utcnow()
        })
        
        if not success:
            return jsonify({'error': 'Failed to generate reset token'}), 500
        
        # Send password reset email
        email_sent = False
        try:
            user_profile = user.get('profile', {})
            user_name = user_profile.get('name', '')
            
            if email_service.enabled:
                # You can customize the reset URL based on your frontend
                frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
                reset_url = f"{frontend_url}/reset-password?token={reset_token}"
                
                # Use email as display name if no name in profile
                display_name = user_name if user_name else email.split('@')[0].title()
                email_sent = email_service.send_password_reset_email(email, display_name, reset_token, reset_url)
                
                if email_sent:
                    logger.info(f"Password reset email sent to {email}")
                else:
                    logger.warning(f"Failed to send password reset email to {email}")
                    return jsonify({'error': 'Failed to send reset email'}), 500
            else:
                logger.warning("Email service disabled, cannot send reset email")
                return jsonify({'error': 'Email service not available'}), 503
                
        except Exception as e:
            logger.error(f"Error sending password reset email: {e}")
            return jsonify({'error': 'Failed to send reset email'}), 500
        
        logger.info(f"Password reset initiated for: {email}")
        
        return jsonify({
            'message': 'Password reset email sent successfully',
            'expires_in': '1 hour',
            'email_sent': email_sent
        }), 200
        
    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}")
        return jsonify({'error': 'Failed to process password reset request', 'details': str(e)}), 500

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password using token"""
    try:
        if not user_model:
            return jsonify({'error': 'Database not available'}), 500
            
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        reset_token = data.get('token')
        new_password = data.get('new_password')
        
        if not reset_token or not new_password:
            return jsonify({'error': 'Reset token and new password are required'}), 400
        
        # Validate new password
        password_validation = Validator.validate_password(new_password)
        if not password_validation['valid']:
            return jsonify({'error': password_validation['message']}), 400
        
        # Hash the provided token
        hashed_token = hash_token(reset_token)
        
        # Find user with this reset token
        user = user_model.get_user_by_reset_token(hashed_token)
        
        if not user:
            return jsonify({'error': 'Invalid or expired reset token'}), 400
        
        # Check if token is expired
        reset_expires = user.get('password_reset_expires')
        if not reset_expires or datetime.utcnow() > reset_expires:
            return jsonify({'error': 'Reset token has expired'}), 400
        
        # Update password and clear reset token
        new_password_hash = generate_password_hash(new_password)
        success = user_model.update_user(user['id'], {
            'password': new_password_hash,
            'password_reset_token': None,
            'password_reset_expires': None,
            'password_reset_requested_at': None,
            'password_changed_at': datetime.utcnow()
        })
        
        if not success:
            return jsonify({'error': 'Failed to reset password'}), 500
        
        # Send password change confirmation email
        email_sent = False
        try:
            user_profile = user.get('profile', {})
            user_name = user_profile.get('name', '')
            user_email = user.get('email', '')
            
            if email_service.enabled and user_email:
                # Use email as display name if no name in profile
                display_name = user_name if user_name else user_email.split('@')[0].title()
                email_sent = email_service.send_password_change_notification(user_email, display_name)
                if email_sent:
                    logger.info(f"Password reset confirmation sent to {user_email}")
                else:
                    logger.warning(f"Failed to send password reset confirmation to {user_email}")
        except Exception as e:
            logger.error(f"Error sending password reset confirmation: {e}")
            # Don't fail password reset if email fails
        
        logger.info(f"Password reset completed for user: {user['id']}")
        
        return jsonify({
            'message': 'Password reset successfully',
            'email_sent': email_sent
        }), 200
        
    except Exception as e:
        logger.error(f"Reset password error: {str(e)}")
        return jsonify({'error': 'Failed to reset password', 'details': str(e)}), 500

# ==================== TESTING AND DEBUG ENDPOINTS ====================

@auth_bp.route('/test-email', methods=['POST'])
def test_email():
    """Test email functionality (for development/testing)"""
    try:
        data = request.get_json()
        email = data.get('email') if data else None
        
        if not email:
            return jsonify({'error': 'Email address required for testing'}), 400
        
        if not email_service.enabled:
            return jsonify({'error': 'Email service is not configured'}), 503
        
        # Test connection first
        connection_ok = email_service.test_connection()
        if not connection_ok:
            return jsonify({'error': 'Email service connection failed'}), 503
        
        # Send test email - always use email as display name for test
        display_name = email.split('@')[0].title()
        success = email_service.send_welcome_email(email, display_name)
        
        if success:
            return jsonify({
                'message': 'Test email sent successfully',
                'email': email,
                'display_name_used': display_name,
                'smtp_server': email_service.smtp_server,
                'smtp_port': email_service.smtp_port
            }), 200
        else:
            return jsonify({'error': 'Failed to send test email'}), 500
        
    except Exception as e:
        logger.error(f"Test email error: {str(e)}")
        return jsonify({'error': 'Email test failed', 'details': str(e)}), 500

@auth_bp.route('/test-otp', methods=['POST'])
def test_otp():
    """Test OTP functionality (for development/testing)"""
    try:
        data = request.get_json()
        phone = data.get('phone') if data else None
        method = data.get('method', 'sms')
        
        if not phone:
            return jsonify({'error': 'Phone number required for testing'}), 400
        
        if not otp_service.sms_enabled and not otp_service.whatsapp_enabled:
            return jsonify({'error': 'OTP service is not configured'}), 503
        
        # Send test OTP
        success, message = otp_service.send_otp(phone, 'login', method)
        
        if success:
            return jsonify({
                'message': 'Test OTP sent successfully',
                'phone': otp_service.format_phone_number(phone),
                'method': method,
                'expires_in_minutes': otp_service.otp_expiry_minutes,
                'service_debug_info': otp_service.get_debug_info()
            }), 200
        else:
            return jsonify({
                'error': f'Failed to send test OTP: {message}',
                'service_debug_info': otp_service.get_debug_info()
            }), 500
        
    except Exception as e:
        logger.error(f"Test OTP error: {str(e)}")
        return jsonify({'error': 'OTP test failed', 'details': str(e)}), 500

@auth_bp.route('/debug/otp-config', methods=['GET'])
def debug_otp_config():
    """Debug OTP configuration - shows what's loaded"""
    try:
        debug_info = otp_service.get_debug_info()
        
        # Add environment variable check
        env_vars = {
            'TWILIO_ACCOUNT_SID': bool(os.environ.get('TWILIO_ACCOUNT_SID')),
            'TWILIO_AUTH_TOKEN': bool(os.environ.get('TWILIO_AUTH_TOKEN')),
            'TWILIO_PHONE_NUMBER': bool(os.environ.get('TWILIO_PHONE_NUMBER')),
            'SMS_API_KEY': bool(os.environ.get('SMS_API_KEY')),
            'SMS_SENDER_ID': os.environ.get('SMS_SENDER_ID', 'SKBUDY'),
            'MSG91_FLOW_ID': bool(os.environ.get('MSG91_FLOW_ID')),
            'WHATSAPP_ACCESS_TOKEN': bool(os.environ.get('WHATSAPP_ACCESS_TOKEN')),
            'WHATSAPP_PHONE_ID': bool(os.environ.get('WHATSAPP_PHONE_ID'))
        }
        
        recommendations = []
        
        if not debug_info['sms_enabled'] and not debug_info['whatsapp_enabled']:
            recommendations.append("Configure at least one SMS service (Twilio or MSG91) or WhatsApp Business API")
        
        if not debug_info['twilio_configured'] and not debug_info['msg91_configured']:
            recommendations.extend([
                "For Twilio: Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER",
                "For MSG91: Set SMS_API_KEY, SMS_SENDER_ID, MSG91_FLOW_ID"
            ])
        
        if not debug_info['whatsapp_configured']:
            recommendations.append("For WhatsApp: Set WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_ID")
        
        return jsonify({
            'otp_service_debug': debug_info,
            'environment_variables': env_vars,
            'recommendations': recommendations
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Debug failed',
            'details': str(e)
        }), 500

@auth_bp.route('/cleanup-expired-otps', methods=['POST'])
def cleanup_expired_otps():
    """Manually trigger cleanup of expired OTPs"""
    try:
        otp_service.cleanup_expired_otps()
        return jsonify({'message': 'Expired OTPs cleaned up successfully'}), 200
    except Exception as e:
        logger.error(f"Cleanup OTPs error: {str(e)}")
        return jsonify({'error': 'Failed to cleanup expired OTPs', 'details': str(e)}), 500