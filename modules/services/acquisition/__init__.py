"""Provider registry for lawful source discovery and acquisition."""

from .discovery import (
    AcquisitionCandidate,
    AcquisitionDiscoveryResult,
    AcquisitionSubtitleHint,
    discover_acquisition_candidates,
)
from .provider_registry import (
    AcquisitionProvider,
    AcquisitionProviderRegistry,
    list_acquisition_providers,
)

__all__ = [
    "AcquisitionCandidate",
    "AcquisitionDiscoveryResult",
    "AcquisitionProvider",
    "AcquisitionProviderRegistry",
    "AcquisitionSubtitleHint",
    "discover_acquisition_candidates",
    "list_acquisition_providers",
]
