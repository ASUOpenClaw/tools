from __future__ import annotations

import json
import uuid

import nats
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select

from src.auth import Auth
from src.config import settings
from src.dependencies import DB
from src.models.file import File
from src.models.transcription import TranscriptionStatus, TranscriptionTask

router = APIRouter()


class StartTranscriptionRequest(BaseModel):
    file_id: str
    language: str | None = None
    include_timestamps: bool = False


class GetTranscriptionRequest(BaseModel):
    task_id: str


class ListTranscriptionsRequest(BaseModel):
    page: int = 1
    limit: int = 20


@router.post("/transcriptions/start")
async def start_transcription(body: StartTranscriptionRequest, ctx: Auth, db: DB) -> dict:
    ws_id = uuid.UUID(ctx.workspace_id)
    file = await db.scalar(
        select(File).where(File.id == uuid.UUID(body.file_id), File.workspace_id == ws_id)
    )
    if file is None:
        raise HTTPException(status_code=404, detail="file not found")

    task = TranscriptionTask(
        workspace_id=ws_id,
        file_id=file.id,
        language=body.language,
        include_timestamps=body.include_timestamps,
        status=TranscriptionStatus.processing,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    nc = await nats.connect(settings.nats_url)
    js = nc.jetstream()
    await js.publish(
        "transcription.jobs",
        json.dumps({
            "task_id": str(task.id),
            "workspace_id": str(ws_id),
            "s3_key": file.s3_key,
            "filename": file.original_name,
            "mime_type": file.mime_type,
            "language": body.language,
            "include_timestamps": body.include_timestamps,
        }).encode(),
    )
    await nc.close()
    return {"task_id": str(task.id), "status": task.status.value}


@router.post("/transcriptions/status")
async def get_transcription_status(body: GetTranscriptionRequest, ctx: Auth, db: DB) -> dict:
    task = await db.scalar(
        select(TranscriptionTask).where(
            TranscriptionTask.id == uuid.UUID(body.task_id),
            TranscriptionTask.workspace_id == uuid.UUID(ctx.workspace_id),
        )
    )
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return {
        "task_id": str(task.id),
        "status": task.status.value,
        "result": task.result,
        "error": task.error,
    }


@router.post("/transcriptions/list")
async def list_transcriptions(body: ListTranscriptionsRequest, ctx: Auth, db: DB) -> dict:
    ws_id = uuid.UUID(ctx.workspace_id)
    total = await db.scalar(
        select(func.count()).select_from(
            select(TranscriptionTask.id)
            .where(TranscriptionTask.workspace_id == ws_id)
            .subquery()
        )
    ) or 0
    result = await db.execute(
        select(TranscriptionTask)
        .where(TranscriptionTask.workspace_id == ws_id)
        .order_by(TranscriptionTask.created_at.desc())
        .offset((body.page - 1) * body.limit)
        .limit(body.limit)
    )
    tasks = result.scalars().all()
    return {
        "tasks": [
            {"task_id": str(t.id), "status": t.status.value, "file_id": str(t.file_id)}
            for t in tasks
        ],
        "total": total,
    }
