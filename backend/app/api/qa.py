from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.qa import QARequest, QAResponse
from app.services.rag_service import generate_rag_answer


router = APIRouter(
    prefix="/api/v1",
    tags=["qa"],
)


@router.post("/ask", response_model=QAResponse)
def ask_question(
    request: QARequest,
    db: Session = Depends(get_db),
):
    return generate_rag_answer(
        db=db,
        question=request.question,
        top_k=request.top_k,
        document_id=request.document_id,
        task_type=request.task_type,
    )
