import { useCallback, useEffect, useRef, useState } from 'react';
import { useVideoDubbingAcquisitionProviders } from './useVideoDubbingAcquisitionProviders';
import { useVideoDubbingDiscoverySearch } from './useVideoDubbingDiscoverySearch';
import type { VideoDiscoveryProvider } from './videoDubbingDiscovery';

type VideoDubbingDiscoveryControllerOptions = {
  onClearSelectedDiscoveryTemplate: () => void;
};

export function useVideoDubbingDiscoveryController({
  onClearSelectedDiscoveryTemplate
}: VideoDubbingDiscoveryControllerOptions) {
  const [videoDiscoveryProvider, setVideoDiscoveryProvider] =
    useState<VideoDiscoveryProvider>('nas_video');
  const hasUserSelectedVideoDiscoveryProvider = useRef(false);
  const {
    acquisitionProviders,
    acquisitionProviderError,
    preferredVideoDiscoveryProvider,
    videoDiscoveryProviderOptions,
    isYoutubeSearchAvailable,
    isDownloadStationAvailable,
    isIndexerSearchAvailable,
    isSelectedVideoDiscoveryProviderAvailable,
    youtubeSearchUnavailableMessage,
    manualDownloadsUnavailableMessage,
    downloadStationUnavailableMessage,
    indexerSearchUnavailableMessage,
    selectedVideoDiscoveryProviderUnavailableMessage
  } = useVideoDubbingAcquisitionProviders(videoDiscoveryProvider);
  const {
    discoveryQuery,
    setDiscoveryQuery,
    discoveryError,
    setDiscoveryError,
    isDiscoveringVideos,
    discoveredVideoCandidates,
    discoverVideos,
    handleDiscoveryProviderChange: applyDiscoveryProviderChange
  } = useVideoDubbingDiscoverySearch({
    onClearSelectedDiscoveryTemplate,
    videoDiscoveryProvider,
    onVideoDiscoveryProviderChange: setVideoDiscoveryProvider,
    acquisitionProviders
  });

  useEffect(() => {
    if (
      hasUserSelectedVideoDiscoveryProvider.current ||
      !preferredVideoDiscoveryProvider ||
      preferredVideoDiscoveryProvider === videoDiscoveryProvider
    ) {
      return;
    }
    applyDiscoveryProviderChange(preferredVideoDiscoveryProvider);
  }, [applyDiscoveryProviderChange, preferredVideoDiscoveryProvider, videoDiscoveryProvider]);

  const discoverAvailableVideos = useCallback(async () => {
    await discoverVideos({
      isDiscoveryProviderAvailable: isSelectedVideoDiscoveryProviderAvailable,
      unavailableMessage: selectedVideoDiscoveryProviderUnavailableMessage
    });
  }, [
    discoverVideos,
    isSelectedVideoDiscoveryProviderAvailable,
    selectedVideoDiscoveryProviderUnavailableMessage
  ]);

  const handleDiscoveryProviderChange = useCallback((provider: VideoDiscoveryProvider) => {
    hasUserSelectedVideoDiscoveryProvider.current = true;
    applyDiscoveryProviderChange(provider);
  }, [applyDiscoveryProviderChange]);

  return {
    acquisitionProviderError,
    discoveryQuery,
    setDiscoveryQuery,
    discoveryError,
    setDiscoveryError,
    isDiscoveringVideos,
    discoveredVideoCandidates,
    discoverVideos: discoverAvailableVideos,
    videoDiscoveryProvider,
    videoDiscoveryProviderOptions,
    isYoutubeSearchAvailable,
    isDownloadStationAvailable,
    isIndexerSearchAvailable,
    isSelectedVideoDiscoveryProviderAvailable,
    youtubeSearchUnavailableMessage,
    manualDownloadsUnavailableMessage,
    downloadStationUnavailableMessage,
    indexerSearchUnavailableMessage,
    selectedVideoDiscoveryProviderUnavailableMessage,
    handleDiscoveryProviderChange
  };
}
