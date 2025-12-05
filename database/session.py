"""
Database session management
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from config import config
from .models import Base


# Create async engine
engine = create_async_engine(
    config.DATABASE_URL,
    echo=config.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Create session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_db():
    """Initialize database (create tables)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    """Get database session"""
    async with async_session_maker() as session:
        yield session
