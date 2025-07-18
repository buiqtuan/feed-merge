from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from datetime import datetime
from app.models import SocialConnection
from app.schemas import SocialConnectionCreate, SocialConnectionUpdate
from app.services.encryption import encrypt_access_token, encrypt_refresh_token, decrypt_access_token, decrypt_refresh_token


def get_social_connection(db: Session, connection_id: int) -> Optional[SocialConnection]:
    return db.query(SocialConnection).filter(SocialConnection.id == connection_id).first()


def get_user_social_connections(db: Session, user_id: int) -> List[SocialConnection]:
    return db.query(SocialConnection).filter(
        and_(SocialConnection.user_id == user_id, SocialConnection.is_active == True)
    ).all()


def get_social_connection_by_platform(db: Session, user_id: int, platform: str) -> Optional[SocialConnection]:
    return db.query(SocialConnection).filter(
        and_(
            SocialConnection.user_id == user_id,
            SocialConnection.platform == platform,
            SocialConnection.is_active == True
        )
    ).first()


def create_social_connection(db: Session, connection: SocialConnectionCreate, user_id: int) -> SocialConnection:
    encrypted_access_token = encrypt_access_token(connection.access_token)
    encrypted_refresh_token = None
    if connection.refresh_token:
        encrypted_refresh_token = encrypt_refresh_token(connection.refresh_token)
    
    db_connection = SocialConnection(
        platform=connection.platform,
        platform_user_id=connection.platform_user_id,
        platform_username=connection.platform_username,
        platform_avatar_url=connection.platform_avatar_url,
        encrypted_access_token=encrypted_access_token,
        encrypted_refresh_token=encrypted_refresh_token,
        expires_at=connection.expires_at,
        scopes=connection.scopes,
        user_id=user_id
    )
    db.add(db_connection)
    db.commit()
    db.refresh(db_connection)
    return db_connection


def update_social_connection(db: Session, connection_id: int, connection_update: SocialConnectionUpdate) -> Optional[SocialConnection]:
    db_connection = get_social_connection(db, connection_id)
    if not db_connection:
        return None
    
    update_data = connection_update.model_dump(exclude_unset=True)
    
    # Handle token encryption
    if "access_token" in update_data:
        update_data["encrypted_access_token"] = encrypt_access_token(update_data.pop("access_token"))
    
    if "refresh_token" in update_data:
        refresh_token = update_data.pop("refresh_token")
        if refresh_token:
            update_data["encrypted_refresh_token"] = encrypt_refresh_token(refresh_token)
        else:
            update_data["encrypted_refresh_token"] = None
    
    for field, value in update_data.items():
        setattr(db_connection, field, value)
    
    db.commit()
    db.refresh(db_connection)
    return db_connection


def delete_social_connection(db: Session, connection_id: int) -> bool:
    db_connection = get_social_connection(db, connection_id)
    if not db_connection:
        return False
    
    # Soft delete
    db_connection.is_active = False
    db.commit()
    return True


def get_decrypted_tokens(db_connection: SocialConnection) -> tuple[Optional[str], Optional[str]]:
    """Get decrypted access and refresh tokens from a social connection"""
    access_token = decrypt_access_token(db_connection.encrypted_access_token)
    refresh_token = None
    if db_connection.encrypted_refresh_token:
        refresh_token = decrypt_refresh_token(db_connection.encrypted_refresh_token)
    
    return access_token, refresh_token
