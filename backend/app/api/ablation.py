from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.qa import QARequest
from app.services.ablation_adaptive_service import (
    generate_adaptive_retrieval_answer,
)
from app.services.fixed_rag_service import (
    generate_fixed_rag_answer,
)
from app.services.rag_service import generate_rag_answer


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


# Controlled benchmark corpus.
CONTROLLED_DOCUMENT_IDS = [2, 3, 4, 5, 6]


@router.post("/ask/ablation/fixed-rag")
def ask_fixed_rag_controlled(
    request: QARequest,
    db: Session = Depends(get_db),
):
    return generate_fixed_rag_answer(
        db=db,
        question=request.question,
        top_k=request.top_k,
        document_ids=CONTROLLED_DOCUMENT_IDS,
    )


@router.post("/ask/ablation/full-lumora")
def ask_full_lumora_controlled(
    request: QARequest,
    db: Session = Depends(get_db),
):
    return generate_rag_answer(
        db=db,
        question=request.question,
        top_k=request.top_k,
        task_type=request.task_type,
        document_ids=CONTROLLED_DOCUMENT_IDS,
        force_retrieval=True,
    )
