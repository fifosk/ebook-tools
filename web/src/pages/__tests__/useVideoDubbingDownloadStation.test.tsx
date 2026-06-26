import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  createAcquisitionJob,
  fetchAcquisitionJobStatus
} from '../../api/client';
import type {
  AcquisitionCandidate,
  AcquisitionJobStatusResponse
} from '../../api/dtos';
import { useVideoDubbingDownloadStation } from '../video-dubbing/useVideoDubbingDownloadStation';

vi.mock('../../api/client', () => ({
  createAcquisitionJob: vi.fn(),
  fetchAcquisitionJobStatus: vi.fn()
}));

const mockCreateAcquisitionJob = vi.mocked(createAcquisitionJob);
const mockFetchAcquisitionJobStatus = vi.mocked(fetchAcquisitionJobStatus);

function candidate(overrides: Partial<AcquisitionCandidate> = {}): AcquisitionCandidate {
  return {
    candidate_id: 'candidate-1',
    provider: 'newznab_torznab',
    media_kind: 'video',
    title: 'Episode result',
    rights: 'unknown',
    capabilities: ['acquire'],
    candidate_token: 'candidate-token',
    contributors: [],
    subtitles: [],
    metadata: {},
    requires_confirmation: true,
    policy_notes: [],
    ...overrides
  };
}

function job(overrides: Partial<AcquisitionJobStatusResponse> = {}): AcquisitionJobStatusResponse {
  return {
    provider: 'download_station',
    task_id: 'task-1',
    status: 'running',
    progress: null,
    message: null,
    external_task_id: null,
    raw_status: null,
    started_at: null,
    updated_at: '2026-06-26T12:00:00Z',
    completed_files: [],
    next_actions: [],
    metadata: {},
    ...overrides
  };
}

function renderDownloadStationHook(
  overrides: Partial<Parameters<typeof useVideoDubbingDownloadStation>[0]> = {}
) {
  const onStatusMessageChange = vi.fn();
  const onClearSelectedDiscoveryTemplate = vi.fn();
  const result = renderHook((props: Parameters<typeof useVideoDubbingDownloadStation>[0]) =>
    useVideoDubbingDownloadStation(props),
    {
      initialProps: {
        isDownloadStationAvailable: true,
        downloadStationUnavailableMessage: null,
        onStatusMessageChange,
        onClearSelectedDiscoveryTemplate,
        ...overrides
      }
    }
  );

  return {
    ...result,
    onStatusMessageChange,
    onClearSelectedDiscoveryTemplate
  };
}

