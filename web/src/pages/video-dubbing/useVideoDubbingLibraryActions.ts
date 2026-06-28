import { useCallback } from 'react';
import type { YoutubeNasVideo } from '../../api/dtos';

type VideoDubbingLibraryActionsOptions = {
  refreshLibrary: () => Promise<string | null | undefined>;
  deleteVideo: (video: YoutubeNasVideo) => Promise<string | null | undefined>;
  ensureTargetLanguage: (language: string | null | undefined) => void;
};

export function useVideoDubbingLibraryActions({
  refreshLibrary,
  deleteVideo,
  ensureTargetLanguage
}: VideoDubbingLibraryActionsOptions) {
  const handleRefresh = useCallback(async () => {
    const language = await refreshLibrary();
    ensureTargetLanguage(language);
  }, [ensureTargetLanguage, refreshLibrary]);

  const handleDeleteVideo = useCallback(
    async (video: YoutubeNasVideo) => {
      const language = await deleteVideo(video);
      ensureTargetLanguage(language);
    },
    [deleteVideo, ensureTargetLanguage]
  );

  return {
    handleRefresh,
    handleDeleteVideo
  };
}
