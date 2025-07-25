from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from app.models import User, SocialConnection, Post, NotificationToken, RefreshToken
from app.schemas import UserCreate, UserUpdate, SocialPlatform
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return db.query(User).offset(skip).limit(limit).all()


def create_user(db: Session, user: UserCreate) -> User:
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        name=user.name,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: int, user_update: UserUpdate) -> Optional[User]:
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    
    update_data = user_update.model_dump(exclude_unset=True)
    
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int) -> bool:
    db_user = get_user(db, user_id)
    if not db_user:
        return False
    
    db.delete(db_user)
    db.commit()
    return True


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def delete_user_by_facebook_id(db: Session, facebook_user_id: str) -> dict:
    """
    Delete all user data associated with a Facebook user ID.
    
    This function is called by the Facebook data deletion callback when:
    1. A user removes the app from their Facebook account
    2. A user deletes their Facebook account
    3. A user requests data deletion through Facebook
    
    Args:
        db: Database session
        facebook_user_id: The app-scoped Facebook user ID from the deletion request
    
    Returns:
        dict: Summary of deletion results
    """
    try:
        # Find the user by their Facebook social connection
        facebook_connection = db.query(SocialConnection).filter(
            and_(
                SocialConnection.platform == SocialPlatform.FACEBOOK,
                SocialConnection.platform_user_id == facebook_user_id
            )
        ).first()
        
        if not facebook_connection:
            # User not found - this is okay, might have been deleted already
            return {
                "status": "not_found",
                "message": f"No user found with Facebook ID: {facebook_user_id}",
                "deleted_records": 0
            }
        
        user = facebook_connection.user
        user_id = user.id
        deletion_summary = {
            "status": "success",
            "user_id": user_id,
            "facebook_user_id": facebook_user_id,
            "deleted_records": 0
        }
        
        # Delete all associated data in the correct order (respecting foreign key constraints)
        
        # 1. Delete notification tokens
        notification_tokens_count = db.query(NotificationToken).filter(
            NotificationToken.user_id == user_id
        ).count()
        db.query(NotificationToken).filter(
            NotificationToken.user_id == user_id
        ).delete(synchronize_session=False)
        deletion_summary["deleted_records"] += notification_tokens_count
        
        # 2. Delete refresh tokens
        refresh_tokens_count = db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id
        ).count()
        db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id
        ).delete(synchronize_session=False)
        deletion_summary["deleted_records"] += refresh_tokens_count
        
        # 3. Delete posts (this will cascade to post_targets due to foreign key constraints)
        posts_count = db.query(Post).filter(
            Post.user_id == user_id
        ).count()
        db.query(Post).filter(
            Post.user_id == user_id
        ).delete(synchronize_session=False)
        deletion_summary["deleted_records"] += posts_count
        
        # 4. Delete social connections (including the Facebook connection)
        social_connections_count = db.query(SocialConnection).filter(
            SocialConnection.user_id == user_id
        ).count()
        db.query(SocialConnection).filter(
            SocialConnection.user_id == user_id
        ).delete(synchronize_session=False)
        deletion_summary["deleted_records"] += social_connections_count
        
        # 5. Finally, delete the user record
        db.delete(user)
        deletion_summary["deleted_records"] += 1
        
        # Commit all deletions
        db.commit()
        
        deletion_summary["message"] = f"Successfully deleted all data for user {user_id}"
        
        # Log the deletion for audit purposes
        print(f"Facebook data deletion completed: {deletion_summary}")
        
        return deletion_summary
        
    except Exception as e:
        # Rollback any partial changes
        db.rollback()
        error_summary = {
            "status": "error",
            "facebook_user_id": facebook_user_id,
            "error": str(e),
            "deleted_records": 0
        }
        
        print(f"Facebook data deletion failed: {error_summary}")
        return error_summary
