from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    question: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    system_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="agentic_rag",
    )

    selected_strategy: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    final_strategy: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    fallback_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    total_retrieved_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    final_retrieved_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    selected_context_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    evidence_sufficient: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    retrieval_latency_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    generation_latency_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    total_latency_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    prompt_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    completion_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    total_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
