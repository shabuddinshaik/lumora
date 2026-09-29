def get_relevant_results(
    results: list[dict],
    min_score: float = 0.0,
    strong_score: float = 0.60,
) -> list[dict]:
    """
    Deterministic baseline relevance filter.

    Results above min_score are considered relevant.
    Results at or above strong_score are considered strong.

    The strongest result is always retained.
    If a strong result exists, weaker results are not
    automatically passed to the LLM.
    """

    if not results:
        return []

    valid_results = [
        result
        for result in results
        if result.get("chunk") is not None
        and result.get("score") is not None
    ]

    relevant_results = [
        result
        for result in valid_results
        if float(result["score"]) >= min_score
    ]

    relevant_results.sort(
        key=lambda result: float(result["score"]),
        reverse=True,
    )

    if not relevant_results:
        return []

    strong_results = [
        result
        for result in relevant_results
        if float(result["score"]) >= strong_score
    ]

    if strong_results:
        return strong_results[:1]

    return relevant_results


def check_context_sufficiency(
    results: list[dict],
    min_score: float = 0.0,
) -> bool:
    """
    Baseline retrieval sufficiency check.

    Returns True when at least one valid retrieved result
    meets the configured relevance threshold.

    Note:
    This checks retrieval relevance only. It does not prove
    that the retrieved context fully answers the question.
    """

    return len(
        get_relevant_results(
            results,
            min_score=min_score,
        )
    ) > 0
