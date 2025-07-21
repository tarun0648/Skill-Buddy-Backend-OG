# utils/encryption.py
import os
import base64
import hashlib
import secrets

class EncryptionUtils:
    
    def __init__(self, key=None):
        self.key = key or 'default-key'
    
    def encrypt(self, data: str) -> str:
        """Simple base64 encoding (for demo purposes)"""
        if not data:
            return data
        try:
            encoded = base64.b64encode(data.encode()).decode()
            return encoded
        except Exception:
            return data
    
    def decrypt(self, encrypted_data: str) -> str:
        """Simple base64 decoding (for demo purposes)"""
        if not encrypted_data:
            return encrypted_data
        try:
            decoded = base64.b64decode(encrypted_data.encode()).decode()
            return decoded
        except Exception:
            return encrypted_data
    
    def encrypt_dict(self, data: dict, fields_to_encrypt: list) -> dict:
        """Encrypt specific fields in a dictionary"""
        encrypted_data = data.copy()
        for field in fields_to_encrypt:
            if field in encrypted_data and encrypted_data[field]:
                encrypted_data[field] = self.encrypt(str(encrypted_data[field]))
        return encrypted_data
    
    def decrypt_dict(self, data: dict, fields_to_decrypt: list) -> dict:
        """Decrypt specific fields in a dictionary"""
        decrypted_data = data.copy()
        for field in fields_to_decrypt:
            if field in decrypted_data and decrypted_data[field]:
                decrypted_data[field] = self.decrypt(decrypted_data[field])
        return decrypted_data

# Global encryption instance
encryption_utils = EncryptionUtils()