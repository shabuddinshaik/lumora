import re

from sqlalchemy import select
from sqlalchemy.orm import Session
from rank_bm25 import BM25Okapi

from app.models.document_chunk import DocumentChunk


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for",
    "from", "how", "in", "is", "it", "of", "on", "or", "that",
    "the", "this", "to", "was", "what", "when", "where", "which",
    "who", "why", "with",
}


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return [token for token in tokens if token not in STOPWORDS]


def bm25_search(
    db: Session,
    query: str,
    top_k: int = 5,
    document_id: int | None = None,
) -> list[dict]:
    if not query.strip():
        return []

    query_tokens = _tokenize(query)

    if not query_tokens:
        return []

    statement = select(DocumentChunk).where(
        DocumentChunk.content.is_not(None)
    )

    if document_id is not None:
        statement = statement.where(
            DocumentChunk.document_id == document_id
        )

    chunks = db.execute(statement).scalars().all()

    if not chunks:
        return []

    corpus = [
        _tokenize(chunk.content)
        for chunk in chunks
    ]

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
