from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.qa import QARequest
from app.services.ablation_context_selection_service import (
    generate_context_selection_answer,
)


router = APIRouter(
    prefix="/api/v1",
    tags=["ablation"],
)


@router.post("/ask/ablation/context-selection")
def ask_context_selection(
    request: QARequest,
    db: Session = Depends(get_db),
):
    return generate_context_selection_answer(
        db=db,
        question=request.question,
        top_k=5,
    )
