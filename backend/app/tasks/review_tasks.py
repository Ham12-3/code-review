import asyncio
import time
from typing import Any

from celery_app import celery_app


def run_async(coro):
    """Helper to run async code in Celery tasks."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3)
def analyze_code_task(self, review_id: int, use_complex_model: bool = False) -> dict[str, Any]:
    """
    Celery task for async code analysis.
    Use this for longer-running analyses or when you need reliable retries.
    """
    from app.core.database import async_session_maker
    from app.core.config import get_settings
    from app.models.review import CodeReview, ReviewComment, ReviewResult, ReviewStatus
    from app.services.ai.langchain_pipeline import CodeReviewPipeline
    from sqlalchemy import select

    settings = get_settings()

    async def _run_analysis():
        async with async_session_maker() as db:
            # Fetch the review
            query = select(CodeReview).where(CodeReview.id == review_id)
            result = await db.execute(query)
            review = result.scalar_one_or_none()

            if not review:
                return {"error": "Review not found"}

            start_time = time.time()

            try:
                # Use LangGraph pipeline for comprehensive analysis
                model = (
                    settings.ai_model_complex
                    if use_complex_model
                    else settings.ai_model_review
                )

                pipeline = CodeReviewPipeline(
                    api_key=settings.anthropic_api_key,
                    model=model,
                )

                analysis_result = await pipeline.run(
                    code=review.code_content,
                    language=review.language,
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

                # Create result
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

                return {
                    "status": "completed",
                    "review_id": review_id,
                    "issues_found": len(analysis_result.get("issues", [])),
                    "processing_time_ms": processing_time,
                }

            except Exception as e:
                review.status = ReviewStatus.FAILED
                await db.commit()
                raise self.retry(exc=e, countdown=60)

    return run_async(_run_analysis())


@celery_app.task
def generate_report_task(review_id: int) -> dict[str, Any]:
    """Generate a detailed report for a completed review."""
    from app.core.database import async_session_maker
    from app.models.review import CodeReview, ReviewStatus
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    async def _generate_report():
        async with async_session_maker() as db:
            query = (
                select(CodeReview)
                .options(
                    selectinload(CodeReview.comments),
                    selectinload(CodeReview.result),
                )
                .where(CodeReview.id == review_id)
            )
            result = await db.execute(query)
            review = result.scalar_one_or_none()

            if not review or review.status != ReviewStatus.COMPLETED:
                return {"error": "Review not found or not completed"}

            # Build report
            report = {
                "review_id": review_id,
                "filename": review.filename,
                "language": review.language,
                "summary": review.result.summary if review.result else None,
                "quality_score": review.result.quality_score if review.result else None,
                "total_issues": len(review.comments),
                "issues_by_severity": {},
                "issues_by_category": {},
                "comments": [],
            }

            for comment in review.comments:
                # Count by severity
                sev = comment.severity.value
                report["issues_by_severity"][sev] = (
                    report["issues_by_severity"].get(sev, 0) + 1
                )

                # Count by category
                cat = comment.category or "other"
                report["issues_by_category"][cat] = (
                    report["issues_by_category"].get(cat, 0) + 1
                )

                # Add comment detail
                report["comments"].append(
                    {
                        "lines": f"{comment.line_start}-{comment.line_end}",
                        "severity": sev,
                        "category": cat,
                        "description": comment.content,
                        "suggestion": comment.suggestion,
                    }
                )

            return report

    return run_async(_generate_report())
