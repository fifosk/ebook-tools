import { useCallback, useEffect, useMemo, useState } from 'react';
import { fetchAcquisitionProviders } from '../../api/client';
import type { AcquisitionProvider } from '../../api/dtos';
import {
  resolveVideoDiscoveryProviderState,
  type VideoDiscoveryProvider
} from './videoDubbingDiscovery';

export function useVideoDubbingAcquisitionProviders(selectedProvider: VideoDiscoveryProvider) {
  const [providers, setProviders] = useState<AcquisitionProvider[]>([]);
  const [providerError, setProviderError] = useState<string | null>(null);

  const refreshProviders = useCallback(async () => {
    setProviderError(null);
    try {
      const response = await fetchAcquisitionProviders();
      setProviders(response.providers ?? []);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message || 'Unable to load discovery providers.'
          : 'Unable to load discovery providers.';
      setProviderError(message);
    }
  }, []);

  useEffect(() => {
    void refreshProviders();
  }, [refreshProviders]);

  const providerState = useMemo(
    () =>
      resolveVideoDiscoveryProviderState({
        providers,
        selectedProvider
      }),
    [providers, selectedProvider]
  );

  return {
    acquisitionProviderError: providerError,
    refreshAcquisitionProviders: refreshProviders,
    ...providerState
  };
}
