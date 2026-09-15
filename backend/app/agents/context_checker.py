def check_context_sufficiency(
    results: list[dict],
    min_score: float = 0.0,
) -> bool:
    """
    Baseline context sufficiency check.

    Checks whether at least one retrieved result
    has a score above the configured threshold.
    """

    if not results:
        return False

    valid_results = [
        result
        for result in results
        if result.get("chunk") is not None
        and result.get("score") is not None
    ]

    if not valid_results:
        return False

    best_score = max(
        float(result["score"])
        for result in valid_results
    )

    return best_score >= min_score
