# ================================
# FILE: app/core/database.py
# ================================

import os
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String
from fastapi import Depends
from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase

from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


# --------------------------------------
# SQLAlchemy Setup for ORM and FastAPI Users
# --------------------------------------

class Base(DeclarativeBase):
    pass


class User(SQLAlchemyBaseUserTableUUID, Base):
    oauth_provider = Column(String, nullable=True)
    oauth_account_id = Column(String, nullable=True)


# SQLAlchemy async engine and session
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=int(os.getenv("DB_POOL_SIZE", "50")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

# Yield AsyncSession for FastAPI Dependency Injection
from typing import AsyncGenerator


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


# FastAPI Users dependency
async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)


# Create tables
async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("SQLAlchemy tables (including users) created successfully")

    # Ensure the threads table exists for raw SQL operations
    create_threads_table_query = """
    CREATE TABLE IF NOT EXISTS threads (
        id VARCHAR(36) PRIMARY KEY,
        user_id VARCHAR(255) NOT NULL,
        thread_title TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL
    );
    """
    async with db_manager.get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(create_threads_table_query)
            logger.info("Ensured threads table exists in the database")


# --------------------------------------
# Psycopg Pool and LangGraph Checkpointer
# --------------------------------------

class DatabaseManager:
    def __init__(self):
        self.pool: AsyncConnectionPool | None = None
        self.memory: AsyncPostgresSaver | None = None

    async def initialize(self):
        """Initialize database connection pool and memory checkpointer"""
        try:
            # Construct a connection string for psycopg_pool without +asyncpg dialect
            db_url_for_psycopg = f"postgresql://{settings.PSQL_USERNAME}:{settings.PSQL_PASSWORD}@{settings.PSQL_HOST}:{settings.PSQL_PORT}/{settings.PSQL_DATABASE}"
            self.pool = AsyncConnectionPool(
                conninfo=db_url_for_psycopg,
                max_size=20,
                kwargs={
                    "autocommit": True,
                    "prepare_threshold": 0,
                    "row_factory": dict_row,
                    "sslmode": settings.PSQL_SSLMODE,
                },
            )

            # Initialize the memory checkpointer
            async with self.pool.connection() as conn:
                self.memory = AsyncPostgresSaver(conn)  # type: ignore[arg-type]
                # Setup the checkpointer tables (run only once)
                try:
                    await self.memory.setup()
                    logger.info("Memory checkpointer setup completed")
                except Exception as e:
                    logger.info(f"Memory checkpointer already setup or error: {e}")

            # Ensure all database tables are created
            await create_db_and_tables()

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()

    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection from the pool"""
        if self.pool is None:
            raise ValueError("Database pool is not initialized")
        async with self.pool.connection() as conn:
            yield conn

    def get_memory_checkpointer(self) -> AsyncPostgresSaver:
        """Get the memory checkpointer instance"""
        if self.memory is None:
            raise ValueError("Memory checkpointer is not initialized")
        return self.memory


# Global database manager instance
db_manager = DatabaseManager()
