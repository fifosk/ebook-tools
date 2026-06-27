import { cloneElement, isValidElement } from 'react';
import { act, cleanup, fireEvent, render as rtlRender, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { Mock, SpyInstance } from 'vitest';
import PlayerPanel from '../PlayerPanel';
import type { LiveMediaChunk, LiveMediaItem, LiveMediaState } from '../../hooks/useLiveMedia';
import { timingStore } from '../../stores/timingStore';
import type { TimingPayload } from '../../types/timing';
import { __TESTING__ as AudioSyncTest } from '../../player/AudioSyncController';
import { LanguageProvider } from '../../context/LanguageProvider';
import { MyLinguistProvider } from '../../context/MyLinguistProvider';
import { MyPainterProvider } from '../../context/MyPainterProvider';

function createMediaState(overrides: Partial<LiveMediaState>): LiveMediaState {
  return {
    text: [],
    audio: [],
    video: [],
    ...overrides,
  } as LiveMediaState;
}

function PlayerPanelTestProviders({ children }: { children: React.ReactNode }) {
  return (
    <LanguageProvider>
      <MyLinguistProvider>
        <MyPainterProvider>{children}</MyPainterProvider>
      </MyLinguistProvider>
    </LanguageProvider>
  );
}

function renderWithProviders(ui: Parameters<typeof rtlRender>[0]) {
  const content =
    isValidElement(ui) && ui.type === PlayerPanel
      ? cloneElement(ui, {
          playerFeatures: {
            search: false,
            ...(ui.props as { playerFeatures?: Record<string, boolean> }).playerFeatures,
          },
        } as Partial<Parameters<typeof PlayerPanel>[0]>)
      : ui;
  return rtlRender(content, { wrapper: PlayerPanelTestProviders });
}

const mediaPrototype = HTMLMediaElement.prototype;
const originalCurrentTimeDescriptor = Object.getOwnPropertyDescriptor(mediaPrototype, 'currentTime');
const elementPrototype = HTMLElement.prototype;
const originalScrollDescriptor = Object.getOwnPropertyDescriptor(elementPrototype, 'scrollTop');
const originalElementRequestFullscreen = elementPrototype.requestFullscreen;
const originalFullscreenDescriptor = Object.getOwnPropertyDescriptor(document, 'fullscreenElement');
const videoPrototype = HTMLVideoElement.prototype as HTMLVideoElement & {
  requestFullscreen?: () => Promise<void>;
};
const documentPrototype = Document.prototype as Document & {
  exitFullscreen?: () => Promise<void>;
};
const originalRequestFullscreen = videoPrototype.requestFullscreen;
const originalExitFullscreen = documentPrototype.exitFullscreen;

let requestFullscreenMock: Mock<[], Promise<void>>;
let exitFullscreenMock: Mock<[], Promise<void>>;
let elementRequestFullscreenMock: Mock<[], Promise<void>>;
let fullscreenElementSlot: Element | null = null;
let playSpy: SpyInstance<[], Promise<void>>;
let pauseSpy: SpyInstance<[], void>;
let loadSpy: SpyInstance<[], void>;

beforeAll(() => {
  Object.defineProperty(mediaPrototype, 'currentTime', {
    configurable: true,
    get() {
      return (this as HTMLMediaElement & { __currentTime?: number }).__currentTime ?? 0;
    },
    set(value: number) {
      (this as HTMLMediaElement & { __currentTime?: number }).__currentTime = value;
    },
  });

  Object.defineProperty(elementPrototype, 'scrollTop', {
    configurable: true,
    get() {
      return (this as HTMLElement & { __scrollTop?: number }).__scrollTop ?? 0;
    },
    set(value: number) {
      (this as HTMLElement & { __scrollTop?: number }).__scrollTop = value;
    },
  });
});

afterAll(() => {
  if (originalCurrentTimeDescriptor) {
    Object.defineProperty(mediaPrototype, 'currentTime', originalCurrentTimeDescriptor);
  }
  if (originalScrollDescriptor) {
    Object.defineProperty(elementPrototype, 'scrollTop', originalScrollDescriptor);
  }
});

describe('PlayerPanel', () => {
  const originalFetch = globalThis.fetch;

  function buildInteractiveFixtures(): {
    media: LiveMediaState;
    chunks: LiveMediaChunk[];
  } {
    const chunkOneText: LiveMediaItem = {
      type: 'text',
      name: 'chunk-1.html',
      url: 'https://example.com/text/chunk-1.html',
      source: 'live',
    };
    const chunkTwoText: LiveMediaItem = {
      type: 'text',
      name: 'chunk-2.html',
      url: 'https://example.com/text/chunk-2.html',
      source: 'live',
    };
    const chunkOneAudio: LiveMediaItem = {
      type: 'audio',
      name: 'chunk-1.mp3',
      url: 'https://example.com/audio/chunk-1.mp3',
      source: 'live',
    };
    const chunkTwoAudio: LiveMediaItem = {
      type: 'audio',
      name: 'chunk-2.mp3',
      url: 'https://example.com/audio/chunk-2.mp3',
      source: 'live',
    };

    const chunks: LiveMediaChunk[] = [
      {
        chunkId: 'chunk-1',
        rangeFragment: 'Chunk 1',
        startSentence: 1,
        endSentence: 2,
        files: [chunkOneText, chunkOneAudio],
        sentences: [
          {
            sentence_number: 1,
            original: {
              text: 'Hello world',
              tokens: ['Hello', 'world'],
            },
            translation: null,
            transliteration: null,
            timeline: [],
            totalDuration: 2,
          },
        ],
      },
      {
        chunkId: 'chunk-2',
        rangeFragment: 'Chunk 2',
        startSentence: 3,
        endSentence: 4,
        files: [chunkTwoText, chunkTwoAudio],
        sentences: [
          {
            sentence_number: 2,
            original: {
              text: 'Another line',
              tokens: ['Another', 'line'],
            },
            translation: null,
            transliteration: null,
            timeline: [],
            totalDuration: 2,
          },
        ],
      },
    ];

    return {
      media: createMediaState({
        text: [chunkOneText, chunkTwoText],
        audio: [chunkOneAudio, chunkTwoAudio],
        video: [],
      }),
      chunks,
    };
  }

beforeEach(() => {
  window.history.replaceState({}, '', '/?wordsync=0');
  window.sessionStorage.clear();
  playSpy = vi.spyOn(mediaPrototype, 'play').mockImplementation(() => Promise.resolve());
  pauseSpy = vi.spyOn(mediaPrototype, 'pause').mockImplementation(() => undefined);
  loadSpy = vi.spyOn(mediaPrototype, 'load').mockImplementation(() => undefined);
  fullscreenElementSlot = null;
  requestFullscreenMock = vi.fn<[], Promise<void>>().mockImplementation(function (this: HTMLVideoElement) {
    fullscreenElementSlot = this;
    return Promise.resolve(undefined);
  });
  elementRequestFullscreenMock = vi.fn<[], Promise<void>>().mockImplementation(function (this: HTMLElement) {
    fullscreenElementSlot = this;
    return Promise.resolve(undefined);
  });
  videoPrototype.requestFullscreen = requestFullscreenMock as typeof videoPrototype.requestFullscreen;
  (elementPrototype as HTMLElement & { requestFullscreen?: () => Promise<void> }).requestFullscreen =
    elementRequestFullscreenMock as typeof elementPrototype.requestFullscreen;
  exitFullscreenMock = vi.fn<[], Promise<void>>().mockImplementation(() => {
    fullscreenElementSlot = null;
    return Promise.resolve(undefined);
  });
  documentPrototype.exitFullscreen = exitFullscreenMock as typeof documentPrototype.exitFullscreen;
  Object.defineProperty(document, 'fullscreenElement', {
    configurable: true,
    get() {
      return fullscreenElementSlot;
    },
    set(value) {
      fullscreenElementSlot = value as Element | null;
    },
  });
});

afterEach(() => {
  cleanup();
  window.history.replaceState({}, '', '/');
  if (originalFetch) {
    globalThis.fetch = originalFetch;
    } else {
    Reflect.deleteProperty(globalThis as typeof globalThis & { fetch?: typeof fetch }, 'fetch');
  }
  vi.restoreAllMocks();
  if (originalRequestFullscreen) {
    videoPrototype.requestFullscreen = originalRequestFullscreen;
  } else {
    Reflect.deleteProperty(videoPrototype, 'requestFullscreen');
  }
  if (originalExitFullscreen) {
    documentPrototype.exitFullscreen = originalExitFullscreen;
  } else {
    Reflect.deleteProperty(documentPrototype, 'exitFullscreen');
  }
  if (originalElementRequestFullscreen) {
    elementPrototype.requestFullscreen = originalElementRequestFullscreen;
  } else {
    Reflect.deleteProperty(elementPrototype as HTMLElement & { requestFullscreen?: () => Promise<void> }, 'requestFullscreen');
  }
  if (originalFullscreenDescriptor) {
    Object.defineProperty(document, 'fullscreenElement', originalFullscreenDescriptor);
  } else {
    Reflect.deleteProperty(document as Document & { fullscreenElement?: Element | null }, 'fullscreenElement');
  }
  fullscreenElementSlot = null;
});

  it('loads text previews and updates when selecting items from the list', async () => {
    const fetchMock = vi
      .fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockImplementation((url) => {
        const target = typeof url === 'string' ? url : url instanceof URL ? url.toString() : url.url;
        const body = target.includes('chapter-two')
          ? '<html><body><p>Second chapter content.</p></body></html>'
          : '<html><body><h1>Chapter One</h1><p>Hello <strong>world</strong>.</p></body></html>';
        return Promise.resolve({
          ok: true,
          status: 200,
          text: () => Promise.resolve(body),
          json: () => Promise.resolve({}),
        } as Response);
      });

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

    renderWithProviders(
      <PlayerPanel jobId="job-42" media={media} chunks={[]} mediaComplete isLoading={false} error={null} />
    );

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

    expect(firstButton).toBeInTheDocument();
    expect(previousButton).toBeInTheDocument();
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
    });

    expect(firstButton).not.toBeDisabled();
    expect(previousButton).not.toBeDisabled();
    expect(nextButton).toBeInTheDocument();
    expect(lastButton).toBeInTheDocument();

    await user.click(firstButton);

    await waitFor(() => {
      expect(screen.getByTestId('player-panel-document')).toHaveTextContent('Chapter One');
    });

    expect(
      fetchMock.mock.calls.filter(([url]) => String(url).includes('/text/')),
    ).toHaveLength(2);
    expect(firstButton).toBeInTheDocument();
    expect(previousButton).toBeInTheDocument();
    expect(nextButton).not.toBeDisabled();
    expect(lastButton).not.toBeDisabled();

    await user.click(nextButton);

    await waitFor(() => {
      expect(screen.getByTestId('player-panel-document')).toHaveTextContent('Second chapter content.');
    });

    expect(
      fetchMock.mock.calls.filter(([url]) => String(url).includes('/text/')),
    ).toHaveLength(2);
    expect(firstButton).not.toBeDisabled();
    expect(previousButton).not.toBeDisabled();
    expect(nextButton).toBeInTheDocument();
    expect(lastButton).toBeInTheDocument();

    await user.click(previousButton);

    await waitFor(() => {
      expect(screen.getByTestId('player-panel-document')).toHaveTextContent('Chapter One');
    });

    expect(
      fetchMock.mock.calls.filter(([url]) => String(url).includes('/text/')),
    ).toHaveLength(2);
  });

  it('plays and pauses synchronized audio via the player controls', async () => {
    const { media, chunks } = buildInteractiveFixtures();
    const fetchMock = vi
      .fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockImplementation((url) => {
        const target = typeof url === 'string' ? url : '';
        if (target.includes('sentences.json')) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve(['one', 'two', 'three', 'four']),
          } as Response);
        }
        const body = target.includes('chunk-1')
          ? '<html><body><p>Chunk one.</p></body></html>'
          : '<html><body><p>Chunk two.</p></body></html>';
        return Promise.resolve({
          ok: true,
          status: 200,
          text: () => Promise.resolve(body),
        } as Response);
      });

    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const user = userEvent.setup();

    renderWithProviders(
      <PlayerPanel
        jobId="job-99"
        media={media}
        chunks={chunks}
        mediaComplete
        isLoading={false}
        error={null}
      />
    );

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });

    const playbackButtons = screen.getAllByRole('button', { name: /Play playback/i });
    const playbackButton = playbackButtons.find((button) => button.classList.contains('player-panel__nav-button'));
    expect(playbackButton).toBeDefined();
    if (!playbackButton) {
      throw new Error('Navigation playback toggle not found');
    }
    expect(playbackButton).toHaveAttribute('aria-label', 'Play playback');

    await waitFor(() => {
      expect(playbackButton).not.toBeDisabled();
    });

    const initialPlayCalls = playSpy.mock.calls.length;
    await user.click(playbackButton);
    expect(playSpy.mock.calls.length).toBeGreaterThan(initialPlayCalls);
    const inlineAudio = document.querySelector('.player-panel__interactive-audio audio');
    if (inlineAudio) {
      fireEvent(inlineAudio, new Event('play'));
    }
  });

  it('prefetches metadata for nearby chunks when the interactive reader is active', async () => {
    const chunks: LiveMediaChunk[] = Array.from({ length: 5 }, (_, index) => {
      const chunkIndex = index + 1;
      return {
        chunkId: `chunk-${chunkIndex}`,
        rangeFragment: `Chunk ${chunkIndex}`,
        startSentence: chunkIndex * 2 - 1,
        endSentence: chunkIndex * 2,
        files: [],
        metadataUrl: `https://example.com/chunks/chunk-${chunkIndex}.json`,
      };
    });

    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            sentences: [],
          }),
      } as Response),
    );

    globalThis.fetch = fetchMock as unknown as typeof fetch;

    renderWithProviders(
      <PlayerPanel
        jobId="job-prefetch"
        media={createMediaState({ text: [], audio: [], video: [] })}
        chunks={chunks}
        mediaComplete
        isLoading={false}
        error={null}
      />,
    );

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('https://example.com/chunks/chunk-3.json', {
        credentials: 'include',
      });
    });

    expect(fetchMock).toHaveBeenCalledWith('https://example.com/chunks/chunk-1.json', {
      credentials: 'include',
    });
    expect(fetchMock).toHaveBeenCalledWith('https://example.com/chunks/chunk-2.json', {
      credentials: 'include',
    });
    expect(fetchMock).toHaveBeenCalledWith('https://example.com/chunks/chunk-3.json', {
      credentials: 'include',
    });
  });

  it('advances chunks automatically while interactive fullscreen is enabled', async () => {
    const { media, chunks } = buildInteractiveFixtures();
    const fetchMock = vi
      .fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockImplementation((url) => {
        const target = typeof url === 'string' ? url : '';
        if (target.includes('sentences.json')) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve(['a', 'b', 'c', 'd', 'e']),
          } as Response);
        }
        const body = target.includes('chunk-1')
          ? '<html><body><p>Chunk one.</p></body></html>'
          : '<html><body><p>Chunk two.</p></body></html>';
        return Promise.resolve({
          ok: true,
          status: 200,
          text: () => Promise.resolve(body),
        } as Response);
      });

    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const user = userEvent.setup();

    renderWithProviders(
      <PlayerPanel
        jobId="job-100"
        media={media}
        chunks={chunks}
        mediaComplete
        isLoading={false}
        error={null}
      />
    );

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });

    const fullscreenToggle = screen.getByTestId('player-panel-interactive-fullscreen');
    expect(fullscreenToggle).not.toBeDisabled();

    await user.click(fullscreenToggle);

    expect(elementRequestFullscreenMock).toHaveBeenCalled();
    expect(fullscreenToggle).toHaveAttribute('aria-pressed', 'true');

    const audioElement = document.querySelector('audio');
    expect(audioElement).not.toBeNull();

    const playCallsBeforeAdvance = playSpy.mock.calls.length;
    fireEvent.ended(audioElement as HTMLAudioElement);

    await waitFor(() => {
      expect((audioElement as HTMLAudioElement).getAttribute('src')).toContain('chunk-2.mp3');
    });

    expect(fullscreenToggle).toHaveAttribute('aria-pressed', 'true');
    expect(playSpy.mock.calls.length).toBeGreaterThan(playCallsBeforeAdvance);

    const exitCallsBefore = exitFullscreenMock.mock.calls.length;
    await user.click(fullscreenToggle);
    expect(exitFullscreenMock.mock.calls.length).toBe(exitCallsBefore + 1);
    expect(fullscreenToggle).toHaveAttribute('aria-pressed', 'false');
  });

  it('keeps interactive fullscreen active while the next chunk document is loading', async () => {
    const { media, chunks } = buildInteractiveFixtures();
    let resolveSecondText: (() => void) | null = null;
    const fetchMock = vi
      .fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockImplementation((url) => {
        const target = typeof url === 'string' ? url : '';
        if (target.includes('sentences.json')) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve(['first', 'second', 'third']),
          } as Response);
        }
        if (target.includes('chunk-1')) {
          return Promise.resolve({
            ok: true,
            status: 200,
            text: () => Promise.resolve('<html><body><p>Chunk one.</p></body></html>'),
          } as Response);
        }
        const deferred = new Promise<string>((resolve) => {
          resolveSecondText = () => resolve('<html><body><p>Chunk two.</p></body></html>');
        });
        return Promise.resolve({
          ok: true,
          status: 200,
          text: () => deferred,
        } as Response);
      });

    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const user = userEvent.setup();

    renderWithProviders(
      <PlayerPanel
        jobId="job-200"
        media={media}
        chunks={chunks}
        mediaComplete
        isLoading={false}
        error={null}
      />
    );

    await waitFor(() => {
      expect(fetchMock.mock.calls.some(([url]) => String(url).includes('chunk-1'))).toBe(true);
    });

    const fullscreenToggle = screen.getByTestId('player-panel-interactive-fullscreen');
    await user.click(fullscreenToggle);

    expect(fullscreenToggle).toHaveAttribute('aria-pressed', 'true');

    const nextButtons = screen.getAllByRole('button', { name: 'Go to next item' });
    const exitCallsBefore = exitFullscreenMock.mock.calls.length;

    await user.click(nextButtons[0]);

    await waitFor(() => {
      expect(fetchMock.mock.calls.some(([url]) => String(url).includes('chunk-2'))).toBe(true);
    });

    expect(fullscreenToggle).toHaveAttribute('aria-pressed', 'true');
    expect(exitFullscreenMock.mock.calls.length).toBe(exitCallsBefore);
    expect(screen.getAllByText('Loading document…').length).toBeGreaterThan(0);

    act(() => {
      resolveSecondText?.();
    });

    await waitFor(() => {
      expect(fullscreenToggle).toHaveAttribute('aria-pressed', 'true');
    });
  });

  it('pauses inline audio for dictionary long presses and resumes without seeking', async () => {
    const { media, chunks } = buildInteractiveFixtures();
    const fetchMock = vi
      .fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockImplementation((url) => {
        const target = typeof url === 'string' ? url : '';
        if (target.includes('sentences.json')) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve(['alpha', 'beta']),
          } as Response);
        }
        const body = target.includes('chunk-1')
          ? '<html><body><p>Chunk body.</p></body></html>'
          : '<html><body><p>Chunk two.</p></body></html>';
        return Promise.resolve({
          ok: true,
          status: 200,
          text: () => Promise.resolve(body),
        } as Response);
      });

    globalThis.fetch = fetchMock as unknown as typeof fetch;

    renderWithProviders(
      <PlayerPanel
        jobId="job-dictionary"
        media={media}
        chunks={chunks}
        mediaComplete
        isLoading={false}
        error={null}
      />
    );

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });

    const token = await screen.findByText('Hello');
    const audioElement = document.querySelector('audio') as HTMLAudioElement | null;
    expect(audioElement).not.toBeNull();

    act(() => {
      if (audioElement) {
        audioElement.currentTime = 2.5;
      }
    });

    const pauseCallsBefore = pauseSpy.mock.calls.length;
    vi.useFakeTimers();
    try {
      fireEvent.pointerDown(token, {
        pointerId: 1,
        pointerType: 'mouse',
        button: 0,
        isPrimary: true,
      });

      act(() => {
        vi.advanceTimersByTime(500);
      });

      expect(pauseSpy.mock.calls.length).toBeGreaterThanOrEqual(pauseCallsBefore);

      fireEvent.pointerUp(token, {
        pointerId: 1,
        pointerType: 'mouse',
        button: 0,
        isPrimary: true,
      });

      const baselineTime = audioElement?.currentTime ?? 0;
      fireEvent.click(token);
      expect(audioElement?.currentTime ?? 0).toBe(baselineTime);

      const playCallsBeforeResume = playSpy.mock.calls.length;
      fireEvent.pointerDown(document.body, {
        pointerId: 2,
        pointerType: 'mouse',
        button: 0,
        isPrimary: true,
      });

      act(() => {
        vi.runAllTimers();
      });

      expect(playSpy.mock.calls.length).toBeGreaterThanOrEqual(playCallsBeforeResume);
    } finally {
      vi.useRealTimers();
    }
  });

  it('remembers playback and scroll positions across media types', async () => {
    const fetchMock = vi
      .fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockImplementation(async () =>
        ({
          ok: true,
          status: 200,
          text: async () => '<html><body><p>Sample text content for memory tests.</p></body></html>',
        } as Response),
      );

    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const media = createMediaState({
      text: [
        {
          type: 'text',
          name: 'chapter-one.html',
          url: 'https://example.com/text/chapter-one.html',
          source: 'completed',
        },
      ],
      audio: [
        {
          type: 'audio',
          name: 'chapter-one.mp3',
          url: 'https://example.com/audio/chapter-one.mp3',
          source: 'completed',
        },
      ],
      video: [
        {
          type: 'video',
          name: 'chapter-one.mp4',
          url: 'https://example.com/video/chapter-one.mp4',
          source: 'completed',
        },
      ],
    });

    const { unmount } = renderWithProviders(
      <PlayerPanel jobId="job-123" media={media} chunks={[]} mediaComplete={false} isLoading={false} error={null} />,
    );

    expect(screen.queryByTestId('media-tab-audio')).not.toBeInTheDocument();

    const article = await screen.findByTestId('player-panel-document');

    article.scrollTop = 150;
    fireEvent.scroll(article);

    await waitFor(() => {
      const stored = window.sessionStorage.getItem('media-memory:job-123');
      expect(stored).toBeTruthy();
      const parsed = JSON.parse(stored ?? '{}');
      const entry = parsed.entries?.['https://example.com/text/chapter-one.html'];
      expect(entry?.position).toBeCloseTo(150, 0);
    });

    unmount();
  });

  it('restores remembered reader selection from session storage after rerendering', async () => {
    const fetchMock = vi
      .fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockImplementation(async () =>
        ({
          ok: true,
          status: 200,
          text: async () => '<html><body><p>Persisted text content.</p></body></html>',
        } as Response),
      );

    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const media = createMediaState({
      text: [
        {
          type: 'text',
          name: 'chapter-one.html',
          url: 'https://example.com/text/chapter-one.html',
          source: 'completed',
        },
      ],
      audio: [
        {
          type: 'audio',
          name: 'chapter-one.mp3',
          url: 'https://example.com/audio/chapter-one.mp3',
          source: 'completed',
        },
      ],
      video: [
        {
          type: 'video',
          name: 'chapter-one.mp4',
          url: 'https://example.com/video/chapter-one.mp4',
          source: 'completed',
        },
      ],
    });

    const { unmount } = renderWithProviders(
      <PlayerPanel jobId="job-456" media={media} chunks={[]} mediaComplete={false} isLoading={false} error={null} />,
    );

    const article = await screen.findByTestId('player-panel-document');
    article.scrollTop = 80;
    fireEvent.scroll(article);

    unmount();

    renderWithProviders(
      <PlayerPanel jobId="job-456" media={media} chunks={[]} mediaComplete={false} isLoading={false} error={null} />,
    );

    await screen.findByTestId('player-panel-document');
    expect(window.sessionStorage.getItem('media-memory:job-456')).toContain('chapter-one.html');
  });

  it('shows book metadata in the player header when provided', () => {
    const media = createMediaState({});

    renderWithProviders(
      <PlayerPanel
        jobId="job-789"
        media={media}
        chunks={[]}
        mediaComplete={false}
        isLoading={false}
        error={null}
        mediaMetadata={{ book_title: 'Example Title', book_author: 'Jane Doe' }}
      />,
    );

    const mediaNotices = screen.getAllByText('No generated media yet for Example Title.');
    expect(mediaNotices.length).toBeGreaterThan(0);
    expect(document.querySelector('.player-panel__player-info-art-main')).toBeNull();
  });

  it('renders the cover image once reader media is available', async () => {
    const { media, chunks } = buildInteractiveFixtures();
    globalThis.fetch = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>().mockImplementation((url) => {
      const target = typeof url === 'string' ? url : '';
      if (target.includes('sentences.json')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve([]),
        } as Response);
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        text: () => Promise.resolve('<html><body><p>Example text.</p></body></html>'),
      } as Response);
    });

    renderWithProviders(
      <PlayerPanel
        jobId="job-789"
        media={media}
        chunks={chunks}
        mediaComplete
        isLoading={false}
        error={null}
        mediaMetadata={{ book_title: 'Example Title', book_author: 'Jane Doe' }}
      />,
    );

    await screen.findByTestId('player-panel-document');
    const coverImage = document.querySelector<HTMLImageElement>('.player-panel__player-info-art-main');
    expect(coverImage).toBeTruthy();
    expect(coverImage?.src).toContain('/pipelines/job-789/cover');
    expect(coverImage?.alt).toBe('Cover of Example Title by Jane Doe');
  });

  it('surfaces a word sync warning when timing is unavailable for the current chunk', async () => {
    window.history.replaceState({}, '', '/?wordsync=1');
    const { media, chunks } = buildInteractiveFixtures();
    globalThis.fetch = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>().mockImplementation((url) => {
      const target = typeof url === 'string' ? url : url instanceof URL ? url.toString() : url.url;
      if (target.includes('/api/jobs/job-no-timing/timing')) {
        return Promise.resolve({
          ok: false,
          status: 404,
          text: () => Promise.resolve(''),
          json: () => Promise.resolve({}),
        } as Response);
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        text: () => Promise.resolve('<html><body><p>Interactive text.</p></body></html>'),
        json: () => Promise.resolve({}),
      } as Response);
    });

    renderWithProviders(
      <PlayerPanel
        jobId="job-no-timing"
        media={media}
        chunks={chunks}
        mediaComplete
        isLoading={false}
        error={null}
      />,
    );

    const warning = await screen.findByLabelText('Word sync unavailable');
    expect(warning).toHaveTextContent('Word sync unavailable for this chunk.');
    expect(screen.getByRole('link', { name: /View media diagnostics/i })).toHaveAttribute(
      'href',
      '#media-diagnostics',
    );
  });

  it('keeps the word sync warning hidden while timing is still loading', async () => {
    window.history.replaceState({}, '', '/?wordsync=1');
    const { media, chunks } = buildInteractiveFixtures();
    globalThis.fetch = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>().mockImplementation((url) => {
      const target = typeof url === 'string' ? url : url instanceof URL ? url.toString() : url.url;
      if (target.includes('/api/jobs/job-loading-timing/timing')) {
        return new Promise<Response>(() => undefined);
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        text: () => Promise.resolve('<html><body><p>Interactive text.</p></body></html>'),
        json: () => Promise.resolve({}),
      } as Response);
    });

    renderWithProviders(
      <PlayerPanel
        jobId="job-loading-timing"
        media={media}
        chunks={chunks}
        mediaComplete
        isLoading={false}
        error={null}
      />,
    );

    await screen.findByTestId('player-panel-document');
    expect(screen.queryByLabelText('Word sync unavailable')).not.toBeInTheDocument();
  });

  it('toggles immersive mode from the header controls', async () => {
    const user = userEvent.setup();
    const { media, chunks } = buildInteractiveFixtures();
    globalThis.fetch = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve([]),
      text: () => Promise.resolve('<html><body><p>Interactive text.</p></body></html>'),
    } as Response);

    renderWithProviders(
      <PlayerPanel jobId="job-900" media={media} chunks={chunks} mediaComplete={false} isLoading={false} error={null} />,
    );

    const toggle = await screen.findByTestId('player-panel-interactive-fullscreen');
    expect(toggle).toHaveAttribute('aria-pressed', 'false');
    expect(document.querySelector('.player-panel__interactive--fullscreen')).toBeNull();

    await user.click(toggle);
    await waitFor(() => {
      expect(toggle).toHaveAttribute('aria-pressed', 'true');
    });
    await waitFor(() => {
      expect(elementRequestFullscreenMock).toHaveBeenCalled();
    });
    expect(document.querySelector('.player-panel__interactive--fullscreen')).not.toBeNull();

    await user.click(toggle);
    expect(toggle).toHaveAttribute('aria-pressed', 'false');
    await waitFor(() => {
      expect(exitFullscreenMock).toHaveBeenCalled();
    });
    expect(document.querySelector('.player-panel__interactive--fullscreen')).toBeNull();
  });

  it('keeps the reader active when interactive chunks exist without text files', async () => {
    globalThis.fetch = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve([]),
      text: () => Promise.resolve(''),
    } as Response);

    const audioItem: LiveMediaItem = {
      type: 'audio',
      name: 'chunk-1.mp3',
      url: 'https://example.com/audio/chunk-1.mp3',
      source: 'live',
    };

    const chunk: LiveMediaChunk = {
      chunkId: 'chunk-1',
      rangeFragment: 'Chunk 1',
      startSentence: 1,
      endSentence: 2,
      files: [audioItem],
      sentences: [
        {
          sentence_number: 1,
          original: { text: 'Hello world', tokens: ['Hello', 'world'] },
          translation: null,
          transliteration: null,
          timeline: [],
          totalDuration: 2,
        },
      ],
    };

    const media = createMediaState({ text: [], audio: [audioItem], video: [] });
    const { rerender } = renderWithProviders(
      <PlayerPanel
        jobId="job-keep-text"
        media={media}
        chunks={[chunk]}
        mediaComplete
        isLoading={false}
        error={null}
      />,
    );

    await waitFor(() => {
      expect(screen.getByTestId('player-panel-document')).toHaveTextContent('Hello');
    });

    rerender(
      <PlayerPanel
        jobId="job-keep-text"
        media={media}
        chunks={[chunk]}
        mediaComplete
        isLoading={false}
        error={null}
      />,
    );

    await waitFor(() => {
      expect(screen.getByTestId('player-panel-document')).toHaveTextContent('Hello');
    });
  });

  it('clamps translation-only highlights to the active sentence gate', () => {
    const payload: TimingPayload = {
      trackKind: 'translation_only',
      segments: [
        {
          id: '1',
          t0: 0,
          t1: 2,
          sentenceIdx: 1,
          tokens: [
            {
              id: 's1-w1',
              text: 'Hello',
              t0: 0,
              t1: 0.9,
              lane: 'tran',
              segId: '1',
              sentenceIdx: 1,
              startGate: 0,
              endGate: 2,
            },
            {
              id: 's1-w2',
              text: 'world',
              t0: 0.9,
              t1: 2,
              lane: 'tran',
              segId: '1',
              sentenceIdx: 1,
              startGate: 0,
              endGate: 2,
            },
          ],
        },
        {
          id: '2',
          t0: 2,
          t1: 4,
          sentenceIdx: 2,
          tokens: [
            {
              id: 's2-w1',
              text: 'Again',
              t0: 2.5,
              t1: 3.1,
              lane: 'tran',
              segId: '2',
              sentenceIdx: 2,
              startGate: 2.5,
              endGate: 4,
            },
            {
              id: 's2-w2',
              text: 'Soon',
              t0: 3.1,
              t1: 4.0,
              lane: 'tran',
              segId: '2',
              sentenceIdx: 2,
              startGate: 2.5,
              endGate: 4,
            },
          ],
        },
      ],
    };

    const firstGate = {
      start: 0,
      end: 2,
      sentenceIdx: 1,
      segmentIndex: 0,
    };
    const secondGate = {
      start: 2.5,
      end: 4,
      sentenceIdx: 2,
      segmentIndex: 1,
    };

    act(() => {
      timingStore.setPayload(payload);
      timingStore.setActiveGate(firstGate);
      AudioSyncTest.applyTime(2.25);
    });
    expect(timingStore.get().last).toMatchObject({ segIndex: 0, tokIndex: 1 });

    act(() => {
      timingStore.setActiveGate(secondGate);
      AudioSyncTest.applyTime(2.4);
    });
    expect(timingStore.get().last).toBeNull();

    act(() => {
      AudioSyncTest.applyTime(2.6);
    });
    expect(timingStore.get().last).toMatchObject({ segIndex: 1, tokIndex: 0 });

    act(() => {
      timingStore.setRate(1.5);
      AudioSyncTest.applyTime(3.2);
    });
    expect(timingStore.get().last).toMatchObject({ segIndex: 1, tokIndex: 1 });

    act(() => {
      timingStore.setActiveGate(null);
      timingStore.setLast(null);
      timingStore.setPayload({
        trackKind: 'translation_only',
        segments: [],
      });
    });
  });

});
