import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Text, Enum, BigInteger, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PRReviewStatus(str, enum.Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class GitHubInstallation(Base):
    """Represents a GitHub App installation on a user/org account."""

    __tablename__ = "github_installations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    installation_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    account_login: Mapped[str] = mapped_column(index=True)
    account_type: Mapped[str]  # "User" or "Organization"
    account_avatar_url: Mapped[Optional[str]] = mapped_column(default=None)
    suspended_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(insert_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        insert_default=func.now(), onupdate=func.now()
    )

    # Relationships
    repositories: Mapped[list["GitHubRepository"]] = relationship(
        back_populates="installation", cascade="all, delete-orphan"
    )


class GitHubRepository(Base):
    """Represents a repository accessible by an installation."""

    __tablename__ = "github_repositories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    installation_id: Mapped[int] = mapped_column(
        ForeignKey("github_installations.id", ondelete="CASCADE")
    )
    repo_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(index=True)  # owner/repo
    private: Mapped[bool] = mapped_column(default=False)
    default_branch: Mapped[str] = mapped_column(default="main")
    language: Mapped[Optional[str]] = mapped_column(default=None)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(insert_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        insert_default=func.now(), onupdate=func.now()
    )

    # Relationships
    installation: Mapped["GitHubInstallation"] = relationship(
        back_populates="repositories"
    )
    pr_reviews: Mapped[list["PullRequestReview"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )

    @property
    def owner(self) -> str:
        return self.full_name.split("/")[0]

    @property
    def name(self) -> str:
        return self.full_name.split("/")[1]


class PullRequestReview(Base):
    """Tracks AI reviews of pull requests."""

    __tablename__ = "pull_request_reviews"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("github_repositories.id", ondelete="CASCADE")
    )
    pr_number: Mapped[int]
    pr_title: Mapped[Optional[str]] = mapped_column(default=None)
    head_sha: Mapped[str]  # Commit SHA being reviewed
    base_branch: Mapped[Optional[str]] = mapped_column(default=None)
    head_branch: Mapped[Optional[str]] = mapped_column(default=None)
    status: Mapped[PRReviewStatus] = mapped_column(
        Enum(PRReviewStatus), default=PRReviewStatus.PENDING
    )
    review_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("code_reviews.id", ondelete="SET NULL"), default=None
    )
    github_review_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, default=None
    )  # ID of review posted to GitHub
    issues_found: Mapped[int] = mapped_column(default=0)
    files_reviewed: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(insert_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(default=None)

    # Relationships
    repository: Mapped["GitHubRepository"] = relationship(back_populates="pr_reviews")
