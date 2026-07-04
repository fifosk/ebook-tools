"""Public acquisition provider registry contract validation."""

from __future__ import annotations

from typing import Mapping, Protocol

from .discovery_values import (
    ACQUISITION_CAPABILITIES,
    ACQUISITION_MEDIA_KINDS,
    ACQUISITION_PROVIDER_STATUSES,
    ACQUISITION_RIGHTS,
    unsupported_contract_values,
)


class AcquisitionProviderSnapshot(Protocol):
    id: str
    media_kinds: tuple[str, ...]
    capabilities: tuple[str, ...]
    status: str
    rights: tuple[str, ...]
    discovery_media_kinds: tuple[str, ...]
    default_eligible_media_kinds: tuple[str, ...]


class AcquisitionProviderRegistrySnapshot(Protocol):
    providers: tuple[AcquisitionProviderSnapshot, ...]
    default_provider_ids: Mapping[str, tuple[str, ...]]


def validate_provider_registry_contract(
    registry: AcquisitionProviderRegistrySnapshot,
) -> None:
    """Fail fast when backend provider metadata drifts from public API enums."""

    providers_by_id = {provider.id: provider for provider in registry.providers}
    for provider in registry.providers:
        _ensure_provider_values(
            provider,
            field="media_kinds",
            values=provider.media_kinds,
            allowed_values=ACQUISITION_MEDIA_KINDS,
        )
        _ensure_provider_values(
            provider,
            field="capabilities",
            values=provider.capabilities,
            allowed_values=ACQUISITION_CAPABILITIES,
        )
        _ensure_provider_values(
            provider,
            field="rights",
            values=provider.rights,
            allowed_values=ACQUISITION_RIGHTS,
        )
        _ensure_provider_values(
            provider,
            field="discovery_media_kinds",
            values=provider.discovery_media_kinds,
            allowed_values=ACQUISITION_MEDIA_KINDS,
        )
        _ensure_provider_values(
            provider,
            field="default_eligible_media_kinds",
            values=provider.default_eligible_media_kinds,
            allowed_values=ACQUISITION_MEDIA_KINDS,
        )
        non_discoverable_defaults = tuple(
            media_kind
            for media_kind in provider.default_eligible_media_kinds
            if media_kind not in provider.discovery_media_kinds
        )
        if non_discoverable_defaults:
            raise ValueError(
                "Acquisition provider default_eligible_media_kinds must be "
                "discoverable for provider "
                f"{provider.id!r}: {', '.join(non_discoverable_defaults)}."
            )
        if provider.status not in ACQUISITION_PROVIDER_STATUSES:
            raise ValueError(
                "Unsupported acquisition provider status "
                f"{provider.status!r} for provider {provider.id!r}."
            )

    for media_kind, default_provider_ids in registry.default_provider_ids.items():
        if media_kind not in ACQUISITION_MEDIA_KINDS:
            raise ValueError(
                f"Unsupported acquisition default-provider media kind {media_kind!r}."
            )
        unknown_provider_ids = tuple(
            provider_id
            for provider_id in default_provider_ids
            if provider_id not in providers_by_id
        )
        if unknown_provider_ids:
            raise ValueError(
                "Unknown acquisition default provider ids for "
                f"{media_kind!r}: {', '.join(unknown_provider_ids)}."
            )
        ineligible_provider_ids = tuple(
            provider_id
            for provider_id in default_provider_ids
            if media_kind not in providers_by_id[provider_id].default_eligible_media_kinds
        )
        if ineligible_provider_ids:
            raise ValueError(
                "Ineligible acquisition default provider ids for "
                f"{media_kind!r}: {', '.join(ineligible_provider_ids)}."
            )


def _ensure_provider_values(
    provider: AcquisitionProviderSnapshot,
    *,
    field: str,
    values: tuple[str, ...],
    allowed_values: tuple[str, ...],
) -> None:
    unsupported = unsupported_contract_values(values, allowed_values=allowed_values)
    if unsupported:
        raise ValueError(
            f"Unsupported acquisition provider {field} values for "
            f"{provider.id!r}: {', '.join(unsupported)}."
        )
