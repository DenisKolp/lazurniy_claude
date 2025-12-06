"""
Reset database script
This script will:
1. Drop all tables
2. Recreate all tables
3. Initialize admin users
"""
import asyncio
import logging
from database.session import init_db, async_session_maker, engine
from database.models import Base
from database.crud import UserCRUD
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def reset_database():
    """Reset the database to initial state"""
    logger.info("Starting database reset...")

    # Drop all tables
    logger.info("Dropping all tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.info("All tables dropped")

    # Recreate all tables
    logger.info("Creating all tables...")
    await init_db()
    logger.info("All tables created")

    # Initialize admin users
    logger.info("Initializing admin users...")
    async with async_session_maker() as session:
        for admin_id in config.ADMIN_IDS:
            logger.info(f"Admin ID {admin_id} will be set as admin on first login")

    logger.info("Database reset complete!")
    logger.info("The database is now clean and ready for deployment")


if __name__ == "__main__":
    asyncio.run(reset_database())
