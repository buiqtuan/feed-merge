#!/usr/bin/env python3
"""
Celery worker startup script for FeedMerge
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.celery_app import celery_app

if __name__ == "__main__":
    celery_app.start()
