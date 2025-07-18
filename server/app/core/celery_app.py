from celery import Celery
from app.core.config import settings

# Create Celery instance
celery_app = Celery(
    "feedmerge",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.scheduler"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    result_expires=3600,
    task_routes={
        'app.tasks.scheduler.publish_scheduled_posts': {'queue': 'scheduler'},
        'app.tasks.scheduler.publish_single_post': {'queue': 'publisher'},
    },
    beat_schedule={
        'publish-scheduled-posts': {
            'task': 'app.tasks.scheduler.publish_scheduled_posts',
            'schedule': 60.0,  # Run every minute
        },
    },
)
