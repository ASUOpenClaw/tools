from __future__ import annotations

import uuid

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from src.auth import Auth
from src.dependencies import DB
from src.models import Conversation

router = APIRouter()


class ListConversationsRequest(BaseModel):
    page: int = 1
    limit: int = 20


@router.post("/conversations/list")
async def list_conversations(body: ListConversationsRequest, ctx: Auth, db: DB) -> dict:
    stmt = (
        select(Conversation)
        .where(Conversation.workspace_id == uuid.UUID(ctx.workspace_id))
        .order_by(Conversation.last_message_at.desc())
        .offset((body.page - 1) * body.limit)
        .limit(body.limit)
    )
    result = await db.execute(stmt)
    convs = result.scalars().all()
    return {
        "conversations": [
            {
                "id": str(c.id),
                "title": c.title,
                "message_count": c.message_count,
                "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None,
                "goclaw_session_key": c.goclaw_session_key,
            }
            for c in convs
        ]
    }
