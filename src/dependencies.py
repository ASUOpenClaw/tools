from __future__ import annotations

from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db


def get_redis() -> aioredis.Redis:
    """Overridden in lifespan via app.dependency_overrides."""
    raise RuntimeError("get_redis not overridden")


DB = Annotated[AsyncSession, Depends(get_db)]
Redis = Annotated[aioredis.Redis, Depends(get_redis)]
