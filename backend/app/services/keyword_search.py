from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.document_chunk import DocumentChunk


def keyword_search(
    db: Session,
    query: str,
    top_k: int = 5,
) -> list[dict]:
    if not query.strip():
        return []

    search_query = func.websearch_to_tsquery(
        "english",
        query,
    )

    rank = func.ts_rank_cd(
        DocumentChunk.search_vector,
        search_query,
    )

    statement = (
        select(
            DocumentChunk,
            rank.label("rank"),
        )
        .where(
            DocumentChunk.search_vector.op("@@")(search_query)
        )
        .order_by(rank.desc())
        .limit(top_k)
    )

    results = db.execute(statement).all()

    return [
        {
            "chunk": chunk,
            "score": float(rank_value),
            "retrieval_method": "keyword",
        }
        for chunk, rank_value in results
    ]
