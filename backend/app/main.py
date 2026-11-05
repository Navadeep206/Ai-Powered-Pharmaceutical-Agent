"""RootIQ FastAPI Application Entrypoint.

AI-Powered Root Cause Analysis (RCA) and CAPA Intelligence Platform
for Pharmaceutical API Manufacturing.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.errors import register_error_handlers
from app.api.router import api_router

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown events."""
    setup_logging()
    logger.info("Initializing %s v%s (DEBUG=%s)", settings.APP_NAME, settings.APP_VERSION, settings.DEBUG)
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise AI-Powered Root Cause Analysis (RCA) and CAPA Platform for Pharmaceutical API Manufacturing.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Register Centralized Error Handlers
register_error_handlers(app)

# Configure CORS Middleware using settings.FRONTEND_URL and settings.CORS_ORIGINS
origins = list(set(settings.CORS_ORIGINS + [settings.FRONTEND_URL]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Centrally register API router with /api prefix
app.include_router(api_router)


@app.get("/", tags=["Root"], include_in_schema=False)
async def root():
    """Root redirect / information endpoint."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "docs": "/docs",
        "health": "/api/health",
        "version": settings.APP_VERSION,
    }
