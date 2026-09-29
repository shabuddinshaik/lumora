from sqlalchemy.orm import Session
import time
from app.agents.context_checker import (
    check_context_sufficiency,
    get_relevant_results,
)
from app.agents.fallback_policy import get_fallback_strategies
from app.agents.retrieval_policy import choose_retrieval_strategy
from app.agents.task_analyzer import analyze_task
from app.agents.context_policy import choose_context_policy
from app.agents.evidence_validator import validate_evidence
from app.services.context_formatter import format_context
from app.services.hybrid_search import hybrid_search
from app.services.vector_search import vector_search
from app.services.bm25_search import bm25_search
from app.services.llm_service import check_evidence_sufficiency


RETRIEVAL_THRESHOLDS = {
    "dense": 0.50,
    "bm25": 0.10,
}


def _definition_evidence_guard(query: str, context: str) -> bool:
    """
    Deterministic guard for simple definition questions.

    A topic being merely mentioned or listed is not enough.
    The context should contain an explanatory statement about the topic.
    """

    normalized_query = query.lower().strip()

    if not normalized_query.startswith("what is "):
        return True

    topic = normalized_query[len("what is "):].strip().rstrip("?").strip()

    if not topic:
        return True

    normalized_context = context.lower()

    if topic not in normalized_context:
        return False

    explanation_patterns = [
        " is a ",
        " is an ",
        " refers to ",
        " means ",
        " defined as ",
        " involves ",
        " enables ",
        " allows ",
        " used to ",
        " consists of ",
        " is the ",
    ]

    # Look at sentences containing the requested topic.
    sentences = [
        sentence.strip()
        for sentence in normalized_context.replace("?", ".").split(".")
        if sentence.strip()
    ]

    topic_sentences = [
        sentence
        for sentence in sentences
        if topic in sentence
    ]

    if not topic_sentences:
        return False

    return any(
        any(pattern in sentence for pattern in explanation_patterns)
        for sentence in topic_sentences
    )


def _is_complex_query(query: str) -> bool:
    """
    Identify questions that may require multiple pieces of evidence.

    This is a deterministic baseline heuristic, not an LLM decision.
    """

    normalized = query.lower().strip()

    complex_terms = [
        " and ",
        "compare",
        "difference",
        "differences",
        "explain",
        "how",
        "why",
        "steps",
        "phases",
        "list",
        "advantages",
        "disadvantages",
        "pros",
        "cons",
    ]

    return any(term in normalized for term in complex_terms)


def _retrieve(
    db: Session,
    query: str,
    strategy: str,
    top_k: int,
    document_id: int | None = None,
):
    if strategy == "bm25":
        return bm25_search(
            db,
            query,
            top_k=top_k,
            document_id=document_id,
        )

    if strategy == "hybrid":
        return hybrid_search(
            db,
            query,
            top_k=top_k,
            document_id=document_id,
        )

    return vector_search(
        db,
        query,
        top_k=top_k,
        document_id=document_id,
    )


