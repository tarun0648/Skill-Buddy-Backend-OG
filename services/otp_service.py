# services/otp_service.py (FIXED - Firestore Index Compatible)
import os
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple
import logging
import requests
import json
from config.firebase_config import firebase_config
from firebase_admin import firestore

logger = logging.getLogger(__name__)

class OTPService:
    """Service for handling OTP generation, storage, and verification - FIXED for Firestore"""
    
    def __init__(self):
        self.db = firebase_config.get_db()
        self.collection_name = 'otp_codes'
        
        # Twilio configuration
        self.twilio_account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        self.twilio_auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        self.twilio_phone_number = os.environ.get('TWILIO_PHONE_NUMBER')
        
        # Alternative SMS service (like MSG91, TextLocal, etc.)
        self.sms_api_key = os.environ.get('SMS_API_KEY')
        self.sms_sender_id = os.environ.get('SMS_SENDER_ID', 'SKBUDY')
        
        # WhatsApp Business API (optional)
        self.whatsapp_token = os.environ.get('WHATSAPP_ACCESS_TOKEN')
        self.whatsapp_phone_id = os.environ.get('WHATSAPP_PHONE_ID')
        
        # OTP configuration
        self.otp_length = 6
        self.otp_expiry_minutes = 10
        self.max_attempts = 3
        self.rate_limit_minutes = 1  # Minimum time between OTP requests
        
        # Check which service is available
        self.sms_enabled = bool(self.twilio_account_sid and self.twilio_auth_token) or bool(self.sms_api_key)
        self.whatsapp_enabled = bool(self.whatsapp_token and self.whatsapp_phone_id)
        
        logger.info(f"OTP Service initialized - SMS: {self.sms_enabled}, WhatsApp: {self.whatsapp_enabled}")
    
    def generate_otp(self) -> str:
        """Generate a secure 6-digit OTP"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(self.otp_length)])
    
    def hash_otp(self, otp: str, phone: str) -> str:
        """Hash OTP for secure storage"""
        return hashlib.sha256(f"{otp}{phone}".encode()).hexdigest()
    
    def format_phone_number(self, phone: str) -> str:
        """Format phone number to international format"""
        # Remove all non-digit characters
        phone = ''.join(filter(str.isdigit, phone))
        
        # Add country code if not present (assuming India +91 as default)
        if not phone.startswith('91') and len(phone) == 10:
            phone = f"91{phone}"
        elif phone.startswith('0'):
            phone = f"91{phone[1:]}"
        
        return f"+{phone}"
    
    def is_valid_phone_number(self, phone: str) -> bool:
        """Validate phone number format"""
        # Remove all non-digit characters
        digits_only = ''.join(filter(str.isdigit, phone))
        
        # Check if it's a valid length (10-15 digits)
        return 10 <= len(digits_only) <= 15
    
    def can_send_otp(self, phone: str) -> Tuple[bool, str]:
        """Check if OTP can be sent (rate limiting) - FIXED to avoid index requirement"""
        try:
            if not self.db:
                return False, "Database not available"
            
            formatted_phone = self.format_phone_number(phone)
            
            # FIXED: Use simple query without ordering by timestamp to avoid composite index
            # Get all OTPs for this phone number and check in Python
            query = self.db.collection(self.collection_name)\
                .where(filter=firestore.FieldFilter('phone_number', '==', formatted_phone))\
                .where(filter=firestore.FieldFilter('is_active', '==', True))\
                .limit(10)  # Limit to recent entries
            
            docs = query.get()
            
            # Check rate limiting in Python
            recent_time = datetime.now(timezone.utc) - timedelta(minutes=self.rate_limit_minutes)
            
            for doc in docs:
                otp_data = doc.to_dict()
                created_at = otp_data.get('created_at')
                
                if created_at and created_at > recent_time:
                    return False, f"Please wait {self.rate_limit_minutes} minute(s) before requesting another OTP"
            
            return True, "OK"
            
        except Exception as e:
            logger.error(f"Error checking OTP rate limit: {e}")
            return False, "Rate limit check failed"
    
    def store_otp(self, phone: str, otp: str, purpose: str = 'login') -> bool:
        """Store OTP in database"""
        try:
            if not self.db:
                return False
            
            formatted_phone = self.format_phone_number(phone)
            hashed_otp = self.hash_otp(otp, formatted_phone)
            
            now = datetime.now(timezone.utc)
            otp_data = {
                'phone_number': formatted_phone,
                'otp_hash': hashed_otp,
                'purpose': purpose,  # 'login', 'signup', 'verification'
                'created_at': now,
                'expires_at': now + timedelta(minutes=self.otp_expiry_minutes),
                'attempts': 0,
                'is_verified': False,
                'is_active': True
            }
            
            # Delete any existing active OTPs for this phone (cleanup)
            existing_query = self.db.collection(self.collection_name)\
                .where(filter=firestore.FieldFilter('phone_number', '==', formatted_phone))\
                .where(filter=firestore.FieldFilter('is_active', '==', True))
            
            existing_docs = existing_query.get()
            for doc in existing_docs:
                doc.reference.update({'is_active': False})
            
            # Store new OTP
            self.db.collection(self.collection_name).add(otp_data)
            
            logger.info(f"OTP stored for phone: {formatted_phone}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing OTP: {e}")
            return False
    
    def send_sms_twilio(self, phone: str, message: str) -> bool:
        """Send SMS using Twilio"""
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_account_sid}/Messages.json"
            
            data = {
                'From': self.twilio_phone_number,
                'To': phone,
                'Body': message
            }
            
            response = requests.post(
                url,
                data=data,
                auth=(self.twilio_account_sid, self.twilio_auth_token),
                timeout=30
            )
            
            if response.status_code == 201:
                logger.info(f"SMS sent successfully via Twilio to {phone}")
                return True
            else:
                logger.error(f"Twilio SMS failed: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending SMS via Twilio: {e}")
            return False
    
    def send_sms_msg91(self, phone: str, message: str) -> bool:
        """Send SMS using MSG91 (Indian SMS service)"""
        try:
            # Remove country code for Indian numbers if using MSG91
            phone_number = phone[3:] if phone.startswith('+91') else phone
            
            url = "https://api.msg91.com/api/v5/flow/"
            
            payload = {
                "flow_id": os.environ.get('MSG91_FLOW_ID'),  # You need to create a flow in MSG91
                "sender": self.sms_sender_id,
                "mobiles": phone_number,
                "var1": message  # OTP message variable
            }
            
            headers = {
                "authkey": self.sms_api_key,
                "content-type": "application/json"
            }
            
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
            
            if response.status_code == 200:
                logger.info(f"SMS sent successfully via MSG91 to {phone}")
                return True
            else:
                logger.error(f"MSG91 SMS failed: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending SMS via MSG91: {e}")
            return False
    
    def send_whatsapp_message(self, phone: str, message: str) -> bool:
        """Send WhatsApp message using WhatsApp Business API"""
        try:
            url = f"https://graph.facebook.com/v17.0/{self.whatsapp_phone_id}/messages"
            
            headers = {
                "Authorization": f"Bearer {self.whatsapp_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "to": phone.replace('+', ''),
                "type": "text",
                "text": {
                    "body": message
                }
            }
            
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
            
            if response.status_code == 200:
                logger.info(f"WhatsApp message sent successfully to {phone}")
                return True
            else:
                logger.error(f"WhatsApp message failed: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            return False
    
    def send_otp(self, phone: str, purpose: str = 'login', method: str = 'sms') -> Tuple[bool, str]:
        """Send OTP via SMS or WhatsApp"""
        try:
            # Validate phone number
            if not self.is_valid_phone_number(phone):
                return False, "Invalid phone number format"
            
            formatted_phone = self.format_phone_number(phone)
            
            # Check rate limiting
            can_send, rate_limit_message = self.can_send_otp(formatted_phone)
            if not can_send:
                return False, rate_limit_message
            
            # Generate OTP
            otp = self.generate_otp()
            
            # Create message
            message = (
                f"Welcome to Skill Buddy! Your verification code is: {otp}."
                if purpose == 'signup'
                else f"Your Skill Buddy login code is: {otp}."
            )
            message += f" This code will expire in {self.otp_expiry_minutes} minutes. Do not share this code with anyone."
            
            # Send based on method
            sent = False
            if method == 'whatsapp' and self.whatsapp_enabled:
                sent = self.send_whatsapp_message(formatted_phone, message)
            elif method == 'sms' or not self.whatsapp_enabled:
                if self.twilio_account_sid and self.twilio_auth_token:
                    sent = self.send_sms_twilio(formatted_phone, message)
                elif self.sms_api_key:
                    sent = self.send_sms_msg91(formatted_phone, message)
                else:
                    return False, "SMS service not configured"
            
            if sent:
                # Store OTP in database
                if self.store_otp(formatted_phone, otp, purpose):
                    return True, f"OTP sent successfully via {method}"
                else:
                    return False, "Failed to store OTP"
            else:
                return False, f"Failed to send OTP via {method}"
                
        except Exception as e:
            logger.error(f"Error sending OTP: {e}")
            return False, "Failed to send OTP"
    
    def verify_otp(self, phone: str, otp: str, purpose: str = 'login') -> Tuple[bool, str]:
        """Verify OTP code - FIXED to avoid index requirement"""
        try:
            if not self.db:
                return False, "Database not available"
            
            formatted_phone = self.format_phone_number(phone)
            
            # FIXED: Simple query without ordering to avoid composite index
            query = self.db.collection(self.collection_name)\
                .where(filter=firestore.FieldFilter('phone_number', '==', formatted_phone))\
                .where(filter=firestore.FieldFilter('purpose', '==', purpose))\
                .where(filter=firestore.FieldFilter('is_active', '==', True))\
                .limit(5)  # Get recent entries
            
            docs = query.get()
            
            if not docs:
                return False, "No active OTP found for this phone number"
            
            # Find the most recent valid OTP by checking in Python
            valid_otp_doc = None
            for doc in docs:
                otp_data = doc.to_dict()
                if datetime.now(timezone.utc) <= otp_data['expires_at']:
                    valid_otp_doc = doc
                    break
            
            if not valid_otp_doc:
                return False, "OTP has expired. Please request a new one."
            
            otp_data = valid_otp_doc.to_dict()
            
            # Check attempts
            if otp_data['attempts'] >= self.max_attempts:
                valid_otp_doc.reference.update({'is_active': False})
                return False, "Maximum verification attempts exceeded. Please request a new OTP."
            
            # Verify OTP
            provided_otp_hash = self.hash_otp(otp, formatted_phone)
            
            if provided_otp_hash == otp_data['otp_hash']:
                # OTP is correct
                valid_otp_doc.reference.update({
                    'is_verified': True,
                    'is_active': False,
                    'verified_at': datetime.now(timezone.utc)
                })
                return True, "OTP verified successfully"
            else:
                # OTP is incorrect
                new_attempts = otp_data['attempts'] + 1
                valid_otp_doc.reference.update({'attempts': new_attempts})
                
                remaining_attempts = self.max_attempts - new_attempts
                if remaining_attempts > 0:
                    return False, f"Invalid OTP. {remaining_attempts} attempts remaining."
                else:
                    valid_otp_doc.reference.update({'is_active': False})
                    return False, "Invalid OTP. Maximum attempts exceeded. Please request a new OTP."
                    
        except Exception as e:
            logger.error(f"Error verifying OTP: {e}")
            return False, "OTP verification failed . Maximum attempts exceeded. Please request a new OTP."
                    
        except Exception as e:
            logger.error(f"Error verifying OTP: {e}")
            return False, "OTP verification failed"
    
    def cleanup_expired_otps(self):
        """Clean up expired OTPs (should be run periodically) - FIXED to avoid index requirement"""
        try:
            if not self.db:
                return
            
            # Get all active OTPs and check expiry in Python to avoid index
            query = self.db.collection(self.collection_name)\
                .where(filter=firestore.FieldFilter('is_active', '==', True))\
                .limit(1000)  # Process in batches
            
            docs = query.get()
            expired_count = 0
            
            for doc in docs:
                otp_data = doc.to_dict()
                if datetime.now(timezone.utc) > otp_data['expires_at']:
                    doc.reference.update({'is_active': False})
                    expired_count += 1
            
            logger.info(f"Cleaned up {expired_count} expired OTPs")
            
        except Exception as e:
            logger.error(f"Error cleaning up expired OTPs: {e}")
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information about OTP service configuration"""
        return {
            'sms_enabled': self.sms_enabled,
            'whatsapp_enabled': self.whatsapp_enabled,
            'twilio_configured': bool(self.twilio_account_sid and self.twilio_auth_token),
            'msg91_configured': bool(self.sms_api_key),
            'whatsapp_configured': bool(self.whatsapp_token and self.whatsapp_phone_id),
            'otp_length': self.otp_length,
            'otp_expiry_minutes': self.otp_expiry_minutes,
            'max_attempts': self.max_attempts,
            'rate_limit_minutes': self.rate_limit_minutes
        }

# Global OTP service instance
otp_service = OTPService()