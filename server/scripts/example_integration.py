#!/usr/bin/env python3
"""
Example Integration: Adding Auto-Migration to FastAPI Application

This example shows how to integrate the auto-migration system into your
main FastAPI application. You can use this as a reference for updating
your app/main.py file.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import your existing modules
from app.core.config import settings
from app.api import auth, users, posts

# Import the migration system
import sys
from pathlib import Path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
from migrate_on_startup import run_startup_migrations

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with automatic migrations"""
    
    # Startup
    logger.info("Starting application...")
    
    try:
        # Run database migrations on startup
        logger.info("Running database migrations...")
        success = run_startup_migrations(
            force=True,          # Skip confirmations in production
            fail_on_error=True,  # Fail startup if migrations fail
            max_retries=3        # Retry on temporary failures
        )
        
        if success:
            logger.info("✅ Database migrations completed successfully")
        else:
            logger.error("❌ Database migrations failed")
            raise Exception("Migration failure during startup")
            
    except Exception as e:
        logger.error(f"❌ Startup migration error: {e}")
        # You can choose to:
        # 1. Fail startup (recommended for production)
        raise
        # 2. Or continue without migrations (not recommended)
        # logger.warning("Continuing startup despite migration failure")
    
    logger.info("✅ Application startup completed")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("Shutting down application...")


def create_application() -> FastAPI:
    """Create and configure the FastAPI application"""
    
    # Create FastAPI instance with lifespan
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan  # Add the lifespan manager
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure based on your needs
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
    app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
    app.include_router(posts.router, prefix=f"{settings.API_V1_STR}/posts", tags=["posts"])
    
    @app.get("/")
    async def root():
        return {"message": "Feed Merge API", "version": settings.PROJECT_VERSION}
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy", "version": settings.PROJECT_VERSION}
    
    return app


# Alternative approach without lifespan (for older FastAPI versions)
def create_application_legacy() -> FastAPI:
    """Create FastAPI application with legacy startup events"""
    
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json"
    )
    
    @app.on_event("startup")
    async def startup_event():
        """Run migrations on startup"""
        try:
            logger.info("Running database migrations...")
            success = run_startup_migrations(force=True, fail_on_error=True)
            if success:
                logger.info("✅ Database migrations completed")
            else:
                raise Exception("Migration failed")
        except Exception as e:
            logger.error(f"❌ Migration error: {e}")
            raise
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown"""
        logger.info("Application shutting down...")
    
    # Add middleware and routes as above...
    
    return app


# For development with optional migration control
def create_application_dev() -> FastAPI:
    """Development version with optional migration control"""
    
    import os
    
    @asynccontextmanager
    async def dev_lifespan(app: FastAPI):
        # Check environment variable to control migrations
        run_migrations = os.getenv("RUN_MIGRATIONS", "true").lower() == "true"
        
        if run_migrations:
            logger.info("Running database migrations (set RUN_MIGRATIONS=false to skip)...")
            try:
                success = run_startup_migrations(
                    force=True,
                    fail_on_error=False,  # Don't fail startup in dev
                    max_retries=1
                )
                if success:
                    logger.info("✅ Migrations completed")
                else:
                    logger.warning("⚠️ Migrations failed, but continuing...")
            except Exception as e:
                logger.warning(f"⚠️ Migration error: {e}, but continuing...")
        else:
            logger.info("Skipping migrations (RUN_MIGRATIONS=false)")
        
        yield
        
        logger.info("Development server shutting down...")
    
    app = FastAPI(
        title=f"{settings.PROJECT_NAME} (Dev)",
        version=settings.PROJECT_VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=dev_lifespan
    )
    
    # Add your routes and middleware...
    
    return app


# Configuration for different environments
if settings.ENVIRONMENT == "development":
    app = create_application_dev()
elif settings.ENVIRONMENT == "production":
    app = create_application()
else:
    app = create_application()  # Default to production-like behavior


if __name__ == "__main__":
    import uvicorn
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    uvicorn.run(
        "example_integration:app",
        host="0.0.0.0", 
        port=8000, 
        reload=True if settings.ENVIRONMENT == "development" else False
    ) 