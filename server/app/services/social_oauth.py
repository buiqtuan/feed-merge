"""
OAuth utilities for social media platform authentication
"""

import httpx
import secrets
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode
from app.core.config import settings
from app.schemas import SocialPlatform


class OAuthConfig:
    """OAuth configuration for different social media platforms"""
    
    @staticmethod
    def get_platform_config(platform: SocialPlatform) -> Dict[str, str]:
        """Get OAuth configuration for a specific platform"""
        
        base_redirect_uri = settings.OAUTH_REDIRECT_URI
        
        configs = {
            SocialPlatform.GOOGLE: {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "profile_url": "https://people.googleapis.com/v1/people/me",
                "redirect_uri": settings.GOOGLE_REDIRECT_URI or base_redirect_uri,
                "scope": "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/yt-analytics.readonly https://www.googleapis.com/auth/yt-analytics-monetary.readonly openid email profile",
                "response_type": "code",
                "access_type": "offline",
                "prompt": "consent"
            },
            SocialPlatform.FACEBOOK: {
                "client_id": settings.FACEBOOK_CLIENT_ID,
                "client_secret": settings.FACEBOOK_CLIENT_SECRET,
                "auth_url": "https://www.facebook.com/v18.0/dialog/oauth",
                "token_url": "https://graph.facebook.com/v18.0/oauth/access_token",
                "profile_url": "https://graph.facebook.com/me",
                "redirect_uri": settings.FACEBOOK_REDIRECT_URI or base_redirect_uri,
                "scope": "email,public_profile",
                "response_type": "code"
            },
            SocialPlatform.TIKTOK: {
                "client_id": settings.TIKTOK_CLIENT_ID,
                "client_secret": settings.TIKTOK_CLIENT_SECRET,
                "auth_url": "https://www.tiktok.com/auth/authorize/",
                "token_url": "https://open.tiktokapis.com/v2/oauth/token/",
                "profile_url": "https://open.tiktokapis.com/v2/user/info/",
                "redirect_uri": settings.TIKTOK_REDIRECT_URI or base_redirect_uri,
                "scope": "user.info.basic,user.info.stats,video.upload,video.list",
                "response_type": "code"
            }
        }
        
        config = configs.get(platform)
        if not config:
            raise ValueError(f"Unsupported platform: {platform}")
        
        # Validate required credentials
        if not config["client_id"] or not config["client_secret"]:
            raise ValueError(f"Missing OAuth credentials for platform: {platform}")
        
        return config


