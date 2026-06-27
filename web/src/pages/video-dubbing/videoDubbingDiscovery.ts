import type {
  AcquisitionCandidate,
  AcquisitionDiscoveryResponse,
  AcquisitionProvider,
  AcquisitionProviderListResponse
} from '../../api/dtos';

export type VideoDiscoveryProvider = string;

export type VideoDiscoveryProviderOption = {
  id: VideoDiscoveryProvider;
  label: string;
  available: boolean;
};

export type VideoDiscoveryProviderState = {
  youtubeSearchProvider: AcquisitionProvider | null;
  manualDownloadsProvider: AcquisitionProvider | null;
  downloadStationProvider: AcquisitionProvider | null;
  indexerSearchProvider: AcquisitionProvider | null;
  selectedVideoDiscoveryProvider: AcquisitionProvider | null;
  videoDiscoveryProviderOptions: VideoDiscoveryProviderOption[];
  isYoutubeSearchAvailable: boolean;
  isDownloadStationAvailable: boolean;
  isIndexerSearchAvailable: boolean;
  isSelectedVideoDiscoveryProviderAvailable: boolean;
  youtubeSearchUnavailableMessage: string | null;
  manualDownloadsUnavailableMessage: string | null;
  downloadStationUnavailableMessage: string | null;
  indexerSearchUnavailableMessage: string | null;
  selectedVideoDiscoveryProviderUnavailableMessage: string | null;
};

export const DEFAULT_VIDEO_DISCOVERY_PROVIDER: VideoDiscoveryProvider = 'backend_defaults';

const VIDEO_DISCOVERY_PROVIDERS: Array<Pick<VideoDiscoveryProviderOption, 'id' | 'label'>> = [
  { id: DEFAULT_VIDEO_DISCOVERY_PROVIDER, label: 'Default sources' },
  { id: 'nas_video', label: 'NAS videos' },
  { id: 'manual_downloads', label: 'Manual downloads' },
  { id: 'youtube_url', label: 'YouTube URL' },
  { id: 'youtube_search', label: 'YouTube search' },
  { id: 'newznab_torznab', label: 'Indexers' }
];

const VIDEO_DISCOVERY_PROVIDER_ORDER = VIDEO_DISCOVERY_PROVIDERS.map((entry) => entry.id);
const VIDEO_DISCOVERY_PROVIDER_LABELS = new Map(
  VIDEO_DISCOVERY_PROVIDERS.map((entry) => [entry.id, entry.label])
);
const VIDEO_DISCOVERY_CAPABILITIES = new Set(['search', 'import_local']);
const YOUTUBE_METADATA_VIDEO_DISCOVERY_PROVIDERS = new Set(['youtube_url', 'youtube_search']);

export function isYoutubeMetadataVideoDiscoveryProvider(providerId: string): boolean {
  return YOUTUBE_METADATA_VIDEO_DISCOVERY_PROVIDERS.has(providerId);
}

export function findVideoAcquisitionProvider(
  providers: AcquisitionProvider[],
  providerId: string
): AcquisitionProvider | null {
  return providers.find((provider) => provider.id === providerId) ?? null;
}

export function buildVideoDiscoveryProviderOptions(
  providers: AcquisitionProvider[],
  defaultProviderIds?: AcquisitionProviderListResponse['default_provider_ids']
): VideoDiscoveryProviderOption[] {
  if (providers.length === 0) {
    return VIDEO_DISCOVERY_PROVIDERS.map((entry) => ({
      ...entry,
      available: entry.id === DEFAULT_VIDEO_DISCOVERY_PROVIDER ? false : true
    })).filter((entry) => entry.id !== DEFAULT_VIDEO_DISCOVERY_PROVIDER);
  }
  const providerOptions = providers
    .filter(isVideoDiscoveryProvider)
    .sort((left, right) => {
      const rankDifference = videoDiscoveryProviderRank(left.id) - videoDiscoveryProviderRank(right.id);
      if (rankDifference !== 0) {
        return rankDifference;
      }
      return videoDiscoveryProviderLabel(left).localeCompare(videoDiscoveryProviderLabel(right));
    })
    .map((provider) => ({
      id: provider.id,
      label: videoDiscoveryProviderLabel(provider),
      available: provider.available
    }));
  const defaultOption = buildDefaultVideoDiscoveryProviderOption(providerOptions, defaultProviderIds);
  return defaultOption ? [defaultOption, ...providerOptions] : providerOptions;
}

