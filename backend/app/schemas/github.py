from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.github import PRReviewStatus


# Installation schemas
class GitHubInstallationBase(BaseModel):
    installation_id: int
    account_login: str
    account_type: str
    account_avatar_url: Optional[str] = None


class GitHubInstallationResponse(GitHubInstallationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class GitHubInstallationWithRepos(GitHubInstallationResponse):
    repositories: list["GitHubRepositoryResponse"] = []


# Repository schemas
class GitHubRepositoryBase(BaseModel):
    repo_id: int
    full_name: str
    private: bool
    default_branch: str
    language: Optional[str] = None
    description: Optional[str] = None


class GitHubRepositoryResponse(GitHubRepositoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    installation_id: int
    created_at: datetime
    updated_at: datetime


# Pull Request Review schemas
class PRReviewBase(BaseModel):
    pr_number: int
    pr_title: Optional[str] = None
    head_sha: str
    base_branch: Optional[str] = None
    head_branch: Optional[str] = None


class PRReviewResponse(PRReviewBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: int
    status: PRReviewStatus
    review_id: Optional[int] = None
    github_review_id: Optional[int] = None
    issues_found: int
    files_reviewed: int
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class PRReviewCreate(BaseModel):
    pr_number: int
    use_complex_model: bool = False


# Content schemas
class RepoContentItem(BaseModel):
    name: str
    path: str
    type: str  # "file" or "dir"
    size: Optional[int] = None
    sha: str


class RepoContentsResponse(BaseModel):
    items: list[RepoContentItem]
    path: str
    ref: Optional[str] = None


class FileContentResponse(BaseModel):
    content: str
    path: str
    sha: str
    size: int
    language: Optional[str] = None


# Pull Request schemas (from GitHub API)
class PullRequestInfo(BaseModel):
    number: int
    title: str
    state: str
    user_login: str
    user_avatar: Optional[str] = None
    head_sha: str
    head_ref: str
    base_ref: str
    created_at: str
    updated_at: str
    additions: int
    deletions: int
    changed_files: int
    html_url: str


class PRFileInfo(BaseModel):
    filename: str
    status: str  # added, removed, modified, renamed
    additions: int
    deletions: int
    patch: Optional[str] = None


# Review file request
class ReviewFileRequest(BaseModel):
    path: str
    ref: Optional[str] = None
    use_complex_model: bool = False


class ReviewFolderRequest(BaseModel):
    path: str = ""
    ref: Optional[str] = None
    file_extensions: list[str] = []  # Filter by extension, empty = all
    use_complex_model: bool = False
    max_files: int = 10
