from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.review import ReviewStatus, Severity


# Base schemas
class ReviewCommentBase(BaseModel):
    line_start: int
    line_end: int
    content: str
    severity: Severity = Severity.INFO
    category: Optional[str] = None
    suggestion: Optional[str] = None


class ReviewResultBase(BaseModel):
    summary: str
    issues_found: int = 0
    security_issues: int = 0
    quality_score: Optional[int] = None
    ai_model_used: str
    processing_time_ms: Optional[int] = None


class CodeReviewBase(BaseModel):
    code_content: str
    language: Optional[str] = None
    filename: Optional[str] = None


# Create schemas
class CodeReviewCreate(CodeReviewBase):
    pass


class ReviewCommentCreate(ReviewCommentBase):
    pass


# Response schemas
class ReviewCommentResponse(ReviewCommentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    review_id: int
    created_at: datetime


class ReviewResultResponse(ReviewResultBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    review_id: int
    created_at: datetime


class CodeReviewResponse(CodeReviewBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: ReviewStatus
    created_at: datetime
    updated_at: datetime


class CodeReviewDetailResponse(CodeReviewResponse):
    model_config = ConfigDict(from_attributes=True)

    comments: list[ReviewCommentResponse] = []
    result: Optional[ReviewResultResponse] = None


# List response
class CodeReviewListResponse(BaseModel):
    items: list[CodeReviewResponse]
    total: int
    page: int
    page_size: int


# Analysis request
class AnalyzeRequest(BaseModel):
    use_complex_model: bool = False
