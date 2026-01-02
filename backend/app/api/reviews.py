from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.review import CodeReview, ReviewStatus
from app.schemas.review import (
    CodeReviewCreate,
    CodeReviewResponse,
    CodeReviewDetailResponse,
    CodeReviewListResponse,
    AnalyzeRequest,
)
from app.services.ai.claude_client import ClaudeClient

router = APIRouter()


@router.post("", response_model=CodeReviewResponse)
async def create_review(
    review_data: CodeReviewCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new code review."""
    review = CodeReview(
        code_content=review_data.code_content,
        language=review_data.language,
        filename=review_data.filename,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review


@router.get("", response_model=CodeReviewListResponse)
async def list_reviews(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """List all code reviews with pagination."""
    offset = (page - 1) * page_size

    # Get total count
    count_query = select(func.count(CodeReview.id))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    query = (
        select(CodeReview)
        .order_by(CodeReview.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    reviews = result.scalars().all()

    return CodeReviewListResponse(
        items=reviews,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{review_id}", response_model=CodeReviewDetailResponse)
async def get_review(
    review_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific code review with all details."""
    query = (
        select(CodeReview)
        .options(selectinload(CodeReview.comments), selectinload(CodeReview.result))
        .where(CodeReview.id == review_id)
    )
    result = await db.execute(query)
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    return review


@router.post("/{review_id}/analyze", response_model=CodeReviewDetailResponse)
async def analyze_review(
    review_id: int,
    analyze_request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Trigger AI analysis for a code review."""
    query = (
        select(CodeReview)
        .options(selectinload(CodeReview.comments), selectinload(CodeReview.result))
        .where(CodeReview.id == review_id)
    )
    result = await db.execute(query)
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review.status == ReviewStatus.ANALYZING:
        raise HTTPException(status_code=400, detail="Analysis already in progress")

    # Update status to analyzing
    review.status = ReviewStatus.ANALYZING
    await db.commit()

    # Run analysis in background
    background_tasks.add_task(
        run_analysis,
        review_id=review_id,
        use_complex_model=analyze_request.use_complex_model,
    )

    await db.refresh(review)
    return review


@router.delete("/{review_id}")
async def delete_review(
    review_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a code review."""
    query = select(CodeReview).where(CodeReview.id == review_id)
    result = await db.execute(query)
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    await db.delete(review)
    await db.commit()

    return {"message": "Review deleted"}


async def run_analysis(review_id: int, use_complex_model: bool = False):
    """Background task to run AI analysis."""
    from app.core.database import async_session_maker
    from app.models.review import ReviewComment, ReviewResult
    from app.core.config import get_settings
    from sqlalchemy import delete
    import time

    settings = get_settings()

    async with async_session_maker() as db:
        try:
            query = select(CodeReview).where(CodeReview.id == review_id)
            result = await db.execute(query)
            review = result.scalar_one_or_none()

            if not review:
                return

            # Clear any existing comments and results (for re-analysis)
            await db.execute(delete(ReviewComment).where(ReviewComment.review_id == review_id))
            await db.execute(delete(ReviewResult).where(ReviewResult.review_id == review_id))
            await db.commit()

            start_time = time.time()

            # Initialize Claude client
            client = ClaudeClient(api_key=settings.anthropic_api_key)

            # Select model based on complexity
            model = (
                settings.ai_model_complex
                if use_complex_model
                else settings.ai_model_review
            )

            # Run analysis
            analysis_result = await client.analyze_code(
                code=review.code_content,
                language=review.language,
                model=model,
            )

            # Create comments from issues
            for issue in analysis_result.get("issues", []):
                comment = ReviewComment(
                    review_id=review_id,
                    line_start=issue.get("line_start", 1),
                    line_end=issue.get("line_end", 1),
                    content=issue.get("description", ""),
                    severity=issue.get("severity", "info"),
                    category=issue.get("category"),
                    suggestion=issue.get("suggestion"),
                )
                db.add(comment)

            # Create result summary
            processing_time = int((time.time() - start_time) * 1000)
            review_result = ReviewResult(
                review_id=review_id,
                summary=analysis_result.get("summary", "Analysis complete"),
                issues_found=len(analysis_result.get("issues", [])),
                security_issues=analysis_result.get("security_issues", 0),
                quality_score=analysis_result.get("quality_score"),
                ai_model_used=model,
                processing_time_ms=processing_time,
            )
            db.add(review_result)

            review.status = ReviewStatus.COMPLETED
            await db.commit()

        except Exception as e:
            await db.rollback()
            # Update status in a fresh transaction
            query = select(CodeReview).where(CodeReview.id == review_id)
            result = await db.execute(query)
            review = result.scalar_one_or_none()
            if review:
                review.status = ReviewStatus.FAILED
                await db.commit()
            print(f"Analysis error for review {review_id}: {e}")
            raise e
