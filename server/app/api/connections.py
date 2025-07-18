from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import httpx

from app.core.config import settings
from app.db.database import get_db
from app.api.auth import get_current_user
from app.models import User
from app.schemas import (
    ConnectionsListResponse, ConnectionsOAuthStartRequest, ConnectionsOAuthStartResponse,
    ConnectionsOAuthExchangeRequest, ConnectionsOAuthExchangeResponse,
    SocialConnectionCreate, SocialConnectionUpdate
)
from app.crud import (
    get_user_social_connections, get_social_connection, 
    create_social_connection, get_social_connection_by_platform,
    update_social_connection, delete_social_connection
)
from app.services.social_oauth import oauth_service
from app.services.oauth_state import oauth_state_service

router = APIRouter()


@router.get("/", response_model=List[ConnectionsListResponse])
async def get_connected_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get Connected Accounts
    
    Fetches a list of the user's currently connected social accounts and their status.
    All endpoints are protected and require a valid JWT from our application.
    """
    # Get user's active social connections
    connections = get_user_social_connections(db, current_user.id)
    
    # Convert to response format
    response_connections = []
    for conn in connections:
        response_connections.append(ConnectionsListResponse(
            id=conn.id,
            platform=conn.platform,
            platform_username=conn.platform_username,
            platform_avatar_url=conn.platform_avatar_url
        ))
    
    return response_connections


@router.post("/oauth/start", response_model=ConnectionsOAuthStartResponse)
async def initiate_oauth_flow(
    request: ConnectionsOAuthStartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initiate OAuth Authorization Flow
    
    Generates the unique, secure authorization URL for the user to begin the connection process.
    Implements CSRF protection using a cryptographically secure state parameter.
    """
    try:
        # Store state in database for CSRF protection
        stored_state = oauth_state_service.create_state(
            db=db,
            user_id=current_user.id,
            platform=request.platform
        )
        
        # Generate authorization URL with temporary state
        authorization_url, temp_state = oauth_service.generate_authorization_url(
            request.platform, 
            current_user.id
        )
        
        # Replace the generated state with our stored state in the URL
        authorization_url = authorization_url.replace(f"state={temp_state}", f"state={stored_state}")
        
        return ConnectionsOAuthStartResponse(authorizationUrl=authorization_url)
        
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


@router.post("/oauth/exchange", response_model=ConnectionsOAuthExchangeResponse, status_code=status.HTTP_201_CREATED)
async def exchange_authorization_code(
    request: ConnectionsOAuthExchangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Exchange Authorization Code & Finalize Connection
    
    The final, critical step. Receives the authorizationCode and state from client,
    validates them, and securely completes the connection with proper CSRF protection.
    """
    try:
        # Step 1: CSRF Check - Validate state parameter
        is_valid_state = oauth_state_service.validate_state(
            db=db,
            user_id=current_user.id,
            platform=request.platform,
            state=request.state
        )
        
        if not is_valid_state:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or expired state parameter - potential CSRF attack"
            )
        
        # Step 2: Server-to-Server Call - Exchange authorization code for tokens
        access_token, refresh_token = await oauth_service.exchange_code_for_tokens(
            request.platform,
            request.authorizationCode
        )
        
        # Step 3: Server-to-Server Call - Fetch user profile from platform
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
        
        # Extract profile information
        platform_username = profile_data.get("platform_username")
        platform_avatar_url = profile_data.get("avatar_url")
        
        # Get granted scopes (this would ideally come from the OAuth response)
        # For now, we'll use the requested scopes as granted scopes
        from app.services.social_oauth import OAuthConfig
        config = OAuthConfig.get_platform_config(request.platform)
        granted_scopes = config["scope"].split(" ") if "scope" in config else []
        
        # Step 4: Database Upsert - Find or create social connection
        existing_connection = get_social_connection_by_platform(
            db, current_user.id, request.platform
        )
        
        if existing_connection:
            # Update existing connection with new tokens and profile info
            connection_update = SocialConnectionUpdate(
                access_token=access_token,
                refresh_token=refresh_token,
                platform_username=platform_username,
                platform_avatar_url=platform_avatar_url,
                scopes=granted_scopes,
                is_active=True
            )
            db_connection = update_social_connection(db, existing_connection.id, connection_update)
        else:
            # Create new social connection
            connection_create = SocialConnectionCreate(
                platform=request.platform,
                platform_user_id=platform_user_id,
                platform_username=platform_username,
                platform_avatar_url=platform_avatar_url,
                access_token=access_token,
                refresh_token=refresh_token,
                scopes=granted_scopes
            )
            db_connection = create_social_connection(db, connection_create, current_user.id)
        
        # Step 5: Return connection details for UI update
        return ConnectionsOAuthExchangeResponse(
            id=db_connection.id,
            platform=db_connection.platform,
            platform_username=db_connection.platform_username,
            platform_avatar_url=db_connection.platform_avatar_url
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete OAuth connection"
        )


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_social_account(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disconnect a Social Account
    
    Allows a user to remove a connected social account from the application.
    Includes ownership verification and optional platform token revocation.
    """
    # Find the social connection
    db_connection = get_social_connection(db, connection_id)
    if not db_connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Social connection not found"
        )
    
    # Ownership check - verify user owns this connection
    if db_connection.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to disconnect this account"
        )
    
    # Optional: Revoke tokens on the social platform
    # This would require platform-specific revocation endpoints
    # For now, we'll just deactivate the connection in our database
    
    try:
        # Attempt to revoke tokens on social platforms if they support it
        from app.crud.social_connection import get_decrypted_tokens
        access_token, refresh_token = get_decrypted_tokens(db_connection)
        
        if access_token:
            await _revoke_platform_tokens(db_connection.platform, access_token)
        
    except Exception as e:
        # Log the error but don't fail the disconnection
        # The main goal is to remove the connection from our database
        print(f"Failed to revoke platform tokens: {e}")
    
    # Delete the connection from our database
    success = delete_social_connection(db, connection_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disconnect social account"
        )
    
    # Return 204 No Content on success (no response body)
    return None


async def _revoke_platform_tokens(platform, access_token: str):
    """
    Helper function to revoke tokens on social platforms
    This is optional and platform-specific
    """
    try:
        if platform.value == "google":
            # Google token revocation
            async with httpx.AsyncClient() as client:
                await client.post(
                    "https://oauth2.googleapis.com/revoke",
                    data={"token": access_token}
                )
        elif platform.value == "facebook":
            # Facebook token revocation
            async with httpx.AsyncClient() as client:
                await client.delete(
                    f"https://graph.facebook.com/me/permissions?access_token={access_token}"
                )
        # TikTok doesn't have a standard revocation endpoint
        # Other platforms can be added here
        
    except Exception as e:
        # Log but don't propagate the error
        print(f"Platform token revocation failed: {e}")
