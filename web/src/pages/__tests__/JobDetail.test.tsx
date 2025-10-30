import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import JobDetail from '../JobDetail';
import type { PipelineMediaResponse, ProgressEventPayload } from '../../api/dtos';

const fetchLiveJobMediaMock = vi.hoisted(() => vi.fn<[], Promise<PipelineMediaResponse>>());
const subscribeToJobEventsMock = vi.hoisted(() => vi.fn());
const resolveStorageMock = vi.hoisted(() => vi.fn<[string | null | undefined, string | null | undefined], string>());

vi.mock('../../api/client', () => ({
  fetchLiveJobMedia: fetchLiveJobMediaMock,
}));

vi.mock('../../services/api', () => ({
  subscribeToJobEvents: subscribeToJobEventsMock,
}));

vi.mock('../../utils/storageResolver', async () => {
  const actual = await vi.importActual<typeof import('../../utils/storageResolver')>(
    '../../utils/storageResolver',
  );
  return {
    ...actual,
    resolve: resolveStorageMock,
  };
});

describe('JobDetail', () => {
  let playSpy: ReturnType<typeof vi.spyOn>;
  let fetchMock: ReturnType<typeof vi.fn>;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    playSpy = vi.spyOn(window.HTMLMediaElement.prototype, 'play').mockImplementation(() => Promise.resolve());
    fetchMock = vi
      .fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValue({
        ok: true,
        status: 200,
        text: () => Promise.resolve('<html><body><p>Preview</p></body></html>'),
      } as Response);
    globalThis.fetch = fetchMock as unknown as typeof fetch;
    fetchLiveJobMediaMock.mockReset();
    subscribeToJobEventsMock.mockReset();
    resolveStorageMock.mockReset();
  });

  afterEach(() => {
    playSpy.mockRestore();
    if (originalFetch) {
      globalThis.fetch = originalFetch;
    } else {
      // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
      delete (globalThis as typeof globalThis & { fetch?: typeof fetch }).fetch;
    }
  });

  it('renders fetched media and updates tab counts when live media arrives', async () => {
    fetchLiveJobMediaMock.mockResolvedValue({
      media: {
        html: [
          {
            name: '001-010_output.html',
            url: 'https://storage.example/jobs/job-1/001-010_output.html',
            source: 'live',
          },
        ],
      },
    });

    const listeners: Array<(event: ProgressEventPayload) => void> = [];
    subscribeToJobEventsMock.mockImplementation(
      (_jobId: string, options: { onEvent?: (event: ProgressEventPayload) => void }) => {
        if (options?.onEvent) {
          listeners.push(options.onEvent);
        }
        return () => {};
      },
    );

    resolveStorageMock.mockImplementation((jobId, path) => `https://storage.example/${jobId}/${path}`);

    render(<JobDetail jobId="job-1" />);

    await act(async () => {
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText(/Selected media: 001-010_output\.html/i)).toBeInTheDocument();
    });

    expect(screen.getByRole('tab', { name: /Text \(1\)/i })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tab', { name: /Audio \(0\)/i })).toBeInTheDocument();

    const payload: ProgressEventPayload = {
      event_type: 'file_chunk_generated',
      timestamp: Date.now(),
      metadata: {
        generated_files: {
          files: [
            {
              type: 'audio',
              path: 'audio/001-010_output.mp3',
              name: '001-010_output.mp3',
              source: 'live',
            },
          ],
        },
      },
      snapshot: { completed: 1, total: null, elapsed: 0, speed: 0, eta: null },
      error: null,
    };

    expect(listeners).toHaveLength(1);

    await act(async () => {
      listeners[0](payload);
    });

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /Audio \(1\)/i })).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole('tab', { name: /Audio \(1\)/i }));

    await waitFor(() => {
      expect(screen.getByTestId('audio-player')).toBeInTheDocument();
    });

    expect(screen.getByText(/Selected media: 001-010_output\.mp3/i)).toBeInTheDocument();
  });

  it('defaults to populated media tab and shows empty messages for empty categories', async () => {
    fetchLiveJobMediaMock.mockResolvedValue({
      media: {
        audio: [
          {
            name: 'Intro.mp3',
            url: 'https://storage.example/jobs/job-2/intro.mp3',
            source: 'live',
          },
        ],
      },
    });

    subscribeToJobEventsMock.mockReturnValue(() => {});

    render(<JobDetail jobId="job-2" />);

    await act(async () => {
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(screen.getByTestId('audio-player')).toBeInTheDocument();
    });

    expect(fetchMock).not.toHaveBeenCalled();

    expect(screen.getByRole('tab', { name: /Audio \(1\)/i })).toHaveAttribute('aria-selected', 'true');

    const user = userEvent.setup();
    await user.click(screen.getByRole('tab', { name: /Text \(0\)/i }));

    expect(screen.getByText('No text media yet.')).toBeInTheDocument();
  });
});
