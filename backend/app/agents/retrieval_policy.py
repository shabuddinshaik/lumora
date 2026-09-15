def choose_retrieval_strategy(query: str) -> str:
    """
    Baseline retrieval policy for Lumora.

    Returns one of:
    - dense
    - bm25
    - hybrid
    """

    query = query.strip().lower()

    if not query:
        return "dense"

    exact_terms = [
        "supervised learning",
        "unsupervised learning",
        "neural network",
        "database",
        "operating system",
    ]

    has_exact_term = any(
        term in query
        for term in exact_terms
    )

    conceptual_phrases = [
        "how do",
        "why does",
        "why do",
        "explain",
        "how can",
        "what happens",
    ]

    is_conceptual = any(
        phrase in query
        for phrase in conceptual_phrases
    )

    if has_exact_term and is_conceptual:
        return "hybrid"

    if has_exact_term:
        return "bm25"

    return "dense"
