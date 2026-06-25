import { useCallback, useState } from 'react';
import { discoverAcquisitionCandidates } from '../../api/client';
import type { AcquisitionCandidate, AcquisitionDiscoveryResponse } from '../../api/dtos';

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

  const runDiscoverySearch = useCallback(
    async (query = discoveryQuery) => {
      if (isGeneratedSource) {
        return;
      }
      setIsDiscovering(true);
      try {
        const response = await discoverAcquisitionCandidates({
          mediaKind: 'book',
          query,
          provider: 'local_epub',
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
    [discoveryQuery, isGeneratedSource],
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

  return {
    activeDiscoveryDialog,
    discoveryQuery,
    discoveryResponse,
    discoveryError,
    isDiscovering,
    closeDiscoveryDialog,
    openDiscoveryDialog,
    runDiscoverySearch,
    selectDiscoveryCandidate,
    setDiscoveryQuery
  };
}
