from dataclasses import dataclass

from app.agents.task_analyzer import TaskAnalysis


@dataclass
class ContextPolicy:
    max_chunks: int
    min_chunks: int
    allow_expansion: bool
    context_mode: str = "standard"


def choose_context_policy(
    task: TaskAnalysis,
    available_chunks: int,
) -> ContextPolicy:
    """
    Decide how much retrieved context should initially be used.

    This is the first deterministic baseline.
    It intentionally does not call an LLM.
    """

    available = max(0, available_chunks)

    if available == 0:
        return ContextPolicy(
            max_chunks=0,
            min_chunks=0,
            allow_expansion=False,
        )

    # Simple information questions normally need very little context.
    if task.task_type == "information" and task.complexity == "simple":
        return ContextPolicy(
            max_chunks=min(1, available),
            min_chunks=1,
            allow_expansion=True,
            context_mode="minimal",
        )

    # Simple coding tasks usually need the most relevant source only.
    if task.task_type in {"code", "code_modification", "debugging"}:
        if task.complexity == "simple":
            return ContextPolicy(
                max_chunks=min(1, available),
                min_chunks=1,
                allow_expansion=True,
                context_mode="targeted",
            )

        return ContextPolicy(
            max_chunks=min(3, available),
            min_chunks=1,
            allow_expansion=True,
            context_mode="deep",
        )

    # Comparisons generally need evidence for both sides.
    if task.task_type == "comparison":
        return ContextPolicy(
            max_chunks=min(3, available),
            min_chunks=min(2, available),
            allow_expansion=True,
            context_mode="multi_source",
        )

    # Summaries may need several pieces of the source.
    if task.task_type == "summarization":
        return ContextPolicy(
            max_chunks=min(5, available),
            min_chunks=1,
            allow_expansion=True,
            context_mode="broad",
        )

    # Data analysis may require multiple relevant pieces.
    if task.task_type == "data_analysis":
        return ContextPolicy(
            max_chunks=min(3, available),
            min_chunks=1,
            allow_expansion=True,
            context_mode="analytical",
        )

    # General fallback.
    return ContextPolicy(
        max_chunks=min(2, available),
        min_chunks=1,
        allow_expansion=True,
        context_mode="standard",
    )
