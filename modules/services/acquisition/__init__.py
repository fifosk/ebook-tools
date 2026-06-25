"""Provider registry for lawful source discovery and acquisition."""

from .provider_registry import (
    AcquisitionProvider,
    AcquisitionProviderRegistry,
    list_acquisition_providers,
)

__all__ = [
    "AcquisitionProvider",
    "AcquisitionProviderRegistry",
    "list_acquisition_providers",
]
