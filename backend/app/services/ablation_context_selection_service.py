from sqlalchemy.orm import Session

from app.agents.context_checker import get_relevant_results
from app.agents.retrieval_policy import choose_retrieval_strategy
from app.models.evaluation import EvaluationRun
from app.services.bm25_search import bm25_search
from app.services.context_formatter import format_context
from app.services.hybrid_search import hybrid_search
from app.services.llm_service import generate_answer
from app.services.prompt_builder import build_answer_prompt
from app.services.timing import elapsed, now
from app.services.vector_search import vector_search


FIXED_TOP_K = 5


def generate_context_selection_answer(
    db: Session,
    question: str,
    top_k: int = FIXED_TOP_K,
) -> dict:

    total_start = now()

    strategy = choose_retrieval_strategy(question)

    retrieval_start = now()

    if strategy == "bm25":
        results = bm25_search(
            db,
            question,
            top_k=FIXED_TOP_K,
        )
    elif strategy == "hybrid":
        results = hybrid_search(
            db,
            question,
            top_k=FIXED_TOP_K,
        )
    else:
        results = vector_search(
            db,
            question,
            top_k=FIXED_TOP_K,
        )

    retrieval_latency = elapsed(retrieval_start)

    # Context-selection ablation:
    # retrieve up to 5 chunks, then select only strong relevant chunks.
    relevant_results = get_relevant_results(
        results,
        min_score=0.0,
        strong_score=0.60,
    )

    context = format_context(relevant_results)

    generation_start = now()

    if not relevant_results:
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
        for result in relevant_results
    ]

    evaluation = EvaluationRun(
        question=question,
        system_type="ablation_context_selection",
        selected_strategy=strategy,
        final_strategy=strategy,
        fallback_count=0,
        total_retrieved_count=len(results),
        final_retrieved_count=len(relevant_results),
        selected_context_count=len(relevant_results),
        evidence_sufficient=bool(relevant_results),
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
        "retrieved_count": len(results),
        "selected_context_count": len(relevant_results),
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
