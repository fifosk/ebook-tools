import { useCallback, useMemo, useState } from 'react';
import {
  acquireAcquisitionCandidate,
  discoverAcquisitionCandidates,
  fetchAcquisitionProviders,
  prepareAcquisitionArtifact
} from '../../api/client';
import type {
  AcquisitionCandidate,
  AcquisitionDiscoveryResponse,
  AcquisitionProvider
} from '../../api/dtos';

export type BookNarrationDiscoveryProvider =
  | 'local_epub'
  | 'manual_downloads'
  | 'gutenberg'
  | 'internet_archive'
  | 'openlibrary';

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
  { id: 'openlibrary', label: 'Open Library' }
];

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
  const [discoveryProvider, setDiscoveryProvider] =
    useState<BookNarrationDiscoveryProvider>('local_epub');
  const [acquiringCandidateId, setAcquiringCandidateId] = useState<string | null>(null);

  const providerById = useMemo(() => {
    return new Map(providers.map((entry) => [entry.id, entry]));
  }, [providers]);

  const providerUnavailableMessage = useCallback(
    (provider: BookNarrationDiscoveryProvider) => {
      const entry = providerById.get(provider);
      if (!entry || entry.available) {
        return null;
      }
      const status = entry.status.replace(/_/g, ' ');
      return `${entry.label} is ${status}. Configure the backend source root or choose another discovery source.`;
    },
    [providerById],
  );
  const providerOptions = useMemo<BookNarrationDiscoveryProviderOption[]>(() => {
    return EBOOK_DISCOVERY_PROVIDERS.map((entry) => ({
      ...entry,
      unavailableMessage: providerUnavailableMessage(entry.id)
    }));
  }, [providerUnavailableMessage]);

  const loadProviders = useCallback(async (): Promise<AcquisitionProvider[]> => {
    if (isGeneratedSource) {
      return [];
    }
    setIsLoadingProviders(true);
    try {
      const response = await fetchAcquisitionProviders();
      const entries = response.providers ?? [];
      setProviders(entries);
      setProviderError(null);
      return entries;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Unable to load discovery provider status.';
      setProviderError(message);
      return [];
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
      const loadedProviders = providers.length > 0 ? providers : await loadProviders();
      const selectedProvider = loadedProviders.find((entry) => entry.id === discoveryProvider);
      if (selectedProvider?.available === false) {
        setDiscoveryResponse(null);
        return;
      }
      await runDiscoverySearch();
    })();
  }, [discoveryProvider, isGeneratedSource, loadProviders, providers, runDiscoverySearch]);

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
    openDiscoveryDialog,
    runDiscoverySearch,
    selectDiscoveryCandidate,
    setDiscoveryQuery
  };
}
