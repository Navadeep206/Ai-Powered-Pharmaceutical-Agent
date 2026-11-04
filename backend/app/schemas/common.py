"""Common and reusable Pydantic schemas for RootIQ API."""

from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMetadata(BaseModel):
    """Metadata describing paginated result collections."""

    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    limit: int = Field(..., ge=1, le=100, description="Items per page limit")
    total: int = Field(..., ge=0, description="Total count of available items")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether a subsequent page exists")
    has_prev: bool = Field(..., description="Whether a preceding page exists")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standardized paginated envelope wrapping a collection of items."""

    items: List[T] = Field(..., description="Collection of items for current page")
    pagination: PaginationMetadata = Field(..., description="Pagination navigation metadata")


class StandardResponse(BaseModel, Generic[T]):
    """Generic envelope wrapping single resource responses."""

    success: bool = Field(default=True, description="Operation success indicator")
    message: Optional[str] = Field(default=None, description="Informational message")
    data: Optional[T] = Field(default=None, description="Response payload")


class SuccessResponse(BaseModel):
    """Simple confirmation response for operational status."""

    success: bool = Field(default=True, description="Operation status indicator")
    message: str = Field(..., description="Action confirmation message")


class ErrorResponse(BaseModel):
    """Standardized error envelope adhering to safe disclosure guidelines."""

    error: str = Field(..., description="Machine-readable error category")
    message: str = Field(..., description="Human-readable description of error")
    status_code: int = Field(..., description="HTTP status code")
    details: Optional[dict] = Field(default=None, description="Optional diagnostic details (no secrets)")
