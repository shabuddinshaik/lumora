from sqlalchemy.orm import Session

from app.agents.context_checker import check_context_sufficiency
from app.agents.fallback_policy import get_fallback_strategies
from app.agents.retrieval_policy import choose_retrieval_strategy
from app.services.hybrid_search import hybrid_search
from app.services.vector_search import vector_search
from app.services.bm25_search import bm25_search

RETRIEVAL_THRESHOLDS = {
    "dense": 0.50,
    "bm25": 0.10,
    "hybrid": 0.02,
}


def _retrieve(
    db: Session,
    query: str,
    strategy: str,
    top_k: int,
) -> list[dict]:
    if strategy == "bm25":
        return bm25_search(
            db,
            query,
            top_k=top_k,
        )

    if strategy == "hybrid":
        return hybrid_search(
            db,
            query,
            top_k=top_k,
        )

    return vector_search(
        db,
        query,
        top_k=top_k,
    )


def retrieve_with_agent(
    db: Session,
    query: str,
    top_k: int = 5,
) -> dict:
    initial_strategy = choose_retrieval_strategy(query)

    strategies = [
        initial_strategy,
        *get_fallback_strategies(initial_strategy),
    ]

    attempts = []

    for strategy in strategies:
        results = _retrieve(
            db,
            query,
            strategy,
            top_k,
        )

        threshold = RETRIEVAL_THRESHOLDS[strategy]

        context_sufficient = check_context_sufficiency(
            results,
            min_score=threshold,
        )

        attempts.append(
            {
                "strategy": strategy,
                "threshold": threshold,
                "result_count": len(results),
                "context_sufficient": context_sufficient,
            }
        )

        if context_sufficient:
            return {
                "query": query,
                "selected_strategy": initial_strategy,
                "final_strategy": strategy,
                "results": results,
                "result_count": len(results),
                "context_sufficient": True,
                "attempts": attempts,
            }

    return {
        "query": query,
        "selected_strategy": initial_strategy,
        "final_strategy": strategies[-1],
        "results": results,
        "result_count": len(results),
        "context_sufficient": False,
        "attempts": attempts,
    }
