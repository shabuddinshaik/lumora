from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.document_ingestion import ingest_document

router = APIRouter(
    prefix="/api/v1/documents",
    tags=["documents"],
)

UPLOAD_DIR = Path("/app/uploads")


@router.get("")
def list_documents(
    db: Session = Depends(get_db),
):
    documents = (
        db.query(Document)
        .filter(
            Document.course_id == 1,
            Document.owner_id == 2,
            Document.source_type == "student_note",
        )
        .order_by(Document.created_at.desc())
        .all()
    )

    result = []

    for document in documents:
        chunk_count = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document.id)
            .count()
        )

        result.append(
            {
                "document_id": document.id,
                "title": document.title,
                "file_name": document.file_name,
                "document_type": document.document_type,
                "source_type": document.source_type,
                "visibility": document.visibility,
                "chunk_count": chunk_count,
                "created_at": document.created_at.isoformat()
                if document.created_at
                else None,
            }
        )

    return result


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    allowed_extensions = {".pdf", ".docx", ".txt"}

    original_name = file.filename or ""
    extension = Path(original_name).suffix.lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, DOCX, and TXT files are supported.",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    safe_name = f"{uuid4().hex}{extension}"
    file_path = UPLOAD_DIR / safe_name

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    file_path.write_bytes(content)

    document = Document(
        course_id=1,
        owner_id=2,
        title=Path(original_name).stem,
        file_name=original_name,
        document_type=extension.lstrip("."),
        source_type="student_note",
        visibility="private",
        file_path=str(file_path),
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        chunk_count = ingest_document(
            db=db,
            document=document,
        )
    except Exception as exc:
        db.delete(document)
        db.commit()

        if file_path.exists():
            file_path.unlink()

        raise HTTPException(
            status_code=500,
            detail=f"Document ingestion failed: {exc}",
        )

    return {
        "message": "Document uploaded and processed successfully.",
        "document_id": document.id,
        "file_name": document.file_name,
        "chunk_count": chunk_count,
    }


@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
):
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.course_id == 1,
            Document.owner_id == 2,
            Document.source_type == "student_note",
        )
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Note not found.",
        )

    file_path = Path(document.file_path)

    db.delete(document)
    db.commit()

    if file_path.exists():
        file_path.unlink()

    return {
        "message": "Note deleted successfully.",
        "document_id": document_id,
    }
