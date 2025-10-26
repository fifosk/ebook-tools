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
            url: null,
            relative_path: 'html/001-010_output.html',
            path: '/var/tmp/jobs/job-1/html/001-010_output.html',
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
      url: 'https://storage.example/job-1/html/001-010_output.html',
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

    expect(resolveStorageMock).toHaveBeenCalledWith('job-1', 'html/001-010_output.html');
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

  it('updates state when progress events include generated files', async () => {
    fetchLiveJobMediaMock.mockResolvedValue({ media: {} });

    const listeners: Array<(event: ProgressEventPayload) => void> = [];
    subscribeToJobEventsMock.mockImplementation((_jobId: string, options: { onEvent?: (event: ProgressEventPayload) => void }) => {
      if (options?.onEvent) {
        listeners.push(options.onEvent);
      }
      return () => {};
    });

    resolveStorageMock.mockImplementation((jobId, fileName) => `https://storage.example/${jobId}/${fileName}`);

    const { result } = renderHook(() => useLiveMedia('job-2'));

    await waitFor(() => {
      expect(result.current.media.text).toHaveLength(0);
    });

    const payload: ProgressEventPayload = {
      event_type: 'progress',
      timestamp: Date.now(),
      metadata: {
        generated_files: {
          files: [
            {
              type: 'html',
              path: '/var/tmp/jobs/job-2/html/001-010_output.html'
            }
          ]
        }
      },
      snapshot: { completed: 1, total: null, elapsed: 0, speed: 0, eta: null },
      error: null
    };

    await act(async () => {
      listeners[0](payload);
    });

    await waitFor(() => {
      expect(result.current.media.text).toHaveLength(1);
    });

    expect(result.current.media.text[0]).toMatchObject({
      name: '001-010_output.html',
      url: 'https://storage.example/job-2/html/001-010_output.html',
      source: 'live',
      type: 'text'
    });
  });

  it('extracts generated files nested within metadata containers', async () => {
    fetchLiveJobMediaMock.mockResolvedValue({ media: {} });

    const listeners: Array<(event: ProgressEventPayload) => void> = [];
    subscribeToJobEventsMock.mockImplementation(
      (_jobId: string, options: { onEvent?: (event: ProgressEventPayload) => void }) => {
        if (options?.onEvent) {
          listeners.push(options.onEvent);
        }
        return () => {};
      }
    );

    resolveStorageMock.mockImplementation((jobId, fileName) => `https://storage.example/${jobId}/${fileName}`);

    const { result } = renderHook(() => useLiveMedia('job-3'));

    await waitFor(() => {
      expect(result.current.media.audio).toHaveLength(0);
    });

    const payload: ProgressEventPayload = {
      event_type: 'progress',
      timestamp: Date.now(),
      metadata: {
        stage: 'deferred_write',
        payload: {
          generated_files: {
            files: [
              {
                type: 'audio',
                path: '/var/tmp/jobs/job-3/audio/001-010_output.mp3'
              }
            ]
          }
        }
      },
      snapshot: { completed: 2, total: null, elapsed: 0, speed: 0, eta: null },
      error: null
    };

    await act(async () => {
      listeners[0](payload);
    });

    await waitFor(() => {
      expect(result.current.media.audio).toHaveLength(1);
    });

    expect(result.current.media.audio[0]).toMatchObject({
      name: '001-010_output.mp3',
      url: 'https://storage.example/job-3/audio/001-010_output.mp3',
      type: 'audio'
    });
  });

  it('derives media entries from chunk snapshots when file index is empty', async () => {
    fetchLiveJobMediaMock.mockResolvedValue({ media: {} });

    const listeners: Array<(event: ProgressEventPayload) => void> = [];
    subscribeToJobEventsMock.mockImplementation(
      (_jobId: string, options: { onEvent?: (event: ProgressEventPayload) => void }) => {
        if (options?.onEvent) {
          listeners.push(options.onEvent);
        }
        return () => {};
      }
    );

    resolveStorageMock.mockImplementation((jobId, fileName) => `https://storage.example/${jobId}/${fileName}`);

    const { result } = renderHook(() => useLiveMedia('job-4'));

    await waitFor(() => {
      expect(result.current.media.text).toHaveLength(0);
    });

    const payload: ProgressEventPayload = {
      event_type: 'file_chunk_generated',
      timestamp: Date.now(),
      metadata: {
        generated_files: {
          chunks: [
            {
              chunk_id: 'chunk-1',
              range_fragment: '0001-0002',
              files: [
                {
                  type: 'html',
                  path: '/var/tmp/jobs/job-4/html/0001-0002_output.html'
                }
              ]
            }
          ],
          files: []
        }
      },
      snapshot: { completed: 2, total: null, elapsed: 0, speed: 0, eta: null },
      error: null
    };

    await act(async () => {
      listeners[0](payload);
    });

    await waitFor(() => {
      expect(result.current.media.text).toHaveLength(1);
    });

    expect(result.current.media.text[0]).toMatchObject({
      name: '0001-0002_output.html',
      url: 'https://storage.example/job-4/html/0001-0002_output.html',
      type: 'text'
    });
  });

  it('parses JSON encoded metadata when extracting generated files', async () => {
    fetchLiveJobMediaMock.mockResolvedValue({ media: {} });

    const listeners: Array<(event: ProgressEventPayload) => void> = [];
    subscribeToJobEventsMock.mockImplementation(
      (_jobId: string, options: { onEvent?: (event: ProgressEventPayload) => void }) => {
        if (options?.onEvent) {
          listeners.push(options.onEvent);
        }
        return () => {};
      }
    );

    resolveStorageMock.mockImplementation((jobId, fileName) => `https://storage.example/${jobId}/${fileName}`);

    const { result } = renderHook(() => useLiveMedia('job-4-json'));

    await waitFor(() => {
      expect(result.current.media.text).toHaveLength(0);
    });

    const payload: ProgressEventPayload = {
      event_type: 'progress',
      timestamp: Date.now(),
      metadata: JSON.stringify({
        generated_files: {
          files: [
            {
              type: 'html',
              path: '/var/tmp/jobs/job-4-json/html/0003-0004_output.html'
            }
          ]
        }
      }) as unknown as Record<string, unknown>,
      snapshot: { completed: 3, total: null, elapsed: 0, speed: 0, eta: null },
      error: null
    };

    await act(async () => {
      listeners[0](payload);
    });

    await waitFor(() => {
      expect(result.current.media.text).toHaveLength(1);
    });

    expect(result.current.media.text[0]).toMatchObject({
      name: '0003-0004_output.html',
      url: 'https://storage.example/job-4-json/html/0003-0004_output.html',
      type: 'text'
    });
  });

  it('infers media categories when snapshot entries lack explicit type fields', async () => {
    fetchLiveJobMediaMock.mockResolvedValue({ media: {} });

    const listeners: Array<(event: ProgressEventPayload) => void> = [];
    subscribeToJobEventsMock.mockImplementation(
      (_jobId: string, options: { onEvent?: (event: ProgressEventPayload) => void }) => {
        if (options?.onEvent) {
          listeners.push(options.onEvent);
        }
        return () => {};
      }
    );

    resolveStorageMock.mockImplementation((jobId, fileName) => `https://storage.example/${jobId}/${fileName}`);

    const { result } = renderHook(() => useLiveMedia('job-9'));

    await waitFor(() => {
      expect(result.current.media.text).toHaveLength(0);
    });

    const payload: ProgressEventPayload = {
      event_type: 'progress',
      timestamp: Date.now(),
      metadata: {
        generated_files: {
          text: [
            {
              path: '/var/tmp/jobs/job-9/html/001-010_output.html'
            }
          ],
          audio_files: [
            {
              relative_path: 'audio/001-010_output.m4a'
            }
          ],
          nested: {
            media: {
              video: [
                {
                  path: '/var/tmp/jobs/job-9/video/001-010_output.mp4'
                }
              ]
            }
          }
        }
      },
      snapshot: { completed: 3, total: null, elapsed: 0, speed: 0, eta: null },
      error: null
    };

    await act(async () => {
      listeners[0](payload);
    });

    await waitFor(() => {
      expect(result.current.media.text).toHaveLength(1);
      expect(result.current.media.audio).toHaveLength(1);
      expect(result.current.media.video).toHaveLength(1);
    });

    expect(result.current.media.text[0]).toMatchObject({
      name: '001-010_output.html',
      url: 'https://storage.example/job-9/html/001-010_output.html',
      type: 'text'
    });

    expect(result.current.media.audio[0]).toMatchObject({
      name: '001-010_output.m4a',
      url: 'https://storage.example/job-9/audio/001-010_output.m4a',
      type: 'audio'
    });

    expect(result.current.media.video[0]).toMatchObject({
      name: '001-010_output.mp4',
      url: 'https://storage.example/job-9/video/001-010_output.mp4',
      type: 'video'
    });
  });

  it('falls back to refreshing media when generated file snapshot cannot be normalised', async () => {
    fetchLiveJobMediaMock.mockResolvedValueOnce({ media: {} });
    fetchLiveJobMediaMock.mockResolvedValueOnce({
      media: {
        html: [
          {
            name: null,
            relative_path: 'html/0005-0010_output.html',
            path: '/var/tmp/jobs/job-5/html/0005-0010_output.html',
            source: 'live'
          }
        ]
      }
    });

    const listeners: Array<(event: ProgressEventPayload) => void> = [];
    subscribeToJobEventsMock.mockImplementation(
      (_jobId: string, options: { onEvent?: (event: ProgressEventPayload) => void }) => {
        if (options?.onEvent) {
          listeners.push(options.onEvent);
        }
        return () => {};
      }
    );

    resolveStorageMock.mockImplementation((jobId, fileName) => `https://storage.example/${jobId}/${fileName}`);

    const { result } = renderHook(() => useLiveMedia('job-5'));

    await waitFor(() => {
      expect(result.current.media.text).toHaveLength(0);
    });

    const payload: ProgressEventPayload = {
      event_type: 'progress',
      timestamp: Date.now(),
      metadata: {
        generated_files: {
          files: [
            {
              type: 'html'
            }
          ]
        }
      },
      snapshot: { completed: 5, total: null, elapsed: 0, speed: 0, eta: null },
      error: null
    };

    await act(async () => {
      listeners[0](payload);
    });

    await waitFor(() => {
      expect(fetchLiveJobMediaMock).toHaveBeenCalledTimes(2);
      expect(result.current.media.text).toHaveLength(1);
    });

    expect(result.current.media.text[0]).toMatchObject({
      name: '0005-0010_output.html',
      url: 'https://storage.example/job-5/html/0005-0010_output.html',
      source: 'live',
      type: 'text'
    });
  });

  it('refreshes media when deferred write stage metadata uses different casing', async () => {
    fetchLiveJobMediaMock
      .mockResolvedValueOnce({ media: {} })
      .mockResolvedValueOnce({
        media: {
          html: [
            {
              name: '0011-0012_output.html',
              relative_path: 'html/0011-0012_output.html',
              path: '/var/tmp/jobs/job-6/html/0011-0012_output.html',
              source: 'live'
            }
          ]
        }
      });

    const listeners: Array<(event: ProgressEventPayload) => void> = [];
    subscribeToJobEventsMock.mockImplementation(
      (_jobId: string, options: { onEvent?: (event: ProgressEventPayload) => void }) => {
        if (options?.onEvent) {
          listeners.push(options.onEvent);
        }
        return () => {};
      }
    );

    resolveStorageMock.mockImplementation((jobId, fileName) => `https://storage.example/${jobId}/${fileName}`);

    const { result } = renderHook(() => useLiveMedia('job-6'));

    await waitFor(() => {
      expect(result.current.media.text).toHaveLength(0);
    });

    const payload: ProgressEventPayload = {
      event_type: 'progress',
      timestamp: Date.now(),
      metadata: {
        stage: 'DeferredWrite'
      },
      snapshot: { completed: 6, total: null, elapsed: 0, speed: 0, eta: null },
      error: null
    };

    await act(async () => {
      listeners[0](payload);
    });

    await waitFor(() => {
      expect(fetchLiveJobMediaMock).toHaveBeenCalledTimes(2);
      expect(result.current.media.text).toHaveLength(1);
    });

    expect(result.current.media.text[0]).toMatchObject({
      name: '0011-0012_output.html',
      url: 'https://storage.example/job-6/html/0011-0012_output.html',
      type: 'text'
    });
  });
});
