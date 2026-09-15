from pydantic import BaseModel, Field


class QARequest(BaseModel):
    question: str = Field(
        min_length=1,
        description="Student question",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of retrieval results",
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
    final_strategy: str
    context_sufficient: bool
    attempts: list[dict]
    sources: list[QASource]
    latency: QALatency

class FixedQAResponse(BaseModel):
    question: str
    answer: str
    retrieval_method: str
    result_count: int
    sources: list[QASource]
    latency: QALatency
