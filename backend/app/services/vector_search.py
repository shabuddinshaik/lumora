from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document_chunk import DocumentChunk
from app.services.embedding_service import generate_embeddings


def vector_search(
    db: Session,
    query: str,
    top_k: int = 5,
    document_id: int | None = None,
    document_ids: list[int] | None = None,
) -> list[dict]:
    if not query.strip():
        return []

    query_embedding = generate_embeddings([query])[0]

    distance = DocumentChunk.embedding.cosine_distance(
        query_embedding
    )

    statement = (
        select(
            DocumentChunk,
            distance.label("distance"),
        )
        .where(DocumentChunk.embedding.is_not(None))
    )

    if document_id is not None:
        statement = statement.where(
            DocumentChunk.document_id == document_id
        )

    if document_ids is not None:
        statement = statement.where(
            DocumentChunk.document_id.in_(document_ids)
        )

    statement = (
        statement
        .order_by(distance)
        .limit(top_k)
    )

    results = db.execute(statement).all()

    return [
        {
            "chunk": chunk,
            "score": 1.0 - float(distance_value),
            "retrieval_method": "dense",
        }
        for chunk, distance_value in results
    ]
