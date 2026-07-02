import { useCallback, useEffect, useMemo, useState } from 'react';
import { fetchAcquisitionProviders } from '../../api/client';
import type { AcquisitionProvider, AcquisitionProviderListResponse } from '../../api/dtos';
import {
  resolveDefaultVideoDiscoveryProvider,
  resolveVideoDiscoveryProviderState,
  type VideoDiscoveryProvider
} from './videoDubbingDiscovery';

export function useVideoDubbingAcquisitionProviders(selectedProvider: VideoDiscoveryProvider) {
  const [providers, setProviders] = useState<AcquisitionProvider[]>([]);
  const [defaultProviderIds, setDefaultProviderIds] =
    useState<AcquisitionProviderListResponse['default_provider_ids']>();
  const [providerError, setProviderError] = useState<string | null>(null);

  const refreshProviders = useCallback(async () => {
    setProviderError(null);
    try {
      const response = await fetchAcquisitionProviders();
      setProviders(response.providers);
      setDefaultProviderIds(response.default_provider_ids);
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
        selectedProvider,
        defaultProviderIds
      }),
    [defaultProviderIds, providers, selectedProvider]
  );

  const preferredVideoDiscoveryProvider = useMemo(
    () =>
      resolveDefaultVideoDiscoveryProvider({
        defaultProviderIds,
        options: providerState.videoDiscoveryProviderOptions,
        providers
      }),
    [defaultProviderIds, providerState.videoDiscoveryProviderOptions, providers]
  );

  return {
    acquisitionProviders: providers,
    acquisitionProviderError: providerError,
    refreshAcquisitionProviders: refreshProviders,
    preferredVideoDiscoveryProvider,
    ...providerState
  };
}
