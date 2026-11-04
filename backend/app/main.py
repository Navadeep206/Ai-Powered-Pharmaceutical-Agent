"""RootIQ FastAPI Application Entrypoint.

AI-Powered Root Cause Analysis (RCA) and CAPA Intelligence Platform
for Pharmaceutical API Manufacturing.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes.health import router as health_router

app = FastAPI(
    title="RootIQ API",
    version="1.0.0",
    description="Enterprise AI-Powered Root Cause Analysis (RCA) and CAPA Platform for Pharmaceutical API Manufacturing.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS Middleware
origins = list(set(settings.CORS_ORIGINS + [settings.FRONTEND_URL, "http://localhost:5173"]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Health check router at /api prefix (GET /api/health)
app.include_router(health_router, prefix="/api")


@app.get("/", tags=["Root"], include_in_schema=False)
async def root():
    """Root redirect / information endpoint."""
    return {
        "message": "Welcome to RootIQ API",
        "docs": "/docs",
        "health": "/api/health",
        "version": "1.0.0",
    }
