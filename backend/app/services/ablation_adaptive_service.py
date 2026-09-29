from sqlalchemy.orm import Session

from app.agents.retrieval_policy import choose_retrieval_strategy
from app.models.evaluation import EvaluationRun
from app.services.bm25_search import bm25_search
from app.services.context_formatter import format_context
from app.services.hybrid_search import hybrid_search
from app.services.llm_service import generate_answer
from app.services.prompt_builder import build_answer_prompt
from app.services.timing import elapsed, now
from app.services.vector_search import vector_search


FIXED_CONTEXT_SIZE = 5


def generate_adaptive_retrieval_answer(
    db: Session,
    question: str,
    top_k: int = FIXED_CONTEXT_SIZE,
) -> dict:

    total_start = now()

    strategy = choose_retrieval_strategy(question)

    retrieval_start = now()

    if strategy == "bm25":
        results = bm25_search(
            db,
            question,
            top_k=FIXED_CONTEXT_SIZE,
        )
    elif strategy == "hybrid":
        results = hybrid_search(
            db,
            question,
            top_k=FIXED_CONTEXT_SIZE,
        )
    else:
        results = vector_search(
            db,
            question,
            top_k=FIXED_CONTEXT_SIZE,
        )

    retrieval_latency = elapsed(retrieval_start)

    # Ablation: always keep a fixed context depth.
    results = results[:FIXED_CONTEXT_SIZE]

    context = format_context(results)

    generation_start = now()

    if not results:
        answer = (
            "The available learning materials do not contain enough "
            "information to answer this question."
        )

        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0

    else:
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
        system_type="ablation_adaptive_retrieval",
        selected_strategy=strategy,
        final_strategy=strategy,
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
        "retrieval_method": strategy,
        "selected_context_count": len(results),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "sources": sources,
        "latency": {
            "retrieval_seconds": round(retrieval_latency, 4),
            "generation_seconds": round(generation_latency, 4),
            "total_seconds": round(total_latency, 4),
        },
    }
