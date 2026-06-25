import { useCallback, useState } from 'react';
import { acquireAcquisitionCandidate, discoverAcquisitionCandidates } from '../../api/client';
import type { AcquisitionCandidate, AcquisitionDiscoveryResponse } from '../../api/dtos';

export type BookNarrationDiscoveryProvider = 'local_epub' | 'manual_downloads' | 'gutenberg';

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
  const [discoveryProvider, setDiscoveryProvider] =
    useState<BookNarrationDiscoveryProvider>('local_epub');
  const [acquiringCandidateId, setAcquiringCandidateId] = useState<string | null>(null);

  const runDiscoverySearch = useCallback(
    async (
      query = discoveryQuery,
      provider: BookNarrationDiscoveryProvider = discoveryProvider,
    ) => {
      if (isGeneratedSource) {
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
    [discoveryProvider, discoveryQuery, isGeneratedSource],
  );

  const changeDiscoveryProvider = useCallback(
    (provider: BookNarrationDiscoveryProvider) => {
      setDiscoveryProvider(provider);
      setDiscoveryResponse(null);
      setDiscoveryError(null);
      void runDiscoverySearch(discoveryQuery, provider);
    },
    [discoveryQuery, runDiscoverySearch],
  );

  const openDiscoveryDialog = useCallback(() => {
    if (isGeneratedSource) {
      return;
    }
    setActiveDiscoveryDialog(true);
    void runDiscoverySearch();
  }, [isGeneratedSource, runDiscoverySearch]);

  const closeDiscoveryDialog = useCallback(() => {
    setActiveDiscoveryDialog(false);
  }, []);

  const selectDiscoveryCandidate = useCallback((candidate: AcquisitionCandidate): string | null => {
    const localPath = candidate.local_path?.trim();
    if (localPath) {
      return localPath;
    }
    return null;
  }, []);

  const acquireDiscoveryCandidate = useCallback(async (candidate: AcquisitionCandidate): Promise<string | null> => {
    setAcquiringCandidateId(candidate.candidate_id);
    setDiscoveryError(null);
    try {
      const artifact = await acquireAcquisitionCandidate({
        candidate_token: candidate.candidate_token,
        confirmed: true,
        filename: `${candidate.title || 'acquired'}.epub`
      });
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
    acquireDiscoveryCandidate,
    changeDiscoveryProvider,
    closeDiscoveryDialog,
    openDiscoveryDialog,
    runDiscoverySearch,
    selectDiscoveryCandidate,
    setDiscoveryQuery
  };
}
