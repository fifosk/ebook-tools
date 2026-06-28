import { useMemo } from 'react';
import type { YoutubeNasSubtitle, YoutubeNasVideo } from '../../api/dtos';
import {
  resolveSubtitleLanguageCandidate,
  resolveSubtitleLanguageLabel
} from '../../utils/subtitles';
import {
  canExtractEmbeddedSubtitles,
  filterPlayableSubtitles,
  resolveVideoDubbingMetadataSourceName
} from './videoDubbingUtils';

type VideoDubbingResolvedSelectionOptions = {
  videos: YoutubeNasVideo[];
  selectedVideoPath: string | null;
  selectedSubtitlePath: string | null;
};

export function useVideoDubbingResolvedSelection({
  videos,
  selectedVideoPath,
  selectedSubtitlePath
}: VideoDubbingResolvedSelectionOptions) {
  const selectedVideo = useMemo(
    () => videos.find((video) => video.path === selectedVideoPath) ?? null,
    [videos, selectedVideoPath]
  );
  const playableSubtitles = useMemo<YoutubeNasSubtitle[]>(() => {
    return filterPlayableSubtitles(selectedVideo);
  }, [selectedVideo]);
  const selectedSubtitle = useMemo(
    () => playableSubtitles.find((sub) => sub.path === selectedSubtitlePath) ?? null,
    [playableSubtitles, selectedSubtitlePath]
  );
  const subtitleLanguage = useMemo(
    () => ({
      label: resolveSubtitleLanguageLabel(
        selectedSubtitle?.language,
        selectedSubtitle?.path,
        selectedSubtitle?.filename
      ),
      code: resolveSubtitleLanguageCandidate(
        selectedSubtitle?.language,
        selectedSubtitle?.path,
        selectedSubtitle?.filename
      )
    }),
    [selectedSubtitle]
  );
  const metadataSourceName = useMemo(() => {
    return resolveVideoDubbingMetadataSourceName({
      subtitle: selectedSubtitle,
      video: selectedVideo
    });
  }, [selectedSubtitle, selectedVideo]);
  const canExtractEmbedded = useMemo(() => {
    return canExtractEmbeddedSubtitles(selectedVideo);
  }, [selectedVideo]);

  return {
    selectedVideo,
    playableSubtitles,
    selectedSubtitle,
    subtitleLanguageLabel: subtitleLanguage.label,
    subtitleLanguageCode: subtitleLanguage.code,
    metadataSourceName,
    canExtractEmbedded
  };
}
