from sqlalchemy.orm import Session

from app.models.document_chunk import DocumentChunk
from app.services.bm25_search import bm25_search
from app.services.vector_search import vector_search


def hybrid_search(
    db: Session,
    query: str,
    top_k: int = 5,
    candidate_k: int = 10,
) -> list[dict]:
    if not query.strip():
        return []

    dense_results = vector_search(
        db,
        query,
        top_k=candidate_k,
    )

    bm25_results = bm25_search(
        db,
        query,
        top_k=candidate_k,
    )

    scores: dict[int, float] = {}
    chunks: dict[int, DocumentChunk] = {}

    rrf_k = 60

    for rank, result in enumerate(dense_results, start=1):
        chunk = result["chunk"]

        scores[chunk.id] = scores.get(chunk.id, 0.0) + (
            1.0 / (rrf_k + rank)
        )

        chunks[chunk.id] = chunk

    for rank, result in enumerate(bm25_results, start=1):
        chunk = result["chunk"]

        scores[chunk.id] = scores.get(chunk.id, 0.0) + (
            1.0 / (rrf_k + rank)
        )

        chunks[chunk.id] = chunk

    ranked_ids = sorted(
        scores,
        key=scores.get,
        reverse=True,
    )[:top_k]

    return [
        {
            "chunk": chunks[chunk_id],
            "score": scores[chunk_id],
            "retrieval_method": "hybrid",
        }
        for chunk_id in ranked_ids
    ]
