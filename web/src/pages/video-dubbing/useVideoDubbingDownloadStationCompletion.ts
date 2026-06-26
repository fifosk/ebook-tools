import { useCallback } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import type { AcquisitionJobStatusResponse } from '../../api/dtos';
import {
  findDownloadStationCompletedVideo,
  resolveDefaultSubtitle,
  resolveDownloadStationCompletedFiles
} from './videoDubbingUtils';
import type { VideoDubbingLibraryRefreshResult } from './useVideoDubbingLibraryState';

type DownloadStationCompletionResult = {
  selectedVideoFilename?: string | null;
};

type VideoDubbingDownloadStationCompletionOptions = {
  refreshLibraryWithSelection: (
    options?: { clearStatusMessage?: boolean }
  ) => Promise<VideoDubbingLibraryRefreshResult>;
  onSelectedVideoPathChange: (path: string | null) => void;
  onSelectedSubtitlePathChange: (path: string | null) => void;
  onTargetLanguageEnsure: (language?: string | null) => void;
  onSelectedVideoDiscoveryTemplateStateChange: Dispatch<SetStateAction<Record<string, unknown> | null>>;
};

export function useVideoDubbingDownloadStationCompletion({
  refreshLibraryWithSelection,
  onSelectedVideoPathChange,
  onSelectedSubtitlePathChange,
  onTargetLanguageEnsure,
  onSelectedVideoDiscoveryTemplateStateChange
}: VideoDubbingDownloadStationCompletionOptions) {
  return useCallback(async (
    job: AcquisitionJobStatusResponse
  ): Promise<DownloadStationCompletionResult | null> => {
    const completedFiles = resolveDownloadStationCompletedFiles(job);
    if (completedFiles.length === 0) {
      return null;
    }
    const refreshed = await refreshLibraryWithSelection({ clearStatusMessage: false });
    const completedVideo = findDownloadStationCompletedVideo(
      refreshed.library?.videos ?? [],
      completedFiles
    );
    if (!completedVideo) {
      return null;
    }
    const defaultSubtitle = resolveDefaultSubtitle(completedVideo);
    onSelectedVideoPathChange(completedVideo.path);
    onSelectedSubtitlePathChange(defaultSubtitle?.path ?? null);
    onTargetLanguageEnsure(defaultSubtitle?.language);
    onSelectedVideoDiscoveryTemplateStateChange((current) =>
      current
        ? {
            ...current,
            selected_video_path: completedVideo.path,
            selected_subtitle_path: defaultSubtitle?.path ?? null
          }
        : current
    );
    return {
      selectedVideoFilename: completedVideo.filename || completedVideo.path
    };
  }, [
    onSelectedSubtitlePathChange,
    onSelectedVideoDiscoveryTemplateStateChange,
    onSelectedVideoPathChange,
    onTargetLanguageEnsure,
    refreshLibraryWithSelection
  ]);
}
