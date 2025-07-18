#!/usr/bin/env python3
"""
Database Setup Script

One-time script to set up the database from scratch for new deployments.
This script will:
1. Create the database if it doesn't exist
2. Initialize Alembic
3. Create initial migration
4. Apply all migrations

Usage:
    python scripts/setup_database.py [options]
"""

import sys
import logging
import argparse
from pathlib import Path
from urllib.parse import urlparse

# Add the app directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError, OperationalError

from auto_migrate import DatabaseMigrator
from app.core.config import settings

logger = logging.getLogger(__name__)


def parse_database_url(database_url: str) -> dict:
    """Parse database URL into components"""
    parsed = urlparse(database_url)
    return {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'username': parsed.username,
        'password': parsed.password,
        'database': parsed.path.lstrip('/') if parsed.path else None,
        'scheme': parsed.scheme
    }


def create_database_if_not_exists(database_url: str, dry_run: bool = False) -> bool:
    """Create database if it doesn't exist"""
    try:
        db_config = parse_database_url(database_url)
        
        if not db_config['database']:
            logger.error("No database name found in DATABASE_URL")
            return False
        
        # Connect to postgres database to create our target database
        postgres_url = database_url.replace(f"/{db_config['database']}", "/postgres")
        
        if dry_run:
            logger.info(f"DRY RUN: Would attempt to create database '{db_config['database']}'")
            return True
        
        logger.info(f"Checking if database '{db_config['database']}' exists...")
        
        with create_engine(postgres_url).connect() as conn:
            # Check if database exists
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": db_config['database']}
            )
            
            if result.fetchone():
                logger.info(f"Database '{db_config['database']}' already exists")
                return True
            
            # Create database
            conn.execute(text("COMMIT"))  # End any open transaction
            conn.execute(text(f'CREATE DATABASE "{db_config["database"]}"'))
            logger.info(f"Created database '{db_config['database']}'")
            
        return True
        
    except OperationalError as e:
        if "does not exist" in str(e).lower():
            logger.error(f"Cannot connect to PostgreSQL server. Make sure it's running and accessible.")
        else:
            logger.error(f"Database creation failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Error creating database: {e}")
        return False


def setup_database(
    database_url: str = None, 
    dry_run: bool = False, 
    force: bool = False,
    create_db: bool = True
) -> bool:
    """Complete database setup process"""
    
    database_url = database_url or settings.DATABASE_URL
    
    logger.info("Starting database setup process...")
    logger.info(f"Database URL: {database_url.split('@')[0]}@***")  # Hide password
    
    # Step 1: Create database if needed
    if create_db:
        logger.info("Step 1: Creating database if it doesn't exist...")
        if not create_database_if_not_exists(database_url, dry_run):
            logger.error("Failed to create database")
            return False
    else:
        logger.info("Step 1: Skipping database creation")
    
    # Step 2: Initialize migrations
    logger.info("Step 2: Initializing database migrations...")
    try:
        migrator = DatabaseMigrator(database_url)
        
        # Check if we can connect to the target database
        if not dry_run and not migrator.check_database_exists():
            logger.error("Cannot connect to target database")
            return False
        
        # Initialize database with migrations
        if not migrator.initialize_database(dry_run):
            logger.error("Failed to initialize database migrations")
            return False
            
    except Exception as e:
        logger.error(f"Migration initialization failed: {e}")
        return False
    
    logger.info("✅ Database setup completed successfully!")
    
    if not dry_run:
        logger.info("Your database is now ready to use.")
        logger.info("You can run 'python scripts/auto_migrate.py' to apply future model changes.")
    
    return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Database Setup Script")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be done without making changes")
    parser.add_argument("--force", action="store_true",
                       help="Skip confirmation prompts")
    parser.add_argument("--database-url", type=str,
                       help="Override database URL from settings")
    parser.add_argument("--no-create-db", action="store_true",
                       help="Skip database creation step")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        if not args.force and not args.dry_run:
            print("This will set up your database from scratch.")
            print("Make sure you have:")
            print("1. PostgreSQL server running")
            print("2. Correct DATABASE_URL in your environment")
            print("3. Database user has CREATE DATABASE permissions")
            print()
            
            response = input("Continue? (y/N): ")
            if response.lower() != 'y':
                print("Setup cancelled")
                return
        
        success = setup_database(
            database_url=args.database_url,
            dry_run=args.dry_run,
            force=args.force,
            create_db=not args.no_create_db
        )
        
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 