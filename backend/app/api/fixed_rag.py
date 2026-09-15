from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.qa import QARequest, FixedQAResponse
from app.services.fixed_rag_service import generate_fixed_rag_answer


router = APIRouter(
    prefix="/api/v1",
    tags=["fixed-rag"],
)


@router.post(
    "/ask/fixed",
    response_model=FixedQAResponse,
)
def ask_fixed_question(
    request: QARequest,
    db: Session = Depends(get_db),
):
    return generate_fixed_rag_answer(
        db=db,
        question=request.question,
        top_k=request.top_k,
    )
