"""Client acquisition helpers for translation workflows."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional, Sequence, Tuple

from modules.llm_client import ClientSettings, LLMClient, create_client


_DEFAULT_CLIENT_SETTINGS = ClientSettings()


def configure_default_client(
    *,
    model: Optional[str] = None,
    api_url: Optional[str] = None,
    debug: Optional[bool] = None,
    api_key: Optional[str] = None,
    llm_source: Optional[str] = None,
    local_api_url: Optional[str] = None,
    cloud_api_url: Optional[str] = None,
    lmstudio_api_url: Optional[str] = None,
    fallback_sources: Optional[Sequence[str]] = None,
    allow_fallback: Optional[bool] = None,
    cloud_api_key: Optional[str] = None,
) -> None:
    """Update the implicit client configuration used when no client is supplied."""

    global _DEFAULT_CLIENT_SETTINGS
    updates = {}
    if model is not None:
        updates["model"] = model
    if api_url is not None:
        updates["api_url"] = api_url
    if debug is not None:
        updates["debug"] = debug
    if api_key is not None:
        updates["api_key"] = api_key
    if llm_source is not None:
        updates["llm_source"] = llm_source
    if local_api_url is not None:
        updates["local_api_url"] = local_api_url
    if cloud_api_url is not None:
        updates["cloud_api_url"] = cloud_api_url
    if lmstudio_api_url is not None:
        updates["lmstudio_api_url"] = lmstudio_api_url
    if fallback_sources is not None:
        updates["fallback_sources"] = tuple(fallback_sources)
    if allow_fallback is not None:
        updates["allow_fallback"] = bool(allow_fallback)
    if cloud_api_key is not None:
        updates["cloud_api_key"] = cloud_api_key
    if updates:
        _DEFAULT_CLIENT_SETTINGS = _DEFAULT_CLIENT_SETTINGS.with_updates(**updates)


def acquire_client(client: Optional[LLMClient]) -> Tuple[LLMClient, bool]:
    """Return an ``LLMClient`` and flag indicating whether the caller owns it."""

    if client is not None:
        return client, False
    created = create_client(
        model=_DEFAULT_CLIENT_SETTINGS.model,
        api_url=_DEFAULT_CLIENT_SETTINGS.api_url,
        debug=_DEFAULT_CLIENT_SETTINGS.debug,
        api_key=_DEFAULT_CLIENT_SETTINGS.api_key,
        llm_source=_DEFAULT_CLIENT_SETTINGS.llm_source,
        local_api_url=_DEFAULT_CLIENT_SETTINGS.local_api_url,
        cloud_api_url=_DEFAULT_CLIENT_SETTINGS.cloud_api_url,
        lmstudio_api_url=_DEFAULT_CLIENT_SETTINGS.lmstudio_api_url,
        fallback_sources=_DEFAULT_CLIENT_SETTINGS.fallback_sources,
        allow_fallback=_DEFAULT_CLIENT_SETTINGS.allow_fallback,
        cloud_api_key=_DEFAULT_CLIENT_SETTINGS.cloud_api_key,
    )
    return created, True


def release_client(client: LLMClient, owns_client: bool) -> None:
    """Release ``client`` if it was created by :func:`acquire_client`."""

    if owns_client:
        client.close()


@contextmanager
def client_scope(client: Optional[LLMClient]) -> Iterator[LLMClient]:
    """Context manager that yields a managed ``LLMClient`` instance."""

    resolved, owns_client = acquire_client(client)
    try:
        yield resolved
    finally:
        release_client(resolved, owns_client)
