import time
import base64
from typing import Any
from datetime import datetime, timedelta

import httpx
import jwt

from app.core.config import get_settings


class GitHubAppClient:
    """
    GitHub App client for repository access and PR operations.

    Handles JWT generation for app authentication and
    installation token management for API access.
    """

    BASE_URL = "https://api.github.com"

    def __init__(self):
        self.settings = get_settings()
        self._installation_tokens: dict[int, tuple[str, datetime]] = {}

    def _generate_jwt(self) -> str:
        """Generate a JWT for GitHub App authentication."""
        now = int(time.time())
        payload = {
            "iat": now,  # Issued now
            "exp": now + (5 * 60),  # Expires in 5 minutes
            "iss": self.settings.github_app_id,
        }

        private_key = self.settings.github_app_private_key.replace("\\n", "\n")
        return jwt.encode(payload, private_key, algorithm="RS256")

    async def get_installation_token(self, installation_id: int) -> str:
        """Get or refresh an installation access token."""
        # Check cache
        if installation_id in self._installation_tokens:
            token, expires_at = self._installation_tokens[installation_id]
            if datetime.utcnow() < expires_at - timedelta(minutes=5):
                return token

        # Get new token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/app/installations/{installation_id}/access_tokens",
                headers={
                    "Authorization": f"Bearer {self._generate_jwt()}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            response.raise_for_status()
            data = response.json()

        token = data["token"]
        expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
        self._installation_tokens[installation_id] = (token, expires_at.replace(tzinfo=None))

        return token

    async def _request(
        self,
        method: str,
        endpoint: str,
        installation_id: int,
        **kwargs,
    ) -> Any:
        """Make an authenticated request to GitHub API."""
        token = await self.get_installation_token(installation_id)

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                f"{self.BASE_URL}{endpoint}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                    **kwargs.pop("headers", {}),
                },
                **kwargs,
            )
            response.raise_for_status()

            if response.status_code == 204:
                return None
            return response.json()

    # Repository operations

    async def list_installations(self) -> list[dict]:
        """List all installations of this GitHub App."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/app/installations",
                headers={
                    "Authorization": f"Bearer {self._generate_jwt()}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            response.raise_for_status()
            return response.json()

    async def list_repos(self, installation_id: int) -> list[dict]:
        """List repositories accessible to an installation."""
        data = await self._request(
            "GET",
            "/installation/repositories",
            installation_id,
        )
        return data.get("repositories", [])

    async def get_repo(self, installation_id: int, owner: str, repo: str) -> dict:
        """Get repository details."""
        return await self._request(
            "GET",
            f"/repos/{owner}/{repo}",
            installation_id,
        )

    async def get_repo_contents(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        path: str = "",
        ref: str | None = None,
    ) -> list[dict] | dict:
        """Get repository contents at a path."""
        params = {}
        if ref:
            params["ref"] = ref

        return await self._request(
            "GET",
            f"/repos/{owner}/{repo}/contents/{path}",
            installation_id,
            params=params,
        )

    async def get_file_content(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        path: str,
        ref: str | None = None,
    ) -> tuple[str, str]:
        """
        Get file content decoded from base64.

        Returns:
            Tuple of (content, sha)
        """
        data = await self.get_repo_contents(installation_id, owner, repo, path, ref)

        if isinstance(data, list):
            raise ValueError(f"Path {path} is a directory, not a file")

        if data.get("type") != "file":
            raise ValueError(f"Path {path} is not a file")

        content = base64.b64decode(data["content"]).decode("utf-8")
        return content, data["sha"]

    async def get_tree(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        tree_sha: str,
        recursive: bool = True,
    ) -> list[dict]:
        """Get repository tree (file structure)."""
        params = {"recursive": "1"} if recursive else {}
        data = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/git/trees/{tree_sha}",
            installation_id,
            params=params,
        )
        return data.get("tree", [])

    # Pull Request operations

    async def list_pull_requests(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        state: str = "open",
    ) -> list[dict]:
        """List pull requests for a repository."""
        return await self._request(
            "GET",
            f"/repos/{owner}/{repo}/pulls",
            installation_id,
            params={"state": state, "per_page": 100},
        )

    async def get_pull_request(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> dict:
        """Get pull request details."""
        return await self._request(
            "GET",
            f"/repos/{owner}/{repo}/pulls/{pr_number}",
            installation_id,
        )

    async def get_pr_files(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> list[dict]:
        """Get files changed in a pull request."""
        return await self._request(
            "GET",
            f"/repos/{owner}/{repo}/pulls/{pr_number}/files",
            installation_id,
            params={"per_page": 100},
        )

    async def get_pr_diff(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> str:
        """Get the unified diff for a pull request."""
        token = await self.get_installation_token(installation_id)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3.diff",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            response.raise_for_status()
            return response.text

    # Comment operations

    async def post_issue_comment(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
    ) -> dict:
        """Post a general comment on a PR."""
        return await self._request(
            "POST",
            f"/repos/{owner}/{repo}/issues/{pr_number}/comments",
            installation_id,
            json={"body": body},
        )

    async def create_review(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        pr_number: int,
        commit_id: str,
        body: str,
        event: str = "COMMENT",
        comments: list[dict] | None = None,
    ) -> dict:
        """
        Create a pull request review with inline comments.

        Args:
            event: APPROVE, REQUEST_CHANGES, or COMMENT
            comments: List of {path, line, body} for inline comments
        """
        payload: dict[str, Any] = {
            "commit_id": commit_id,
            "body": body,
            "event": event,
        }

        if comments:
            payload["comments"] = [
                {
                    "path": c["path"],
                    "line": c.get("line") or c.get("position", 1),
                    "body": c["body"],
                }
                for c in comments
            ]

        return await self._request(
            "POST",
            f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
            installation_id,
            json=payload,
        )

    async def post_review_comment(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        pr_number: int,
        commit_id: str,
        path: str,
        line: int,
        body: str,
        side: str = "RIGHT",
    ) -> dict:
        """Post an inline review comment on a specific line."""
        return await self._request(
            "POST",
            f"/repos/{owner}/{repo}/pulls/{pr_number}/comments",
            installation_id,
            json={
                "commit_id": commit_id,
                "path": path,
                "line": line,
                "side": side,
                "body": body,
            },
        )
