from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db import get_db
from src.dependencies import Redis, get_redis
from src.models.workspace import Workspace

_WS_CACHE_TTL = 300  # seconds


@dataclass
class ToolContext:
    workspace_id: str
    user_id: str
    session_key: str


async def require_tool_auth(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Redis,
) -> ToolContext:
    """Validate X-Service-Key and verify X-Goclaw-Tenant-ID is a known workspace."""
    key = request.headers.get("X-Service-Key", "")
    if not key or not settings.tools_service_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing service key")
    if not secrets.compare_digest(key, settings.tools_service_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid service key")

    tenant_id = request.headers.get("X-Goclaw-Tenant-ID", "")
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="missing X-Goclaw-Tenant-ID")

    try:
        ws_uuid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid tenant id")

    cache_key = f"ws_valid:{tenant_id}"
    if not await redis.exists(cache_key):
        row = await db.scalar(select(Workspace.id).where(Workspace.id == ws_uuid))
        if row is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="unknown workspace")
        await redis.setex(cache_key, _WS_CACHE_TTL, "1")

    return ToolContext(
        workspace_id=tenant_id,
        user_id=request.headers.get("X-Goclaw-User-ID", "system"),
        session_key=request.headers.get("X-Goclaw-Session-Key", ""),
    )


Auth = Annotated[ToolContext, Depends(require_tool_auth)]
