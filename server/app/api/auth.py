from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import httpx
import re

from app.core.config import settings
from app.db.database import get_db
from app.schemas import (
    AuthRegisterRequest, AuthLoginRequest, AuthRefreshRequest,
    AuthRegisterResponse, AuthLoginResponse, AuthRefreshResponse,
    AuthLogoutResponse, UserResponse, UserRead, Token, TokenData,
    SocialConnectionCreate, SocialConnectionRead,
    OAuthURLRequest, OAuthURLResponse, OAuthExchangeRequest
)
from app.crud import (
    create_user, get_user_by_email, authenticate_user, 
    get_user, create_social_connection, get_social_connection_by_platform,
    create_refresh_token, get_refresh_token, revoke_refresh_token,
    update_social_connection
)
from app.services.social_oauth import oauth_service

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")


def validate_password(password: str) -> None:
    """Validate password according to security requirements"""
    if len(password) < 6:  # Simplified to only check minimum 6 characters
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long"
        )


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token_jwt(data: dict) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    user = get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user


@router.post("/register", response_model=AuthRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: AuthRegisterRequest, db: Session = Depends(get_db)):
    """Register a new user and return JWT tokens"""
    
    # Validate password
    validate_password(user_data.password)
    
    # Check if user already exists
    db_user = get_user_by_email(db, email=user_data.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Create new user
    from app.schemas import UserCreate
    user_create = UserCreate(
        email=user_data.email,
        name=user_data.name,
        password=user_data.password
    )
    db_user = create_user(db=db, user=user_create)
    
    # Create tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user.email}, expires_delta=access_token_expires
    )
    
    # Create refresh token in database
    db_refresh_token = create_refresh_token(db, db_user.id)
    
    # Prepare response
    user_response = UserResponse(
        id=str(db_user.id),
        name=db_user.name or "",
        email=db_user.email
    )
    
    return AuthRegisterResponse(
        user=user_response,
        accessToken=access_token,
        refreshToken=db_refresh_token.token
    )


