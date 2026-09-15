FALLBACK_ORDER = {
    "dense": ["hybrid", "bm25"],
    "bm25": ["hybrid", "dense"],
    "hybrid": ["dense", "bm25"],
}


def get_fallback_strategies(
    selected_strategy: str,
) -> list[str]:
    return FALLBACK_ORDER.get(
        selected_strategy,
        ["dense", "hybrid", "bm25"],
    )
