import { useCallback, useEffect } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import type {
  AcquisitionCandidate,
  YoutubeNasSubtitle,
  YoutubeNasVideo
} from '../../api/dtos';
import type { VideoDubbingTab, VideoMetadataSection } from './videoDubbingTypes';
import {
  isDownloadStationHandoffCandidate,
  makeVideoDiscoveryTemplateState,
  resolveDefaultSubtitle
} from './videoDubbingUtils';

type VideoDubbingSourceSelectionOptions = {
  selectedVideoPath: string | null;
  selectedVideo: YoutubeNasVideo | null;
  selectedSubtitlePath: string | null;
  playableSubtitles: YoutubeNasSubtitle[];
  videos: YoutubeNasVideo[];
  videoDiscoveryProvider: string;
  discoveryQuery: string;
  onSelectedVideoPathChange: (path: string | null) => void;
  onSelectedSubtitlePathChange: (path: string | null) => void;
  onSelectedVideoDiscoveryTemplateStateChange: Dispatch<SetStateAction<Record<string, unknown> | null>>;
  onTargetLanguageEnsure: (language?: string | null) => void;
  onDiscoveryErrorChange: (message: string | null) => void;
  onYoutubeLookupSourceNameChange: (sourceName: string) => void;
  onMetadataSectionChange: (section: VideoMetadataSection) => void;
  onActiveTabChange: (tab: VideoDubbingTab) => void;
  onYoutubeMetadataLookup: (sourceName: string, force: boolean) => Promise<unknown>;
  onDownloadStationCandidateChange: (candidate: AcquisitionCandidate | null) => void;
  onDownloadStationSourceUriChange: (sourceUri: string) => void;
  onStatusMessageChange: (message: string | null) => void;
};

