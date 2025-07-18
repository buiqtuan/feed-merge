from sqlalchemy.orm import Session
from typing import List, Optional
from app.models import NotificationToken
from app.schemas import NotificationTokenCreate, NotificationTokenUpdate


def get_notification_token(db: Session, token_id: int) -> Optional[NotificationToken]:
    return db.query(NotificationToken).filter(NotificationToken.id == token_id).first()


def get_user_notification_tokens(db: Session, user_id: int) -> List[NotificationToken]:
    return db.query(NotificationToken).filter(
        NotificationToken.user_id == user_id,
        NotificationToken.is_active == True
    ).all()


def get_notification_token_by_token(db: Session, token: str) -> Optional[NotificationToken]:
    return db.query(NotificationToken).filter(NotificationToken.token == token).first()


def create_notification_token(db: Session, token: NotificationTokenCreate, user_id: int) -> NotificationToken:
    # Check if token already exists and update it if so
    existing_token = get_notification_token_by_token(db, token.token)
    if existing_token:
        existing_token.user_id = user_id
        existing_token.device_type = token.device_type
        existing_token.device_id = token.device_id
        existing_token.is_active = True
        db.commit()
        db.refresh(existing_token)
        return existing_token
    
    db_token = NotificationToken(
        token=token.token,
        device_type=token.device_type,
        device_id=token.device_id,
        user_id=user_id
    )
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return db_token


def update_notification_token(db: Session, token_id: int, token_update: NotificationTokenUpdate) -> Optional[NotificationToken]:
    db_token = get_notification_token(db, token_id)
    if not db_token:
        return None
    
    update_data = token_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(db_token, field, value)
    
    db.commit()
    db.refresh(db_token)
    return db_token


def delete_notification_token(db: Session, token_id: int) -> bool:
    db_token = get_notification_token(db, token_id)
    if not db_token:
        return False
    
    # Soft delete
    db_token.is_active = False
    db.commit()
    return True


def delete_notification_token_by_token(db: Session, token: str) -> bool:
    db_token = get_notification_token_by_token(db, token)
    if not db_token:
        return False
    
    # Soft delete
    db_token.is_active = False
    db.commit()
    return True
