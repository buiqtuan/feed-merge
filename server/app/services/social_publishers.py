import httpx
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SocialMediaPublisher:
    """Base class for social media publishers"""
    
    def __init__(self, access_token: str, refresh_token: Optional[str] = None):
        self.access_token = access_token
        self.refresh_token = refresh_token
    
    async def publish_post(self, content: str, media_urls: Optional[list] = None) -> Dict[str, Any]:
        """Publish a post to the social platform"""
        raise NotImplementedError
    
    async def refresh_access_token(self) -> Dict[str, str]:
        """Refresh the access token if needed"""
        raise NotImplementedError


class TwitterPublisher(SocialMediaPublisher):
    """Twitter/X API publisher"""
    
    async def publish_post(self, content: str, media_urls: Optional[list] = None) -> Dict[str, Any]:
        url = "https://api.twitter.com/2/tweets"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        data = {"text": content}
        
        # Handle media uploads (simplified - in production, you'd upload media first)
        if media_urls:
            # Note: This is simplified. In practice, you'd need to upload media to Twitter first
            # and get media IDs, then attach them to the tweet
            logger.warning("Media uploads for Twitter not fully implemented")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=data, headers=headers)
                response.raise_for_status()
                result = response.json()
                
                return {
                    "success": True,
                    "platform_post_id": result["data"]["id"],
                    "response": result
                }
            except httpx.HTTPError as e:
                logger.error(f"Twitter publish failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "response": getattr(e.response, 'text', '') if hasattr(e, 'response') else ''
                }


class FacebookPublisher(SocialMediaPublisher):
    """Facebook API publisher"""
    
    def __init__(self, access_token: str, page_id: str, refresh_token: Optional[str] = None):
        super().__init__(access_token, refresh_token)
        self.page_id = page_id
    
    async def publish_post(self, content: str, media_urls: Optional[list] = None) -> Dict[str, Any]:
        url = f"https://graph.facebook.com/v18.0/{self.page_id}/feed"
        
        data = {
            "message": content,
            "access_token": self.access_token
        }
        
        # Handle media
        if media_urls:
            # For images, use the 'link' parameter or upload photos separately
            data["link"] = media_urls[0]  # Simplified - use first media URL
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, data=data)
                response.raise_for_status()
                result = response.json()
                
                return {
                    "success": True,
                    "platform_post_id": result["id"],
                    "response": result
                }
            except httpx.HTTPError as e:
                logger.error(f"Facebook publish failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "response": getattr(e.response, 'text', '') if hasattr(e, 'response') else ''
                }


class InstagramPublisher(SocialMediaPublisher):
    """Instagram API publisher"""
    
    def __init__(self, access_token: str, instagram_user_id: str, refresh_token: Optional[str] = None):
        super().__init__(access_token, refresh_token)
        self.instagram_user_id = instagram_user_id
    
    async def publish_post(self, content: str, media_urls: Optional[list] = None) -> Dict[str, Any]:
        if not media_urls:
            return {
                "success": False,
                "error": "Instagram posts require media"
            }
        
        # Step 1: Create media container
        create_url = f"https://graph.facebook.com/v18.0/{self.instagram_user_id}/media"
        create_data = {
            "image_url": media_urls[0],  # Use first media URL
            "caption": content,
            "access_token": self.access_token
        }
        
        async with httpx.AsyncClient() as client:
            try:
                # Create media container
                response = await client.post(create_url, data=create_data)
                response.raise_for_status()
                container_result = response.json()
                container_id = container_result["id"]
                
                # Step 2: Publish the container
                publish_url = f"https://graph.facebook.com/v18.0/{self.instagram_user_id}/media_publish"
                publish_data = {
                    "creation_id": container_id,
                    "access_token": self.access_token
                }
                
                response = await client.post(publish_url, data=publish_data)
                response.raise_for_status()
                result = response.json()
                
                return {
                    "success": True,
                    "platform_post_id": result["id"],
                    "response": result
                }
                
            except httpx.HTTPError as e:
                logger.error(f"Instagram publish failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "response": getattr(e.response, 'text', '') if hasattr(e, 'response') else ''
                }


class LinkedInPublisher(SocialMediaPublisher):
    """LinkedIn API publisher"""
    
    def __init__(self, access_token: str, person_id: str, refresh_token: Optional[str] = None):
        super().__init__(access_token, refresh_token)
        self.person_id = person_id
    
    async def publish_post(self, content: str, media_urls: Optional[list] = None) -> Dict[str, Any]:
        url = "https://api.linkedin.com/v2/ugcPosts"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "author": f"urn:li:person:{self.person_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": content
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        # Handle media (simplified)
        if media_urls:
            data["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] = "IMAGE"
            # Note: LinkedIn media uploads require additional steps
            logger.warning("Media uploads for LinkedIn not fully implemented")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=data, headers=headers)
                response.raise_for_status()
                result = response.json()
                
                # LinkedIn returns the post ID in a different format
                post_id = result.get("id", "").split(":")[-1] if result.get("id") else ""
                
                return {
                    "success": True,
                    "platform_post_id": post_id,
                    "response": result
                }
            except httpx.HTTPError as e:
                logger.error(f"LinkedIn publish failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "response": getattr(e.response, 'text', '') if hasattr(e, 'response') else ''
                }


def get_publisher(platform: str, access_token: str, platform_user_id: str, refresh_token: Optional[str] = None) -> SocialMediaPublisher:
    """Factory function to get the appropriate publisher"""
    
    publishers = {
        "twitter": TwitterPublisher,
        "facebook": lambda token, refresh: FacebookPublisher(token, platform_user_id, refresh),
        "instagram": lambda token, refresh: InstagramPublisher(token, platform_user_id, refresh),
        "linkedin": lambda token, refresh: LinkedInPublisher(token, platform_user_id, refresh),
    }
    
    if platform not in publishers:
        raise ValueError(f"Unsupported platform: {platform}")
    
    if platform == "twitter":
        return publishers[platform](access_token, refresh_token)
    else:
        return publishers[platform](access_token, refresh_token)
