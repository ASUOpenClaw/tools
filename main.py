"""
tools — lightweight FastAPI service for GoClaw HTTP tool calls.

GoClaw calls these endpoints when the LLM invokes tools like rag_search, list_files, etc.
Each request carries X-Service-Key + X-Goclaw-Tenant-ID identifying the workspace.
"""

from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI

from src.config import settings
from src.dependencies import get_redis
from src.handlers import conversations, files, folders, rag, transcriptions


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    app.dependency_overrides[get_redis] = lambda: redis_client
    yield
    await redis_client.aclose()


app = FastAPI(title="openclaw-tools", version="0.1.0", lifespan=lifespan)

app.include_router(rag.router)
app.include_router(files.router)
app.include_router(folders.router)
app.include_router(transcriptions.router)
app.include_router(conversations.router)
