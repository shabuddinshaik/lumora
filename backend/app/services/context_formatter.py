def format_context(results: list[dict]) -> str:
    if not results:
        return ""

    context_parts = []

    for index, result in enumerate(results, start=1):
        chunk = result.get("chunk")

        if chunk is None:
            continue

        content = chunk.content.strip()

        if not content:
            continue

        context_parts.append(
            f"[Context {index}]\n"
            f"{content}"
        )

    return "\n\n".join(context_parts)
