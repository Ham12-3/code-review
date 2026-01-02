from fastapi import APIRouter, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import async_session_maker
from app.models.github import GitHubInstallation, GitHubRepository, PullRequestReview
from app.schemas.github import (
    GitHubInstallationResponse,
    GitHubInstallationWithRepos,
    GitHubRepositoryResponse,
    PRReviewResponse,
    PRReviewCreate,
    RepoContentsResponse,
    RepoContentItem,
    FileContentResponse,
    PullRequestInfo,
    ReviewFileRequest,
)
from app.services.github import GitHubAppClient

router = APIRouter()


def get_github_client() -> GitHubAppClient:
    return GitHubAppClient()


# Installation endpoints


@router.post("/installations/sync")
async def sync_installations():
    """
    Sync installations from GitHub API to local database.
    Use this for local development when webhooks aren't available.
    Removes uninstalled apps and adds new ones.
    """
    from sqlalchemy import delete

    client = get_github_client()

    try:
        installations = await client.list_installations()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch installations from GitHub: {str(e)}")

    # Get the list of valid installation IDs from GitHub
    valid_installation_ids = {inst["id"] for inst in installations}

    synced = []
    removed = []

    async with async_session_maker() as db:
        # Remove installations that no longer exist on GitHub
        existing_query = select(GitHubInstallation)
        existing_result = await db.execute(existing_query)
        existing_installations = existing_result.scalars().all()

        for existing in existing_installations:
            if existing.installation_id not in valid_installation_ids:
                # Delete associated repositories first
                await db.execute(
                    delete(GitHubRepository).where(
                        GitHubRepository.installation_id == existing.id
                    )
                )
                # Delete the installation
                await db.delete(existing)
                removed.append(existing.account_login)

        # Add new installations
        for inst in installations:
            query = select(GitHubInstallation).where(
                GitHubInstallation.installation_id == inst["id"]
            )
            result = await db.execute(query)
            existing = result.scalar_one_or_none()

            if not existing:
                # Create new installation
                new_install = GitHubInstallation(
                    installation_id=inst["id"],
                    account_login=inst["account"]["login"],
                    account_type=inst["account"]["type"],
                    account_avatar_url=inst["account"].get("avatar_url"),
                )
                db.add(new_install)
                await db.flush()

                # Now fetch and sync repos for this installation
                try:
                    repos = await client.list_repos(inst["id"])
                    for repo in repos:
                        new_repo = GitHubRepository(
                            installation_id=new_install.id,
                            repo_id=repo["id"],
                            full_name=repo["full_name"],
                            private=repo["private"],
                            default_branch=repo.get("default_branch", "main"),
                        )
                        db.add(new_repo)
                except Exception as e:
                    print(f"Failed to sync repos for installation {inst['id']}: {e}")

                synced.append(inst["account"]["login"])
            else:
                synced.append(f"{inst['account']['login']} (already exists)")

        await db.commit()

    return {
        "message": "Sync complete",
        "installations": synced,
        "removed": removed,
    }


@router.get("/installations", response_model=list[GitHubInstallationWithRepos])
async def list_installations():
    """List all GitHub App installations."""
    async with async_session_maker() as db:
        query = select(GitHubInstallation).options(
            selectinload(GitHubInstallation.repositories)
        )
        result = await db.execute(query)
        return result.scalars().all()


@router.get("/installations/{installation_id}", response_model=GitHubInstallationWithRepos)
async def get_installation(installation_id: int):
    """Get a specific installation by ID."""
    async with async_session_maker() as db:
        query = (
            select(GitHubInstallation)
            .options(selectinload(GitHubInstallation.repositories))
            .where(GitHubInstallation.installation_id == installation_id)
        )
        result = await db.execute(query)
        installation = result.scalar_one_or_none()

        if not installation:
            raise HTTPException(status_code=404, detail="Installation not found")

        return installation


# Repository endpoints


@router.get("/repos", response_model=list[GitHubRepositoryResponse])
async def list_repos(installation_id: int | None = None):
    """List repositories, optionally filtered by installation."""
    async with async_session_maker() as db:
        query = select(GitHubRepository)
        if installation_id:
            query = query.join(GitHubInstallation).where(
                GitHubInstallation.installation_id == installation_id
            )
        query = query.order_by(GitHubRepository.full_name)
        result = await db.execute(query)
        return result.scalars().all()


