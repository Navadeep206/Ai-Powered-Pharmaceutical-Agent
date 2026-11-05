"""SQLAlchemy Database Engine and Session Management for RootIQ.

Establishes a centralized synchronous connection pool, declarative base,
and session generator dependency adhering to SQLAlchemy 2.0 standards.
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("database.session")

# Engine options for PostgreSQL connection pooling
ENGINE_KWARGS = {
    "pool_pre_ping": True,
    "pool_recycle": 1800,  # Recycle connections after 30 minutes
    "echo": settings.DEBUG,
}

# Attach connection pool sizing if not using SQLite in-memory
if "sqlite" in settings.DATABASE_URL.lower():
    ENGINE_KWARGS["connect_args"] = {"check_same_thread": False}
else:
    ENGINE_KWARGS["pool_size"] = 10
    ENGINE_KWARGS["max_overflow"] = 20
    ENGINE_KWARGS["pool_timeout"] = 30

# Centralized engine instance (connection is lazily initialized on first checkout)
engine = create_engine(
    settings.DATABASE_URL,
    **ENGINE_KWARGS,
)

# Reusable sessionmaker factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative Base class for all future RootIQ database entity models."""

    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a managed database session and guarantees closure."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
