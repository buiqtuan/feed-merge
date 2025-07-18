from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from datetime import datetime
from app.models import Post, PostTarget, SocialConnection
from app.schemas import PostCreate, PostUpdate, PostTargetCreate, PostTargetUpdate


def get_post(db: Session, post_id: int) -> Optional[Post]:
    return db.query(Post).filter(Post.id == post_id).first()


def get_user_posts(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Post]:
    return db.query(Post).filter(Post.user_id == user_id).offset(skip).limit(limit).all()


def create_post(db: Session, post: PostCreate, user_id: int) -> Post:
    db_post = Post(
        content=post.content,
        media_urls=post.media_urls,
        scheduled_at=post.scheduled_at,
        user_id=user_id
    )
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    
    # Create post targets if specified
    if post.target_platforms:
        for social_connection_id in post.target_platforms:
            # Verify the social connection belongs to the user
            social_connection = db.query(SocialConnection).filter(
                and_(
                    SocialConnection.id == social_connection_id,
                    SocialConnection.user_id == user_id,
                    SocialConnection.is_active == True
                )
            ).first()
            
            if social_connection:
                post_target = PostTarget(
                    post_id=db_post.id,
                    social_connection_id=social_connection_id
                )
                db.add(post_target)
        
        db.commit()
        db.refresh(db_post)
    
    return db_post


def update_post(db: Session, post_id: int, post_update: PostUpdate) -> Optional[Post]:
    db_post = get_post(db, post_id)
    if not db_post:
        return None
    
    update_data = post_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(db_post, field, value)
    
    db.commit()
    db.refresh(db_post)
    return db_post


def delete_post(db: Session, post_id: int) -> bool:
    db_post = get_post(db, post_id)
    if not db_post:
        return False
    
    db.delete(db_post)
    db.commit()
    return True


def get_scheduled_posts(db: Session) -> List[Post]:
    """Get posts that are scheduled but not yet published"""
    return db.query(Post).filter(
        and_(
            Post.status == "scheduled",
            Post.scheduled_at <= datetime.utcnow()
        )
    ).all()


# PostTarget CRUD
def get_post_target(db: Session, target_id: int) -> Optional[PostTarget]:
    return db.query(PostTarget).filter(PostTarget.id == target_id).first()


def get_post_targets(db: Session, post_id: int) -> List[PostTarget]:
    return db.query(PostTarget).filter(PostTarget.post_id == post_id).all()


def create_post_target(db: Session, target: PostTargetCreate) -> PostTarget:
    db_target = PostTarget(
        post_id=target.post_id,
        social_connection_id=target.social_connection_id
    )
    db.add(db_target)
    db.commit()
    db.refresh(db_target)
    return db_target


def update_post_target(db: Session, target_id: int, target_update: PostTargetUpdate) -> Optional[PostTarget]:
    db_target = get_post_target(db, target_id)
    if not db_target:
        return None
    
    update_data = target_update.model_dump(exclude_unset=True)
    
    # Set published_at when status changes to published
    if "status" in update_data and update_data["status"] == "published" and not db_target.published_at:
        update_data["published_at"] = datetime.utcnow()
    
    for field, value in update_data.items():
        setattr(db_target, field, value)
    
    db.commit()
    db.refresh(db_target)
    return db_target


def delete_post_target(db: Session, target_id: int) -> bool:
    db_target = get_post_target(db, target_id)
    if not db_target:
        return False
    
    db.delete(db_target)
    db.commit()
    return True