def retrieve_with_agent(
    db: Session,
    query: str,
    top_k: int = 5,
    document_id: int | None = None,
    task_type: str = "auto",
) -> dict:
    initial_strategy = choose_retrieval_strategy(query)

    task_analysis = analyze_task(query)

    print(
        "[Task Analysis] "
        f"type={task_analysis.task_type} "
        f"complexity={task_analysis.complexity} "
        f"context={task_analysis.requires_context} "
        f"retrieval={task_analysis.requires_retrieval} "
        f"validation={task_analysis.requires_validation}"
    )

    strategies = [
        initial_strategy,
        *get_fallback_strategies(initial_strategy),
    ]

    complex_query = _is_complex_query(query)

    attempts = []

    for strategy in strategies:
        results = _retrieve(
            db=db,
            query=query,
            strategy=strategy,
            top_k=top_k,
            document_id=document_id,
        )

        if strategy == "hybrid":
            threshold = None
            retrieval_relevant = bool(results)
        else:
            threshold = RETRIEVAL_THRESHOLDS[strategy]

            retrieval_relevant = check_context_sufficiency(
                results,
                min_score=threshold,
            )

        if not retrieval_relevant:
            attempts.append(
                {
                    "strategy": strategy,
                    "threshold": threshold,
                    "result_count": len(results),
                    "selected_context_count": 0,
                    "retrieval_relevant": False,
                    "evidence_sufficient": False,
                }
            )
            continue

        print(
            f"[Retrieval Scores] strategy={strategy} "
            f"scores={[getattr(r, 'score', None) for r in results]}"
        )

        relevant_results = get_relevant_results(
            results,
            min_score=threshold if threshold is not None else 0.0,
            strong_score=float("inf") if complex_query else 0.60,
        )

        if not relevant_results:
            attempts.append(
                {
                    "strategy": strategy,
                    "threshold": threshold,
                    "result_count": len(results),
                    "selected_context_count": 0,
                    "retrieval_relevant": True,
                    "evidence_sufficient": False,
                }
            )
            continue

        context_policy = choose_context_policy(
            task_analysis,
            available_chunks=len(relevant_results),
        )

        max_chunks = min(
            context_policy.max_chunks,
            len(relevant_results),
        )

        min_chunks = min(
            context_policy.min_chunks,
            max_chunks,
        )

        if min_chunks == 0:
            min_chunks = 1

        print(
            "[Context Policy] "
            f"min={min_chunks} "
            f"max={max_chunks} "
            f"expand={context_policy.allow_expansion}"
        )

        context_depths = [min_chunks]

        if context_policy.allow_expansion:
            context_depths.extend(
                depth
                for depth in range(min_chunks + 1, max_chunks + 1)
            )

        for context_depth in context_depths:
            selected_results = relevant_results[:context_depth]

            context = format_context(selected_results)

            print(
                "[Context Expansion] "
                f"strategy={strategy} "
                f"depth={context_depth}/{max_chunks}"
            )

            print("[Retrieved Context]")
            print(context)
            print("[End Retrieved Context]")

            evidence_start = time.perf_counter()

            deterministic_evidence = validate_evidence(
                question=query,
                context=context,
                task_type=task_analysis.task_type,
            )

            if not deterministic_evidence:
                print(
                    "[Evidence Validator] "
                    "deterministic validation failed"
                )

            evidence_sufficient = (
                deterministic_evidence
                and check_evidence_sufficiency(
                    query,
                    context,
                )
            )

            if evidence_sufficient:
                definition_supported = _definition_evidence_guard(
                    query,
                    context,
                )

                if not definition_supported:
                    print(
                        "[Definition Guard] "
                        "evidence rejected because the requested concept "
                        "is not directly explained in the context"
                    )
                    evidence_sufficient = False

            evidence_latency = time.perf_counter() - evidence_start

            print(
                f"[Evidence Check] strategy={strategy} "
                f"chunks={len(selected_results)} "
                f"sufficient={evidence_sufficient} "
                f"latency={evidence_latency:.2f}s"
            )

            attempts.append(
                {
                    "strategy": strategy,
                    "threshold": threshold,
                    "result_count": len(results),
                    "selected_context_count": len(selected_results),
                    "retrieval_relevant": True,
                    "evidence_sufficient": evidence_sufficient,
                }
            )

            if evidence_sufficient:
                return {
                    "query": query,
                    "selected_strategy": initial_strategy,
                    "final_strategy": strategy,
                    "document_id": document_id,
                    "results": selected_results,
                    "result_count": len(relevant_results),
                    "context_sufficient": True,
                    "attempts": attempts,
                }

            if not context_policy.allow_expansion:
                break

    return {
        "query": query,
        "selected_strategy": initial_strategy,
        "final_strategy": None,
        "document_id": document_id,
        "results": [],
        "result_count": 0,
        "context_sufficient": False,
        "attempts": attempts,
    }

