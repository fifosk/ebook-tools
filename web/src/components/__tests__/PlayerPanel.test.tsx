import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import PlayerPanel from '../PlayerPanel';
import type { LiveMediaState } from '../../hooks/useLiveMedia';

function createMediaState(overrides: Partial<LiveMediaState>): LiveMediaState {
  return {
    text: [],
    audio: [],
    video: [],
    ...overrides,
  } as LiveMediaState;
}

describe('PlayerPanel', () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    if (originalFetch) {
      globalThis.fetch = originalFetch;
    } else {
      // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
      delete (globalThis as typeof globalThis & { fetch?: typeof fetch }).fetch;
    }
    vi.restoreAllMocks();
  });

  it('loads text previews and updates when selecting items from the list', async () => {
    const fetchMock = vi
      .fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        text: () =>
          Promise.resolve(
            '<html><body><h1>Chapter One</h1><p>Hello <strong>world</strong>.</p></body></html>',
          ),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        text: () => Promise.resolve('<html><body><p>Second chapter content.</p></body></html>'),
      } as Response);

    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const media = createMediaState({
      text: [
        {
          type: 'text',
          name: 'chapter-one.html',
          url: 'https://example.com/text/chapter-one.html',
          source: 'live',
        },
        {
          type: 'text',
          name: 'chapter-two.html',
          url: 'https://example.com/text/chapter-two.html',
          source: 'live',
        },
      ],
    });

    const user = userEvent.setup();

    render(<PlayerPanel jobId="job-42" media={media} isLoading={false} error={null} />);

    await act(async () => {
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('https://example.com/text/chapter-one.html', {
        credentials: 'include',
      });
    });

    await waitFor(() => {
      expect(screen.getByTestId('player-panel-document')).toHaveTextContent('Chapter One');
      expect(screen.getByTestId('player-panel-document')).toHaveTextContent('Hello world.');
    });

    const toggleButton = screen.getByRole('button', { name: /show detailed file list/i });
    await user.click(toggleButton);

    const list = screen.getByTestId('media-list-text');
    const secondEntry = within(list).getByText('chapter-two.html');
    const rowButton = secondEntry.closest('button');
    expect(rowButton).not.toBeNull();
    if (rowButton) {
      await user.click(rowButton);
    }

    await waitFor(() => {
      expect(fetchMock).toHaveBeenLastCalledWith('https://example.com/text/chapter-two.html', {
        credentials: 'include',
      });
    });

    await waitFor(() => {
      expect(screen.getByTestId('player-panel-document')).toHaveTextContent('Second chapter content.');
      expect(screen.getByText('Selected media: chapter-two.html')).toBeInTheDocument();
    });
  });
});
