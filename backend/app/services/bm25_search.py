from sqlalchemy import select
from sqlalchemy.orm import Session

from rank_bm25 import BM25Okapi

from app.models.document_chunk import DocumentChunk


def bm25_search(
    db: Session,
    query: str,
    top_k: int = 5,
) -> list[dict]:
    if not query.strip():
        return []

    statement = select(DocumentChunk).where(
        DocumentChunk.content.is_not(None)
    )

    chunks = db.execute(statement).scalars().all()

    if not chunks:
        return []

    corpus = [
        chunk.content.lower().split()
        for chunk in chunks
    ]

    query_tokens = query.lower().split()

    bm25 = BM25Okapi(corpus)

    scores = bm25.get_scores(query_tokens)

    ranked_indexes = sorted(
        range(len(scores)),
        key=lambda index: scores[index],
        reverse=True,
    )

    results = []

    for index in ranked_indexes[:top_k]:
        score = float(scores[index])

        if score <= 0:
            continue

        results.append(
            {
                "chunk": chunks[index],
                "score": score,
                "retrieval_method": "bm25",
            }
        )

    return results
