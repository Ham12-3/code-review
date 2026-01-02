import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Text, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class Severity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class CodeReview(Base):
    __tablename__ = "code_reviews"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code_content: Mapped[str] = mapped_column(Text)
    language: Mapped[Optional[str]] = mapped_column(default=None)
    filename: Mapped[Optional[str]] = mapped_column(default=None)
    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus), default=ReviewStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(insert_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        insert_default=func.now(), onupdate=func.now()
    )

    # Relationships
    comments: Mapped[list["ReviewComment"]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )
    result: Mapped[Optional["ReviewResult"]] = relationship(
        back_populates="review", cascade="all, delete-orphan", uselist=False
    )


class ReviewComment(Base):
    __tablename__ = "review_comments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("code_reviews.id"))
    line_start: Mapped[int]
    line_end: Mapped[int]
    content: Mapped[str] = mapped_column(Text)
    severity: Mapped[Severity] = mapped_column(Enum(Severity), default=Severity.INFO)
    category: Mapped[Optional[str]] = mapped_column(default=None)
    suggestion: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(insert_default=func.now())

    # Relationships
    review: Mapped["CodeReview"] = relationship(back_populates="comments")


class ReviewResult(Base):
    __tablename__ = "review_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("code_reviews.id"), unique=True)
    summary: Mapped[str] = mapped_column(Text)
    issues_found: Mapped[int] = mapped_column(default=0)
    security_issues: Mapped[int] = mapped_column(default=0)
    quality_score: Mapped[Optional[int]] = mapped_column(default=None)
    ai_model_used: Mapped[str]
    processing_time_ms: Mapped[Optional[int]] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(insert_default=func.now())

    # Relationships
    review: Mapped["CodeReview"] = relationship(back_populates="result")
