from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas import NotificationTokenCreate, NotificationTokenRead
from app.crud.notification_token import create_notification_token
from app.api.auth import get_current_user
from app.models import User

router = APIRouter()

@router.get("/")
async def get_users():
    return {"message": "Get users endpoint"}

@router.get("/{user_id}")
async def get_user(user_id: int):
    return {"message": f"Get user {user_id} endpoint"}

@router.put("/{user_id}")
async def update_user(user_id: int):
    return {"message": f"Update user {user_id} endpoint"}

@router.post("/notification-token", response_model=NotificationTokenRead)
async def create_user_notification_token(
    token_data: NotificationTokenCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create or update a notification token for the current user
    """
    try:
        notification_token = create_notification_token(
            db=db,
            token=token_data,
            user_id=current_user.id
        )
        return notification_token
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save notification token: {str(e)}"
        )
