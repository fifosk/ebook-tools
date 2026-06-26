import { useCallback, useMemo, useRef, useState } from 'react';
import {
  acquireAcquisitionCandidate,
  discoverAcquisitionCandidates,
  fetchAcquisitionProviders,
  prepareAcquisitionArtifact
} from '../../api/client';
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

function isBookDiscoveryProvider(provider: AcquisitionProvider) {
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

function resolveDefaultBookDiscoveryProvider({
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

function extractInternetArchiveSourceIds(candidate: AcquisitionCandidate): string[] {
  const value = candidate.metadata.internet_archive_ids;
  const ids = Array.isArray(value) ? value : [value];
  const seen = new Set<string>();
  const normalized: string[] = [];
  for (const entry of ids) {
    if (typeof entry !== 'string') {
      continue;
    }
    const trimmed = entry.trim();
    const key = trimmed.toLowerCase();
    if (!trimmed || seen.has(key)) {
      continue;
    }
    seen.add(key);
    normalized.push(trimmed);
  }
  return normalized;
}

type UseBookNarrationDiscoveryOptions = {
  isGeneratedSource: boolean;
};

export function useBookNarrationDiscovery({
  isGeneratedSource
}: UseBookNarrationDiscoveryOptions) {
  const [activeDiscoveryDialog, setActiveDiscoveryDialog] = useState(false);
  const [discoveryQuery, setDiscoveryQuery] = useState('');
  const [discoveryResponse, setDiscoveryResponse] =
    useState<AcquisitionDiscoveryResponse | null>(null);
  const [discoveryError, setDiscoveryError] = useState<string | null>(null);
  const [isDiscovering, setIsDiscovering] = useState(false);
  const [isLoadingProviders, setIsLoadingProviders] = useState(false);
  const [providerError, setProviderError] = useState<string | null>(null);
  const [providers, setProviders] = useState<AcquisitionProvider[]>([]);
  const [defaultProviderIds, setDefaultProviderIds] =
    useState<AcquisitionProviderListResponse['default_provider_ids']>();
  const [discoveryProvider, setDiscoveryProvider] =
    useState<BookNarrationDiscoveryProvider>('local_epub');
  const [acquiringCandidateId, setAcquiringCandidateId] = useState<string | null>(null);
  const hasUserSelectedDiscoveryProvider = useRef(false);

  const providerById = useMemo(() => {
    return new Map(providers.map((entry) => [entry.id, entry]));
  }, [providers]);

  const providerUnavailableMessage = useCallback(
    (provider: BookNarrationDiscoveryProvider) => {
      const entry = providerById.get(provider);
      if (!entry) {
        if (providers.length > 0) {
          const fallback = EBOOK_DISCOVERY_PROVIDERS.find((option) => option.id === provider);
          const label = fallback?.label ?? provider;
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
    },
    [providerById, providers.length],
  );
  const providerOptions = useMemo<BookNarrationDiscoveryProviderOption[]>(() => {
    if (providers.length === 0) {
      return EBOOK_DISCOVERY_PROVIDERS.map((entry) => ({
        ...entry,
        unavailableMessage: providerUnavailableMessage(entry.id)
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
        unavailableMessage: providerUnavailableMessage(entry.id)
      }));
  }, [providerUnavailableMessage, providers]);

  const loadProviders = useCallback(async (): Promise<{
    entries: AcquisitionProvider[];
    defaults?: AcquisitionProviderListResponse['default_provider_ids'];
  }> => {
    if (isGeneratedSource) {
      return { entries: [] };
    }
    setIsLoadingProviders(true);
    try {
      const response = await fetchAcquisitionProviders();
      const entries = response.providers ?? [];
      setProviders(entries);
      setDefaultProviderIds(response.default_provider_ids);
      setProviderError(null);
      return { entries, defaults: response.default_provider_ids };
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Unable to load discovery provider status.';
      setProviderError(message);
      return { entries: [] };
    } finally {
      setIsLoadingProviders(false);
    }
  }, [isGeneratedSource]);

  const runDiscoverySearch = useCallback(
    async (
      query = discoveryQuery,
      provider: BookNarrationDiscoveryProvider = discoveryProvider,
    ) => {
      if (isGeneratedSource) {
        return;
      }
      const unavailableMessage = providerUnavailableMessage(provider);
      if (unavailableMessage) {
        setDiscoveryError(null);
        setDiscoveryResponse(null);
        return;
      }
      setIsDiscovering(true);
      try {
        const response = await discoverAcquisitionCandidates({
          mediaKind: 'book',
          query,
          provider,
          limit: 25
        });
        setDiscoveryResponse(response);
        setDiscoveryError(null);
      } catch (error) {
        const message =
          error instanceof Error ? error.message : 'Unable to search discovery sources.';
        setDiscoveryError(message);
        setDiscoveryResponse(null);
      } finally {
        setIsDiscovering(false);
      }
    },
    [discoveryProvider, discoveryQuery, isGeneratedSource, providerUnavailableMessage],
  );

  const changeDiscoveryProvider = useCallback(
    (provider: BookNarrationDiscoveryProvider) => {
      hasUserSelectedDiscoveryProvider.current = true;
      setDiscoveryProvider(provider);
      setDiscoveryResponse(null);
      setDiscoveryError(null);
      if (providerUnavailableMessage(provider)) {
        return;
      }
      void runDiscoverySearch(discoveryQuery, provider);
    },
    [discoveryQuery, providerUnavailableMessage, runDiscoverySearch],
  );

  const openDiscoveryDialog = useCallback(() => {
    if (isGeneratedSource) {
      return;
    }
    setActiveDiscoveryDialog(true);
    void (async () => {
      const loaded = providers.length > 0
        ? { entries: providers, defaults: defaultProviderIds }
        : await loadProviders();
      const effectiveProvider = hasUserSelectedDiscoveryProvider.current
        ? discoveryProvider
        : resolveDefaultBookDiscoveryProvider({
            defaultProviderIds: loaded.defaults,
            providers: loaded.entries,
            fallback: discoveryProvider
          });
      if (effectiveProvider !== discoveryProvider) {
        setDiscoveryProvider(effectiveProvider);
        setDiscoveryResponse(null);
        setDiscoveryError(null);
      }
      const selectedProvider = loaded.entries.find((entry) => entry.id === effectiveProvider);
      if (selectedProvider?.available === false) {
        setDiscoveryResponse(null);
        return;
      }
      await runDiscoverySearch(discoveryQuery, effectiveProvider);
    })();
  }, [
    defaultProviderIds,
    discoveryProvider,
    discoveryQuery,
    isGeneratedSource,
    loadProviders,
    providers,
    runDiscoverySearch
  ]);

  const closeDiscoveryDialog = useCallback(() => {
    setActiveDiscoveryDialog(false);
  }, []);

  const selectDiscoveryCandidate = useCallback(async (candidate: AcquisitionCandidate): Promise<string | null> => {
    const localPath = candidate.local_path?.trim();
    if (!localPath) {
      return null;
    }
    setAcquiringCandidateId(candidate.candidate_id);
    setDiscoveryError(null);
    try {
      const prepared = await prepareAcquisitionArtifact(candidate.candidate_token);
      return prepared.input_file?.trim() || prepared.local_path?.trim() || localPath;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Unable to prepare discovery candidate.';
      setDiscoveryError(message);
      return null;
    } finally {
      setAcquiringCandidateId(null);
    }
  }, []);

  const acquireDiscoveryCandidate = useCallback(async (candidate: AcquisitionCandidate): Promise<string | null> => {
    if (!candidate.capabilities.includes('acquire')) {
      setDiscoveryError(
        'Open Library results provide metadata only. Choose a local, Gutenberg, Internet Archive, or manually downloaded EPUB source before narrating.'
      );
      return null;
    }
    setAcquiringCandidateId(candidate.candidate_id);
    setDiscoveryError(null);
    try {
      const artifact = await acquireAcquisitionCandidate({
        candidate_token: candidate.candidate_token,
        confirmed: true,
        filename: `${candidate.title || 'acquired'}.epub`
      });
      if (artifact.artifact_id?.trim()) {
        const prepared = await prepareAcquisitionArtifact(artifact.artifact_id);
        return prepared.input_file?.trim() || prepared.local_path?.trim() || artifact.local_path?.trim() || null;
      }
      return artifact.local_path?.trim() || null;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Unable to acquire discovery candidate.';
      setDiscoveryError(message);
      return null;
    } finally {
      setAcquiringCandidateId(null);
    }
  }, []);

  const discoverInternetArchiveCandidatesForCandidate = useCallback(
    async (candidate: AcquisitionCandidate): Promise<boolean> => {
      const sourceIds = extractInternetArchiveSourceIds(candidate);
      if (sourceIds.length === 0) {
        return false;
      }
      setAcquiringCandidateId(candidate.candidate_id);
      setDiscoveryError(null);
      try {
        const response = await discoverAcquisitionCandidates({
          mediaKind: 'book',
          query: candidate.title,
          provider: 'internet_archive',
          sourceIds,
          limit: 25
        });
        setDiscoveryProvider('internet_archive');
        setDiscoveryResponse(response);
        if (response.candidates.length === 0) {
          setDiscoveryError(
            'No public Internet Archive EPUB was available for that Open Library record.'
          );
        }
        return true;
      } catch (error) {
        const message =
          error instanceof Error ? error.message : 'Unable to search Internet Archive source IDs.';
        setDiscoveryError(message);
        return true;
      } finally {
        setAcquiringCandidateId(null);
      }
    },
    [],
  );

  return {
    acquiringCandidateId,
    activeDiscoveryDialog,
    discoveryProvider,
    discoveryQuery,
    discoveryResponse,
    discoveryError,
    isDiscovering,
    isLoadingProviders,
    providerError,
    providerOptions,
    selectedProviderUnavailableMessage: providerUnavailableMessage(discoveryProvider),
    acquireDiscoveryCandidate,
    changeDiscoveryProvider,
    closeDiscoveryDialog,
    discoverInternetArchiveCandidatesForCandidate,
    openDiscoveryDialog,
    runDiscoverySearch,
    selectDiscoveryCandidate,
    setDiscoveryQuery
  };
}
