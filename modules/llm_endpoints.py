"""Endpoint adapter registry for Ollama/OpenAI-compatible LLM backends."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, List, Optional, Sequence, TYPE_CHECKING

from modules import config_manager as cfg

if TYPE_CHECKING:  # pragma: no cover - used for typing only
    from .llm_client import ClientSettings


class LLMSource(str, Enum):
    """Supported logical sources for LLM inference."""

    LOCAL = "local"
    CLOUD = "cloud"
    LMSTUDIO = "lmstudio"

    @classmethod
    def from_value(cls, value: Optional[str]) -> "LLMSource":
        if isinstance(value, str):
            candidate = value.strip().lower()
            if candidate.startswith("lmstudio"):
                return cls.LMSTUDIO
            for member in cls:
                if member.value == candidate:
                    return member
        return cls.LOCAL


@dataclass(frozen=True)
class ResolvedEndpoint:
    """Concrete endpoint details prepared for request dispatch."""

    source: LLMSource
    url: str
    headers: Dict[str, str]
    supports_stream: bool = True


class LLMEndpointAdapter:
    """Adapter contract for translating logical sources into HTTP endpoints."""

    source: LLMSource

    def resolve_url(self, settings: "ClientSettings") -> str:
        raise NotImplementedError

    def build_headers(self, settings: "ClientSettings") -> Dict[str, str]:
        return {}

    def supports_stream(self, settings: "ClientSettings") -> bool:  # pragma: no cover - default
        return True

    def is_available(self, settings: "ClientSettings") -> bool:
        return True


class LocalOllamaAdapter(LLMEndpointAdapter):
    """Adapter that targets a local Ollama runtime."""

    source = LLMSource.LOCAL

    def resolve_url(self, settings: "ClientSettings") -> str:
        if settings.llm_source == self.source.value and settings.api_url:
            return settings.api_url
        if settings.local_api_url:
            return settings.local_api_url
        return cfg.get_local_ollama_url()

    def build_headers(self, settings: "ClientSettings") -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if settings.api_key:
            headers["Authorization"] = f"Bearer {settings.api_key}"
        return headers


class CloudOllamaAdapter(LLMEndpointAdapter):
    """Adapter that targets the hosted Ollama Cloud service."""

    source = LLMSource.CLOUD

    def resolve_url(self, settings: "ClientSettings") -> str:
        if settings.llm_source == self.source.value and settings.api_url:
            return settings.api_url
        if settings.cloud_api_url:
            return settings.cloud_api_url
        return cfg.get_cloud_ollama_url()

    def build_headers(self, settings: "ClientSettings") -> Dict[str, str]:
        headers: Dict[str, str] = {}
        api_key = settings.cloud_api_key or settings.api_key
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def is_available(self, settings: "ClientSettings") -> bool:
        return bool(settings.cloud_api_key or settings.api_key)


class LMStudioAdapter(LLMEndpointAdapter):
    """Adapter that targets a local LM Studio endpoint."""

    source = LLMSource.LMSTUDIO

    def resolve_url(self, settings: "ClientSettings") -> str:
        if settings.llm_source == self.source.value and settings.api_url:
            return settings.api_url
        if settings.lmstudio_api_url:
            return settings.lmstudio_api_url
        return cfg.get_lmstudio_url()

    def build_headers(self, settings: "ClientSettings") -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if settings.api_key:
            headers["Authorization"] = f"Bearer {settings.api_key}"
        return headers


_ADAPTERS: Dict[LLMSource, LLMEndpointAdapter] = {
    LLMSource.LOCAL: LocalOllamaAdapter(),
    LLMSource.CLOUD: CloudOllamaAdapter(),
    LLMSource.LMSTUDIO: LMStudioAdapter(),
}


def _iter_sources(primary: LLMSource, fallbacks: Sequence[str], allow_fallback: bool) -> Iterable[LLMSource]:
    seen: List[LLMSource] = []

    if primary not in seen:
        seen.append(primary)
        yield primary

    if not allow_fallback:
        return

    fallback_candidates = [LLMSource.from_value(candidate) for candidate in fallbacks]
    if not fallback_candidates:
        fallback_candidates = [LLMSource.CLOUD if primary == LLMSource.LOCAL else LLMSource.LOCAL]

    for candidate in fallback_candidates:
        if candidate not in seen:
            seen.append(candidate)
            yield candidate


def resolve_endpoints(settings: "ClientSettings") -> List[ResolvedEndpoint]:
    """Return a list of endpoint attempts for ``settings`` in priority order."""

    primary = LLMSource.from_value(settings.llm_source)
    resolved: List[ResolvedEndpoint] = []

    for source in _iter_sources(primary, settings.fallback_sources, settings.allow_fallback):
        adapter = _ADAPTERS.get(source)
        if adapter is None:
            continue
        if not adapter.is_available(settings):
            continue
        url = adapter.resolve_url(settings)
        headers = adapter.build_headers(settings)
        resolved.append(
            ResolvedEndpoint(
                source=source,
                url=url,
                headers=headers,
                supports_stream=adapter.supports_stream(settings),
            )
        )
    return resolved


__all__ = [
    "LLMSource",
    "ResolvedEndpoint",
    "resolve_endpoints",
]
