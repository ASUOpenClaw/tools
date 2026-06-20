from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from .config import settings

_engine = create_async_engine(settings.database_url, pool_pre_ping=True)
AsyncSessionLocal: sessionmaker = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


def get_qdrant():
    from qdrant_client import AsyncQdrantClient

    return AsyncQdrantClient(url=settings.qdrant_url)
