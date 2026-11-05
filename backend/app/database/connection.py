"""Database Connectivity and Health Verification Service for RootIQ."""

from typing import Any, Dict, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import settings
from app.core.logging import get_logger
from app.database.session import engine

logger = get_logger("database.connection")


def check_database_connectivity(target_engine=None) -> Tuple[bool, Optional[str]]:
    """Execute a lightweight 'SELECT 1' connection check on the engine.

    Returns:
        (True, None) if reachable.
        (False, error_message) if unreachable (with sanitized error details and no secrets).
    """
    check_engine = target_engine or engine
    try:
        with check_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, None
    except SQLAlchemyError as err:
        error_type = err.__class__.__name__
        logger.warning(
            "Database connectivity check failed on '%s': %s",
            settings.safe_database_url,
            error_type,
        )
        return False, f"Database connectivity failed ({error_type})."
    except Exception as err:
        error_type = err.__class__.__name__
        logger.warning(
            "Unexpected error during database connectivity verification: %s",
            error_type,
        )
        return False, f"Database unreachable ({error_type})."


def get_database_status(target_engine=None) -> Dict[str, Any]:
    """Retrieve structured connectivity metadata for diagnostics and readiness probes."""
    check_engine = target_engine or engine
    is_connected, error = check_database_connectivity(check_engine)

    pool_info = {}
    if hasattr(check_engine.pool, "size"):
        try:
            pool_info = {
                "size": check_engine.pool.size(),
                "checkedin": check_engine.pool.checkedin(),
                "checkedout": check_engine.pool.checkedout(),
                "overflow": check_engine.pool.overflow(),
            }
        except Exception:
            pool_info = {}

    status_data = {
        "connected": is_connected,
        "database": "postgresql",
        "pool": pool_info,
    }
    if not is_connected:
        status_data["error"] = error

    return status_data

