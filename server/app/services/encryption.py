from cryptography.fernet import Fernet
from app.core.config import settings
import base64
import os
from typing import Optional


class TokenEncryption:
    """Utility class for encrypting and decrypting OAuth tokens"""
    
    def __init__(self):
        # Generate or get encryption key from environment
        # In production, this should be stored securely
        if hasattr(settings, 'TOKEN_ENCRYPTION_KEY') and settings.TOKEN_ENCRYPTION_KEY:
            self.key = settings.TOKEN_ENCRYPTION_KEY.encode()
        else:
            # Generate a key for development (not recommended for production)
            self.key = Fernet.generate_key()
        
        self.cipher_suite = Fernet(self.key)
    
    def encrypt_token(self, token: str) -> str:
        """Encrypt a token string"""
        if not token:
            return ""
        
        token_bytes = token.encode('utf-8')
        encrypted_token = self.cipher_suite.encrypt(token_bytes)
        return base64.b64encode(encrypted_token).decode('utf-8')
    
    def decrypt_token(self, encrypted_token: str) -> Optional[str]:
        """Decrypt a token string"""
        if not encrypted_token:
            return None
        
        try:
            encrypted_bytes = base64.b64decode(encrypted_token.encode('utf-8'))
            decrypted_bytes = self.cipher_suite.decrypt(encrypted_bytes)
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            # Log the error in production
            print(f"Token decryption failed: {e}")
            return None
    
    @classmethod
    def generate_key(cls) -> str:
        """Generate a new encryption key (for setup purposes)"""
        return Fernet.generate_key().decode()


# Global instance
token_encryption = TokenEncryption()


def encrypt_access_token(token: str) -> str:
    """Encrypt an access token"""
    return token_encryption.encrypt_token(token)


def decrypt_access_token(encrypted_token: str) -> Optional[str]:
    """Decrypt an access token"""
    return token_encryption.decrypt_token(encrypted_token)


def encrypt_refresh_token(token: str) -> str:
    """Encrypt a refresh token"""
    return token_encryption.encrypt_token(token)


def decrypt_refresh_token(encrypted_token: str) -> Optional[str]:
    """Decrypt a refresh token"""
    return token_encryption.decrypt_token(encrypted_token)
