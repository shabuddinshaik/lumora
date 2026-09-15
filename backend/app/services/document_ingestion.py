from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.chunker import chunk_text
from app.services.document_extractor import extract_text
from app.services.embedding_service import generate_embeddings


def ingest_document(
    db: Session,
    document: Document,
) -> int:
    text = extract_text(document.file_path)

    if not text:
        raise ValueError(
            f"No text could be extracted from document: {document.file_name}"
        )

    chunks = chunk_text(text)

    if not chunks:
        raise ValueError(
            f"No chunks could be created from document: {document.file_name}"
        )

    embeddings = generate_embeddings(chunks)

    if len(chunks) != len(embeddings):
        raise ValueError(
            "Number of chunks does not match number of embeddings"
        )

    for index, (chunk, embedding) in enumerate(
        zip(chunks, embeddings)
    ):
        db_chunk = DocumentChunk(
            document_id=document.id,
            chunk_index=index,
            content=chunk,
            embedding=embedding,
        )

        db.add(db_chunk)

    db.commit()

    return len(chunks)
