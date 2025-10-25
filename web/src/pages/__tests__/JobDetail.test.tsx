import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
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
  beforeEach(() => {
    fetchLiveJobMediaMock.mockReset();
    subscribeToJobEventsMock.mockReset();
    resolveStorageMock.mockReset();
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

    await waitFor(() => {
      expect(screen.getByText('001-010_output.html')).toBeInTheDocument();
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

    const audioList = screen.getByTestId('media-list-audio');
    expect(within(audioList).getByText('001-010_output.mp3')).toBeInTheDocument();
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

    await waitFor(() => {
      expect(screen.getByTestId('audio-player')).toBeInTheDocument();
    });

    expect(screen.getByRole('tab', { name: /Audio \(1\)/i })).toHaveAttribute('aria-selected', 'true');

    const user = userEvent.setup();
    await user.click(screen.getByRole('tab', { name: /Text \(0\)/i }));

    expect(screen.getByTestId('media-list-text')).toHaveTextContent('No text media yet.');
  });
});
