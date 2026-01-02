from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "Code Review API"
    debug: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./code_review.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Anthropic
    anthropic_api_key: str = ""

    # AI Model Configuration
    ai_model_triage: str = "claude-3-5-haiku-20241022"
    ai_model_review: str = "claude-sonnet-4-20250514"
    ai_model_complex: str = "claude-opus-4-20250514"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # GitHub App
    github_app_id: str = ""
    github_app_private_key: str = ""
    github_webhook_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
