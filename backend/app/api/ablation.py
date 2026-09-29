from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.qa import QARequest
from app.services.ablation_adaptive_service import (
    generate_adaptive_retrieval_answer,
)


router = APIRouter(
    prefix="/api/v1",
    tags=["ablation"],
)


@router.post("/ask/ablation/adaptive-retrieval")
def ask_adaptive_retrieval(
    request: QARequest,
    db: Session = Depends(get_db),
):
    return generate_adaptive_retrieval_answer(
        db=db,
        question=request.question,
        top_k=5,
    )
