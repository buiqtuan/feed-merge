import os
import logging
from typing import List, Optional, Dict, Any
from firebase_admin import credentials, messaging, initialize_app
from sqlalchemy.orm import Session
from app.crud.notification_token import get_user_notification_tokens
from app.crud.user import get_user

logger = logging.getLogger(__name__)

class NotificationService:
    """Firebase Cloud Messaging notification service"""
    
    def __init__(self):
        self._app = None
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            # Check if Firebase is already initialized
            if self._app is None:
                # Load service account credentials
                service_account_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH')
                
                if service_account_path and os.path.exists(service_account_path):
                    # Initialize with service account file
                    cred = credentials.Certificate(service_account_path)
                    self._app = initialize_app(cred)
                    logger.info("Firebase initialized with service account file")
                else:
                    # Try to initialize with default credentials (for Google Cloud environments)
                    try:
                        cred = credentials.ApplicationDefault()
                        self._app = initialize_app(cred)
                        logger.info("Firebase initialized with application default credentials")
                    except Exception as e:
                        logger.error(f"Failed to initialize Firebase: {e}")
                        logger.warning("Firebase notifications will not work without proper credentials")
                        
        except Exception as e:
            logger.error(f"Error initializing Firebase: {e}")
    
    async def send_notification(
        self,
        db: Session,
        user_id: int,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        notification_type: Optional[str] = None
    ) -> bool:
        """
        Send notification to a specific user
        
        Args:
            db: Database session
            user_id: Target user ID
            title: Notification title
            body: Notification body
            data: Additional data payload
            notification_type: Type of notification for routing
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self._app:
            logger.error("Firebase not initialized, cannot send notification")
            return False
        
        try:
            # Get user's FCM tokens
            tokens = get_user_notification_tokens(db, user_id)
            
            if not tokens:
                logger.warning(f"No FCM tokens found for user {user_id}")
                return False
            
            # Prepare notification data
            notification_data = data or {}
            if notification_type:
                notification_data['type'] = notification_type
            
            # Create FCM message
            token_strings = [token.token for token in tokens]
            
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=notification_data,
                tokens=token_strings,
                android=messaging.AndroidConfig(
                    notification=messaging.AndroidNotification(
                        icon='ic_notification',
                        color='#FF6B35',
                        sound='default',
                        channel_id='default'
                    ),
                    priority='high'
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            alert=messaging.ApsAlert(
                                title=title,
                                body=body
                            ),
                            badge=1,
                            sound='default'
                        )
                    )
                )
            )
            
            # Send notification
            response = messaging.send_multicast(message)
            
            # Log results
            logger.info(f"Notification sent: {response.success_count}/{len(token_strings)} successful")
            
            if response.failure_count > 0:
                logger.warning(f"Failed to send to {response.failure_count} tokens")
                # TODO: Handle invalid tokens (remove from database)
                await self._handle_failed_tokens(db, response.responses, tokens)
            
            return response.success_count > 0
            
        except Exception as e:
            logger.error(f"Error sending notification to user {user_id}: {e}")
            return False
    
    async def send_notification_to_tokens(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Send notification to specific FCM tokens
        
        Args:
            tokens: List of FCM tokens
            title: Notification title
            body: Notification body
            data: Additional data payload
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self._app:
            logger.error("Firebase not initialized, cannot send notification")
            return False
        
        if not tokens:
            logger.warning("No tokens provided")
            return False
        
        try:
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=data or {},
                tokens=tokens
            )
            
            response = messaging.send_multicast(message)
            logger.info(f"Notification sent: {response.success_count}/{len(tokens)} successful")
            
            return response.success_count > 0
            
        except Exception as e:
            logger.error(f"Error sending notification to tokens: {e}")
            return False
    
    async def send_topic_notification(
        self,
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Send notification to a topic
        
        Args:
            topic: Topic name
            title: Notification title
            body: Notification body
            data: Additional data payload
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self._app:
            logger.error("Firebase not initialized, cannot send notification")
            return False
        
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=data or {},
                topic=topic
            )
            
            response = messaging.send(message)
            logger.info(f"Topic notification sent: {response}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending topic notification: {e}")
            return False
    
    async def _handle_failed_tokens(
        self,
        db: Session,
        responses: List[messaging.SendResponse],
        tokens: List,
        
    ):
        """Handle failed token responses (remove invalid tokens)"""
        try:
            from app.crud.notification_token import update_notification_token
            from app.schemas import NotificationTokenUpdate
            
            for i, response in enumerate(responses):
                if not response.success:
                    error_code = response.exception.code if response.exception else None
                    
                    # Deactivate invalid tokens
                    if error_code in ['INVALID_ARGUMENT', 'UNREGISTERED']:
                        token = tokens[i]
                        logger.info(f"Deactivating invalid token: {token.id}")
                        
                        update_notification_token(
                            db,
                            token.id,
                            NotificationTokenUpdate(is_active=False)
                        )
                        
        except Exception as e:
            logger.error(f"Error handling failed tokens: {e}")

# Global notification service instance
notification_service = NotificationService()

# Convenience functions
async def send_post_published_notification(
    db: Session,
    user_id: int,
    post_title: str,
    platform: str
) -> bool:
    """Send notification when a post is published successfully"""
    return await notification_service.send_notification(
        db=db,
        user_id=user_id,
        title="Post Published! 🎉",
        body=f"Your post '{post_title}' was published to {platform}",
        notification_type="post_published"
    )

async def send_post_failed_notification(
    db: Session,
    user_id: int,
    post_title: str,
    platform: str,
    error_message: str
) -> bool:
    """Send notification when a post fails to publish"""
    return await notification_service.send_notification(
        db=db,
        user_id=user_id,
        title="Post Failed ❌",
        body=f"Failed to publish '{post_title}' to {platform}: {error_message}",
        notification_type="post_failed"
    )

async def send_connection_expired_notification(
    db: Session,
    user_id: int,
    platform: str
) -> bool:
    """Send notification when a social connection expires"""
    return await notification_service.send_notification(
        db=db,
        user_id=user_id,
        title="Connection Expired 🔗",
        body=f"Your {platform} connection has expired. Please reconnect in settings.",
        notification_type="connection_expired"
    )

async def send_scheduled_post_reminder(
    db: Session,
    user_id: int,
    post_title: str,
    scheduled_time: str
) -> bool:
    """Send reminder notification for scheduled posts"""
    return await notification_service.send_notification(
        db=db,
        user_id=user_id,
        title="Scheduled Post Reminder 📅",
        body=f"'{post_title}' is scheduled to publish at {scheduled_time}",
        notification_type="scheduled_reminder"
    )