describe('useVideoDubbingDownloadStation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('clears an indexer candidate and saved template when a manual source is typed', () => {
    const { result, onClearSelectedDiscoveryTemplate } = renderDownloadStationHook();

    act(() => {
      result.current.setDownloadStationCandidate(candidate());
    });
    act(() => {
      result.current.handleDownloadStationSourceUriChange(' magnet:?xt=urn:btih:123 ');
    });

    expect(result.current.downloadStationSourceUri).toBe(' magnet:?xt=urn:btih:123 ');
    expect(result.current.downloadStationCandidate).toBeNull();
    expect(onClearSelectedDiscoveryTemplate).toHaveBeenCalledTimes(1);
  });

  it('validates a missing reviewed source before creating a downloader task', async () => {
    const { result } = renderDownloadStationHook();

    await act(async () => {
      await result.current.submitDownloadStation();
    });

    expect(result.current.downloadStationError).toBe('Enter a reviewed URL or magnet link.');
    expect(mockCreateAcquisitionJob).not.toHaveBeenCalled();
  });

  it('reports provider unavailability before creating a downloader task', async () => {
    const { result } = renderDownloadStationHook({
      isDownloadStationAvailable: false,
      downloadStationUnavailableMessage: 'Download Station needs backend credentials.'
    });

    act(() => {
      result.current.handleDownloadStationSourceUriChange('https://example.test/video');
      result.current.setDownloadStationConfirmed(true);
    });
    await act(async () => {
      await result.current.submitDownloadStation();
    });

    expect(result.current.downloadStationError).toBe('Download Station needs backend credentials.');
    expect(mockCreateAcquisitionJob).not.toHaveBeenCalled();
  });

  it('submits a trimmed manual source and destination to Download Station', async () => {
    mockCreateAcquisitionJob.mockResolvedValueOnce(job({ message: 'Task submitted.' }));
    const { result, onStatusMessageChange } = renderDownloadStationHook();

    act(() => {
      result.current.handleDownloadStationSourceUriChange(' https://example.test/video ');
      result.current.setDownloadStationDestination(' /downloads/series ');
      result.current.setDownloadStationConfirmed(true);
    });
    await act(async () => {
      await result.current.submitDownloadStation();
    });

    expect(mockCreateAcquisitionJob).toHaveBeenCalledWith({
      provider: 'download_station',
      source_uri: 'https://example.test/video',
      candidate_token: null,
      confirmed: true,
      destination: '/downloads/series'
    });
    expect(result.current.downloadStationJob?.task_id).toBe('task-1');
    expect(onStatusMessageChange).toHaveBeenCalledWith('Task submitted.');
  });

  it('submits an indexer candidate token without a manual source URL', async () => {
    mockCreateAcquisitionJob.mockResolvedValueOnce(job());
    const { result } = renderDownloadStationHook();

    act(() => {
      result.current.setDownloadStationCandidate(candidate({ candidate_token: ' token-from-indexer ' }));
      result.current.setDownloadStationConfirmed(true);
    });
    await act(async () => {
      await result.current.submitDownloadStation();
    });

    expect(mockCreateAcquisitionJob).toHaveBeenCalledWith(expect.objectContaining({
      source_uri: null,
      candidate_token: 'token-from-indexer'
    }));
  });

  it('polls the active Download Station task and surfaces completion', async () => {
    mockCreateAcquisitionJob.mockResolvedValueOnce(job());
    mockFetchAcquisitionJobStatus.mockResolvedValueOnce(job({
      status: 'completed',
      metadata: { completed_files: ['/downloads/Demo.mkv'] }
    }));
    const { result, onStatusMessageChange } = renderDownloadStationHook();

    act(() => {
      result.current.handleDownloadStationSourceUriChange('https://example.test/video');
      result.current.setDownloadStationConfirmed(true);
    });
    await act(async () => {
      await result.current.submitDownloadStation();
    });
    await act(async () => {
      await result.current.pollDownloadStation();
    });

    expect(mockFetchAcquisitionJobStatus).toHaveBeenCalledWith('task-1', 'download_station');
    expect(onStatusMessageChange).toHaveBeenLastCalledWith(
      'Download Station task completed. Completed: Demo.mkv. Refresh manual downloads to select the file.'
    );
  });

  it('reports refreshed manual-download selection after a completed task', async () => {
    mockCreateAcquisitionJob.mockResolvedValueOnce(job());
    mockFetchAcquisitionJobStatus.mockResolvedValueOnce(job({
      status: 'completed',
      completed_files: ['/downloads/Demo.mkv']
    }));
    const onDownloadStationCompleted = vi.fn().mockResolvedValue({
      selectedVideoFilename: 'Demo.mkv'
    });
    const { result, onStatusMessageChange } = renderDownloadStationHook({
      onDownloadStationCompleted
    });

    act(() => {
      result.current.handleDownloadStationSourceUriChange('https://example.test/video');
      result.current.setDownloadStationConfirmed(true);
    });
    await act(async () => {
      await result.current.submitDownloadStation();
    });
    await act(async () => {
      await result.current.pollDownloadStation();
    });

    expect(onDownloadStationCompleted).toHaveBeenCalledWith(expect.objectContaining({
      status: 'completed',
      completed_files: ['/downloads/Demo.mkv']
    }));
    expect(onStatusMessageChange).toHaveBeenLastCalledWith(
      'Download Station task completed. Completed: Demo.mkv. Selected Demo.mkv from refreshed manual downloads.'
    );
  });
});
