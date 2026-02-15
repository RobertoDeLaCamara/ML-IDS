"""API Key authentication middleware for ML-IDS.

Provides header-based API key authentication for HTTP endpoints
and query-parameter authentication for WebSocket connections.
"""

import logging
import os
from typing import List, Optional

from fastapi import HTTPException, WebSocket
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

PUBLIC_PATHS = {"/health", "/docs", "/redoc", "/openapi.json", "/openapi.yaml", "/"}


def get_api_keys() -> List[str]:
    """Parse API keys from the ML_IDS_API_KEYS environment variable (comma-separated)."""
    raw = os.getenv("ML_IDS_API_KEYS", "")
    return [k.strip() for k in raw.split(",") if k.strip()]


def is_auth_enabled() -> bool:
    """Check whether authentication is enabled via ML_IDS_AUTH_ENABLED (default true)."""
    return os.getenv("ML_IDS_AUTH_ENABLED", "true").lower() in ("true", "1", "yes")


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces X-API-Key header authentication."""

    async def dispatch(self, request: Request, call_next):
        if not is_auth_enabled():
            return await call_next(request)

        path = request.url.path

        # Skip public paths
        if path in PUBLIC_PATHS:
            return await call_next(request)

        # Skip dashboard static files
        if path.startswith("/dashboard"):
            return await call_next(request)

        # Skip metrics endpoint
        if path == "/metrics":
            return await call_next(request)

        keys = get_api_keys()
        if not keys:
            logger.warning("No API keys configured — allowing request (dev mode)")
            return await call_next(request)

        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing X-API-Key header"},
            )

        if api_key not in keys:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid API key"},
            )

        return await call_next(request)


async def verify_ws_api_key(websocket: WebSocket) -> bool:
    """Verify API key for WebSocket connections via query parameter.

    Returns True if authorized, False otherwise.
    """
    if not is_auth_enabled():
        return True

    keys = get_api_keys()
    if not keys:
        logger.warning("No API keys configured — allowing WebSocket (dev mode)")
        return True

    api_key = websocket.query_params.get("api_key")
    if not api_key or api_key not in keys:
        return False

    return True
