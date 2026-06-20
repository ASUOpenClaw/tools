from __future__ import annotations

import uuid

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from src.auth import Auth
from src.dependencies import DB
from src.models.folder import Folder

router = APIRouter()


class ListFoldersRequest(BaseModel):
    parent_id: str | None = None


@router.post("/folders/list")
async def list_folders(body: ListFoldersRequest, ctx: Auth, db: DB) -> dict:
    stmt = select(Folder).where(Folder.workspace_id == uuid.UUID(ctx.workspace_id))
    if body.parent_id:
        stmt = stmt.where(Folder.parent_id == uuid.UUID(body.parent_id))
    else:
        stmt = stmt.where(Folder.parent_id.is_(None))

    result = await db.execute(stmt)
    folders = result.scalars().all()
    return {
        "folders": [
            {
                "id": str(f.id),
                "name": f.name,
                "parent_id": str(f.parent_id) if f.parent_id else None,
            }
            for f in folders
        ]
    }
