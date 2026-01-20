import os
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# 1. Load environment variables from .env file
load_dotenv()

# 2. Get the URL. If it's not found, raise an error to fail fast.
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set. Please check your .env file.")

# 3. Create the Async Engine
engine = create_async_engine(DATABASE_URL, echo=False, future=True)

async def init_db():
    async with engine.begin() as conn:
        # This creates the tables if they don't exist
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_session() -> AsyncSession:
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session