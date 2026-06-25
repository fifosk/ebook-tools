"""Provider registry for lawful source discovery and acquisition."""

from .acquire import (
    AcquisitionArtifact,
    acquire_acquisition_candidate,
)
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
    "AcquisitionArtifact",
    "AcquisitionCandidate",
    "AcquisitionDiscoveryResult",
    "AcquisitionProvider",
    "AcquisitionProviderRegistry",
    "AcquisitionSubtitleHint",
    "acquire_acquisition_candidate",
    "discover_acquisition_candidates",
    "list_acquisition_providers",
]