export function resolveDefaultVideoDiscoveryProvider({
  defaultProviderIds,
  options,
  fallback = 'nas_video'
}: {
  defaultProviderIds?: AcquisitionProviderListResponse['default_provider_ids'];
  options: VideoDiscoveryProviderOption[];
  fallback?: VideoDiscoveryProvider;
}): VideoDiscoveryProvider {
  const optionIds = new Set(options.map((option) => option.id));
  if (optionIds.has(DEFAULT_VIDEO_DISCOVERY_PROVIDER)) {
    return DEFAULT_VIDEO_DISCOVERY_PROVIDER;
  }
  const availableOptions = options.filter((option) => option.available);
  const availableOptionIds = new Set(availableOptions.map((option) => option.id));
  const preferredOptionIds = availableOptionIds.size > 0 ? availableOptionIds : optionIds;
  const backendDefaults = defaultProviderIds?.video ?? [];
  const selectedDefault = backendDefaults.find((providerId) => preferredOptionIds.has(providerId));
  if (selectedDefault) {
    return selectedDefault;
  }
  if (preferredOptionIds.has(fallback)) {
    return fallback;
  }
  const firstPreferred = options.find((option) => preferredOptionIds.has(option.id))?.id;
  if (firstPreferred) {
    return firstPreferred;
  }
  return optionIds.has(fallback) ? fallback : (options[0]?.id ?? fallback);
}

export function resolveVideoDiscoveryProviderState({
  providers,
  selectedProvider,
  defaultProviderIds
}: {
  providers: AcquisitionProvider[];
  selectedProvider: VideoDiscoveryProvider;
  defaultProviderIds?: AcquisitionProviderListResponse['default_provider_ids'];
}): VideoDiscoveryProviderState {
  const youtubeSearchProvider = findVideoAcquisitionProvider(providers, 'youtube_search');
  const manualDownloadsProvider = findVideoAcquisitionProvider(providers, 'manual_downloads');
  const downloadStationProvider = findVideoAcquisitionProvider(providers, 'download_station');
  const indexerSearchProvider = findVideoAcquisitionProvider(providers, 'newznab_torznab');
  const selectedVideoDiscoveryProvider = findVideoAcquisitionProvider(providers, selectedProvider);
  const hasProviderInventory = providers.length > 0;
  const videoDiscoveryProviderOptions = buildVideoDiscoveryProviderOptions(providers, defaultProviderIds);
  const selectedVideoDiscoveryProviderOption = videoDiscoveryProviderOptions.find(
    (option) => option.id === selectedProvider
  );
  const selectedVideoDiscoveryProviderFallbackLabel =
    VIDEO_DISCOVERY_PROVIDER_LABELS.get(selectedProvider) ?? selectedProvider;
  const isYoutubeSearchAvailable = youtubeSearchProvider?.available ?? !hasProviderInventory;
  const isDownloadStationAvailable = downloadStationProvider?.available === true;
  const isIndexerSearchAvailable = indexerSearchProvider?.available === true;
  const isSelectedVideoDiscoveryProviderAvailable =
    selectedProvider === DEFAULT_VIDEO_DISCOVERY_PROVIDER
      ? selectedVideoDiscoveryProviderOption?.available ?? false
      : selectedProvider === 'newznab_torznab'
      ? isIndexerSearchAvailable
      : selectedVideoDiscoveryProvider?.available ?? !hasProviderInventory;
  const youtubeSearchUnavailableMessage =
    youtubeSearchProvider && !youtubeSearchProvider.available
      ? `${youtubeSearchProvider.label} is ${youtubeSearchProvider.status.replace('_', ' ')}. Configure the YouTube Data API key to search videos, or use NAS videos.`
      : null;
  const manualDownloadsUnavailableMessage =
    manualDownloadsProvider && !manualDownloadsProvider.available
      ? `${manualDownloadsProvider.label} is ${manualDownloadsProvider.status.replace('_', ' ')}. Configure the backend source root or choose another discovery source.`
      : null;
  const downloadStationUnavailableMessage =
    downloadStationProvider && !downloadStationProvider.available
      ? `${downloadStationProvider.label} is ${downloadStationProvider.status.replace('_', ' ')}. Configure backend Download Station credentials, or use manual downloads.`
      : null;
  const indexerSearchUnavailableMessage =
    indexerSearchProvider && !indexerSearchProvider.available
      ? `${indexerSearchProvider.label} is ${indexerSearchProvider.status.replace('_', ' ')}. Configure backend Newznab/Torznab indexer settings, or use NAS videos.`
      : null;
  const selectedVideoDiscoveryProviderUnavailableMessage =
    selectedProvider === DEFAULT_VIDEO_DISCOVERY_PROVIDER && !isSelectedVideoDiscoveryProviderAvailable
      ? 'No backend default video discovery providers are available. Choose a specific source.'
      : selectedProvider === 'newznab_torznab' && !isIndexerSearchAvailable
      ? indexerSearchUnavailableMessage ?? 'This backend does not advertise Newznab/Torznab indexer discovery yet.'
      : selectedProvider !== DEFAULT_VIDEO_DISCOVERY_PROVIDER && hasProviderInventory && !selectedVideoDiscoveryProvider
        ? `${selectedVideoDiscoveryProviderFallbackLabel} is unavailable on this backend. Choose another discovery source.`
      : selectedVideoDiscoveryProvider && !selectedVideoDiscoveryProvider.available
        ? selectedProvider === 'youtube_search'
          ? youtubeSearchUnavailableMessage
          : `${selectedVideoDiscoveryProvider.label} is ${selectedVideoDiscoveryProvider.status.replace('_', ' ')}. Configure the backend source root or choose another discovery source.`
        : null;

  return {
    youtubeSearchProvider,
    manualDownloadsProvider,
    downloadStationProvider,
    indexerSearchProvider,
    selectedVideoDiscoveryProvider,
    videoDiscoveryProviderOptions,
    isYoutubeSearchAvailable,
    isDownloadStationAvailable,
    isIndexerSearchAvailable,
    isSelectedVideoDiscoveryProviderAvailable,
    youtubeSearchUnavailableMessage,
    manualDownloadsUnavailableMessage,
    downloadStationUnavailableMessage,
    indexerSearchUnavailableMessage,
    selectedVideoDiscoveryProviderUnavailableMessage
  };
}

