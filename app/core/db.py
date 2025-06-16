import os
import asyncpg
from fastapi import Path
from app.core.config import DATABASE_URL
from app.core.migrations import migration_manager
from app.core.logging_config import get_logger
from app.core.exceptions import DatabaseConnectionError, DatabaseError, DatabaseTransactionError

logger = get_logger("database")

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        """Connect to database and run migrations"""
        if not self.pool:
            try:
                logger.info("Attempting to connect to database...")
                self.pool = await asyncpg.create_pool(
                    DATABASE_URL,
                    min_size=5,
                    max_size=20,
                    command_timeout=60
                )
                logger.info("Database connection pool created successfully")
                
                # Run migrations
                await self.run_migrations()
                
            except asyncpg.PostgresConnectionError as e:
                logger.error(f"Failed to connect to PostgreSQL database: {e}", exc_info=True)
                raise DatabaseConnectionError(
                    message="Failed to connect to database",
                    details={"connection_error": str(e)}
                )
            except Exception as e:
                logger.critical(f"Unexpected error during database connection: {e}", exc_info=True)
                raise DatabaseError(
                    message="Unexpected database connection error",
                    details={"error": str(e)}
                )

    async def disconnect(self):
        """Disconnect from database"""
        if self.pool:
            try:
                logger.info("Closing database connection pool...")
                await self.pool.close()
                self.pool = None
                logger.info("Database connection pool closed successfully")
            except Exception as e:
                logger.error(f"Error closing database connection: {e}", exc_info=True)
                raise DatabaseError(
                    message="Failed to close database connection",
                    details={"error": str(e)}
                )

    async def get_pool(self):
        """Get database connection pool"""
        if not self.pool:
            logger.warning("Database pool not initialized, attempting to connect...")
            await self.connect()
        return self.pool

    async def run_migrations(self):
        """Run database migrations using the migration manager"""
        try:
            logger.info("Starting database migrations...")
            await migration_manager.run_migrations(self.pool)
            logger.info("Database migrations completed successfully")
        except Exception as e:
            logger.error(f"Database migration failed: {e}", exc_info=True)
            raise DatabaseError(
                message="Database migration failed",
                details={"migration_error": str(e)}
            )

db = Database() 