from pydantic import BaseModel, Field


class QARequest(BaseModel):
    question: str = Field(
        min_length=1,
        description="User question or task",
    )
    task_type: str = Field(
        default="auto",
        description="Task type. Use auto for automatic task classification.",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of retrieval results",
    )
    document_id: int | None = Field(
        default=None,
        description="Optional document ID to restrict retrieval to a specific note",
    )


class QASource(BaseModel):
    document_id: int
    chunk_id: int
    score: float
    retrieval_method: str


class QALatency(BaseModel):
    retrieval_seconds: float
    generation_seconds: float
    total_seconds: float


class QAResponse(BaseModel):
    question: str
    answer: str
    selected_strategy: str
    final_strategy: str | None
    context_sufficient: bool
    fallback_count: int
    selected_context_count: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    attempts: list[dict]
    sources: list[QASource]
    latency: QALatency

class FixedQAResponse(BaseModel):
    question: str
    answer: str
    retrieval_method: str
    result_count: int
    selected_context_count: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    sources: list[QASource]
    latency: QALatency