export function filterDiscoveredVideoCandidates(
  response: AcquisitionDiscoveryResponse | null,
  selectedProvider: VideoDiscoveryProvider
): AcquisitionCandidate[] {
  const queriedProviders = new Set(response?.providers_queried ?? []);
  return (response?.candidates ?? []).filter((candidate) => {
    const effectiveProvider =
      selectedProvider === DEFAULT_VIDEO_DISCOVERY_PROVIDER ? candidate.provider : selectedProvider;
    if (
      selectedProvider === DEFAULT_VIDEO_DISCOVERY_PROVIDER &&
      queriedProviders.size > 0 &&
      !queriedProviders.has(candidate.provider)
    ) {
      return false;
    }
    if (candidate.provider !== effectiveProvider) {
      return false;
    }
    if (isYoutubeMetadataVideoDiscoveryProvider(effectiveProvider)) {
      const metadataYoutubeUrl = candidate.metadata['youtube_url'];
      return Boolean(
        candidate.source_url?.trim() ||
        (typeof metadataYoutubeUrl === 'string' && metadataYoutubeUrl.trim())
      );
    }
    if (effectiveProvider === 'newznab_torznab') {
      return candidate.requires_confirmation;
    }
    return Boolean(candidate.local_path);
  });
}

function isVideoDiscoveryProvider(provider: AcquisitionProvider) {
  if (Array.isArray(provider.discovery_media_kinds)) {
    return provider.discovery_media_kinds.includes('video');
  }
  return (
    provider.media_kinds.includes('video') &&
    provider.capabilities.some((capability) => VIDEO_DISCOVERY_CAPABILITIES.has(capability))
  );
}

function videoDiscoveryProviderRank(id: string) {
  const index = VIDEO_DISCOVERY_PROVIDER_ORDER.indexOf(id);
  return index === -1 ? Number.MAX_SAFE_INTEGER : index;
}

function videoDiscoveryProviderLabel(provider: AcquisitionProvider) {
  return VIDEO_DISCOVERY_PROVIDER_LABELS.get(provider.id) ?? provider.label;
}

function buildDefaultVideoDiscoveryProviderOption(
  options: VideoDiscoveryProviderOption[],
  defaultProviderIds?: AcquisitionProviderListResponse['default_provider_ids']
): VideoDiscoveryProviderOption | null {
  const backendDefaults = defaultProviderIds?.video ?? [];
  const optionIds = new Set(options.map((option) => option.id));
  const availableOptionIds = new Set(options.filter((option) => option.available).map((option) => option.id));
  const availableDefaults = backendDefaults.filter((providerId) => availableOptionIds.has(providerId));
  if (availableDefaults.length < 2) {
    return null;
  }
  return {
    id: DEFAULT_VIDEO_DISCOVERY_PROVIDER,
    label: 'Default sources',
    available: backendDefaults.some((providerId) => optionIds.has(providerId))
  };
}
