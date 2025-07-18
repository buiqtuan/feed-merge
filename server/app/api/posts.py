from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import boto3
from botocore.exceptions import ClientError
import uuid
from datetime import datetime, timedelta

from app.core.config import settings
from app.db.database import get_db
from app.api.auth import get_current_user
from app.schemas import (
    PostCreate, PostRead, PostUpdate, PostWithTargets,
    UserRead
)
from app.crud import (
    create_post, get_post, get_user_posts, update_post, delete_post,
    get_user_social_connections
)

router = APIRouter()


@router.post("/upload-url")
async def generate_upload_url(
    filename: str,
    content_type: str,
    current_user: UserRead = Depends(get_current_user)
):
    """Generate a pre-signed URL for direct S3 upload"""
    
    if not all([settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY, settings.AWS_S3_BUCKET]):
        raise HTTPException(
            status_code=500,
            detail="AWS S3 not configured"
        )
    
    # Create S3 client
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION
    )
    
    # Generate unique file key
    file_extension = filename.split('.')[-1] if '.' in filename else ''
    unique_filename = f"uploads/{current_user.id}/{uuid.uuid4()}.{file_extension}"
    
    try:
        # Generate pre-signed URL for PUT operation
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': settings.AWS_S3_BUCKET,
                'Key': unique_filename,
                'ContentType': content_type
            },
            ExpiresIn=3600  # URL expires in 1 hour
        )
        
        # Generate the final file URL (where the file will be accessible)
        file_url = f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{unique_filename}"
        
        return {
            "upload_url": presigned_url,
            "file_url": file_url,
            "filename": unique_filename
        }
        
    except ClientError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate upload URL: {str(e)}"
        )


@router.post("/", response_model=PostWithTargets)
async def create_scheduled_post(
    post: PostCreate,
    background_tasks: BackgroundTasks,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new scheduled post"""
    
    # Validate target platforms belong to user
    if post.target_platforms:
        user_connections = get_user_social_connections(db, current_user.id)
        valid_connection_ids = {conn.id for conn in user_connections}
        
        for platform_id in post.target_platforms:
            if platform_id not in valid_connection_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid social connection ID: {platform_id}"
                )
    
    # Create the post
    db_post = create_post(db=db, post=post, user_id=current_user.id)
    
    # If scheduled for immediate posting, add to background tasks
    if post.scheduled_at and post.scheduled_at <= datetime.utcnow():
        from app.tasks.scheduler import publish_single_post
        background_tasks.add_task(publish_single_post, db_post.id)
    
    return db_post


@router.get("/", response_model=List[PostRead])
async def get_posts(
    skip: int = 0,
    limit: int = 100,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's posts"""
    posts = get_user_posts(db, user_id=current_user.id, skip=skip, limit=limit)
    return posts


@router.get("/{post_id}", response_model=PostWithTargets)
async def get_post_detail(
    post_id: int,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific post with targets"""
    db_post = get_post(db, post_id=post_id)
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check if post belongs to current user
    if db_post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this post")
    
    return db_post


@router.put("/{post_id}", response_model=PostRead)
async def update_post_endpoint(
    post_id: int,
    post_update: PostUpdate,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a post"""
    db_post = get_post(db, post_id=post_id)
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check if post belongs to current user
    if db_post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this post")
    
    # Don't allow updating published posts
    if db_post.status == "published":
        raise HTTPException(status_code=400, detail="Cannot update published posts")
    
    updated_post = update_post(db=db, post_id=post_id, post_update=post_update)
    return updated_post


@router.delete("/{post_id}")
async def delete_post_endpoint(
    post_id: int,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a post"""
    db_post = get_post(db, post_id=post_id)
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check if post belongs to current user
    if db_post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")
    
    success = delete_post(db=db, post_id=post_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete post")
    
    return {"message": "Post deleted successfully"}
