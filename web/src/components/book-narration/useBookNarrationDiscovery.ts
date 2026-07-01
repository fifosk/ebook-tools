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
  AcquisitionPreparedArtifactResponse,
  AcquisitionProvider,
  AcquisitionProviderListResponse
} from '../../api/dtos';
import {
  bookDiscoveryProviderUnavailableMessage,
  buildBookNarrationDiscoveryProviderOptions,
  DEFAULT_BOOK_DISCOVERY_PROVIDER,
  filterBookNarrationDiscoveryCandidates,
  resolveDefaultBookDiscoveryProvider,
  type BookNarrationDiscoveryProvider,
  type BookNarrationDiscoveryProviderOption
} from './bookNarrationDiscoveryProviders';

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

export type BookNarrationDiscoverySelection = {
  selectedPath: string;
  preparedMetadata?: Record<string, unknown> | null;
};

function selectedPathFromPrepared(
  prepared: AcquisitionPreparedArtifactResponse,
  fallbackPath?: string | null
): string | null {
  return (
    prepared.input_file?.trim() ||
    prepared.local_path?.trim() ||
    fallbackPath?.trim() ||
    null
  );
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
    useState<BookNarrationDiscoveryProvider>(DEFAULT_BOOK_DISCOVERY_PROVIDER);
  const [acquiringCandidateId, setAcquiringCandidateId] = useState<string | null>(null);
  const hasUserSelectedDiscoveryProvider = useRef(false);

  const providerUnavailableMessage = useCallback(
    (provider: BookNarrationDiscoveryProvider) => {
      return bookDiscoveryProviderUnavailableMessage(provider, providers);
    },
    [providers],
  );
  const providerOptions = useMemo<BookNarrationDiscoveryProviderOption[]>(() => {
    return buildBookNarrationDiscoveryProviderOptions(providers, defaultProviderIds);
  }, [defaultProviderIds, providers]);
  const discoveryCandidates = useMemo(() => {
    return filterBookNarrationDiscoveryCandidates(
      discoveryResponse,
      discoveryProvider,
      providers
    );
  }, [discoveryProvider, discoveryResponse, providers]);

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
          provider: provider === DEFAULT_BOOK_DISCOVERY_PROVIDER ? null : provider,
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

  const selectDiscoveryCandidate = useCallback(async (candidate: AcquisitionCandidate): Promise<BookNarrationDiscoverySelection | null> => {
    const localPath = candidate.local_path?.trim();
    if (!localPath) {
      return null;
    }
    setAcquiringCandidateId(candidate.candidate_id);
    setDiscoveryError(null);
    try {
      const prepared = await prepareAcquisitionArtifact(candidate.candidate_token);
      const selectedPath = selectedPathFromPrepared(prepared, localPath);
      return selectedPath ? { selectedPath, preparedMetadata: prepared.metadata } : null;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Unable to prepare discovery candidate.';
      setDiscoveryError(message);
      return null;
    } finally {
      setAcquiringCandidateId(null);
    }
  }, []);

  const acquireDiscoveryCandidate = useCallback(async (candidate: AcquisitionCandidate): Promise<BookNarrationDiscoverySelection | null> => {
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
        const selectedPath = selectedPathFromPrepared(prepared, artifact.local_path);
        return selectedPath ? { selectedPath, preparedMetadata: prepared.metadata } : null;
      }
      const selectedPath = artifact.local_path?.trim() || null;
      return selectedPath ? { selectedPath, preparedMetadata: artifact.metadata } : null;
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
    discoveryCandidates,
    discoveryProvider,
    discoveryQuery,
    discoveryResponse,
    discoveryError,
    isDiscovering,
    isLoadingProviders,
    providerError,
    providers,
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
