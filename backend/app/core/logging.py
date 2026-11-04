"""RootIQ Centralized Logging Configuration.

Provides a unified, secure logging system adhering to GxP/FDA Part 11 audit
integrity principles by avoiding the emission of secrets, tokens, or credentials.
Prevents duplicate handlers across uvicorn reload cycles.
"""

import logging
import sys
import re
from typing import Optional
from app.core.config import settings

# Sensitive token and credential patterns to redact
SENSITIVE_PATTERNS = [
    (re.compile(r"(gsk_[a-zA-Z0-9_\-]{8,})", re.IGNORECASE), "gsk_***REDACTED***"),
    (re.compile(r"(password=)[^&\s]+", re.IGNORECASE), r"\1***REDACTED***"),
    (re.compile(r"(Bearer\s+)[a-zA-Z0-9_\-\.]+", re.IGNORECASE), r"\1***REDACTED***"),
    (re.compile(r"(postgres(?:ql)?:\/\/[^:]+:)([^@]+)(@)", re.IGNORECASE), r"\1***REDACTED***\3"),
]


class SensitiveDataFilter(logging.Filter):
    """Logging filter that scrubs known secret patterns from log messages and arguments."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, replacement in SENSITIVE_PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
        if record.args:
            if isinstance(record.args, dict):
                cleaned_args = {}
                for k, v in record.args.items():
                    if isinstance(v, str):
                        for pattern, replacement in SENSITIVE_PATTERNS:
                            v = pattern.sub(replacement, v)
                    cleaned_args[k] = v
                record.args = cleaned_args
            elif isinstance(record.args, tuple):
                cleaned_args = []
                for arg in record.args:
                    if isinstance(arg, str):
                        for pattern, replacement in SENSITIVE_PATTERNS:
                            arg = pattern.sub(replacement, arg)
                    cleaned_args.append(arg)
                record.args = tuple(cleaned_args)
        return True


def setup_logging(level: Optional[int] = None) -> None:
    """Configure RootIQ logging handlers and formatters.

    Idempotent across application reloads to prevent duplicate handlers.
    """
    if level is None:
        level = logging.DEBUG if settings.DEBUG else logging.INFO

    logger = logging.getLogger("rootiq")
    logger.setLevel(level)

    # Avoid adding duplicate handlers if already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)

        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(SensitiveDataFilter())

        logger.addHandler(handler)
        logger.propagate = False


def get_logger(name: str = "rootiq") -> logging.Logger:
    """Obtain a logger instance under the rootiq namespace."""
    if not name.startswith("rootiq"):
        name = f"rootiq.{name}"
    return logging.getLogger(name)

