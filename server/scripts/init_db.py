#!/usr/bin/env python3
"""
Database initialization script for FeedMerge application.
This script creates the initial database tables and generates the first migration.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from app.core.config import settings
from app.db.database import Base
from app.models import *  # Import all models


def create_tables():
    """Create all tables in the database"""
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")


def main():
    """Main function to initialize the database"""
    print("🚀 Initializing FeedMerge database...")
    
    # Check if database URL is configured
    if not settings.DATABASE_URL:
        print("❌ DATABASE_URL not configured in environment variables")
        sys.exit(1)
    
    try:
        create_tables()
        print("🎉 Database initialization completed!")
        print("📝 Next steps:")
        print("   1. Run: alembic revision --autogenerate -m 'Initial migration'")
        print("   2. Run: alembic upgrade head")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
