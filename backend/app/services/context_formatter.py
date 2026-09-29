def format_context(
    results: list[dict],
    max_chars: int = 6000,
) -> str:
    if not results:
        return ""

    context_parts = []
    total_chars = 0

    # Keep complete chunks only.
    # Never cut a chunk in the middle.
    for index, result in enumerate(results, start=1):
        chunk = result.get("chunk")

        if chunk is None:
            continue

        content = chunk.content.strip()

        if not content:
            continue

        context_block = (
            f"[Context {index}]\n"
            f"{content}"
        )

        separator_chars = 2 if context_parts else 0
        required_chars = separator_chars + len(context_block)

        # Stop before adding a chunk that would exceed the budget.
        if total_chars + required_chars > max_chars:
            break

        context_parts.append(context_block)
        total_chars += required_chars

    return "\n\n".join(context_parts)
