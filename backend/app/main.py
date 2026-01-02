from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import init_db
from app.api.reviews import router as reviews_router
from app.api.github import router as github_router
from app.api.github_webhooks import router as github_webhooks_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    await init_db()
    yield
    # Shutdown
    pass


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(reviews_router, prefix="/api/reviews", tags=["reviews"])
app.include_router(github_router, prefix="/api/github", tags=["github"])
app.include_router(github_webhooks_router, prefix="/api/github", tags=["github-webhooks"])


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
