import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useLiveMedia } from '../useLiveMedia';
import { PipelineMediaResponse, ProgressEventPayload } from '../../api/dtos';

const fetchLiveJobMediaMock = vi.hoisted(() => vi.fn<[], Promise<PipelineMediaResponse>>());
const subscribeToJobEventsMock = vi.hoisted(() => vi.fn());
const resolveStorageMock = vi.hoisted(() => vi.fn<[string | null | undefined, string | null | undefined], string>());

vi.mock('../../api/client', () => ({
  fetchLiveJobMedia: fetchLiveJobMediaMock
}));

vi.mock('../../services/api', () => ({
  subscribeToJobEvents: subscribeToJobEventsMock
}));

vi.mock('../../utils/storageResolver', async () => {
  const actual = await vi.importActual<typeof import('../../utils/storageResolver')>(
    '../../utils/storageResolver'
  );
  return {
    ...actual,
    resolve: resolveStorageMock
  };
});

describe('useLiveMedia', () => {
  beforeEach(() => {
    fetchLiveJobMediaMock.mockReset();
    subscribeToJobEventsMock.mockReset();
    resolveStorageMock.mockReset();
  });

  it('loads initial media and updates when file chunks are generated', async () => {
    fetchLiveJobMediaMock.mockResolvedValue({
      media: {
        html: [
          {
            name: '001-010_output.html',
            url: 'https://storage.example/jobs/job-1/001-010_output.html',
            source: 'live'
          }
        ]
      }
    });

    const listeners: Array<(event: ProgressEventPayload) => void> = [];
    subscribeToJobEventsMock.mockImplementation((_jobId: string, options: { onEvent?: (event: ProgressEventPayload) => void }) => {
      if (options?.onEvent) {
        listeners.push(options.onEvent);
      }
      return () => {};
    });

    resolveStorageMock.mockImplementation((jobId, fileName) =>
      `https://storage.example/${jobId}/${fileName}`
    );

    const { result } = renderHook(() => useLiveMedia('job-1'));

    await waitFor(() => {
      expect(result.current.media.text).toHaveLength(1);
    });

    expect(result.current.media.text[0]).toMatchObject({
      name: '001-010_output.html',
      url: 'https://storage.example/jobs/job-1/001-010_output.html',
      source: 'live',
      type: 'text'
    });

    expect(subscribeToJobEventsMock).toHaveBeenCalledWith('job-1', expect.objectContaining({ onEvent: expect.any(Function) }));

    const payload: ProgressEventPayload = {
      event_type: 'file_chunk_generated',
      timestamp: Date.now(),
      metadata: {
        generated_files: {
          files: [
            {
              type: 'audio',
              path: '/var/tmp/jobs/job-1/audio/001-010_output.mp3'
            }
          ]
        }
      },
      snapshot: { completed: 1, total: null, elapsed: 0, speed: 0, eta: null },
      error: null
    };

    expect(listeners).toHaveLength(1);

    await act(async () => {
      listeners[0](payload);
    });

    await waitFor(() => {
      expect(result.current.media.audio).toHaveLength(1);
    });

    expect(resolveStorageMock).toHaveBeenCalledWith('job-1', 'audio/001-010_output.mp3');
    expect(result.current.media.audio[0]).toMatchObject({
      name: '001-010_output.mp3',
      url: 'https://storage.example/job-1/audio/001-010_output.mp3',
      source: 'live',
      type: 'audio'
    });
  });

  it('does not update state for non media events', async () => {
    fetchLiveJobMediaMock.mockResolvedValue({ media: {} });

    const listeners: Array<(event: ProgressEventPayload) => void> = [];
    subscribeToJobEventsMock.mockImplementation((_jobId: string, options: { onEvent?: (event: ProgressEventPayload) => void }) => {
      if (options?.onEvent) {
        listeners.push(options.onEvent);
      }
      return () => {};
    });

    const { result } = renderHook(() => useLiveMedia('job-1'));

    await waitFor(() => {
      expect(result.current.media.text).toHaveLength(0);
    });

    await act(async () => {
      listeners[0]({
        event_type: 'progress',
        timestamp: Date.now(),
        metadata: {},
        snapshot: { completed: 0, total: null, elapsed: 0, speed: 0, eta: null },
        error: null
      });
    });

    expect(result.current.media).toEqual({ text: [], audio: [], video: [] });
  });
});
