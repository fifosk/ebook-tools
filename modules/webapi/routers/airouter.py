"""Transparent proxy to Ollama Cloud API.

Forwards OpenAI-compatible requests (model listing, chat completions) to the
upstream Ollama Cloud endpoint, injecting the server-side API key so that
consumers never need to hold the cloud token themselves.

The API key is resolved in the following order:
1. ``OLLAMA_CLOUD_API_KEY`` environment variable (highest priority)
2. ``api_keys.ollama`` from the active database configuration snapshot
3. ``ollama_api_key`` from the loaded application settings

Endpoints
---------
GET  /api/airouter/v1/models                → upstream GET  /v1/models
POST /api/airouter/v1/chat/completions       → upstream POST /v1/chat/completions

Both streaming (``stream: true``) and non-streaming requests are supported.
"""

from __future__ import annotations

import json as _json
import logging
import os
from typing import AsyncIterator

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from modules.webapi.dependencies import RequestUserContext, get_request_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/airouter", tags=["airouter"])

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_UPSTREAM_BASE = os.environ.get(
    "AIROUTER_UPSTREAM_URL", "https://ollama.com"
).rstrip("/")

_API_KEY: str = os.environ.get("OLLAMA_CLOUD_API_KEY", "")

_REQUEST_TIMEOUT = float(os.environ.get("AIROUTER_TIMEOUT", "120"))


def _resolve_api_key() -> str:
    """Return the Ollama Cloud API key, falling back to config system if env var is empty."""
    global _API_KEY
    if _API_KEY:
        return _API_KEY

    # Fallback 1: try the application settings (reads from DB snapshot + config files)
    try:
        from modules.config_manager.loader import get_settings

        settings = get_settings()
        if settings.ollama_api_key:
            _API_KEY = settings.ollama_api_key.get_secret_value()
            logger.info("airouter: loaded API key from application settings")
            return _API_KEY
    except Exception as exc:
        logger.debug("airouter: could not load API key from settings: %s", exc)

    return _API_KEY

# Headers we never forward to upstream (hop-by-hop / overridden).
_STRIP_REQUEST_HEADERS = frozenset(
    {
        "host",
        "authorization",
        "content-length",
        "transfer-encoding",
        "connection",
        "keep-alive",
        "te",
        "trailers",
        "upgrade",
    }
)

# Headers we never relay back to the caller.
_STRIP_RESPONSE_HEADERS = frozenset(
    {
        "content-encoding",
        "content-length",
        "transfer-encoding",
        "connection",
        "keep-alive",
    }
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_user(request_user: RequestUserContext) -> str:
    """Raise 401 if there is no authenticated user."""
    if not request_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing session token",
        )
    return request_user.user_id


def _require_api_key() -> str:
    """Raise 503 if no upstream Ollama Cloud API key is configured.

    Returns the resolved key on success.
    """
    key = _resolve_api_key()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI Router is not configured: set OLLAMA_CLOUD_API_KEY or api_keys.ollama in config",
        )
    return key


def _upstream_headers(incoming: Request, api_key: str = "") -> dict[str, str]:
    """Build the header dict forwarded to the upstream Ollama Cloud API.

    Parameters
    ----------
    incoming:
        The original FastAPI request (its headers are selectively forwarded).
    api_key:
        The resolved API key to inject.  When empty the global key is resolved
        automatically.
    """
    key = api_key or _resolve_api_key()
    headers: dict[str, str] = {}
    for k, value in incoming.headers.items():
        if k.lower() not in _STRIP_REQUEST_HEADERS:
            headers[k] = value
    # Always inject server-side bearer token (replacing the consumer's
    # ebook-tools session token with the Ollama Cloud API key).
    if key:
        headers["Authorization"] = f"Bearer {key}"
    return headers


def _filtered_response_headers(upstream_headers: httpx.Headers) -> dict[str, str]:
    """Return upstream response headers safe for relaying back to the caller."""
    return {
        k: v
        for k, v in upstream_headers.items()
        if k.lower() not in _STRIP_RESPONSE_HEADERS
    }


def _get_client() -> httpx.AsyncClient:
    """Return a fresh async HTTP client (short-lived, per-request)."""
    return httpx.AsyncClient(
        timeout=httpx.Timeout(_REQUEST_TIMEOUT, connect=10.0),
        follow_redirects=True,
    )


# ---------------------------------------------------------------------------
# GET /v1/models — model discovery
# ---------------------------------------------------------------------------


@router.get("/v1/models")
async def list_models(
    request: Request,
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Proxy model listing from the upstream Ollama Cloud API."""
    _require_user(request_user)
    logger.info("airouter: %s listing models", request_user.user_id)

    async with _get_client() as client:
        try:
            resp = await client.get(
                f"{_UPSTREAM_BASE}/v1/models",
                headers=_upstream_headers(request),
            )
        except httpx.RequestError as exc:
            logger.error("airouter: upstream request failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Upstream request failed: {exc}",
            ) from exc

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()


# ---------------------------------------------------------------------------
# POST /v1/chat/completions — chat (streaming + non-streaming)
# ---------------------------------------------------------------------------


async def _stream_upstream(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    body: bytes,
) -> AsyncIterator[bytes]:
    """Yield raw bytes from the upstream SSE stream."""
    async with client.stream(
        "POST",
        url,
        content=body,
        headers=headers,
    ) as resp:
        if resp.status_code != 200:
            error_body = await resp.aread()
            raise HTTPException(status_code=resp.status_code, detail=error_body.decode("utf-8", errors="replace"))
        async for chunk in resp.aiter_bytes():
            yield chunk


@router.post("/v1/chat/completions")
async def chat_completions(
    request: Request,
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Proxy chat completion requests to the upstream Ollama Cloud API.

    Supports both ``stream: true`` (SSE) and ``stream: false`` (JSON).
    """
    _require_user(request_user)
    api_key = _require_api_key()

    body = await request.body()
    headers = _upstream_headers(request, api_key=api_key)
    upstream_url = f"{_UPSTREAM_BASE}/v1/chat/completions"

    logger.info("airouter: %s → POST /v1/chat/completions", request_user.user_id)

    try:
        payload = _json.loads(body)
        is_stream = payload.get("stream", False)
    except (ValueError, TypeError):
        is_stream = False

    if is_stream:
        # Streaming: keep the httpx client alive for the duration of the SSE
        # response and relay chunks verbatim.
        client = _get_client()

        async def _streaming_body() -> AsyncIterator[bytes]:
            try:
                async for chunk in _stream_upstream(client, upstream_url, headers, body):
                    yield chunk
            finally:
                await client.aclose()

        return StreamingResponse(
            _streaming_body(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # Non-streaming: simple request → response.
    async with _get_client() as client:
        try:
            resp = await client.post(upstream_url, content=body, headers=headers)
        except httpx.RequestError as exc:
            logger.error("airouter: upstream request failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Upstream request failed: {exc}",
            ) from exc

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()


__all__ = ["router"]
