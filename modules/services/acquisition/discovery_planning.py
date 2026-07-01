"""Provider fan-out planning for acquisition discovery."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, Sequence, TypeVar


LOCAL_FILE_DISCOVERY_PROVIDERS = frozenset({"local_epub", "manual_downloads", "nas_video"})


class DiscoveryCandidateForPlanning(Protocol):
    """Candidate fields required to order default-source discovery results."""

    provider: str
    title: str
    modified_at: datetime | None


CandidateT = TypeVar("CandidateT", bound=DiscoveryCandidateForPlanning)


def order_default_discovery_candidates(
    candidates: Sequence[CandidateT],
    providers: Sequence[str],
) -> list[CandidateT]:
    """Order default-source candidates after every advertised provider responds."""

    provider_rank = {provider: index for index, provider in enumerate(providers)}

    def sort_key(candidate: CandidateT) -> tuple[int, float, int, str]:
        local_priority = 0 if candidate.provider in LOCAL_FILE_DISCOVERY_PROVIDERS else 1
        modified_priority = (
            -candidate.modified_at.timestamp() if candidate.modified_at else 0.0
        )
        return (
            local_priority,
            modified_priority,
            provider_rank.get(candidate.provider, len(provider_rank)),
            candidate.title.casefold(),
        )

    return sorted(candidates, key=sort_key)


def provider_query_limit(
    provider_id: str,
    *,
    candidates: Sequence[object],
    effective_limit: int,
    is_default_provider_fanout: bool,
) -> int:
    """Return how many candidates a provider should fetch for this discovery pass."""

    if not is_default_provider_fanout:
        return max(0, effective_limit - len(candidates))
    if provider_id in LOCAL_FILE_DISCOVERY_PROVIDERS:
        return effective_limit
    remaining_visible_slots = effective_limit - len(candidates)
    return max(1, remaining_visible_slots)
