from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from src.auth import Auth
from src.config import settings

router = APIRouter()

_qdrant: AsyncQdrantClient | None = None


def get_qdrant() -> AsyncQdrantClient:
    global _qdrant
    if _qdrant is None:
        _qdrant = AsyncQdrantClient(url=settings.qdrant_url)
    return _qdrant


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    folder_id: str | None = None


@router.post("/rag/search")
async def rag_search(body: SearchRequest, ctx: Auth) -> dict:
    """Semantic search over workspace documents via Qdrant."""
    client = get_qdrant()
    must = [FieldCondition(key="workspace_id", match=MatchValue(value=ctx.workspace_id))]
    if body.folder_id:
        must.append(FieldCondition(key="folder_id", match=MatchValue(value=body.folder_id)))

    # ponytail: placeholder vector — actual embedding handled by qdrant fastembed
    results = await client.search(
        collection_name=settings.qdrant_collection,
        query_vector=[0.0],
        query_filter=Filter(must=must),
        limit=body.top_k,
        with_payload=True,
    )
    return {
        "results": [
            {
                "id": str(r.id),
                "score": r.score,
                "content": r.payload.get("content", "") if r.payload else "",
                "source": r.payload.get("source", "") if r.payload else "",
                "file_id": r.payload.get("file_id", "") if r.payload else "",
            }
            for r in results
        ]
    }
