#!/usr/bin/env python3
"""
Utility script to generate encryption keys for FeedMerge application.
"""

import secrets
import string
from cryptography.fernet import Fernet


def generate_secret_key(length=32):
    """Generate a random secret key for JWT signing"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_encryption_key():
    """Generate a Fernet encryption key for token encryption"""
    return Fernet.generate_key().decode()


def main():
    print("🔐 FeedMerge Security Key Generator")
    print("=" * 40)
    
    secret_key = generate_secret_key()
    encryption_key = generate_encryption_key()
    
    print(f"SECRET_KEY={secret_key}")
    print(f"TOKEN_ENCRYPTION_KEY={encryption_key}")
    
    print("\n📝 Add these to your .env file:")
    print("=" * 40)
    print(f"SECRET_KEY={secret_key}")
    print(f"TOKEN_ENCRYPTION_KEY={encryption_key}")
    
    print("\n⚠️  Keep these keys secure and never commit them to version control!")


if __name__ == "__main__":
    main()
