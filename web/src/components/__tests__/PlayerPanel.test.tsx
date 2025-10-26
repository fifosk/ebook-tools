import { act, render, screen, waitFor } from '@testing-library/react';
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

    const firstButton = screen.getByRole('button', { name: /go to first item/i });
    const previousButton = screen.getByRole('button', { name: /go to previous item/i });
    const nextButton = screen.getByRole('button', { name: /go to next item/i });
    const lastButton = screen.getByRole('button', { name: /go to last item/i });

    expect(firstButton).toBeDisabled();
    expect(previousButton).toBeDisabled();
    expect(nextButton).not.toBeDisabled();
    expect(lastButton).not.toBeDisabled();

    await user.click(lastButton);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenLastCalledWith('https://example.com/text/chapter-two.html', {
        credentials: 'include',
      });
    });

    await waitFor(() => {
      expect(screen.getByTestId('player-panel-document')).toHaveTextContent('Second chapter content.');
      expect(screen.getByText('Selected media: chapter-two.html')).toBeInTheDocument();
    });

    expect(firstButton).not.toBeDisabled();
    expect(previousButton).not.toBeDisabled();
    expect(nextButton).toBeDisabled();
    expect(lastButton).toBeDisabled();

    await user.click(firstButton);

    await waitFor(() => {
      expect(screen.getByTestId('player-panel-document')).toHaveTextContent('Chapter One');
      expect(screen.getByText('Selected media: chapter-one.html')).toBeInTheDocument();
    });

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(firstButton).toBeDisabled();
    expect(previousButton).toBeDisabled();
    expect(nextButton).not.toBeDisabled();
    expect(lastButton).not.toBeDisabled();

    await user.click(nextButton);

    await waitFor(() => {
      expect(screen.getByTestId('player-panel-document')).toHaveTextContent('Second chapter content.');
      expect(screen.getByText('Selected media: chapter-two.html')).toBeInTheDocument();
    });

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(firstButton).not.toBeDisabled();
    expect(previousButton).not.toBeDisabled();
    expect(nextButton).toBeDisabled();
    expect(lastButton).toBeDisabled();

    await user.click(previousButton);

    await waitFor(() => {
      expect(screen.getByTestId('player-panel-document')).toHaveTextContent('Chapter One');
      expect(screen.getByText('Selected media: chapter-one.html')).toBeInTheDocument();
    });

    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
