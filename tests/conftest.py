import os
import asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from app import models

# Use an SQLite file for testing
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test.db"

# Re-import app after setting env var
from importlib import reload
import app.config as config_module
reload(config_module)

# Recreate engine with new DB URL
engine = create_async_engine(config_module.settings.DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(bind=engine, class_=asyncio.Future, expire_on_commit=False)

# Create tables before tests
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

# Drop tables after tests
async def drop_tables():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.drop_all)

@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    await create_tables()
    yield
    await drop_tables()

@pytest.fixture
async def client():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac
