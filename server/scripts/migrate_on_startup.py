#!/usr/bin/env python3
"""
Startup Migration Script

This script can be integrated into your application startup process to 
automatically run migrations when the application starts.

Usage:
    python scripts/migrate_on_startup.py
    
Or import and use in your main.py:
    from scripts.migrate_on_startup import run_startup_migrations
    run_startup_migrations()
"""

import sys
import logging
from pathlib import Path

# Add the app directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir.parent))

from auto_migrate import DatabaseMigrator

logger = logging.getLogger(__name__)


def run_startup_migrations(
    force: bool = True, 
    fail_on_error: bool = True,
    max_retries: int = 3
) -> bool:
    """
    Run migrations during application startup
    
    Args:
        force: Skip user confirmation prompts
        fail_on_error: Whether to raise exception on migration failure
        max_retries: Number of times to retry on failure
        
    Returns:
        bool: Success status
    """
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Running startup migrations (attempt {attempt + 1}/{max_retries})")
            
            migrator = DatabaseMigrator()
            
            # Check database connectivity first
            if not migrator.check_database_exists():
                logger.error("Database not accessible during startup")
                if fail_on_error and attempt == max_retries - 1:
                    raise Exception("Database not accessible")
                continue
            
            # Run auto migration with force=True for startup
            success = migrator.auto_migrate(dry_run=False, force=force)
            
            if success:
                logger.info("Startup migrations completed successfully")
                return True
            else:
                logger.warning(f"Migration attempt {attempt + 1} failed")
                if attempt == max_retries - 1:
                    if fail_on_error:
                        raise Exception("Migration failed after all retries")
                    else:
                        logger.error("Migration failed, but continuing startup")
                        return False
                        
        except Exception as e:
            logger.error(f"Migration error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                if fail_on_error:
                    raise
                else:
                    logger.error("Migration failed, but continuing startup")
                    return False
    
    return False


def configure_startup_logging():
    """Configure logging for startup migrations"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


if __name__ == "__main__":
    configure_startup_logging()
    
    try:
        success = run_startup_migrations()
        if success:
            print("✅ Startup migrations completed successfully")
            sys.exit(0)
        else:
            print("❌ Startup migrations failed")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Startup migration error: {e}")
        sys.exit(1) 