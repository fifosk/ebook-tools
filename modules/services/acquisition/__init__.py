"""Provider registry for lawful source discovery and acquisition."""

from .acquire import (
    AcquisitionArtifact,
    AcquisitionPreparedArtifact,
    acquire_acquisition_candidate,
    prepare_acquisition_artifact,
)
from .discovery import (
    AcquisitionCandidate,
    AcquisitionDiscoveryResult,
    AcquisitionProviderDiscoveryError,
    AcquisitionSubtitleHint,
    discover_acquisition_candidates,
)
from .download_station import (
    AcquisitionJobStatus,
    DownloadStationConfig,
    DownloadStationError,
    enqueue_download_station_task,
    poll_download_station_task,
    resolve_download_station_config,
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
    "AcquisitionJobStatus",
    "AcquisitionPreparedArtifact",
    "AcquisitionProvider",
    "AcquisitionProviderDiscoveryError",
    "AcquisitionProviderRegistry",
    "AcquisitionSubtitleHint",
    "DownloadStationConfig",
    "DownloadStationError",
    "acquire_acquisition_candidate",
    "discover_acquisition_candidates",
    "enqueue_download_station_task",
    "list_acquisition_providers",
    "poll_download_station_task",
    "prepare_acquisition_artifact",
    "resolve_download_station_config",
]
