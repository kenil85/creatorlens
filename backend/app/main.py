import asyncio
import sys

# Fix for Windows — asyncio subprocess requires ProactorEventLoop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import get_settings
from app.core.logging import setup_logging, logger
from app.api.routes import pipeline, search

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.app_env)
    logger.info("creatorlens.startup", env=settings.app_env)
    yield
    logger.info("creatorlens.shutdown")


app = FastAPI(
    title="CreatorLens API",
    description="AI-powered video intelligence engine for the creator economy",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pipeline.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env, "version": "1.0.0"}


@app.get("/")
async def root():
    return {
        "name": "CreatorLens API",
        "docs": "/docs",
        "health": "/health",
    }