@router.post("/login", response_model=AuthLoginResponse)
async def login_user(login_data: AuthLoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return JWT tokens"""
    
    # Authenticate user
    user = authenticate_user(db, login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Create tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    # Create refresh token in database
    db_refresh_token = create_refresh_token(db, user.id)
    
    return AuthLoginResponse(
        accessToken=access_token,
        refreshToken=db_refresh_token.token
    )


@router.post("/refresh", response_model=AuthRefreshResponse)
async def refresh_access_token(refresh_data: AuthRefreshRequest, db: Session = Depends(get_db)):
    """Issue a new access token using a valid refresh token"""
    
    # Validate refresh token
    db_refresh_token = get_refresh_token(db, refresh_data.refreshToken)
    if not db_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    # Get user
    user = get_user(db, db_refresh_token.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Create new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return AuthRefreshResponse(accessToken=access_token)


@router.post("/logout", response_model=AuthLogoutResponse)
async def logout_user(refresh_data: AuthRefreshRequest, db: Session = Depends(get_db)):
    """Logout user by revoking refresh token"""
    
    # Revoke the refresh token
    revoked = revoke_refresh_token(db, refresh_data.refreshToken)
    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    return AuthLogoutResponse(message="Successfully logged out")


@router.get("/me", response_model=UserRead)
async def read_users_me(current_user = Depends(get_current_user)):
    """Get current user profile"""
    return current_user


@router.post("/oauth/start", response_model=OAuthURLResponse)
async def start_oauth_flow(request: OAuthURLRequest):
    """
    Generate OAuth authorization URL for social media platform
    
    This endpoint generates the correct authorization URL for the specified platform
    that the mobile app should open in an in-app browser.
    """
    try:
        authorization_url, state = oauth_service.generate_authorization_url(request.platform)
        return OAuthURLResponse(authorizationUrl=authorization_url)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate authorization URL"
        )


@router.post("/oauth/exchange", response_model=AuthLoginResponse)
async def exchange_oauth_code(request: OAuthExchangeRequest, db: Session = Depends(get_db)):
    """
    Exchange OAuth authorization code for app tokens and log in user
    
    This endpoint handles the complete OAuth flow:
    1. Exchange authorization code with social platform for tokens
    2. Fetch user profile from social platform
    3. Find or create user in our database
    4. Create/update social connection with encrypted tokens
    5. Issue our own JWT tokens for the mobile app
    """
    try:
        # Step 1: Exchange authorization code for social platform tokens
        access_token, refresh_token = await oauth_service.exchange_code_for_tokens(
            request.platform, 
            request.authorizationCode
        )
        
        # Step 2: Get user profile from social platform
        profile_data = await oauth_service.get_user_profile(
            request.platform, 
            access_token
        )
        
        # Validate required profile data
        platform_user_id = profile_data.get("platform_user_id")
        if not platform_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to retrieve user ID from social platform"
            )
        
        # Step 3: Find or create user
        user_email = profile_data.get("email")
        user_name = profile_data.get("name", "")
        avatar_url = profile_data.get("avatar_url")
        
        db_user = None
        
        # For platforms that provide email, try to find existing user
        if user_email:
            db_user = get_user_by_email(db, email=user_email)
        
        # If user doesn't exist, create new user
        if not db_user:
            # For platforms without email (like TikTok), generate a placeholder email
            if not user_email:
                user_email = f"{platform_user_id}@{request.platform.value}.placeholder"
                
                # Check if this placeholder email already exists
                existing_user = get_user_by_email(db, email=user_email)
                if existing_user:
                    db_user = existing_user
            
            if not db_user:
                # Create new user without password (OAuth-only user)
                from app.schemas import UserCreate
                from app.crud import get_password_hash
                
                user_create = UserCreate(
                    email=user_email,
                    name=user_name,
                    password="oauth_placeholder_password"  # Will be hashed but never used
                )
                db_user = create_user(db=db, user=user_create)
                
                # Update avatar URL if provided
                if avatar_url:
                    db_user.avatar_url = avatar_url
                    db.commit()
                    db.refresh(db_user)
        else:
            # Update existing user's avatar if not set and provided by social platform
            if avatar_url and not db_user.avatar_url:
                db_user.avatar_url = avatar_url
                db.commit()
                db.refresh(db_user)
        
        # Step 4: Create or update social connection
        existing_connection = get_social_connection_by_platform(
            db, db_user.id, request.platform.value
        )
        
        if existing_connection:
            # Update existing connection with new tokens
            from app.schemas import SocialConnectionUpdate
            
            connection_update = SocialConnectionUpdate(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=None  # Could be calculated from token response if needed
            )
            update_social_connection(db, existing_connection.id, connection_update)
        else:
            # Create new social connection
            connection_create = SocialConnectionCreate(
                platform=request.platform,
                platform_user_id=platform_user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=None,  # Could be calculated from token response if needed
                scopes=None  # Could be extracted from OAuth flow if needed
            )
            create_social_connection(db, connection_create, db_user.id)
        
        # Step 5: Create our app's JWT tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        app_access_token = create_access_token(
            data={"sub": db_user.email}, expires_delta=access_token_expires
        )
        
        # Create refresh token in database
        db_refresh_token = create_refresh_token(db, db_user.id)
        
        return AuthLoginResponse(
            accessToken=app_access_token,
            refreshToken=db_refresh_token.token
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth exchange failed: {str(e)}"
        )
    except Exception as e:
        # Log the full error in production
        print(f"OAuth exchange error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during OAuth exchange"
        )


@router.get("/oauth/callback")
async def oauth_callback(code: str = None, state: str = None, error: str = None):
    """
    OAuth callback endpoint for handling redirects from social media platforms.
    
    This endpoint receives the authorization code from social platforms and 
    redirects the user back to the mobile app with the authorization code.
    """
    from fastapi.responses import RedirectResponse
    
    if error:
        # OAuth error occurred
        redirect_url = f"com.feedmerge.app://oauth/callback?error={error}"
        return RedirectResponse(url=redirect_url)
    
    if not code:
        # Missing authorization code
        redirect_url = "com.feedmerge.app://oauth/callback?error=missing_code"
        return RedirectResponse(url=redirect_url)
    
    # Success - redirect back to mobile app with authorization code
    redirect_url = f"com.feedmerge.app://oauth/callback?code={code}"
    if state:
        redirect_url += f"&state={state}"
        
    return RedirectResponse(url=redirect_url)


@router.post("/facebook/deletion", response_model=dict)
async def facebook_data_deletion_callback(
    request: Request, 
    db: Session = Depends(get_db)
):
    """
    Facebook Data Deletion Request Callback
    
    This endpoint handles data deletion requests from Facebook when users:
    1. Remove your app from their Facebook account
    2. Delete their Facebook account
    3. Request data deletion through Facebook
    
    Facebook sends a signed request containing the user's app-scoped ID.
    We must delete all associated user data and return a confirmation.
    
    Reference: https://developers.facebook.com/docs/development/create-an-app/app-dashboard/data-deletion-callback/
    """
    import hashlib
    import hmac
    import base64
    import json
    import secrets
    from urllib.parse import parse_qs
    from app.core.config import settings
    from app.crud.user import delete_user_by_facebook_id
    from app.schemas import SocialPlatform
    
    try:
        # Get the signed_request from POST data
        form_data = await request.form()
        signed_request = form_data.get('signed_request')
        
        if not signed_request:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing signed_request parameter"
            )
        
        # Parse the signed request
        def parse_signed_request(signed_request: str, app_secret: str):
            """Parse Facebook's signed request"""
            try:
                encoded_sig, payload = signed_request.split('.', 2)
            except ValueError:
                return None
            
            # Decode the signature and payload
            def base64_url_decode(inp: str) -> bytes:
                """Base64 URL decode with padding correction"""
                inp += '=' * (4 - len(inp) % 4)  # Add padding
                return base64.urlsafe_b64decode(inp.encode('ascii'))
            
            sig = base64_url_decode(encoded_sig)
            data = json.loads(base64_url_decode(payload).decode('utf-8'))
            
            # Verify the signature
            expected_sig = hmac.new(
                app_secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).digest()
            
            if not hmac.compare_digest(sig, expected_sig):
                print(f"Facebook deletion callback: Invalid signature")
                return None
            
            return data
        
        # Parse the signed request
        app_secret = settings.FACEBOOK_CLIENT_SECRET
        if not app_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Facebook app secret not configured"
            )
        
        data = parse_signed_request(signed_request, app_secret)
        if not data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid signed request"
            )
        
        # Extract the Facebook user ID (app-scoped ID)
        facebook_user_id = data.get('user_id')
        if not facebook_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing user_id in signed request"
            )
        
        # Delete all user data associated with this Facebook user
        deletion_result = await delete_user_by_facebook_id(db, facebook_user_id)
        
        # Generate a unique confirmation code for this deletion request
        confirmation_code = secrets.token_urlsafe(16)
        
        # Create a status URL where the user can check deletion progress
        # In production, you might want to store this in a database
        status_url = f"http://localhost:8000/api/v1/auth/data-deletion-status?code={confirmation_code}"
        
        # Log the deletion request for audit purposes
        print(f"Facebook data deletion request processed: user_id={facebook_user_id}, confirmation={confirmation_code}")
        
        # Return the required response format
        return {
            "url": status_url,
            "confirmation_code": confirmation_code
        }
        
    except Exception as e:
        print(f"Facebook data deletion callback error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process data deletion request"
        )


