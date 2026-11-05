"""RootIQ Global Exception Handlers.

Provides safe, structured JSON responses for application and domain errors
without exposing internal stack traces, system paths, or credential secrets.
Preserves FastAPI's native validation error behavior (422 Unprocessable Entity).
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.exceptions import (
    RootIQBaseException,
    OversizedDocumentError,
    InvalidPDFFormatError,
    EmptyDocumentError,
    InvalidIncidentTextError,
    InvalidEmailInputError,
    CorruptedPDFError,
    PasswordProtectedPDFError,
)
from app.core.logging import get_logger

logger = get_logger("errors")


def register_error_handlers(app: FastAPI) -> None:
    """Register custom exception handlers on the FastAPI application."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """Handle standard HTTP exceptions with structured response."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTPException",
                "message": exc.detail,
                "status_code": exc.status_code,
            },
            headers=exc.headers,
        )

    @app.exception_handler(RootIQBaseException)
    async def domain_exception_handler(request: Request, exc: RootIQBaseException) -> JSONResponse:
        """Handle domain-specific business exceptions with appropriate status codes."""
        if isinstance(exc, OversizedDocumentError):
            status_code = 413
        elif isinstance(exc, (InvalidPDFFormatError, EmptyDocumentError, InvalidIncidentTextError, InvalidEmailInputError)):
            status_code = 400
        elif isinstance(exc, (CorruptedPDFError, PasswordProtectedPDFError)):
            status_code = 422
        else:
            status_code = 422

        return JSONResponse(
            status_code=status_code,
            content={
                "error": exc.__class__.__name__,
                "message": exc.message,
                "status_code": status_code,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected internal errors safely without leaking stack traces or secrets."""
        logger.error(
            "Unhandled server error on %s %s: %s",
            request.method,
            request.url.path,
            str(exc),
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred while processing your request. Please contact the administrator.",
                "status_code": 500,
            },
        )
