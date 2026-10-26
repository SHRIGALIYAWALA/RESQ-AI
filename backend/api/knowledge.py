"""Knowledge retrieval API with optional FAISS vector search."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from knowledge_base.knowledge_service import knowledge_service
from backend.security.dependencies import get_identity

logger = logging.getLogger("resq_ai.api.knowledge")
router = APIRouter(prefix="/api/knowledge", tags=["Knowledge"])


class KnowledgeQuery(BaseModel):
    incident_type: str = "general"
    query: str = ""
    top_k: int = 3


_faiss_index = None
_faiss_texts: List[str] = []
_faiss_sops: List[Dict[str, Any]] = []


def _init_faiss_index() -> bool:
    global _faiss_index, _faiss_texts, _faiss_sops
    if _faiss_index is not None:
        return True
    try:
        import faiss
        import numpy as np
        from sentence_transformers import SentenceTransformer

        sops = knowledge_service.sops
        if not sops:
            return False

        texts = []
        for sop in sops:
            blob = f"{sop.get('title', '')} {sop.get('hazard_type', '')} " + " ".join(sop.get("key_actions", []))
            texts.append(blob)

        model = SentenceTransformer("all-MiniLM-L6-v2")
        embeddings = model.encode(texts, convert_to_numpy=True)
        dim = embeddings.shape[1]
        index = faiss.IndexFlatL2(dim)
        index.add(np.array(embeddings, dtype=np.float32))

        _faiss_index = index
        _faiss_texts = texts
        _faiss_sops = sops
        return True
    except Exception as exc:
        logger.debug("FAISS index init skipped: %s", exc)
        return False


def _faiss_search(query: str, top_k: int) -> List[Dict[str, Any]]:
    import numpy as np
    from sentence_transformers import SentenceTransformer

    if _faiss_index is None:
        return []
    model = SentenceTransformer("all-MiniLM-L6-v2")
    vector = model.encode([query], convert_to_numpy=True).astype(np.float32)
    distances, indices = _faiss_index.search(vector, min(top_k, len(_faiss_sops)))
    results = []
    for idx, dist in zip(indices[0], distances[0]):
        if idx < 0 or idx >= len(_faiss_sops):
            continue
        sop = dict(_faiss_sops[idx])
        sop["relevance_score"] = round(float(1.0 / (1.0 + dist)), 3)
        sop["retrieval_method"] = "faiss_embedding"
        results.append(sop)
    return results


@router.post("/query")
def query_knowledge(payload: KnowledgeQuery, request: Request) -> Any:
    """Retrieve verified emergency SOPs grounded in the knowledge base."""
    identity = get_identity(request)
    results: List[Dict[str, Any]] = []

    if payload.query and _init_faiss_index():
        results = _faiss_search(payload.query, payload.top_k)

    if not results:
        keyword_results = knowledge_service.query_sops(payload.incident_type, payload.query)
        results = []
        for sop in keyword_results[: payload.top_k]:
            entry = dict(sop)
            entry["retrieval_method"] = "keyword_match"
            results.append(entry)

    if not results:
        raise HTTPException(
            status_code=404,
            detail="No verified emergency procedures found. Do not invent procedures — escalate to human operator.",
        )

    return {
        "tenant_id": identity.get("tenant_id", "demo"),
        "incident_type": payload.incident_type,
        "query": payload.query,
        "results": results,
        "grounded": True,
        "human_review_required": True,
        "limitations": [
            "Retrieved content is decision-support only.",
            "Follow authorized building SOPs and local regulations.",
        ],
    }


@router.get("/sops")
def list_sops() -> Any:
    return {"count": len(knowledge_service.sops), "sops": knowledge_service.sops}
