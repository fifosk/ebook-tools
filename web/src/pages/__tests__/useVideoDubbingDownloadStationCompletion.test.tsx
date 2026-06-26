import { renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type {
  AcquisitionJobStatusResponse,
  YoutubeNasSubtitle,
  YoutubeNasVideo
} from '../../api/dtos';
import { useVideoDubbingDownloadStationCompletion } from '../video-dubbing/useVideoDubbingDownloadStationCompletion';

const englishSubtitle: YoutubeNasSubtitle = {
  path: '/media/Demo/Demo.en.srt',
  filename: 'Demo.en.srt',
  language: 'en',
  format: 'srt'
};

const video: YoutubeNasVideo = {
  path: '/media/Demo/Demo.mkv',
  filename: 'Demo.mkv',
  folder: '/media/Demo',
  size_bytes: 1024,
  modified_at: '2026-06-26T12:00:00Z',
  subtitles: [englishSubtitle]
};

function job(overrides: Partial<AcquisitionJobStatusResponse> = {}): AcquisitionJobStatusResponse {
  return {
    provider: 'download_station',
    task_id: 'task-1',
    status: 'completed',
    progress: 1,
    message: null,
    external_task_id: null,
    raw_status: 'finished',
    started_at: null,
    updated_at: '2026-06-26T12:00:00Z',
    completed_files: ['/downloads/Demo.mkv'],
    next_actions: ['discover_manual_downloads'],
    metadata: {},
    ...overrides
  };
}

function renderCompletionHook(
  overrides: Partial<Parameters<typeof useVideoDubbingDownloadStationCompletion>[0]> = {}
) {
  let templateState: Record<string, unknown> | null = { provider: 'newznab_torznab' };
  const onSelectedVideoDiscoveryTemplateStateChange = vi.fn((next) => {
    templateState = typeof next === 'function' ? next(templateState) : next;
  });
  const props: Parameters<typeof useVideoDubbingDownloadStationCompletion>[0] = {
    refreshLibraryWithSelection: vi.fn().mockResolvedValue({
      library: { base_dir: '/media', videos: [video] },
      selection: {
        video,
        subtitle: englishSubtitle,
        videoPath: video.path,
        subtitlePath: englishSubtitle.path
      },
      language: 'en'
    }),
    onSelectedVideoPathChange: vi.fn(),
    onSelectedSubtitlePathChange: vi.fn(),
    onTargetLanguageEnsure: vi.fn(),
    onSelectedVideoDiscoveryTemplateStateChange,
    ...overrides
  };
  const result = renderHook((hookProps: Parameters<typeof useVideoDubbingDownloadStationCompletion>[0]) =>
    useVideoDubbingDownloadStationCompletion(hookProps),
    { initialProps: props }
  );
  return {
    ...result,
    props,
    get templateState() {
      return templateState;
    }
  };
}

describe('useVideoDubbingDownloadStationCompletion', () => {
  it('refreshes manual downloads and selects a matched completed video', async () => {
    const hook = renderCompletionHook();

    const result = await hook.result.current(job());

    expect(hook.props.refreshLibraryWithSelection).toHaveBeenCalledWith({ clearStatusMessage: false });
    expect(hook.props.onSelectedVideoPathChange).toHaveBeenCalledWith(video.path);
    expect(hook.props.onSelectedSubtitlePathChange).toHaveBeenCalledWith(englishSubtitle.path);
    expect(hook.props.onTargetLanguageEnsure).toHaveBeenCalledWith('en');
    expect(hook.templateState).toEqual({
      provider: 'newznab_torznab',
      selected_video_path: video.path,
      selected_subtitle_path: englishSubtitle.path
    });
    expect(result).toEqual({ selectedVideoFilename: 'Demo.mkv' });
  });

  it('does not refresh when a completed task has no file hints', async () => {
    const hook = renderCompletionHook();

    const result = await hook.result.current(job({ completed_files: [], metadata: {} }));

    expect(hook.props.refreshLibraryWithSelection).not.toHaveBeenCalled();
    expect(hook.props.onSelectedVideoPathChange).not.toHaveBeenCalled();
    expect(result).toBeNull();
  });

  it('keeps selection unchanged when refreshed videos do not match completed files', async () => {
    const hook = renderCompletionHook({
      refreshLibraryWithSelection: vi.fn().mockResolvedValue({
        library: { base_dir: '/media', videos: [video] },
        selection: {
          video,
          subtitle: englishSubtitle,
          videoPath: video.path,
          subtitlePath: englishSubtitle.path
        },
        language: 'en'
      })
    });

    const result = await hook.result.current(job({ completed_files: ['/downloads/Other.mkv'] }));

    expect(hook.props.refreshLibraryWithSelection).toHaveBeenCalledWith({ clearStatusMessage: false });
    expect(hook.props.onSelectedVideoPathChange).not.toHaveBeenCalled();
    expect(hook.props.onSelectedSubtitlePathChange).not.toHaveBeenCalled();
    expect(result).toBeNull();
  });
});