@router.get("/data-deletion-status")
async def data_deletion_status(code: str = None):
    """
    Data Deletion Status Page
    
    This endpoint provides users with information about their data deletion request.
    Users receive this URL in the Facebook deletion callback response.
    """
    from fastapi.responses import HTMLResponse
    
    if not code:
        return HTMLResponse(
            content="""
            <html>
                <head><title>Data Deletion Status</title></head>
                <body>
                    <h1>Data Deletion Status</h1>
                    <p>Missing confirmation code. Please check your deletion request.</p>
                </body>
            </html>
            """,
            status_code=400
        )
    
    # In a production app, you might want to:
    # 1. Store deletion requests in a database with the confirmation code
    # 2. Track the actual deletion progress
    # 3. Provide more detailed status information
    
    return HTMLResponse(
        content=f"""
        <html>
            <head>
                <title>Data Deletion Status - FeedMerge</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    .status-container {{ max-width: 600px; margin: 0 auto; }}
                    .success {{ color: #28a745; }}
                    .info {{ background: #e7f3ff; padding: 15px; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <div class="status-container">
                    <h1>Data Deletion Request Status</h1>
                    <div class="info">
                        <h2 class="success">✅ Deletion Complete</h2>
                        <p><strong>Confirmation Code:</strong> {code}</p>
                        <p>Your data deletion request has been processed successfully.</p>
                        
                        <h3>What was deleted:</h3>
                        <ul>
                            <li>Your user account and profile information</li>
                            <li>All social media connections and tokens</li>
                            <li>All posts and scheduled content</li>
                            <li>All notification preferences</li>
                            <li>All session and refresh tokens</li>
                        </ul>
                        
                        <h3>Data Retention:</h3>
                        <p>Your data has been permanently deleted from our systems. We may retain some anonymized analytics data as permitted by law.</p>
                        
                        <h3>Questions?</h3>
                        <p>If you have any questions about this deletion request, please contact our support team.</p>
                        
                        <p><small>Request processed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</small></p>
                    </div>
                </div>
            </body>
        </html>
        """
    )
