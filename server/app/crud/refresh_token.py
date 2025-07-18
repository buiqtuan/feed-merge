from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
from typing import Optional
import secrets

from app.models import RefreshToken, User
from app.core.config import settings


def create_refresh_token(db: Session, user_id: int) -> RefreshToken:
    """Create a new refresh token for a user"""
    # Generate a secure random token
    token = secrets.token_urlsafe(32)
    
    # Calculate expiration date
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    db_refresh_token = RefreshToken(
        token=token,
        user_id=user_id,
        expires_at=expires_at
    )
    
    db.add(db_refresh_token)
    db.commit()
    db.refresh(db_refresh_token)
    return db_refresh_token


def get_refresh_token(db: Session, token: str) -> Optional[RefreshToken]:
    """Get a refresh token by token string"""
    return db.query(RefreshToken).filter(
        and_(
            RefreshToken.token == token,
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > datetime.utcnow()
        )
    ).first()


def revoke_refresh_token(db: Session, token: str) -> bool:
    """Revoke a refresh token"""
    db_token = db.query(RefreshToken).filter(
        and_(
            RefreshToken.token == token,
            RefreshToken.is_revoked == False
        )
    ).first()
    if db_token:
        db_token.is_revoked = True
        db.commit()
        return True
    return False


def revoke_user_refresh_tokens(db: Session, user_id: int) -> int:
    """Revoke all refresh tokens for a user (logout from all devices)"""
    count = db.query(RefreshToken).filter(
        and_(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False
        )
    ).update({"is_revoked": True})
    db.commit()
    return count


def cleanup_expired_tokens(db: Session) -> int:
    """Remove expired refresh tokens from database"""
    count = db.query(RefreshToken).filter(
        RefreshToken.expires_at <= datetime.utcnow()
    ).delete()
    db.commit()
    return count


def is_token_valid(db: Session, token: str) -> bool:
    """Check if a refresh token is valid"""
    return get_refresh_token(db, token) is not None 