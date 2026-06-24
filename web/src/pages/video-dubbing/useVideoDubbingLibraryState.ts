import { useCallback, useState } from 'react';
import type { MutableRefObject } from 'react';
import {
  deleteYoutubeVideo,
  fetchYoutubeLibrary
} from '../../api/client';
import type {
  JobParameterSnapshot,
  YoutubeNasLibraryResponse,
  YoutubeNasVideo
} from '../../api/dtos';
import {
  resolveSelectionAfterVideoDelete,
  resolveVideoDubPrefill,
  resolveVideoDubbingSelection
} from './videoDubbingUtils';

type VideoDubbingLibraryStateOptions = {
  baseDir: string;
  selectedVideoPath: string | null;
  selectedSubtitlePath: string | null;
  selectedVideoPathRef: MutableRefObject<string | null>;
  selectedSubtitlePathRef: MutableRefObject<string | null>;
  prefillParameters: JobParameterSnapshot | null;
  onBaseDirChange: (baseDir: string) => void;
  onSelectedVideoPathChange: (path: string | null) => void;
  onSelectedSubtitlePathChange: (path: string | null) => void;
  onStatusMessageChange: (message: string | null) => void;
};

export function useVideoDubbingLibraryState({
  baseDir,
  selectedVideoPath,
  selectedSubtitlePath,
  selectedVideoPathRef,
  selectedSubtitlePathRef,
  prefillParameters,
  onBaseDirChange,
  onSelectedVideoPathChange,
  onSelectedSubtitlePathChange,
  onStatusMessageChange
}: VideoDubbingLibraryStateOptions) {
  const [library, setLibrary] = useState<YoutubeNasLibraryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [deletingVideoPath, setDeletingVideoPath] = useState<string | null>(null);

  const refreshLibrary = useCallback(async (): Promise<string | null | undefined> => {
    setIsLoading(true);
    setLoadError(null);
    onStatusMessageChange(null);
    try {
      const response = await fetchYoutubeLibrary(baseDir.trim() || undefined);
      setLibrary(response);
      onBaseDirChange(response.base_dir || baseDir);
      if (response.videos.length > 0) {
        const prefill = resolveVideoDubPrefill(prefillParameters);
        const selection = resolveVideoDubbingSelection({
          videos: response.videos,
          preferredVideoPath: prefill?.videoPath || selectedVideoPathRef.current,
          preferredSubtitlePath: prefill?.subtitlePath || selectedSubtitlePathRef.current,
        });
        onSelectedVideoPathChange(selection.videoPath);
        onSelectedSubtitlePathChange(selection.subtitlePath);
        return selection.subtitle?.language ?? null;
      } else {
        onSelectedVideoPathChange(null);
        onSelectedSubtitlePathChange(null);
        return null;
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message || 'Unable to load NAS videos.' : 'Unable to load NAS videos.';
      setLoadError(message);
    } finally {
      setIsLoading(false);
    }
  }, [
    baseDir,
    onBaseDirChange,
    onSelectedSubtitlePathChange,
    onSelectedVideoPathChange,
    onStatusMessageChange,
    prefillParameters,
    selectedSubtitlePathRef,
    selectedVideoPathRef
  ]);

  const deleteVideo = useCallback(
    async (video: YoutubeNasVideo): Promise<string | null | undefined> => {
      if (video.linked_job_ids && video.linked_job_ids.length > 0) {
        return;
      }
      const targetFolder = video.folder || video.path;
      const confirmed = window.confirm(
        `Delete the folder "${targetFolder}" and all dubbed outputs/subtitles inside it? This will remove the downloaded video and any generated artifacts.`
      );
      if (!confirmed) {
        return;
      }
      setDeletingVideoPath(video.path);
      setLoadError(null);
      try {
        await deleteYoutubeVideo({ video_path: video.path });
        let nextSelectedPath = selectedVideoPath;
        let nextSubtitle = selectedSubtitlePath;
        let fallbackLanguage: string | null = null;
        if (library) {
          const selection = resolveSelectionAfterVideoDelete({
            videos: library.videos,
            deletedVideoPath: video.path,
            selectedVideoPath: nextSelectedPath,
            selectedSubtitlePath: nextSubtitle,
          });
          nextSelectedPath = selection.selectedVideoPath;
          nextSubtitle = selection.selectedSubtitlePath;
          fallbackLanguage = selection.fallbackLanguage;
          setLibrary({ ...library, videos: selection.videos });
        }
        onSelectedVideoPathChange(nextSelectedPath);
        onSelectedSubtitlePathChange(nextSubtitle);
        return fallbackLanguage;
      } catch (error) {
        const message =
          error instanceof Error ? error.message || 'Unable to delete video.' : 'Unable to delete video.';
        setLoadError(message);
      } finally {
        setDeletingVideoPath(null);
      }
    },
    [
      library,
      onSelectedSubtitlePathChange,
      onSelectedVideoPathChange,
      selectedSubtitlePath,
      selectedVideoPath
    ]
  );

  return {
    library,
    isLoading,
    loadError,
    deletingVideoPath,
    refreshLibrary,
    deleteVideo
  };
}
