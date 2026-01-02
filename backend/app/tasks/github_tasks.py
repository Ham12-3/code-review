import asyncio
import logging
from datetime import datetime
from typing import Any

from celery_app import celery_app

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async code in Celery tasks."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3)
def review_pull_request_task(
    self,
    installation_id: int,
    owner: str,
    repo: str,
    pr_number: int,
    pr_review_id: int,
    use_complex_model: bool = False,
) -> dict[str, Any]:
    """
    Celery task to review a pull request and post comments to GitHub.

    1. Fetch PR diff and changed files
    2. Analyze each changed file with AI
    3. Post inline comments for issues
    4. Post summary comment
    """
    from app.core.database import async_session_maker
    from app.core.config import get_settings
    from app.models.github import PullRequestReview, PRReviewStatus
    from app.services.github import GitHubAppClient
    from app.services.ai.claude_client import ClaudeClient
    from sqlalchemy import select

    settings = get_settings()

    async def _run_review():
        async with async_session_maker() as db:
            # Get the review record
            query = select(PullRequestReview).where(PullRequestReview.id == pr_review_id)
            result = await db.execute(query)
            review = result.scalar_one_or_none()

            if not review:
                return {"error": "Review not found"}

            review.status = PRReviewStatus.ANALYZING
            await db.commit()

            try:
                github = GitHubAppClient()
                claude = ClaudeClient(api_key=settings.anthropic_api_key)

                model = (
                    settings.ai_model_complex
                    if use_complex_model
                    else settings.ai_model_review
                )

                # Get PR details and files
                pr = await github.get_pull_request(
                    installation_id, owner, repo, pr_number
                )
                pr_files = await github.get_pr_files(
                    installation_id, owner, repo, pr_number
                )

                all_issues = []
                files_reviewed = 0
                review_comments = []

                # Review each changed file
                for file in pr_files:
                    filename = file["filename"]
                    status = file["status"]

                    # Skip deleted files and non-code files
                    if status == "removed":
                        continue

                    # Check if it's a code file
                    code_extensions = {
                        ".py", ".js", ".ts", ".tsx", ".jsx", ".java",
                        ".go", ".rs", ".cpp", ".c", ".cs", ".rb", ".php",
                    }
                    ext = "." + filename.split(".")[-1] if "." in filename else ""
                    if ext not in code_extensions:
                        continue

                    # Get file content
                    try:
                        content, _ = await github.get_file_content(
                            installation_id,
                            owner,
                            repo,
                            filename,
                            pr["head"]["sha"],
                        )
                    except Exception as e:
                        logger.warning(f"Could not fetch {filename}: {e}")
                        continue

                    # Get language from extension
                    ext_to_lang = {
                        ".py": "python",
                        ".js": "javascript",
                        ".ts": "typescript",
                        ".tsx": "typescript",
                        ".jsx": "javascript",
                        ".java": "java",
                        ".go": "go",
                        ".rs": "rust",
                    }
                    language = ext_to_lang.get(ext)

                    # Analyze with Claude
                    try:
                        analysis = await claude.analyze_code(
                            code=content,
                            language=language,
                            model=model,
                        )
                    except Exception as e:
                        logger.error(f"Analysis failed for {filename}: {e}")
                        continue

                    files_reviewed += 1

                    # Collect issues
                    for issue in analysis.get("issues", []):
                        severity = issue.get("severity", "info")
                        # Only include warnings and above
                        if severity in ("warning", "error", "critical"):
                            all_issues.append({
                                "file": filename,
                                **issue,
                            })

                            # Prepare inline comment
                            line = issue.get("line_start", 1)
                            body = f"**{severity.upper()}**: {issue.get('description', '')}"
                            if issue.get("suggestion"):
                                body += f"\n\n💡 **Suggestion**: {issue['suggestion']}"

                            review_comments.append({
                                "path": filename,
                                "line": line,
                                "body": body,
                            })

                # Build summary
                if not files_reviewed:
                    summary = "No code files to review in this PR."
                else:
                    severity_counts = {}
                    for issue in all_issues:
                        sev = issue.get("severity", "info")
                        severity_counts[sev] = severity_counts.get(sev, 0) + 1

                    summary_parts = [
                        f"## AI Code Review Summary\n",
                        f"**Files reviewed**: {files_reviewed}",
                        f"**Issues found**: {len(all_issues)}",
                    ]

                    if severity_counts:
                        counts_str = ", ".join(
                            f"{count} {sev}" for sev, count in severity_counts.items()
                        )
                        summary_parts.append(f"**Breakdown**: {counts_str}")

                    if len(all_issues) == 0:
                        summary_parts.append("\n✅ No significant issues found!")
                    elif severity_counts.get("critical", 0) > 0:
                        summary_parts.append(
                            "\n⚠️ **Critical issues found** - please review before merging."
                        )

                    summary_parts.append(
                        f"\n\n---\n*Reviewed with {model}*"
                    )
                    summary = "\n".join(summary_parts)

                # Post review to GitHub
                try:
                    # Determine review event based on issues
                    if severity_counts.get("critical", 0) > 0:
                        event = "REQUEST_CHANGES"
                    elif len(all_issues) > 0:
                        event = "COMMENT"
                    else:
                        event = "APPROVE"

                    github_review = await github.create_review(
                        installation_id=installation_id,
                        owner=owner,
                        repo=repo,
                        pr_number=pr_number,
                        commit_id=pr["head"]["sha"],
                        body=summary,
                        event=event,
                        comments=review_comments[:50],  # GitHub limits to 50 comments
                    )

                    review.github_review_id = github_review.get("id")

                except Exception as e:
                    logger.error(f"Failed to post GitHub review: {e}")
                    # Still mark as completed, just note the error
                    review.error_message = f"Posted analysis but failed to create GitHub review: {e}"

                # Update review record
                review.status = PRReviewStatus.COMPLETED
                review.issues_found = len(all_issues)
                review.files_reviewed = files_reviewed
                review.completed_at = datetime.utcnow()
                await db.commit()

                return {
                    "status": "completed",
                    "files_reviewed": files_reviewed,
                    "issues_found": len(all_issues),
                    "github_review_id": review.github_review_id,
                }

            except Exception as e:
                logger.exception(f"PR review failed: {e}")
                review.status = PRReviewStatus.FAILED
                review.error_message = str(e)
                await db.commit()
                raise self.retry(exc=e, countdown=60)

    return run_async(_run_review())