export function useVideoDubbingSourceSelection({
  selectedVideoPath,
  selectedVideo,
  selectedSubtitlePath,
  playableSubtitles,
  videos,
  videoDiscoveryProvider,
  discoveryQuery,
  onSelectedVideoPathChange,
  onSelectedSubtitlePathChange,
  onSelectedVideoDiscoveryTemplateStateChange,
  onTargetLanguageEnsure,
  onDiscoveryErrorChange,
  onYoutubeLookupSourceNameChange,
  onMetadataSectionChange,
  onActiveTabChange,
  onYoutubeMetadataLookup,
  onDownloadStationCandidateChange,
  onDownloadStationSourceUriChange,
  onStatusMessageChange
}: VideoDubbingSourceSelectionOptions) {
  useEffect(() => {
    if (selectedVideoPath && !selectedVideo) {
      return;
    }
    if (playableSubtitles.length === 0) {
      onSelectedSubtitlePathChange(null);
      return;
    }
    const current = playableSubtitles.find((sub) => sub.path === selectedSubtitlePath);
    if (current) {
      return;
    }
    const defaultSubtitle = resolveDefaultSubtitle(selectedVideo) ?? playableSubtitles[0];
    onSelectedSubtitlePathChange(defaultSubtitle?.path ?? null);
    onTargetLanguageEnsure(defaultSubtitle?.language);
  }, [
    onSelectedSubtitlePathChange,
    onTargetLanguageEnsure,
    playableSubtitles,
    selectedSubtitlePath,
    selectedVideo,
    selectedVideoPath
  ]);

  const handleSelectVideo = useCallback((video: YoutubeNasVideo) => {
    onSelectedVideoDiscoveryTemplateStateChange(null);
    onSelectedVideoPathChange(video.path);
    const defaultSubtitle = resolveDefaultSubtitle(video);
    onSelectedSubtitlePathChange(defaultSubtitle?.path ?? null);
    onTargetLanguageEnsure(defaultSubtitle?.language);
  }, [
    onSelectedSubtitlePathChange,
    onSelectedVideoDiscoveryTemplateStateChange,
    onSelectedVideoPathChange,
    onTargetLanguageEnsure
  ]);

  const handleSelectDiscoveryCandidate = useCallback((candidate: AcquisitionCandidate) => {
    const templateState = (selectedVideoPath?: string | null, selectedSubtitlePath?: string | null) =>
      makeVideoDiscoveryTemplateState(candidate, {
        selectedProvider: videoDiscoveryProvider,
        query: discoveryQuery,
        selectedVideoPath,
        selectedSubtitlePath
      });
    if (candidate.provider === 'youtube_search') {
      const metadataYoutubeUrl = candidate.metadata['youtube_url'];
      const sourceUrl =
        candidate.source_url?.trim() ||
        (typeof metadataYoutubeUrl === 'string' ? metadataYoutubeUrl.trim() : '');
      if (!sourceUrl) {
        onDiscoveryErrorChange('Selected YouTube result does not include a reviewable URL.');
        return;
      }
      onYoutubeLookupSourceNameChange(sourceUrl);
      onMetadataSectionChange('youtube');
      onActiveTabChange('metadata');
      void onYoutubeMetadataLookup(sourceUrl, false);
      onSelectedVideoDiscoveryTemplateStateChange(templateState(null, null));
      onStatusMessageChange(`Selected YouTube discovery result ${candidate.title}. Review metadata before downloading or dubbing.`);
      return;
    }

    if (candidate.provider === 'newznab_torznab') {
      if (isDownloadStationHandoffCandidate(candidate)) {
        onDownloadStationCandidateChange(candidate);
        onDownloadStationSourceUriChange('');
      }
      onSelectedVideoDiscoveryTemplateStateChange(templateState(null, null));
      onStatusMessageChange(`Selected indexer result ${candidate.title}. Confirm lawful access before any downloader handoff.`);
      return;
    }

    const localPath = candidate.local_path?.trim();
    if (!localPath) {
      return;
    }
    const libraryVideo = videos.find((video) => video.path === localPath);
    if (libraryVideo) {
      const defaultSubtitle = resolveDefaultSubtitle(libraryVideo);
      handleSelectVideo(libraryVideo);
      onSelectedVideoDiscoveryTemplateStateChange(templateState(libraryVideo.path, defaultSubtitle?.path ?? null));
      onStatusMessageChange(`Selected discovered video ${libraryVideo.filename}.`);
      return;
    }
    onSelectedVideoPathChange(localPath);
    const selectedSubtitlePath = candidate.subtitles[0]?.path ?? null;
    onSelectedSubtitlePathChange(selectedSubtitlePath);
    onSelectedVideoDiscoveryTemplateStateChange(templateState(localPath, selectedSubtitlePath));
    onStatusMessageChange('Selected a discovered video path. Refresh the NAS library if the video row is not visible yet.');
  }, [
    discoveryQuery,
    handleSelectVideo,
    onActiveTabChange,
    onDiscoveryErrorChange,
    onDownloadStationCandidateChange,
    onDownloadStationSourceUriChange,
    onMetadataSectionChange,
    onSelectedSubtitlePathChange,
    onSelectedVideoDiscoveryTemplateStateChange,
    onSelectedVideoPathChange,
    onStatusMessageChange,
    onYoutubeLookupSourceNameChange,
    onYoutubeMetadataLookup,
    videoDiscoveryProvider,
    videos
  ]);

  const handleSelectSubtitle = useCallback((path: string) => {
    onSelectedSubtitlePathChange(path);
    onSelectedVideoDiscoveryTemplateStateChange((current) =>
      current ? { ...current, selected_subtitle_path: path } : current
    );
    const match = playableSubtitles.find((sub) => sub.path === path);
    onTargetLanguageEnsure(match?.language);
  }, [
    onSelectedSubtitlePathChange,
    onSelectedVideoDiscoveryTemplateStateChange,
    onTargetLanguageEnsure,
    playableSubtitles
  ]);

  return {
    handleSelectVideo,
    handleSelectDiscoveryCandidate,
    handleSelectSubtitle
  };
}
