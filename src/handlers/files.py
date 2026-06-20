from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from qdrant_client.models import FieldCondition, Filter, MatchValue
from sqlalchemy import select

from src.auth import Auth
from src.db import get_db, get_qdrant
from src.dependencies import DB
from src.models.file import File, IndexingStatus
from src.services.s3 import download_bytes

router = APIRouter()

_TEXT_MIMES = {"text/", "application/json", "application/xml", "application/yaml"}
_MAX_CONTENT_BYTES = 64 * 1024


class ListFilesRequest(BaseModel):
    folder_id: str | None = None
    page: int = 1
    limit: int = 50


class GetFileRequest(BaseModel):
    file_id: str


@router.post("/files/list")
async def list_files(body: ListFilesRequest, ctx: Auth, db: DB) -> dict:
    stmt = select(File).where(File.workspace_id == uuid.UUID(ctx.workspace_id))
    if body.folder_id:
        stmt = stmt.where(File.folder_id == uuid.UUID(body.folder_id))
    stmt = (
        stmt.order_by(File.created_at.desc())
        .offset((body.page - 1) * body.limit)
        .limit(body.limit)
    )
    result = await db.execute(stmt)
    files = result.scalars().all()
    return {
        "files": [
            {
                "id": str(f.id),
                "name": f.original_name,
                "mime_type": f.mime_type,
                "size": f.size_bytes,
                "s3_key": f.s3_key,
                "folder_id": str(f.folder_id) if f.folder_id else None,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in files
        ]
    }


@router.post("/files/get")
async def get_file(body: GetFileRequest, ctx: Auth, db: DB) -> dict:
    try:
        file_uuid = uuid.UUID(body.file_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid file_id")

    file = await db.scalar(
        select(File).where(
            File.id == file_uuid,
            File.workspace_id == uuid.UUID(ctx.workspace_id),
        )
    )
    if file is None:
        raise HTTPException(status_code=404, detail="file not found")

    meta = {
        "id": str(file.id),
        "name": file.original_name,
        "mime_type": file.mime_type,
        "size": file.size_bytes,
        "s3_key": file.s3_key,
        "indexing_status": file.indexing_status.value,
    }

    if any(file.mime_type.startswith(p) for p in _TEXT_MIMES):
        raw = await download_bytes(file.s3_key)
        text = raw[:_MAX_CONTENT_BYTES].decode("utf-8", errors="replace")
        return {**meta, "content": text, "truncated": len(raw) > _MAX_CONTENT_BYTES, "from_index": False}

    if file.indexing_status == IndexingStatus.completed:
        client = get_qdrant()
        results, _ = await client.scroll(
            collection_name=ctx.workspace_id,
            scroll_filter=Filter(
                must=[FieldCondition(key="file_id", match=MatchValue(value=str(file.id)))]
            ),
            limit=50,
            with_payload=True,
        )
        chunks = " ".join(r.payload.get("content", "") for r in results if r.payload)
        return {**meta, "content": chunks or None, "truncated": False, "from_index": True}

    return {**meta, "content": None, "note": "binary file, not yet indexed — use rag_search"}
