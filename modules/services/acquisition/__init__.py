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
    resolve_download_station_candidate_source_uri,
    resolve_download_station_config,
)
from .provider_registry import (
    DISCOVERY_PROVIDER_MEDIA_KINDS,
    AcquisitionProvider,
    AcquisitionProviderRegistry,
    default_discovery_provider_ids,
    discovery_media_kinds_for,
    is_indexer_search_configured,
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
    "DISCOVERY_PROVIDER_MEDIA_KINDS",
    "DownloadStationConfig",
    "DownloadStationError",
    "acquire_acquisition_candidate",
    "default_discovery_provider_ids",
    "discovery_media_kinds_for",
    "discover_acquisition_candidates",
    "enqueue_download_station_task",
    "is_indexer_search_configured",
    "list_acquisition_providers",
    "poll_download_station_task",
    "prepare_acquisition_artifact",
    "resolve_download_station_candidate_source_uri",
    "resolve_download_station_config",
]
