import type {
  AcquisitionCandidate,
  AcquisitionDiscoveryResponse,
  AcquisitionProvider,
  AcquisitionProviderListResponse
} from '../../api/dtos';

export type BookNarrationDiscoveryProvider = string;

export type BookNarrationDiscoveryProviderOption = {
  id: BookNarrationDiscoveryProvider;
  label: string;
  unavailableMessage: string | null;
};

export const DEFAULT_BOOK_DISCOVERY_PROVIDER: BookNarrationDiscoveryProvider = 'backend_defaults';

type FallbackBookDiscoveryProvider = Pick<BookNarrationDiscoveryProviderOption, 'id' | 'label'> & {
  fallbackUnavailableMessage?: string;
};

const ZLIBRARY_ATTENDED_IMPORT_MESSAGE =
  'Direct Z-Library automation is intentionally disabled. Use attended browser downloads, then import the EPUB through Manual downloads or Choose EPUB.';

const EBOOK_DISCOVERY_PROVIDERS: FallbackBookDiscoveryProvider[] = [
  { id: 'local_epub', label: 'Local EPUBs' },
  { id: 'manual_downloads', label: 'Manual downloads' },
  { id: 'gutenberg', label: 'Gutenberg' },
  { id: 'internet_archive', label: 'Internet Archive' },
  { id: 'openlibrary', label: 'Open Library' },
  {
    id: 'zlibrary_attended',
    label: 'Z-Library import',
    fallbackUnavailableMessage: ZLIBRARY_ATTENDED_IMPORT_MESSAGE
  }
];

const EBOOK_DISCOVERY_PROVIDER_ORDER = EBOOK_DISCOVERY_PROVIDERS.map((entry) => entry.id);
const EBOOK_DISCOVERY_PROVIDER_LABELS = new Map(
  EBOOK_DISCOVERY_PROVIDERS.map((entry) => [entry.id, entry.label])
);
const EBOOK_DISCOVERY_CAPABILITIES = new Set(['search', 'metadata', 'acquire', 'import_local']);

export function buildBookNarrationDiscoveryProviderOptions(
  providers: AcquisitionProvider[],
  defaultProviderIds?: AcquisitionProviderListResponse['default_provider_ids']
): BookNarrationDiscoveryProviderOption[] {
  if (providers.length === 0) {
    return EBOOK_DISCOVERY_PROVIDERS.map((entry) => ({
      id: entry.id,
      label: entry.label,
      unavailableMessage: bookDiscoveryProviderUnavailableMessage(entry.id, providers)
    }));
  }
  const providerOptions = providers
    .filter(isBookDiscoveryProvider)
    .sort((left, right) => {
      const rankDifference = discoveryProviderRank(left.id) - discoveryProviderRank(right.id);
      if (rankDifference !== 0) {
        return rankDifference;
      }
      return discoveryProviderLabel(left).localeCompare(discoveryProviderLabel(right));
    })
    .map((entry) => ({
      id: entry.id,
      label: discoveryProviderLabel(entry),
      unavailableMessage: bookDiscoveryProviderUnavailableMessage(entry.id, providers)
    }));
  const defaultOption = buildDefaultBookDiscoveryProviderOption(
    providerOptions,
    defaultProviderIds,
    providers
  );
  return defaultOption ? [defaultOption, ...providerOptions] : providerOptions;
}

export function bookDiscoveryProviderUnavailableMessage(
  providerId: BookNarrationDiscoveryProvider,
  providers: AcquisitionProvider[]
): string | null {
  if (providerId === DEFAULT_BOOK_DISCOVERY_PROVIDER) {
    return null;
  }
  const entry = providers.find((provider) => provider.id === providerId);
  if (!entry) {
    const fallback = EBOOK_DISCOVERY_PROVIDERS.find((option) => option.id === providerId);
    if (fallback?.fallbackUnavailableMessage) {
      return fallback.fallbackUnavailableMessage;
    }
    if (providers.length > 0) {
      const label = fallback?.label ?? providerId;
      return `${label} is unavailable on this backend. Choose another discovery source.`;
    }
    return null;
  }
  if (entry.available) {
    return null;
  }
  const status = entry.status.replace(/_/g, ' ');
  const policyNote = entry.policy_notes?.find((note) => note.trim());
  if (policyNote) {
    return `${entry.label} is ${status}. ${policyNote}`;
  }
  return `${entry.label} is ${status}. Configure ${providerSourceLabel(entry).toLowerCase()} or choose another discovery source.`;
}

