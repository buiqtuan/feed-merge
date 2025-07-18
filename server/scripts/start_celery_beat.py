#!/usr/bin/env python3
"""
Celery Beat startup script for FeedMerge scheduler
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from celery import Celery
from app.core.celery_app import celery_app

if __name__ == "__main__":
    celery_app.start(["celery", "beat", "--loglevel=info"])
