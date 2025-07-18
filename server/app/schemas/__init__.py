from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class PostStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


class SocialPlatform(str, Enum):
    GOOGLE = "google"
    FACEBOOK = "facebook"
    TIKTOK = "tiktok"
    # Legacy platforms for future implementation
    TWITTER = "twitter"
    INSTAGRAM = "instagram" 
    LINKEDIN = "linkedin"
    YOUTUBE = "youtube"


# User schemas
class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    avatar_url: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    password: Optional[str] = None


class UserInDB(UserBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    hashed_password: str
    created_at: datetime
    updated_at: datetime
    is_active: bool


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool


# SocialConnection schemas
class SocialConnectionBase(BaseModel):
    platform: SocialPlatform
    platform_user_id: str
    platform_username: Optional[str] = None
    platform_avatar_url: Optional[str] = None
    scopes: Optional[List[str]] = None


class SocialConnectionCreate(SocialConnectionBase):
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None


class SocialConnectionUpdate(BaseModel):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    scopes: Optional[List[str]] = None
    platform_username: Optional[str] = None
    platform_avatar_url: Optional[str] = None
    is_active: Optional[bool] = None


class SocialConnectionInDB(SocialConnectionBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    encrypted_access_token: str
    encrypted_refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    user_id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool


class SocialConnectionRead(SocialConnectionBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool
    # Note: We don't expose encrypted tokens in read schemas


# Post schemas
class PostBase(BaseModel):
    content: str
    media_urls: Optional[List[str]] = None
    scheduled_at: Optional[datetime] = None


class PostCreate(PostBase):
    target_platforms: Optional[List[int]] = None  # List of social_connection_ids


class PostUpdate(BaseModel):
    content: Optional[str] = None
    media_urls: Optional[List[str]] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[PostStatus] = None


class PostInDB(PostBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    status: PostStatus
    published_at: Optional[datetime] = None
    user_id: int
    created_at: datetime
    updated_at: datetime


class PostRead(PostBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    status: PostStatus
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# PostTarget schemas
class PostTargetBase(BaseModel):
    pass


class PostTargetCreate(PostTargetBase):
    post_id: int
    social_connection_id: int


class PostTargetUpdate(BaseModel):
    status: Optional[PostStatus] = None
    platform_post_id: Optional[str] = None
    error_message: Optional[str] = None


class PostTargetInDB(PostTargetBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    post_id: int
    social_connection_id: int
    platform_post_id: Optional[str] = None
    status: PostStatus
    error_message: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class PostTargetRead(PostTargetBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    post_id: int
    social_connection_id: int
    platform_post_id: Optional[str] = None
    status: PostStatus
    error_message: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# NotificationToken schemas
class NotificationTokenBase(BaseModel):
    token: str
    device_type: Optional[str] = None
    device_id: Optional[str] = None


class NotificationTokenCreate(NotificationTokenBase):
    pass


class NotificationTokenUpdate(BaseModel):
    token: Optional[str] = None
    device_type: Optional[str] = None
    device_id: Optional[str] = None
    is_active: Optional[bool] = None


class NotificationTokenInDB(NotificationTokenBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class NotificationTokenRead(NotificationTokenBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# Extended schemas with relationships
class PostWithTargets(PostRead):
    post_targets: List[PostTargetRead] = []


class SocialConnectionWithUser(SocialConnectionRead):
    user: UserRead


class UserWithConnections(UserRead):
    social_connections: List[SocialConnectionRead] = []
    notification_tokens: List[NotificationTokenRead] = []


# New Authentication schemas matching API specification
class AuthRegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class AuthLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthRefreshRequest(BaseModel):
    refreshToken: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    avatar_url: Optional[str] = None


class AuthRegisterResponse(BaseModel):
    user: UserResponse
    accessToken: str
    refreshToken: str


class AuthLoginResponse(BaseModel):
    accessToken: str
    refreshToken: str


class AuthRefreshResponse(BaseModel):
    accessToken: str


class AuthLogoutResponse(BaseModel):
    message: str


# Authentication schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None


# OAuth schemas for social media authentication
class OAuthURLRequest(BaseModel):
    platform: SocialPlatform


class OAuthURLResponse(BaseModel):
    authorizationUrl: str


class OAuthExchangeRequest(BaseModel):
    platform: SocialPlatform
    authorizationCode: str


# New Connections API schemas
class ConnectionsListResponse(BaseModel):
    """Response schema for GET /connections - list of connected accounts"""
    id: int
    platform: SocialPlatform
    platform_username: Optional[str] = None
    platform_avatar_url: Optional[str] = None
    

class ConnectionsOAuthStartRequest(BaseModel):
    """Request schema for POST /connections/oauth/start"""
    platform: SocialPlatform


class ConnectionsOAuthStartResponse(BaseModel):
    """Response schema for POST /connections/oauth/start"""
    authorizationUrl: str


class ConnectionsOAuthExchangeRequest(BaseModel):
    """Request schema for POST /connections/oauth/exchange"""
    platform: SocialPlatform
    authorizationCode: str
    state: str


class ConnectionsOAuthExchangeResponse(BaseModel):
    """Response schema for POST /connections/oauth/exchange"""
    id: int
    platform: SocialPlatform
    platform_username: Optional[str] = None
    platform_avatar_url: Optional[str] = None
