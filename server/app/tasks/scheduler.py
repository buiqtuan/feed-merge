from celery import Celery
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging
import asyncio
from typing import List

from app.core.celery_app import celery_app
from app.db.database import SessionLocal
from app.models import Post, PostTarget, SocialConnection
from app.crud import get_scheduled_posts, update_post_target, get_decrypted_tokens
from app.services.social_publishers import get_publisher

logger = logging.getLogger(__name__)


def get_db() -> Session:
    """Get database session for Celery tasks"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # Don't close here, will be closed in task


@celery_app.task(name="app.tasks.scheduler.publish_scheduled_posts")
def publish_scheduled_posts():
    """
    Periodic task to publish scheduled posts
    Runs every minute via Celery Beat
    """
    db = get_db()
    
    try:
        # Get posts that are scheduled and ready to publish
        scheduled_posts = get_scheduled_posts(db)
        
        logger.info(f"Found {len(scheduled_posts)} scheduled posts to publish")
        
        for post in scheduled_posts:
            try:
                # Process each post
                publish_single_post.delay(post.id)
                
                # Update post status to prevent reprocessing
                post.status = "published"
                post.published_at = datetime.utcnow()
                db.commit()
                
            except Exception as e:
                logger.error(f"Error scheduling post {post.id}: {e}")
                post.status = "failed"
                db.commit()
        
        return f"Processed {len(scheduled_posts)} scheduled posts"
        
    except Exception as e:
        logger.error(f"Error in publish_scheduled_posts: {e}")
        return f"Error: {str(e)}"
    
    finally:
        db.close()


@celery_app.task(name="app.tasks.scheduler.publish_single_post")
def publish_single_post(post_id: int):
    """
    Publish a single post to all its target platforms
    """
    db = get_db()
    
    try:
        # Get the post with its targets
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            logger.error(f"Post {post_id} not found")
            return f"Post {post_id} not found"
        
        # Get all post targets
        post_targets = db.query(PostTarget).filter(PostTarget.post_id == post_id).all()
        
        logger.info(f"Publishing post {post_id} to {len(post_targets)} platforms")
        
        success_count = 0
        failure_count = 0
        
        for target in post_targets:
            try:
                # Get social connection
                social_connection = db.query(SocialConnection).filter(
                    SocialConnection.id == target.social_connection_id
                ).first()
                
                if not social_connection or not social_connection.is_active:
                    logger.warning(f"Invalid social connection {target.social_connection_id}")
                    target.status = "failed"
                    target.error_message = "Social connection not found or inactive"
                    db.commit()
                    failure_count += 1
                    continue
                
                # Get decrypted tokens
                tokens = get_decrypted_tokens(social_connection)
                
                if not tokens["access_token"]:
                    logger.error(f"Failed to decrypt access token for connection {social_connection.id}")
                    target.status = "failed"
                    target.error_message = "Failed to decrypt access token"
                    db.commit()
                    failure_count += 1
                    continue
                
                # Get publisher for the platform
                publisher = get_publisher(
                    platform=social_connection.platform.value,
                    access_token=tokens["access_token"],
                    platform_user_id=social_connection.platform_user_id,
                    refresh_token=tokens["refresh_token"]
                )
                
                # Publish the post
                result = asyncio.run(publisher.publish_post(
                    content=post.content,
                    media_urls=post.media_urls
                ))
                
                if result["success"]:
                    # Update target with success
                    target.status = "published"
                    target.platform_post_id = result["platform_post_id"]
                    target.published_at = datetime.utcnow()
                    target.error_message = None
                    success_count += 1
                    logger.info(f"Successfully published to {social_connection.platform.value}")
                    
                else:
                    # Update target with failure
                    target.status = "failed"
                    target.error_message = result.get("error", "Unknown error")
                    failure_count += 1
                    logger.error(f"Failed to publish to {social_connection.platform.value}: {result.get('error')}")
                
                db.commit()
                
            except Exception as e:
                logger.error(f"Error publishing to target {target.id}: {e}")
                target.status = "failed"
                target.error_message = str(e)
                db.commit()
                failure_count += 1
        
        # Update overall post status
        if success_count > 0 and failure_count == 0:
            post.status = "published"
        elif success_count > 0 and failure_count > 0:
            post.status = "published"  # Partial success still counts as published
        else:
            post.status = "failed"
        
        if not post.published_at and success_count > 0:
            post.published_at = datetime.utcnow()
        
        db.commit()
        
        return f"Post {post_id}: {success_count} successes, {failure_count} failures"
        
    except Exception as e:
        logger.error(f"Error in publish_single_post {post_id}: {e}")
        return f"Error publishing post {post_id}: {str(e)}"
    
    finally:
        db.close()


@celery_app.task(name="app.tasks.scheduler.refresh_expired_tokens")
def refresh_expired_tokens():
    """
    Periodic task to refresh expired OAuth tokens
    """
    db = get_db()
    
    try:
        # Get social connections with expired or soon-to-expire tokens
        expired_connections = db.query(SocialConnection).filter(
            SocialConnection.expires_at <= datetime.utcnow(),
            SocialConnection.is_active == True,
            SocialConnection.encrypted_refresh_token.isnot(None)
        ).all()
        
        logger.info(f"Found {len(expired_connections)} connections with expired tokens")
        
        refreshed_count = 0
        failed_count = 0
        
        for connection in expired_connections:
            try:
                tokens = get_decrypted_tokens(connection)
                
                if not tokens["refresh_token"]:
                    logger.warning(f"No refresh token for connection {connection.id}")
                    failed_count += 1
                    continue
                
                # Get publisher and refresh token
                publisher = get_publisher(
                    platform=connection.platform.value,
                    access_token=tokens["access_token"],
                    platform_user_id=connection.platform_user_id,
                    refresh_token=tokens["refresh_token"]
                )
                
                # Refresh the token (implementation depends on platform)
                new_tokens = asyncio.run(publisher.refresh_access_token())
                
                if new_tokens.get("access_token"):
                    # Update connection with new tokens
                    from app.crud.social_connection import update_social_connection
                    from app.schemas import SocialConnectionUpdate
                    
                    update_data = SocialConnectionUpdate(
                        access_token=new_tokens["access_token"],
                        refresh_token=new_tokens.get("refresh_token"),
                        expires_at=datetime.utcnow() + timedelta(seconds=new_tokens.get("expires_in", 3600))
                    )
                    
                    update_social_connection(db, connection.id, update_data)
                    refreshed_count += 1
                    logger.info(f"Refreshed token for connection {connection.id}")
                    
                else:
                    logger.error(f"Failed to refresh token for connection {connection.id}")
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"Error refreshing token for connection {connection.id}: {e}")
                failed_count += 1
        
        return f"Token refresh: {refreshed_count} successful, {failed_count} failed"
        
    except Exception as e:
        logger.error(f"Error in refresh_expired_tokens: {e}")
        return f"Error: {str(e)}"
    
    finally:
        db.close()
