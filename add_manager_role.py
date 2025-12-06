"""
Migration script to add is_manager field to users table
"""
import asyncio
import logging
from sqlalchemy import text
from database.session import async_session_maker, engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def add_manager_field():
    """Add is_manager field to users table"""
    async with async_session_maker() as session:
        try:
            # Check if column already exists
            result = await session.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='users' AND column_name='is_manager'"
            ))
            exists = result.fetchone()

            if exists:
                logger.info("Column 'is_manager' already exists in users table")
                return

            # Add the column
            logger.info("Adding 'is_manager' column to users table...")
            await session.execute(text(
                "ALTER TABLE users ADD COLUMN is_manager BOOLEAN DEFAULT FALSE"
            ))
            await session.commit()
            logger.info("Successfully added 'is_manager' column to users table")

        except Exception as e:
            logger.error(f"Error adding manager field: {e}")
            await session.rollback()
            raise


async def main():
    """Run migration"""
    try:
        logger.info("Starting migration...")
        await add_manager_field()
        logger.info("Migration completed successfully!")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
