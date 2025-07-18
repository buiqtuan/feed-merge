from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
from typing import Optional
import secrets

from app.models import OAuthState
from app.schemas import SocialPlatform


class OAuthStateService:
    """Service for managing OAuth state tokens for CSRF protection"""
    
    @staticmethod
    def create_state(db: Session, user_id: int, platform: SocialPlatform, expires_minutes: int = 10) -> str:
        """
        Create a new OAuth state token for CSRF protection
        
        Args:
            db: Database session
            user_id: User ID who initiated OAuth flow
            platform: Social platform being connected
            expires_minutes: State expiration time in minutes (default 10 min)
        
        Returns:
            Generated state token string
        """
        # Generate cryptographically secure state token
        state = secrets.token_urlsafe(32)
        
        # Calculate expiration time
        expires_at = datetime.utcnow() + timedelta(minutes=expires_minutes)
        
        # Clean up any existing states for this user/platform combination
        OAuthStateService.cleanup_user_platform_states(db, user_id, platform)
        
        # Create new state record
        db_state = OAuthState(
            state=state,
            user_id=user_id,
            platform=platform,
            expires_at=expires_at
        )
        
        db.add(db_state)
        db.commit()
        db.refresh(db_state)
        
        return state
    
    @staticmethod
    def validate_state(db: Session, user_id: int, platform: SocialPlatform, state: str) -> bool:
        """
        Validate an OAuth state token
        
        Args:
            db: Database session
            user_id: User ID who initiated OAuth flow
            platform: Social platform being connected
            state: State token to validate
        
        Returns:
            True if state is valid, False otherwise
        """
        # Find the state record
        db_state = db.query(OAuthState).filter(
            and_(
                OAuthState.state == state,
                OAuthState.user_id == user_id,
                OAuthState.platform == platform,
                OAuthState.expires_at > datetime.utcnow()
            )
        ).first()
        
        if db_state:
            # State is valid, delete it (one-time use)
            db.delete(db_state)
            db.commit()
            return True
        
        return False
    
    @staticmethod
    def cleanup_user_platform_states(db: Session, user_id: int, platform: SocialPlatform) -> int:
        """
        Clean up existing states for a user/platform combination
        
        Args:
            db: Database session
            user_id: User ID
            platform: Social platform
        
        Returns:
            Number of states deleted
        """
        count = db.query(OAuthState).filter(
            and_(
                OAuthState.user_id == user_id,
                OAuthState.platform == platform
            )
        ).delete()
        
        db.commit()
        return count
    
    @staticmethod
    def cleanup_expired_states(db: Session) -> int:
        """
        Clean up all expired OAuth states
        
        Args:
            db: Database session
        
        Returns:
            Number of expired states deleted
        """
        count = db.query(OAuthState).filter(
            OAuthState.expires_at <= datetime.utcnow()
        ).delete()
        
        db.commit()
        return count


# Global service instance
oauth_state_service = OAuthStateService() 