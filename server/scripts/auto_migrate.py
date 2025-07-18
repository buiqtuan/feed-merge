#!/usr/bin/env python3
"""
Auto Migration Script for Code-First Database Strategy

This script automatically detects changes in SQLAlchemy models and applies them
to the PostgreSQL database using Alembic migrations.

Usage:
    python scripts/auto_migrate.py [options]

Options:
    --dry-run: Show what migrations would be created without applying them
    --force: Skip confirmation prompts (use with caution)
    --init: Initialize database with initial migration
    --check: Only check for pending migrations without applying them
"""

import os
import sys
import subprocess
import argparse
import logging
from pathlib import Path
from typing import Optional, List
import tempfile
from contextlib import contextmanager

# Add the app directory to path for imports
current_dir = Path(__file__).parent
app_dir = current_dir.parent / "app"
sys.path.insert(0, str(current_dir.parent))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
from alembic import command, script
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.autogenerate import compare_metadata

# Import application modules
from app.core.config import settings
from app.db.database import Base
from app.models import *  # Import all models

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('migration.log')
    ]
)
logger = logging.getLogger(__name__)


class DatabaseMigrator:
    """Handles automatic database migrations for code-first strategy"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or settings.DATABASE_URL
        self.alembic_cfg = self._get_alembic_config()
        self.engine = create_engine(self.database_url)
        
    def _get_alembic_config(self) -> Config:
        """Get Alembic configuration"""
        alembic_cfg_path = current_dir.parent / "alembic.ini"
        cfg = Config(str(alembic_cfg_path))
        cfg.set_main_option("sqlalchemy.url", self.database_url)
        return cfg
    
    @contextmanager
    def database_connection(self):
        """Context manager for database connections"""
        connection = None
        try:
            connection = self.engine.connect()
            yield connection
        except SQLAlchemyError as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if connection:
                connection.close()
    
    def check_database_exists(self) -> bool:
        """Check if the database exists and is accessible"""
        try:
            with self.database_connection() as conn:
                conn.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database not accessible: {e}")
            return False
    
    def check_alembic_initialized(self) -> bool:
        """Check if Alembic has been initialized"""
        try:
            script_dir = script.ScriptDirectory.from_config(self.alembic_cfg)
            return len(script_dir.get_revisions("head")) > 0
        except Exception:
            return False
    
    def get_current_revision(self) -> Optional[str]:
        """Get the current database revision"""
        try:
            with self.database_connection() as conn:
                context = MigrationContext.configure(conn)
                return context.get_current_revision()
        except Exception as e:
            logger.warning(f"Could not get current revision: {e}")
            return None
    
    def get_pending_migrations(self) -> List[str]:
        """Get list of pending migrations"""
        try:
            script_dir = script.ScriptDirectory.from_config(self.alembic_cfg)
            current_rev = self.get_current_revision()
            
            if current_rev is None:
                # No migrations applied yet, return all
                return [rev.revision for rev in script_dir.walk_revisions()]
            
            # Get revisions that haven't been applied
            pending = []
            for rev in script_dir.walk_revisions("head", current_rev):
                if rev.revision != current_rev:
                    pending.append(rev.revision)
            
            return pending
        except Exception as e:
            logger.error(f"Error getting pending migrations: {e}")
            return []
    
    def detect_model_changes(self) -> bool:
        """Detect if there are any model changes that need migration"""
        try:
            with self.database_connection() as conn:
                context = MigrationContext.configure(conn)
                diff = compare_metadata(context, Base.metadata)
                return len(diff) > 0
        except Exception as e:
            logger.error(f"Error detecting model changes: {e}")
            return False
    
    def create_migration(self, message: str = None, dry_run: bool = False) -> Optional[str]:
        """Create a new migration based on model changes"""
        try:
            if not message:
                message = "Auto-generated migration"
            
            if dry_run:
                logger.info("DRY RUN: Would create migration with message: %s", message)
                return None
            
            # Use alembic command to generate migration
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_path = temp_file.name
            
            try:
                command.revision(
                    self.alembic_cfg,
                    message=message,
                    autogenerate=True
                )
                
                # Get the latest revision
                script_dir = script.ScriptDirectory.from_config(self.alembic_cfg)
                latest_rev = script_dir.get_current_head()
                
                logger.info(f"Created migration: {latest_rev}")
                return latest_rev
                
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.error(f"Error creating migration: {e}")
            return None
    
    def apply_migrations(self, dry_run: bool = False) -> bool:
        """Apply pending migrations"""
        try:
            pending = self.get_pending_migrations()
            
            if not pending:
                logger.info("No pending migrations to apply")
                return True
            
            if dry_run:
                logger.info("DRY RUN: Would apply %d migrations: %s", 
                           len(pending), pending)
                return True
            
            logger.info(f"Applying {len(pending)} migrations...")
            command.upgrade(self.alembic_cfg, "head")
            logger.info("Migrations applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error applying migrations: {e}")
            return False
    
    def initialize_database(self, dry_run: bool = False) -> bool:
        """Initialize database with initial migration"""
        try:
            if self.check_alembic_initialized():
                logger.info("Database already initialized")
                return True
            
            if dry_run:
                logger.info("DRY RUN: Would initialize database")
                return True
            
            # Create initial migration
            logger.info("Creating initial migration...")
            initial_rev = self.create_migration("Initial migration")
            
            if initial_rev:
                # Apply the initial migration
                return self.apply_migrations()
            
            return False
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            return False
    
    def rollback_migration(self, revision: str = None, dry_run: bool = False) -> bool:
        """Rollback to a specific revision"""
        try:
            target = revision or "-1"  # Rollback one migration by default
            
            if dry_run:
                logger.info(f"DRY RUN: Would rollback to revision: {target}")
                return True
            
            logger.info(f"Rolling back to revision: {target}")
            command.downgrade(self.alembic_cfg, target)
            logger.info("Rollback completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during rollback: {e}")
            return False
    
    def auto_migrate(self, dry_run: bool = False, force: bool = False) -> bool:
        """Perform automatic migration process"""
        logger.info("Starting automatic migration process...")
        
        # Check database connectivity
        if not self.check_database_exists():
            logger.error("Cannot connect to database")
            return False
        
        # Initialize if needed
        if not self.check_alembic_initialized():
            logger.info("Database not initialized, creating initial migration...")
            if not self.initialize_database(dry_run):
                return False
        
        # Check for model changes
        if self.detect_model_changes():
            logger.info("Model changes detected, creating migration...")
            
            if not force and not dry_run:
                response = input("Model changes detected. Create migration? (y/N): ")
                if response.lower() != 'y':
                    logger.info("Migration cancelled by user")
                    return False
            
            # Create migration
            migration_rev = self.create_migration(dry_run=dry_run)
            
            if migration_rev or dry_run:
                # Apply migrations
                return self.apply_migrations(dry_run)
            else:
                logger.error("Failed to create migration")
                return False
        else:
            logger.info("No model changes detected")
            
            # Still check for pending migrations
            pending = self.get_pending_migrations()
            if pending:
                logger.info(f"Found {len(pending)} pending migrations")
                
                if not force and not dry_run:
                    response = input("Apply pending migrations? (y/N): ")
                    if response.lower() != 'y':
                        logger.info("Migration cancelled by user")
                        return False
                
                return self.apply_migrations(dry_run)
            else:
                logger.info("Database is up to date")
                return True


def main():
    """Main entry point for the migration script"""
    parser = argparse.ArgumentParser(description="Auto Migration Script")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be done without applying changes")
    parser.add_argument("--force", action="store_true", 
                       help="Skip confirmation prompts")
    parser.add_argument("--init", action="store_true", 
                       help="Initialize database with initial migration")
    parser.add_argument("--check", action="store_true", 
                       help="Only check for pending migrations")
    parser.add_argument("--rollback", type=str, nargs="?", const="-1",
                       help="Rollback to specific revision (default: previous)")
    parser.add_argument("--database-url", type=str,
                       help="Override database URL from settings")
    
    args = parser.parse_args()
    
    try:
        migrator = DatabaseMigrator(args.database_url)
        
        if args.rollback is not None:
            success = migrator.rollback_migration(args.rollback, args.dry_run)
        elif args.init:
            success = migrator.initialize_database(args.dry_run)
        elif args.check:
            pending = migrator.get_pending_migrations()
            if pending:
                logger.info(f"Pending migrations: {pending}")
            else:
                logger.info("No pending migrations")
            success = True
        else:
            success = migrator.auto_migrate(args.dry_run, args.force)
        
        if success:
            logger.info("Migration process completed successfully")
            sys.exit(0)
        else:
            logger.error("Migration process failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Migration process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 