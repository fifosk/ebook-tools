import { useCallback, useMemo, useState } from 'react';
import { discoverAcquisitionCandidates } from '../../api/client';
import type { AcquisitionDiscoveryResponse, AcquisitionProvider } from '../../api/dtos';
import {
  DEFAULT_VIDEO_DISCOVERY_PROVIDER,
  filterDiscoveredVideoCandidates,
  type VideoDiscoveryProvider
} from './videoDubbingDiscovery';

type VideoDubbingDiscoverySearchOptions = {
  onClearSelectedDiscoveryTemplate: () => void;
  videoDiscoveryProvider?: VideoDiscoveryProvider;
  onVideoDiscoveryProviderChange?: (provider: VideoDiscoveryProvider) => void;
  acquisitionProviders?: AcquisitionProvider[];
};

type VideoDubbingDiscoveryAvailability = {
  isDiscoveryProviderAvailable: boolean;
  unavailableMessage: string | null;
};

export function useVideoDubbingDiscoverySearch({
  onClearSelectedDiscoveryTemplate,
  videoDiscoveryProvider: controlledVideoDiscoveryProvider,
  onVideoDiscoveryProviderChange,
  acquisitionProviders = []
}: VideoDubbingDiscoverySearchOptions) {
  const [uncontrolledVideoDiscoveryProvider, setUncontrolledVideoDiscoveryProvider] =
    useState<VideoDiscoveryProvider>(DEFAULT_VIDEO_DISCOVERY_PROVIDER);
  const videoDiscoveryProvider =
    controlledVideoDiscoveryProvider ?? uncontrolledVideoDiscoveryProvider;
  const setVideoDiscoveryProvider =
    onVideoDiscoveryProviderChange ?? setUncontrolledVideoDiscoveryProvider;
  const [discoveryQuery, setDiscoveryQuery] = useState('');
  const [discoveryResponse, setDiscoveryResponse] =
    useState<AcquisitionDiscoveryResponse | null>(null);
  const [discoveryError, setDiscoveryError] = useState<string | null>(null);
  const [isDiscoveringVideos, setIsDiscoveringVideos] = useState(false);

  const discoveredVideoCandidates = useMemo(() => {
    return filterDiscoveredVideoCandidates(
      discoveryResponse,
      videoDiscoveryProvider,
      acquisitionProviders
    );
  }, [acquisitionProviders, discoveryResponse, videoDiscoveryProvider]);

  const discoverVideos = useCallback(async ({
    isDiscoveryProviderAvailable,
    unavailableMessage
  }: VideoDubbingDiscoveryAvailability) => {
    if (!isDiscoveryProviderAvailable) {
      setDiscoveryError(unavailableMessage ?? 'This discovery source is not available on this backend.');
      setDiscoveryResponse(null);
      return;
    }
    setIsDiscoveringVideos(true);
    setDiscoveryError(null);
    try {
      const response = await discoverAcquisitionCandidates({
        mediaKind: 'video',
        provider:
          videoDiscoveryProvider === DEFAULT_VIDEO_DISCOVERY_PROVIDER
            ? null
            : videoDiscoveryProvider,
        query: discoveryQuery,
        limit: 25
      });
      setDiscoveryResponse(response);
    } catch (error) {
      const message =
        error instanceof Error ? error.message || 'Unable to discover video sources.' : 'Unable to discover video sources.';
      setDiscoveryError(message);
    } finally {
      setIsDiscoveringVideos(false);
    }
  }, [discoveryQuery, videoDiscoveryProvider]);

  const handleDiscoveryProviderChange = useCallback((provider: VideoDiscoveryProvider) => {
    setVideoDiscoveryProvider(provider);
    setDiscoveryResponse(null);
    setDiscoveryError(null);
    onClearSelectedDiscoveryTemplate();
  }, [onClearSelectedDiscoveryTemplate, setVideoDiscoveryProvider]);

  return {
    videoDiscoveryProvider,
    discoveryQuery,
    setDiscoveryQuery,
    discoveryResponse,
    discoveryError,
    setDiscoveryError,
    isDiscoveringVideos,
    discoveredVideoCandidates,
    discoverVideos,
    handleDiscoveryProviderChange
  };
}