@router.get("/repos/{owner}/{repo}/contents", response_model=RepoContentsResponse)
async def get_repo_contents(
    owner: str,
    repo: str,
    path: str = "",
    ref: str | None = None,
):
    """Get repository contents at a path."""
    async with async_session_maker() as db:
        # Find repo
        query = select(GitHubRepository).where(
            GitHubRepository.full_name == f"{owner}/{repo}"
        )
        result = await db.execute(query)
        db_repo = result.scalar_one_or_none()

        if not db_repo:
            raise HTTPException(status_code=404, detail="Repository not found")

        # Get installation
        install_query = select(GitHubInstallation).where(
            GitHubInstallation.id == db_repo.installation_id
        )
        install_result = await db.execute(install_query)
        installation = install_result.scalar_one()

    client = get_github_client()

    try:
        contents = await client.get_repo_contents(
            installation.installation_id,
            owner,
            repo,
            path,
            ref or db_repo.default_branch,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Handle single file vs directory
    if isinstance(contents, dict):
        items = [contents]
    else:
        items = contents

    return RepoContentsResponse(
        items=[
            RepoContentItem(
                name=item["name"],
                path=item["path"],
                type=item["type"],
                size=item.get("size"),
                sha=item["sha"],
            )
            for item in items
        ],
        path=path,
        ref=ref,
    )


@router.get("/repos/{owner}/{repo}/file", response_model=FileContentResponse)
async def get_file_content(
    owner: str,
    repo: str,
    path: str,
    ref: str | None = None,
):
    """Get file content."""
    async with async_session_maker() as db:
        query = select(GitHubRepository).where(
            GitHubRepository.full_name == f"{owner}/{repo}"
        )
        result = await db.execute(query)
        db_repo = result.scalar_one_or_none()

        if not db_repo:
            raise HTTPException(status_code=404, detail="Repository not found")

        install_query = select(GitHubInstallation).where(
            GitHubInstallation.id == db_repo.installation_id
        )
        install_result = await db.execute(install_query)
        installation = install_result.scalar_one()

    client = get_github_client()

    try:
        content, sha = await client.get_file_content(
            installation.installation_id,
            owner,
            repo,
            path,
            ref or db_repo.default_branch,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Detect language from extension
    ext_to_lang = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".jsx": "javascript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".cpp": "cpp",
        ".c": "c",
        ".cs": "csharp",
        ".rb": "ruby",
        ".php": "php",
    }
    ext = "." + path.split(".")[-1] if "." in path else ""
    language = ext_to_lang.get(ext)

    return FileContentResponse(
        content=content,
        path=path,
        sha=sha,
        size=len(content),
        language=language,
    )


@router.post("/repos/{owner}/{repo}/review")
async def review_file(
    owner: str,
    repo: str,
    request: ReviewFileRequest,
    background_tasks: BackgroundTasks,
):
    """Review a specific file from a repository."""
    async with async_session_maker() as db:
        query = select(GitHubRepository).where(
            GitHubRepository.full_name == f"{owner}/{repo}"
        )
        result = await db.execute(query)
        db_repo = result.scalar_one_or_none()

        if not db_repo:
            raise HTTPException(status_code=404, detail="Repository not found")

        install_query = select(GitHubInstallation).where(
            GitHubInstallation.id == db_repo.installation_id
        )
        install_result = await db.execute(install_query)
        installation = install_result.scalar_one()

    client = get_github_client()

    try:
        content, sha = await client.get_file_content(
            installation.installation_id,
            owner,
            repo,
            request.path,
            request.ref or db_repo.default_branch,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Detect language
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
    ext = "." + request.path.split(".")[-1] if "." in request.path else ""
    language = ext_to_lang.get(ext)

    # Create review via existing API
    from app.models.review import CodeReview
    from app.api.reviews import run_analysis

    async with async_session_maker() as db:
        review = CodeReview(
            code_content=content,
            language=language,
            filename=f"{owner}/{repo}/{request.path}",
        )
        db.add(review)
        await db.commit()
        await db.refresh(review)

        background_tasks.add_task(
            run_analysis,
            review_id=review.id,
            use_complex_model=request.use_complex_model,
        )

        return {"review_id": review.id, "message": "Analysis started"}


# Pull Request endpoints


@router.get("/repos/{owner}/{repo}/pulls", response_model=list[PullRequestInfo])
async def list_pull_requests(owner: str, repo: str, state: str = "open"):
    """List pull requests for a repository."""
    async with async_session_maker() as db:
        query = select(GitHubRepository).where(
            GitHubRepository.full_name == f"{owner}/{repo}"
        )
        result = await db.execute(query)
        db_repo = result.scalar_one_or_none()

        if not db_repo:
            raise HTTPException(status_code=404, detail="Repository not found")

        install_query = select(GitHubInstallation).where(
            GitHubInstallation.id == db_repo.installation_id
        )
        install_result = await db.execute(install_query)
        installation = install_result.scalar_one()

    client = get_github_client()

    try:
        prs = await client.list_pull_requests(
            installation.installation_id, owner, repo, state
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return [
        PullRequestInfo(
            number=pr["number"],
            title=pr["title"],
            state=pr["state"],
            user_login=pr["user"]["login"],
            user_avatar=pr["user"].get("avatar_url"),
            head_sha=pr["head"]["sha"],
            head_ref=pr["head"]["ref"],
            base_ref=pr["base"]["ref"],
            created_at=pr["created_at"],
            updated_at=pr["updated_at"],
            additions=pr.get("additions", 0),
            deletions=pr.get("deletions", 0),
            changed_files=pr.get("changed_files", 0),
            html_url=pr["html_url"],
        )
        for pr in prs
    ]


@router.get("/repos/{owner}/{repo}/pulls/{pr_number}/reviews", response_model=list[PRReviewResponse])
async def list_pr_reviews(owner: str, repo: str, pr_number: int):
    """List AI reviews for a pull request."""
    async with async_session_maker() as db:
        query = (
            select(PullRequestReview)
            .join(GitHubRepository)
            .where(
                GitHubRepository.full_name == f"{owner}/{repo}",
                PullRequestReview.pr_number == pr_number,
            )
            .order_by(PullRequestReview.created_at.desc())
        )
        result = await db.execute(query)
        return result.scalars().all()


@router.post("/repos/{owner}/{repo}/pulls/{pr_number}/review", response_model=PRReviewResponse)
async def create_pr_review(
    owner: str,
    repo: str,
    pr_number: int,
    request: PRReviewCreate,
    background_tasks: BackgroundTasks,
):
    """Trigger AI review for a pull request."""
    async with async_session_maker() as db:
        query = select(GitHubRepository).where(
            GitHubRepository.full_name == f"{owner}/{repo}"
        )
        result = await db.execute(query)
        db_repo = result.scalar_one_or_none()

        if not db_repo:
            raise HTTPException(status_code=404, detail="Repository not found")

        install_query = select(GitHubInstallation).where(
            GitHubInstallation.id == db_repo.installation_id
        )
        install_result = await db.execute(install_query)
        installation = install_result.scalar_one()

        # Get PR details from GitHub
        client = get_github_client()
        try:
            pr = await client.get_pull_request(
                installation.installation_id, owner, repo, pr_number
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Create review record
        review = PullRequestReview(
            repository_id=db_repo.id,
            pr_number=pr_number,
            pr_title=pr["title"],
            head_sha=pr["head"]["sha"],
            base_branch=pr["base"]["ref"],
            head_branch=pr["head"]["ref"],
        )
        db.add(review)
        await db.commit()
        await db.refresh(review)

        # Trigger analysis
        from app.tasks.github_tasks import review_pull_request_task

        background_tasks.add_task(
            lambda: review_pull_request_task.delay(
                installation_id=installation.installation_id,
                owner=owner,
                repo=repo,
                pr_number=pr_number,
                pr_review_id=review.id,
                use_complex_model=request.use_complex_model,
            )
        )

        return review
