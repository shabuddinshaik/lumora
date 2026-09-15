from sqlalchemy.orm import Session

from app.services.context_formatter import format_context
from app.services.llm_service import generate_answer
from app.services.prompt_builder import build_answer_prompt
from app.services.timing import elapsed, now
from app.services.vector_search import vector_search


FIXED_RETRIEVAL_METHOD = "dense"
FIXED_TOP_K = 5


def generate_fixed_rag_answer(
    db: Session,
    question: str,
    top_k: int = FIXED_TOP_K,
) -> dict:
    total_start = now()

    retrieval_start = now()

    results = vector_search(
        db,
        question,
        top_k=top_k,
    )

    retrieval_latency = elapsed(retrieval_start)

    context = format_context(results)

    prompt = build_answer_prompt(
        question,
        context,
    )

    generation_start = now()

    answer = generate_answer(prompt)

    generation_latency = elapsed(generation_start)
    total_latency = elapsed(total_start)

    sources = [
        {
            "document_id": result["chunk"].document_id,
            "chunk_id": result["chunk"].id,
            "score": result["score"],
            "retrieval_method": result["retrieval_method"],
        }
        for result in results
    ]

    return {
        "question": question,
        "answer": answer,
        "retrieval_method": FIXED_RETRIEVAL_METHOD,
        "result_count": len(results),
        "sources": sources,
        "latency": {
            "retrieval_seconds": round(
                retrieval_latency,
                4,
            ),
            "generation_seconds": round(
                generation_latency,
                4,
            ),
            "total_seconds": round(
                total_latency,
                4,
            ),
        },
    }