class OAuthService:
    """Service for handling OAuth flows"""
    
    @staticmethod
    def generate_authorization_url(platform: SocialPlatform, user_id: int = None) -> Tuple[str, str]:
        """Generate OAuth authorization URL for a platform and return URL with state"""
        
        config = OAuthConfig.get_platform_config(platform)
        
        # Generate state parameter for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Build query parameters
        params = {
            "client_id": config["client_id"],
            "redirect_uri": config["redirect_uri"],
            "scope": config["scope"],
            "response_type": config["response_type"],
            "state": state
        }
        
        # Add platform-specific parameters
        if platform == SocialPlatform.GOOGLE:
            params.update({
                "access_type": config["access_type"],
                "prompt": config["prompt"]
            })
        
        # Build authorization URL
        query_string = urlencode(params)
        url = f"{config['auth_url']}?{query_string}"
        
        return url, state
    
    @staticmethod
    async def exchange_code_for_tokens(
        platform: SocialPlatform, 
        authorization_code: str
    ) -> Tuple[str, Optional[str]]:
        """
        Exchange authorization code for access and refresh tokens
        Returns: (access_token, refresh_token)
        """
        
        config = OAuthConfig.get_platform_config(platform)
        
        # Prepare token exchange request
        token_data = {
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "code": authorization_code,
            "redirect_uri": config["redirect_uri"]
        }
        
        # Add platform-specific parameters
        if platform in [SocialPlatform.GOOGLE, SocialPlatform.FACEBOOK]:
            token_data["grant_type"] = "authorization_code"
        
        # Make token exchange request
        async with httpx.AsyncClient() as client:
            
            if platform == SocialPlatform.TIKTOK:
                # TikTok uses different request format
                headers = {"Content-Type": "application/x-www-form-urlencoded"}
                response = await client.post(
                    config["token_url"],
                    data=token_data,
                    headers=headers
                )
            else:
                # Google and Facebook
                response = await client.post(
                    config["token_url"],
                    data=token_data
                )
            
            if response.status_code != 200:
                raise ValueError(f"Token exchange failed: {response.text}")
            
            token_response = response.json()
            
            # Extract tokens (format varies by platform)
            access_token = token_response.get("access_token")
            refresh_token = token_response.get("refresh_token")
            
            if not access_token:
                raise ValueError(f"No access token received from {platform}")
            
            return access_token, refresh_token
    
    @staticmethod
    async def get_user_profile(
        platform: SocialPlatform, 
        access_token: str
    ) -> Dict[str, any]:
        """
        Get user profile information from the social platform
        Returns standardized user profile data
        """
        
        config = OAuthConfig.get_platform_config(platform)
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Prepare profile request
        profile_url = config["profile_url"]
        params = {}
        
        if platform == SocialPlatform.GOOGLE:
            params["personFields"] = "names,emailAddresses,photos"
        elif platform == SocialPlatform.FACEBOOK:
            params["fields"] = "id,name,email,picture.width(200).height(200)"
        elif platform == SocialPlatform.TIKTOK:
            params["fields"] = "open_id,union_id,avatar_url,display_name"
        
        # Make profile request
        async with httpx.AsyncClient() as client:
            response = await client.get(
                profile_url,
                headers=headers,
                params=params
            )
            
            if response.status_code != 200:
                raise ValueError(f"Profile fetch failed: {response.text}")
            
            profile_data = response.json()
            
            # Handle TikTok's nested response format
            if platform == SocialPlatform.TIKTOK:
                if "data" in profile_data and "user" in profile_data["data"]:
                    profile_data = profile_data["data"]["user"]
            
            return OAuthService._normalize_profile_data(platform, profile_data)
    
    @staticmethod
    def _normalize_profile_data(platform: SocialPlatform, profile_data: Dict) -> Dict[str, any]:
        """Normalize profile data from different platforms to a standard format"""
        
        if platform == SocialPlatform.GOOGLE:
            # Google People API format
            user_id = profile_data.get("resourceName", "").replace("people/", "")
            
            # Extract name
            names = profile_data.get("names", [])
            name = names[0].get("displayName") if names else None
            
            # Extract email
            emails = profile_data.get("emailAddresses", [])
            email = emails[0].get("value") if emails else None
            
            # Extract photo
            photos = profile_data.get("photos", [])
            avatar_url = photos[0].get("url") if photos else None
            
            return {
                "platform_user_id": user_id,
                "platform_username": email,  # Google uses email as username
                "email": email,
                "name": name,
                "avatar_url": avatar_url
            }
        
        elif platform == SocialPlatform.FACEBOOK:
            # Extract picture URL with improved handling
            picture_url = None
            if "picture" in profile_data:
                if isinstance(profile_data["picture"], dict) and "data" in profile_data["picture"]:
                    picture_url = profile_data["picture"]["data"].get("url")
                elif isinstance(profile_data["picture"], str):
                    picture_url = profile_data["picture"]
            
            return {
                "platform_user_id": profile_data.get("id"),
                "platform_username": profile_data.get("name"),  # Facebook username is display name
                "email": profile_data.get("email"),
                "name": profile_data.get("name"),
                "avatar_url": picture_url
            }
        
        elif platform == SocialPlatform.TIKTOK:
            return {
                "platform_user_id": profile_data.get("open_id"),
                "platform_username": profile_data.get("display_name"),  # TikTok username is display name
                "email": None,  # TikTok doesn't provide email by default
                "name": profile_data.get("display_name"),
                "avatar_url": profile_data.get("avatar_url")
            }
        
        else:
            raise ValueError(f"Unsupported platform for profile normalization: {platform}")


# Initialize service
oauth_service = OAuthService() 