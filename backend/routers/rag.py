from fastapi import APIRouter, HTTPException
from backend.schemas import (
    RAGQueryRequest, RAGQueryResponse, RAGStatusResponse, Citation
)
from backend.services.rag_service import RAGService
from backend import config

router = APIRouter()
_rag_service = RAGService()


@router.post("/index")
async def build_index():
    import os
    import json

    parsed_dir = config.PARSED_DIR
    textbooks = []
    if os.path.exists(parsed_dir):
        for f in os.listdir(parsed_dir):
            if f.endswith(".json"):
                with open(os.path.join(parsed_dir, f), "r", encoding="utf-8") as fh:
                    textbooks.append(json.load(fh))

    if not textbooks:
        raise HTTPException(400, "No parsed textbooks found.")

    _rag_service.build_index(textbooks)
    return {"status": "indexed", "books": len(textbooks), "chunks": _rag_service.chunk_count}


@router.get("/status", response_model=RAGStatusResponse)
async def rag_status():
    return RAGStatusResponse(
        indexed_books=_rag_service.indexed_books,
        chunk_count=_rag_service.chunk_count,
        status="ready" if _rag_service.chunk_count > 0 else "not_indexed",
    )


@router.post("/query", response_model=RAGQueryResponse)
async def rag_query(req: RAGQueryRequest):
    if _rag_service.chunk_count == 0:
        raise HTTPException(400, "Index not built. Call /api/rag/index first.")

    result = _rag_service.query(req.question)
    return result
