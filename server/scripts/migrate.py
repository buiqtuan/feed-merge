#!/usr/bin/env python3
"""
Migration CLI Tool

A convenient command-line interface for all database migration operations.
This is a wrapper around the other migration scripts for easier usage.

Usage:
    python scripts/migrate.py <command> [options]

Commands:
    setup       - Set up database from scratch
    auto        - Auto-detect and apply model changes  
    check       - Check for pending migrations
    rollback    - Rollback to previous migration
    status      - Show current migration status
    history     - Show migration history
    reset       - Reset database (development only)

Examples:
    python scripts/migrate.py setup
    python scripts/migrate.py auto --dry-run
    python scripts/migrate.py check
    python scripts/migrate.py rollback
    python scripts/migrate.py status
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

# Add the app directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir.parent))

from auto_migrate import DatabaseMigrator
from setup_database import setup_database
from migrate_on_startup import run_startup_migrations

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Configure logging"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def cmd_setup(args):
    """Set up database from scratch"""
    logger.info("🚀 Setting up database...")
    
    success = setup_database(
        database_url=args.database_url,
        dry_run=args.dry_run,
        force=args.force,
        create_db=not args.no_create_db
    )
    
    if success:
        logger.info("✅ Database setup completed successfully")
        return 0
    else:
        logger.error("❌ Database setup failed")
        return 1


def cmd_auto(args):
    """Auto-detect and apply model changes"""
    logger.info("🔍 Checking for model changes...")
    
    migrator = DatabaseMigrator(args.database_url)
    
    success = migrator.auto_migrate(
        dry_run=args.dry_run,
        force=args.force
    )
    
    if success:
        logger.info("✅ Auto-migration completed successfully")
        return 0
    else:
        logger.error("❌ Auto-migration failed")
        return 1


def cmd_check(args):
    """Check for pending migrations"""
    logger.info("📋 Checking migration status...")
    
    migrator = DatabaseMigrator(args.database_url)
    
    try:
        current_rev = migrator.get_current_revision()
        pending = migrator.get_pending_migrations()
        has_changes = migrator.detect_model_changes()
        
        logger.info(f"Current revision: {current_rev or 'None'}")
        
        if pending:
            logger.info(f"📦 Pending migrations: {len(pending)}")
            for rev in pending:
                logger.info(f"  - {rev}")
        else:
            logger.info("✅ No pending migrations")
        
        if has_changes:
            logger.info("🔄 Model changes detected (need new migration)")
        else:
            logger.info("✅ Models match database schema")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error checking status: {e}")
        return 1


def cmd_rollback(args):
    """Rollback to previous migration"""
    logger.info("⏪ Rolling back migration...")
    
    migrator = DatabaseMigrator(args.database_url)
    
    success = migrator.rollback_migration(
        revision=args.revision,
        dry_run=args.dry_run
    )
    
    if success:
        logger.info("✅ Rollback completed successfully")
        return 0
    else:
        logger.error("❌ Rollback failed")
        return 1


def cmd_status(args):
    """Show current migration status"""
    logger.info("📊 Migration Status Report")
    logger.info("=" * 50)
    
    migrator = DatabaseMigrator(args.database_url)
    
    try:
        # Database connection
        if migrator.check_database_exists():
            logger.info("✅ Database: Connected")
        else:
            logger.error("❌ Database: Not accessible")
            return 1
        
        # Alembic initialization
        if migrator.check_alembic_initialized():
            logger.info("✅ Alembic: Initialized")
        else:
            logger.warning("⚠️ Alembic: Not initialized")
        
        # Current revision
        current_rev = migrator.get_current_revision()
        logger.info(f"📍 Current revision: {current_rev or 'None'}")
        
        # Pending migrations
        pending = migrator.get_pending_migrations()
        if pending:
            logger.info(f"📦 Pending migrations: {len(pending)}")
            for rev in pending:
                logger.info(f"    - {rev}")
        else:
            logger.info("✅ No pending migrations")
        
        # Model changes
        has_changes = migrator.detect_model_changes()
        if has_changes:
            logger.info("🔄 Model changes detected")
        else:
            logger.info("✅ Models in sync with database")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error getting status: {e}")
        return 1


def cmd_history(args):
    """Show migration history"""
    logger.info("📚 Migration History")
    logger.info("=" * 50)
    
    try:
        from alembic import script
        from alembic.config import Config
        
        # Get Alembic configuration
        alembic_cfg_path = current_dir.parent / "alembic.ini"
        cfg = Config(str(alembic_cfg_path))
        
        script_dir = script.ScriptDirectory.from_config(cfg)
        
        revisions = list(script_dir.walk_revisions())
        
        if not revisions:
            logger.info("No migrations found")
            return 0
        
        for rev in revisions:
            logger.info(f"📄 {rev.revision[:8]} - {rev.doc or 'No description'}")
            logger.info(f"    Date: {getattr(rev, 'create_date', 'Unknown')}")
            if hasattr(rev, 'down_revision') and rev.down_revision:
                logger.info(f"    Parent: {rev.down_revision[:8]}")
            logger.info("")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error getting history: {e}")
        return 1


def cmd_reset(args):
    """Reset database (development only)"""
    if not args.force:
        logger.warning("⚠️ This will DELETE ALL DATA in your database!")
        logger.warning("This command is intended for development only.")
        response = input("Are you absolutely sure? Type 'yes' to continue: ")
        if response.lower() != 'yes':
            logger.info("Reset cancelled")
            return 0
    
    logger.info("🔥 Resetting database...")
    
    try:
        from app.db.database import engine, Base
        
        if args.dry_run:
            logger.info("DRY RUN: Would drop all tables and recreate")
            return 0
        
        # Drop all tables
        logger.info("Dropping all tables...")
        Base.metadata.drop_all(engine)
        
        # Recreate with setup
        logger.info("Setting up fresh database...")
        success = setup_database(
            database_url=args.database_url,
            dry_run=False,
            force=True,
            create_db=False  # Database already exists
        )
        
        if success:
            logger.info("✅ Database reset completed")
            return 0
        else:
            logger.error("❌ Database reset failed")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Reset error: {e}")
        return 1


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Database Migration CLI Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Global options
    parser.add_argument("--database-url", type=str,
                       help="Override database URL from settings")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be done without making changes")
    parser.add_argument("--force", action="store_true",
                       help="Skip confirmation prompts")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Set up database from scratch")
    setup_parser.add_argument("--no-create-db", action="store_true",
                             help="Skip database creation step")
    
    # Auto command
    auto_parser = subparsers.add_parser("auto", help="Auto-detect and apply changes")
    
    # Check command
    check_parser = subparsers.add_parser("check", help="Check migration status")
    
    # Rollback command
    rollback_parser = subparsers.add_parser("rollback", help="Rollback migration")
    rollback_parser.add_argument("revision", nargs="?", default="-1",
                                help="Target revision (default: previous)")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show detailed status")
    
    # History command
    history_parser = subparsers.add_parser("history", help="Show migration history")
    
    # Reset command
    reset_parser = subparsers.add_parser("reset", help="Reset database (DEV ONLY)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Set up logging
    setup_logging(args.verbose)
    
    # Command routing
    command_map = {
        "setup": cmd_setup,
        "auto": cmd_auto,
        "check": cmd_check,
        "rollback": cmd_rollback,
        "status": cmd_status,
        "history": cmd_history,
        "reset": cmd_reset,
    }
    
    try:
        return command_map[args.command](args)
    except KeyboardInterrupt:
        logger.info("❌ Operation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        if args.verbose:
            raise
        return 1


if __name__ == "__main__":
    sys.exit(main()) 