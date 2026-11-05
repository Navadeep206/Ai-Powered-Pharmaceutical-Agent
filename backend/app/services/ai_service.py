"""Groq AI LLM Service Module for RootIQ.

Provides resilient, authenticated access to Groq LLMs using ChatGroq from langchain-groq.
Includes health connection probing, configuration validation, and error classification.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import groq
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from app.core.config import settings
from app.core.exceptions import (
    AIAuthenticationError,
    AIConfigurationError,
    AIConnectionError,
    AIModelUnavailableError,
    AIRateLimitError,
    AITimeoutError,
)
from app.core.logging import get_logger

logger = get_logger("services.ai")


class AIService:
    """Service providing resilient, authenticated access to Groq LLMs via ChatGroq."""

    def __init__(self):
        self._client: Optional[ChatGroq] = None
        self._cached_config_key: Optional[str] = None

    def get_client(self, force_refresh: bool = False) -> ChatGroq:
        """Retrieve or initialize the singleton ChatGroq client.

        Validates configuration before instantiation and avoids redundant client creation.
        """
        if not settings.is_groq_configured:
            raise AIConfigurationError(
                "Groq API key is not configured. Set GROQ_API_KEY in your environment or .env file."
            )

        config_fingerprint = (
            f"{settings.GROQ_MODEL}:{settings.GROQ_TEMPERATURE}:{settings.GROQ_MAX_TOKENS}:{settings.GROQ_TIMEOUT}"
        )

        if self._client is not None and not force_refresh and self._cached_config_key == config_fingerprint:
            return self._client

        try:
            client = ChatGroq(
                groq_api_key=settings.GROQ_API_KEY,
                model_name=settings.GROQ_MODEL,
                temperature=settings.GROQ_TEMPERATURE,
                max_tokens=settings.GROQ_MAX_TOKENS,
                request_timeout=settings.GROQ_TIMEOUT,
                max_retries=2,
            )
            self._client = client
            self._cached_config_key = config_fingerprint
            return client
        except Exception as err:
            logger.error("Failed to initialize Groq client: %s", err.__class__.__name__)
            raise AIConfigurationError(f"Failed to initialize Groq client: {err.__class__.__name__}")

    def test_groq_connection(self) -> Dict[str, Any]:
        """Execute a minimal, harmless ping prompt to verify live Groq API responsiveness.

        Returns a structured dictionary distinguishing:
        - Connected
        - Not configured
        - Authentication failed
        - Model unavailable
        - Rate limited
        - Timeout
        - Service unavailable
        - Unexpected error
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        # 1. Verify API key is configured
        if not settings.is_groq_configured:
            return {
                "status": "Not configured",
                "connected": False,
                "provider": "Groq",
                "model": settings.GROQ_MODEL,
                "detail": "Groq API key is not configured or contains placeholder value.",
                "timestamp": timestamp,
            }

        # 2. Initialize Groq client
        try:
            client = self.get_client()
        except AIConfigurationError as err:
            return {
                "status": "Not configured",
                "connected": False,
                "provider": "Groq",
                "model": settings.GROQ_MODEL,
                "detail": str(err.message),
                "timestamp": timestamp,
            }

        # 3. Send minimal harmless prompt (strictly no pharmaceutical or proprietary incident data)
        test_messages = [HumanMessage(content="Ping. Reply with 'OK'.")]

        try:
            response = client.invoke(test_messages)
            raw_content = response.content
            if isinstance(raw_content, list):
                text_content = "".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in raw_content]).strip()
            else:
                text_content = str(raw_content).strip() if raw_content else ""

            if not text_content:
                logger.warning("Groq connection test received empty response payload.")
                return {
                    "status": "Unexpected error",
                    "connected": False,
                    "provider": "Groq",
                    "model": settings.GROQ_MODEL,
                    "detail": "Groq API returned an empty response body.",
                    "timestamp": timestamp,
                }

            logger.info("Groq connection test successful using model '%s'", settings.GROQ_MODEL)
            return {
                "status": "Connected",
                "connected": True,
                "provider": "Groq",
                "model": settings.GROQ_MODEL,
                "temperature": settings.GROQ_TEMPERATURE,
                "max_tokens": settings.GROQ_MAX_TOKENS,
                "timeout": settings.GROQ_TIMEOUT,
                "detail": f"Successfully established live connection to Groq model '{settings.GROQ_MODEL}'.",
                "timestamp": timestamp,
            }

        except groq.AuthenticationError:
            logger.warning("Groq authentication failed: invalid API key.")
            return {
                "status": "Authentication failed",
                "connected": False,
                "provider": "Groq",
                "model": settings.GROQ_MODEL,
                "detail": "Authentication with Groq API failed. Please verify your GROQ_API_KEY.",
                "timestamp": timestamp,
            }
        except groq.NotFoundError:
            logger.warning("Groq model '%s' not found or deprecated.", settings.GROQ_MODEL)
            return {
                "status": "Model unavailable",
                "connected": False,
                "provider": "Groq",
                "model": settings.GROQ_MODEL,
                "detail": f"Configured model '{settings.GROQ_MODEL}' is unavailable, decommissioned, or invalid.",
                "timestamp": timestamp,
            }
        except groq.RateLimitError:
            logger.warning("Groq rate limit encountered during connection test.")
            return {
                "status": "Rate limited",
                "connected": False,
                "provider": "Groq",
                "model": settings.GROQ_MODEL,
                "detail": "Groq API rate limit exceeded. Please retry after rate limit window resets.",
                "timestamp": timestamp,
            }
        except (groq.APITimeoutError, TimeoutError):
            logger.warning("Groq connection test timed out after %s seconds.", settings.GROQ_TIMEOUT)
            return {
                "status": "Timeout",
                "connected": False,
                "provider": "Groq",
                "model": settings.GROQ_MODEL,
                "detail": f"Request to Groq API timed out after {settings.GROQ_TIMEOUT} seconds.",
                "timestamp": timestamp,
            }
        except (groq.APIConnectionError, groq.InternalServerError):
            logger.warning("Groq service connection error or provider downtime.")
            return {
                "status": "Service unavailable",
                "connected": False,
                "provider": "Groq",
                "model": settings.GROQ_MODEL,
                "detail": "Groq API service is currently unreachable or encountering an outage.",
                "timestamp": timestamp,
            }
        except groq.BadRequestError as err:
            err_msg = str(err).lower()
            if "model" in err_msg:
                status_label = "Model unavailable"
                detail_text = f"Configured model '{settings.GROQ_MODEL}' is invalid."
            else:
                status_label = "Unexpected error"
                detail_text = "Groq request was rejected as invalid."
            logger.warning("Groq bad request error: %s", status_label)
            return {
                "status": status_label,
                "connected": False,
                "provider": "Groq",
                "model": settings.GROQ_MODEL,
                "detail": detail_text,
                "timestamp": timestamp,
            }
        except Exception as err:
            logger.error("Unexpected error during Groq connection test: %s", err.__class__.__name__)
            return {
                "status": "Unexpected error",
                "connected": False,
                "provider": "Groq",
                "model": settings.GROQ_MODEL,
                "detail": f"Unexpected error during Groq connection test: {err.__class__.__name__}",
                "timestamp": timestamp,
            }


# Singleton service instance
ai_service = AIService()

