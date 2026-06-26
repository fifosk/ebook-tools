import type {
  AcquisitionProvider,
  AcquisitionProviderListResponse
} from '../../api/dtos';

export type BookNarrationDiscoveryProvider = string;

export type BookNarrationDiscoveryProviderOption = {
  id: BookNarrationDiscoveryProvider;
  label: string;
  unavailableMessage: string | null;
};

const EBOOK_DISCOVERY_PROVIDERS: Array<Pick<BookNarrationDiscoveryProviderOption, 'id' | 'label'>> = [
  { id: 'local_epub', label: 'Local EPUBs' },
  { id: 'manual_downloads', label: 'Manual downloads' },
  { id: 'gutenberg', label: 'Gutenberg' },
  { id: 'internet_archive', label: 'Internet Archive' },
  { id: 'openlibrary', label: 'Open Library' },
  { id: 'zlibrary_attended', label: 'Z-Library import' }
];

const EBOOK_DISCOVERY_PROVIDER_ORDER = EBOOK_DISCOVERY_PROVIDERS.map((entry) => entry.id);
const EBOOK_DISCOVERY_PROVIDER_LABELS = new Map(
  EBOOK_DISCOVERY_PROVIDERS.map((entry) => [entry.id, entry.label])
);
const EBOOK_DISCOVERY_CAPABILITIES = new Set(['search', 'metadata', 'acquire', 'import_local']);

export function buildBookNarrationDiscoveryProviderOptions(
  providers: AcquisitionProvider[]
): BookNarrationDiscoveryProviderOption[] {
  if (providers.length === 0) {
    return EBOOK_DISCOVERY_PROVIDERS.map((entry) => ({
      ...entry,
      unavailableMessage: bookDiscoveryProviderUnavailableMessage(entry.id, providers)
    }));
  }
  return providers
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
}

export function bookDiscoveryProviderUnavailableMessage(
  providerId: BookNarrationDiscoveryProvider,
  providers: AcquisitionProvider[]
): string | null {
  const entry = providers.find((provider) => provider.id === providerId);
  if (!entry) {
    if (providers.length > 0) {
      const fallback = EBOOK_DISCOVERY_PROVIDERS.find((option) => option.id === providerId);
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
  return `${entry.label} is ${status}. Configure the backend source root or choose another discovery source.`;
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
  const discoverableProviderIds = new Set(providers.filter(isBookDiscoveryProvider).map((provider) => provider.id));
  const selectedDefault = (defaultProviderIds?.book ?? []).find((providerId) =>
    discoverableProviderIds.has(providerId)
  );
  if (selectedDefault) {
    return selectedDefault;
  }
  return discoverableProviderIds.has(fallback)
    ? fallback
    : (providers.find(isBookDiscoveryProvider)?.id ?? fallback);
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

function discoveryProviderRank(id: string) {
  const index = EBOOK_DISCOVERY_PROVIDER_ORDER.indexOf(id);
  return index === -1 ? Number.MAX_SAFE_INTEGER : index;
}

function discoveryProviderLabel(provider: AcquisitionProvider) {
  return EBOOK_DISCOVERY_PROVIDER_LABELS.get(provider.id) ?? provider.label;
}
