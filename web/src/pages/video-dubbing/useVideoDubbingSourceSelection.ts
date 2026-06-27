import { useCallback, useEffect } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import type {
  AcquisitionCandidate,
  AcquisitionSubtitleHint,
  YoutubeNasSubtitle,
  YoutubeNasVideo
} from '../../api/dtos';
import { prepareAcquisitionArtifact } from '../../api/client';
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

  const handleSelectDiscoveryCandidate = useCallback(async (candidate: AcquisitionCandidate) => {
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

    const candidateToken = candidate.candidate_token?.trim();
    if (!candidateToken) {
      onDiscoveryErrorChange('Selected video discovery result is missing a prepared artifact token.');
      return;
    }
    let preparedVideoPath: string | null = null;
    let preparedSubtitlePath: string | null = null;
    let preparedSubtitleHint: AcquisitionSubtitleHint | null = null;
    onDiscoveryErrorChange(null);
    try {
      const prepared = await prepareAcquisitionArtifact(candidateToken);
      preparedVideoPath = prepared.video_path?.trim() || prepared.local_path?.trim() || null;
      preparedSubtitlePath = prepared.subtitle_path?.trim() || prepared.subtitles[0]?.path?.trim() || null;
      preparedSubtitleHint =
        prepared.subtitles.find((subtitle) => subtitle.path === preparedSubtitlePath) ??
        prepared.subtitles[0] ??
        null;
    } catch (error) {
      onDiscoveryErrorChange(error instanceof Error ? error.message : 'Unable to prepare selected video source.');
      return;
    }
    if (!preparedVideoPath) {
      onDiscoveryErrorChange('Prepared video discovery result did not include a usable video path.');
      return;
    }
    const libraryVideo = videos.find((video) => video.path === preparedVideoPath);
    if (libraryVideo) {
      const preparedLibrarySubtitle = preparedSubtitlePath
        ? libraryVideo.subtitles.find((subtitle) => subtitle.path === preparedSubtitlePath)
        : null;
      const selectedSubtitle = preparedLibrarySubtitle ?? resolveDefaultSubtitle(libraryVideo);
      const selectedSubtitlePath = selectedSubtitle?.path ?? preparedSubtitlePath ?? null;
      onSelectedVideoPathChange(libraryVideo.path);
      onSelectedSubtitlePathChange(selectedSubtitlePath);
      onTargetLanguageEnsure(selectedSubtitle?.language ?? preparedSubtitleHint?.language);
      onSelectedVideoDiscoveryTemplateStateChange(templateState(libraryVideo.path, selectedSubtitlePath));
      onStatusMessageChange(`Selected discovered video ${libraryVideo.filename}.`);
      return;
    }
    onSelectedVideoPathChange(preparedVideoPath);
    onSelectedSubtitlePathChange(preparedSubtitlePath);
    onTargetLanguageEnsure(preparedSubtitleHint?.language);
    onSelectedVideoDiscoveryTemplateStateChange(templateState(preparedVideoPath, preparedSubtitlePath));
    onStatusMessageChange('Selected a discovered video path. Refresh the NAS library if the video row is not visible yet.');
  }, [
    discoveryQuery,
    onActiveTabChange,
    onDiscoveryErrorChange,
    onDownloadStationCandidateChange,
    onDownloadStationSourceUriChange,
    onMetadataSectionChange,
    onSelectedSubtitlePathChange,
    onSelectedVideoDiscoveryTemplateStateChange,
    onSelectedVideoPathChange,
    onStatusMessageChange,
    onTargetLanguageEnsure,
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
