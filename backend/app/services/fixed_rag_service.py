from sqlalchemy.orm import Session

from app.models.evaluation import EvaluationRun
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
    document_ids: list[int] | None = None,
) -> dict:
    total_start = now()

    retrieval_start = now()

    results = vector_search(
        db,
        question,
        top_k=top_k,
        document_ids=document_ids,
    )

    retrieval_latency = elapsed(retrieval_start)

    context = format_context(results)

    generation_start = now()

    prompt = build_answer_prompt(
        question,
        context,
    )

    generation_result = generate_answer(prompt)
    answer = generation_result["response"]
    prompt_tokens = generation_result["prompt_tokens"]
    completion_tokens = generation_result["completion_tokens"]
    total_tokens = generation_result["total_tokens"]

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

    evaluation = EvaluationRun(
        question=question,
        system_type="fixed_rag",
        selected_strategy=FIXED_RETRIEVAL_METHOD,
        final_strategy=FIXED_RETRIEVAL_METHOD,
        fallback_count=0,
        total_retrieved_count=len(results),
        final_retrieved_count=len(results),
        selected_context_count=len(results),
        evidence_sufficient=bool(results),
        retrieval_latency_seconds=round(retrieval_latency, 4),
        generation_latency_seconds=round(generation_latency, 4),
        total_latency_seconds=round(total_latency, 4),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )

    db.add(evaluation)
    db.commit()

    return {
        "question": question,
        "answer": answer,
        "retrieval_method": FIXED_RETRIEVAL_METHOD,
        "result_count": len(results),
        "selected_context_count": len(results),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
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