export function resolveDefaultBookDiscoveryProvider({
  defaultProviderIds,
  providers,
  fallback
}: {
  defaultProviderIds?: AcquisitionProviderListResponse['default_provider_ids'];
  providers: AcquisitionProvider[];
  fallback: BookNarrationDiscoveryProvider;
}): BookNarrationDiscoveryProvider {
  if (providers.length === 0) {
    return fallback;
  }
  const discoverableProviders = providers.filter(isBookDiscoveryProvider);
  const providerOptions = buildBookNarrationDiscoveryProviderOptions(providers, defaultProviderIds);
  if (providerOptions.some((option) => option.id === DEFAULT_BOOK_DISCOVERY_PROVIDER)) {
    return DEFAULT_BOOK_DISCOVERY_PROVIDER;
  }
  const discoverableProviderIds = new Set(discoverableProviders.map((provider) => provider.id));
  const availableProviderIds = new Set(
    discoverableProviders.filter((provider) => provider.available).map((provider) => provider.id)
  );
  const preferredProviderIds = availableProviderIds.size > 0 ? availableProviderIds : discoverableProviderIds;
  const backendDefaults = defaultableBookProviderIds(defaultProviderIds?.book ?? [], providers);
  const selectedDefault = backendDefaults.find((providerId) =>
    preferredProviderIds.has(providerId)
  );
  if (selectedDefault) {
    return selectedDefault;
  }
  if (preferredProviderIds.has(fallback)) {
    return fallback;
  }
  const firstPreferred = discoverableProviders.find((provider) => preferredProviderIds.has(provider.id))?.id;
  if (firstPreferred) {
    return firstPreferred;
  }
  return discoverableProviderIds.has(fallback)
    ? fallback
    : (discoverableProviders[0]?.id ?? fallback);
}

export function isBookDiscoveryProvider(provider: AcquisitionProvider) {
  if (Array.isArray(provider.discovery_media_kinds)) {
    return provider.discovery_media_kinds.includes('book');
  }
  return (
    provider.media_kinds.includes('book') &&
    provider.capabilities.some((capability) => EBOOK_DISCOVERY_CAPABILITIES.has(capability))
  );
}

export function filterBookNarrationDiscoveryCandidates(
  response: AcquisitionDiscoveryResponse | null,
  selectedProvider: BookNarrationDiscoveryProvider,
  providers: AcquisitionProvider[] = []
): AcquisitionCandidate[] {
  const queriedProviders = new Set(response?.providers_queried ?? []);
  return (response?.candidates ?? []).filter((candidate) => {
    const effectiveProvider =
      selectedProvider === DEFAULT_BOOK_DISCOVERY_PROVIDER ? candidate.provider : selectedProvider;
    if (candidate.media_kind !== 'book' || candidate.provider !== effectiveProvider) {
      return false;
    }
    if (
      selectedProvider === DEFAULT_BOOK_DISCOVERY_PROVIDER &&
      !defaultableBookProviderIds([candidate.provider], providers).includes(candidate.provider)
    ) {
      return false;
    }
    if (
      selectedProvider === DEFAULT_BOOK_DISCOVERY_PROVIDER &&
      queriedProviders.size > 0 &&
      !queriedProviders.has(candidate.provider)
    ) {
      return false;
    }
    return Boolean(
      candidate.local_path?.trim()
        || candidate.capabilities.includes('acquire')
        || candidate.capabilities.includes('metadata')
    );
  });
}

function discoveryProviderRank(id: string) {
  const index = EBOOK_DISCOVERY_PROVIDER_ORDER.indexOf(id);
  return index === -1 ? Number.MAX_SAFE_INTEGER : index;
}

function discoveryProviderLabel(provider: AcquisitionProvider) {
  return EBOOK_DISCOVERY_PROVIDER_LABELS.get(provider.id) ?? provider.label;
}

function providerSourceLabel(provider: AcquisitionProvider) {
  const sourceLabel = provider.source_label?.trim();
  return sourceLabel && sourceLabel.length > 0 ? sourceLabel : 'the backend source root';
}

function buildDefaultBookDiscoveryProviderOption(
  options: BookNarrationDiscoveryProviderOption[],
  defaultProviderIds?: AcquisitionProviderListResponse['default_provider_ids'],
  providers: AcquisitionProvider[] = []
): BookNarrationDiscoveryProviderOption | null {
  const backendDefaults = defaultableBookProviderIds(defaultProviderIds?.book ?? [], providers);
  const optionIds = new Set(options.map((option) => option.id));
  const availableOptionIds = new Set(
    options
      .filter((option) => option.unavailableMessage === null)
      .map((option) => option.id)
  );
  const availableDefaults = backendDefaults.filter((providerId) => availableOptionIds.has(providerId));
  if (availableDefaults.length < 2) {
    return null;
  }
  if (!backendDefaults.some((providerId) => optionIds.has(providerId))) {
    return null;
  }
  return {
    id: DEFAULT_BOOK_DISCOVERY_PROVIDER,
    label: 'Default sources',
    unavailableMessage: null
  };
}

function defaultableBookProviderIds(
  providerIds: string[],
  providers: AcquisitionProvider[] = []
): string[] {
  const providersById = new Map(providers.map((provider) => [provider.id, provider]));
  const hasProviderInventory = providers.length > 0;
  return providerIds.filter((providerId) => {
    const provider = providersById.get(providerId);
    if (!provider) {
      return !hasProviderInventory;
    }
    return Array.isArray(provider.default_eligible_media_kinds)
      && provider.default_eligible_media_kinds.includes('book');
  });
}
