import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parent.parent.absolute() / '.env'
load_dotenv(dotenv_path=env_path)

# Base class for all models
Base = declarative_base()

# Database configuration
DB_TYPE = os.getenv("DB_TYPE", "sqlite")  # "sqlite" or "postgresql"
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "DiscordBot/data/taipu.db")
POSTGRESQL_URL = os.getenv("POSTGRESQL_URL", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Create database directory if it doesn't exist (for SQLite)
if DB_TYPE == "sqlite":
    os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)

# Create engine based on database type
if DB_TYPE == "sqlite":
    engine = create_engine(f"sqlite:///{SQLITE_DB_PATH}", echo=False)
elif DB_TYPE == "postgresql":
    if SUPABASE_URL and SUPABASE_KEY:
        # Use Supabase for PostgreSQL
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        # Still need a SQLAlchemy engine for ORM operations
        engine = create_engine(POSTGRESQL_URL, echo=False)
    else:
        # Use direct PostgreSQL connection
        engine = create_engine(POSTGRESQL_URL, echo=False)
else:
    raise ValueError(f"Unsupported database type: {DB_TYPE}")

# Create session factory
Session = sessionmaker(bind=engine)

def init_db():
    """Initialize the database by creating all tables."""
    Base.metadata.create_all(engine)

def get_db():
    """Get a database session."""
    db = Session()
    try:
        return db
    finally:
        db.close()

# Async versions for future use
if DB_TYPE == "sqlite":
    async_engine = create_async_engine(f"sqlite+aiosqlite:///{SQLITE_DB_PATH}", echo=False)
elif DB_TYPE == "postgresql":
    async_engine = create_async_engine(POSTGRESQL_URL.replace("postgresql://", "postgresql+asyncpg://"), echo=False)

AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_async_db():
    """Get an async database session."""
    async with AsyncSessionLocal() as session:
        yield session