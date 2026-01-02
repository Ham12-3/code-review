import hashlib
import hmac
import logging

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import async_session_maker
from app.models.github import GitHubInstallation, GitHubRepository, PullRequestReview

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()


def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify GitHub webhook signature."""
    if not settings.github_webhook_secret:
        logger.warning("No webhook secret configured, skipping verification")
        return True

    expected = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


@router.post("/webhooks")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Handle incoming GitHub webhook events."""
    # Verify signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    payload = await request.body()

    if not verify_signature(payload, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Get event type
    event_type = request.headers.get("X-GitHub-Event", "")
    data = await request.json()

    logger.info(f"Received GitHub webhook: {event_type}")

    # Handle events
    if event_type == "installation":
        await handle_installation_event(data)
    elif event_type == "installation_repositories":
        await handle_installation_repos_event(data)
    elif event_type == "pull_request":
        background_tasks.add_task(handle_pull_request_event, data)
    elif event_type == "ping":
        return {"message": "pong"}

    return {"status": "ok"}


async def handle_installation_event(data: dict):
    """Handle app installation/uninstallation events."""
    action = data.get("action")
    installation = data.get("installation", {})
    installation_id = installation.get("id")
    account = installation.get("account", {})

    async with async_session_maker() as db:
        if action == "created":
            # New installation
            new_install = GitHubInstallation(
                installation_id=installation_id,
                account_login=account.get("login"),
                account_type=account.get("type"),
                account_avatar_url=account.get("avatar_url"),
            )
            db.add(new_install)
            await db.commit()
            await db.refresh(new_install)

            # Add repositories
            repos = data.get("repositories", [])
            for repo in repos:
                new_repo = GitHubRepository(
                    installation_id=new_install.id,
                    repo_id=repo.get("id"),
                    full_name=repo.get("full_name"),
                    private=repo.get("private", False),
                )
                db.add(new_repo)

            await db.commit()
            logger.info(
                f"Installation created: {account.get('login')} with {len(repos)} repos"
            )

        elif action == "deleted":
            # Uninstall - cascade will delete repos and reviews
            query = select(GitHubInstallation).where(
                GitHubInstallation.installation_id == installation_id
            )
            result = await db.execute(query)
            install = result.scalar_one_or_none()

            if install:
                await db.delete(install)
                await db.commit()
                logger.info(f"Installation deleted: {account.get('login')}")

        elif action == "suspend":
            query = select(GitHubInstallation).where(
                GitHubInstallation.installation_id == installation_id
            )
            result = await db.execute(query)
            install = result.scalar_one_or_none()

            if install:
                from datetime import datetime

                install.suspended_at = datetime.utcnow()
                await db.commit()


async def handle_installation_repos_event(data: dict):
    """Handle repos added/removed from installation."""
    action = data.get("action")
    installation = data.get("installation", {})
    installation_id = installation.get("id")

    async with async_session_maker() as db:
        # Find installation
        query = select(GitHubInstallation).where(
            GitHubInstallation.installation_id == installation_id
        )
        result = await db.execute(query)
        install = result.scalar_one_or_none()

        if not install:
            logger.warning(f"Installation not found: {installation_id}")
            return

        if action == "added":
            repos = data.get("repositories_added", [])
            for repo in repos:
                new_repo = GitHubRepository(
                    installation_id=install.id,
                    repo_id=repo.get("id"),
                    full_name=repo.get("full_name"),
                    private=repo.get("private", False),
                )
                db.add(new_repo)
            await db.commit()
            logger.info(f"Added {len(repos)} repos to installation {installation_id}")

        elif action == "removed":
            repos = data.get("repositories_removed", [])
            repo_ids = [r.get("id") for r in repos]

            query = select(GitHubRepository).where(
                GitHubRepository.repo_id.in_(repo_ids)
            )
            result = await db.execute(query)
            for repo in result.scalars():
                await db.delete(repo)
            await db.commit()
            logger.info(
                f"Removed {len(repos)} repos from installation {installation_id}"
            )


async def handle_pull_request_event(data: dict):
    """Handle pull request events (opened, synchronize)."""
    action = data.get("action")
    pr = data.get("pull_request", {})
    repo = data.get("repository", {})
    installation = data.get("installation", {})

    # Only auto-review on opened or synchronized (new commits pushed)
    if action not in ("opened", "synchronize"):
        return

    async with async_session_maker() as db:
        # Find repository
        query = select(GitHubRepository).where(
            GitHubRepository.repo_id == repo.get("id")
        )
        result = await db.execute(query)
        db_repo = result.scalar_one_or_none()

        if not db_repo:
            logger.warning(f"Repository not found: {repo.get('full_name')}")
            return

        # Check if we already have a review for this SHA
        existing_query = select(PullRequestReview).where(
            PullRequestReview.repository_id == db_repo.id,
            PullRequestReview.pr_number == pr.get("number"),
            PullRequestReview.head_sha == pr.get("head", {}).get("sha"),
        )
        existing = await db.execute(existing_query)
        if existing.scalar_one_or_none():
            logger.info(f"Review already exists for PR #{pr.get('number')}")
            return

        # Create new review record
        review = PullRequestReview(
            repository_id=db_repo.id,
            pr_number=pr.get("number"),
            pr_title=pr.get("title"),
            head_sha=pr.get("head", {}).get("sha"),
            base_branch=pr.get("base", {}).get("ref"),
            head_branch=pr.get("head", {}).get("ref"),
        )
        db.add(review)
        await db.commit()
        await db.refresh(review)

        logger.info(
            f"Created PR review record for {repo.get('full_name')}#{pr.get('number')}"
        )

        # Trigger analysis task
        from app.tasks.github_tasks import review_pull_request_task

        review_pull_request_task.delay(
            installation_id=installation.get("id"),
            owner=db_repo.owner,
            repo=db_repo.name,
            pr_number=pr.get("number"),
            pr_review_id=review.id,
        )
