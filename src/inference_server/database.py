"""
Database connection and session management for ML-IDS.

Provides async database connectivity using SQLAlchemy with asyncpg driver.
Includes graceful degradation if database is unavailable.
"""

import os
import logging
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text

from .models import Base

logger = logging.getLogger(__name__)

# Database connection configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://mlids:mlids_password@localhost:5432/mlids")

# Global engine and session maker
engine = None
async_session_maker = None
db_available = False


async def init_db() -> bool:
    """
    Initialize database engine and create tables.
    
    Returns:
        bool: True if database is available and initialized, False otherwise
    """
    global engine, async_session_maker, db_available
    
    try:
        # Create async engine with connection pooling
        engine = create_async_engine(
            DATABASE_URL,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,  # Verify connections before using
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
        )
        
        # Test connection
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        # Create session maker
        async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Important for async
            autocommit=False,
            autoflush=False,
        )
        
        # Create tables if they don't exist
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        db_available = True
        logger.info("Database initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        logger.warning("ML-IDS will run with limited functionality (no database)")
        db_available = False
        return False


async def close_db():
    """
    Close database connections gracefully.
    """
    global engine
    if engine:
        await engine.dispose()
        logger.info("Database connections closed")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get database session.
    
    Yields:
        AsyncSession: Database session
        
    Usage in FastAPI:
        @app.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            # Use db
    """
    if not db_available or not async_session_maker:
        logger.warning("Database not available, skipping database operations")
        yield None
        return
    
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


def is_db_available() -> bool:
    """
    Check if database is available.
    
    Returns:
        bool: True if database is available, False otherwise
    """
    return db_available


async def health_check() -> dict:
    """
    Perform database health check.
    
    Returns:
        dict: Health status information
    """
    if not db_available or not engine:
        return {
            "database": "unavailable",
            "status": "degraded"
        }
    
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()
        
        return {
            "database": "healthy",
            "status": "ok"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "database": "unhealthy",
            "status": "error",
            "error": str(e)
        }
