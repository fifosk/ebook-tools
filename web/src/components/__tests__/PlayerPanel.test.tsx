import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { Mock, SpyInstance } from 'vitest';
import PlayerPanel from '../PlayerPanel';
import type { LiveMediaChunk, LiveMediaItem, LiveMediaState } from '../../hooks/useLiveMedia';

function createMediaState(overrides: Partial<LiveMediaState>): LiveMediaState {
  return {
    text: [],
    audio: [],
    video: [],
    ...overrides,
  } as LiveMediaState;
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
            total_duration: 2,
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
            total_duration: 2,
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
  window.sessionStorage.clear();
  playSpy = vi.spyOn(mediaPrototype, 'play').mockImplementation(() => Promise.resolve());
  pauseSpy = vi.spyOn(mediaPrototype, 'pause').mockImplementation(() => undefined);
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

    render(
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

  it('plays and pauses synchronized audio via the player controls', async () => {
    const { media, chunks } = buildInteractiveFixtures();
    const fetchMock = vi
      .fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        text: () => Promise.resolve('<html><body><p>Chunk one.</p></body></html>'),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        text: () => Promise.resolve('<html><body><p>Chunk two.</p></body></html>'),
      } as Response);

    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const user = userEvent.setup();

    render(
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

    const playButton = screen.getByRole('button', { name: /Play playback/i });
    const pauseButton = screen.getByRole('button', { name: /Pause playback/i });

    const initialPlayCalls = playSpy.mock.calls.length;
    await user.click(playButton);
    expect(playSpy.mock.calls.length).toBeGreaterThan(initialPlayCalls);

    const initialPauseCalls = pauseSpy.mock.calls.length;
    await user.click(pauseButton);
    expect(pauseSpy.mock.calls.length).toBeGreaterThan(initialPauseCalls);
  });

  it('advances chunks automatically while interactive fullscreen is enabled', async () => {
    const { media, chunks } = buildInteractiveFixtures();
    const fetchMock = vi
      .fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        text: () => Promise.resolve('<html><body><p>Chunk one.</p></body></html>'),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        text: () => Promise.resolve('<html><body><p>Chunk two.</p></body></html>'),
      } as Response);

    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const user = userEvent.setup();

    render(
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

    const user = userEvent.setup();

    render(
      <PlayerPanel jobId="job-123" media={media} chunks={[]} mediaComplete={false} isLoading={false} error={null} />,
    );

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

    await user.click(screen.getByTestId('media-tab-audio'));
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'chapter-one.mp3' })).toHaveAttribute('aria-pressed', 'true');
    });

    const audioElement = screen.getByTestId('audio-player') as HTMLMediaElement;
    audioElement.currentTime = 12;
    fireEvent.timeUpdate(audioElement);

    await user.click(screen.getByTestId('media-tab-video'));
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'chapter-one.mp4' })).toHaveAttribute('aria-pressed', 'true');
    });

    const videoElement = screen.getByTestId('video-player') as HTMLMediaElement;
    videoElement.currentTime = 34;
    fireEvent.timeUpdate(videoElement);

    article.scrollTop = 0;

    await user.click(screen.getByTestId('media-tab-text'));

    const restoredArticle = await screen.findByTestId('player-panel-document');

    await waitFor(() => {
      expect(restoredArticle.scrollTop).toBeCloseTo(150, 0);
    });

    await user.click(screen.getByTestId('media-tab-audio'));
    const audioElementAfter = screen.getByTestId('audio-player') as HTMLMediaElement;

    await waitFor(() => {
      expect(audioElementAfter.currentTime).toBeCloseTo(12, 0);
    });

    await user.click(screen.getByTestId('media-tab-video'));
    const videoElementAfter = screen.getByTestId('video-player') as HTMLMediaElement;

    await waitFor(() => {
      expect(videoElementAfter.currentTime).toBeCloseTo(34, 0);
    });
  });

  it('restores remembered media from session storage after rerendering', async () => {
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

    const user = userEvent.setup();

    const { unmount } = render(
      <PlayerPanel jobId="job-456" media={media} chunks={[]} mediaComplete={false} isLoading={false} error={null} />,
    );

    await screen.findByTestId('player-panel-document');

    await user.click(screen.getByTestId('media-tab-video'));

    const videoElement = await screen.findByTestId('video-player');
    (videoElement as HTMLMediaElement).currentTime = 28;
    fireEvent.timeUpdate(videoElement as HTMLMediaElement);

    unmount();

    render(
      <PlayerPanel jobId="job-456" media={media} chunks={[]} mediaComplete={false} isLoading={false} error={null} />,
    );

    const videoTab = await screen.findByTestId('media-tab-video');

    await waitFor(() => {
      expect(videoTab).toHaveAttribute('data-state', 'active');
    });

    const restoredVideo = await screen.findByTestId('video-player');

    await waitFor(() => {
      expect((restoredVideo as HTMLMediaElement).currentTime).toBeCloseTo(28, 0);
    });
  });

  it('shows book metadata in the player header when provided', () => {
    const media = createMediaState({});

    render(
      <PlayerPanel
        jobId="job-789"
        media={media}
        chunks={[]}
        mediaComplete={false}
        isLoading={false}
        error={null}
        bookMetadata={{ book_title: 'Example Title', book_author: 'Jane Doe' }}
      />,
    );

    expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('Example Title');
    expect(screen.getByText('By Jane Doe • Job job-789')).toBeInTheDocument();
    const mediaNotices = screen.getAllByText('No generated media yet for Example Title.');
    expect(mediaNotices.length).toBeGreaterThan(0);
    expect(screen.queryByTestId('player-cover-image')).not.toBeInTheDocument();
  });

  it('renders the cover image once media generation completes', () => {
    const media = createMediaState({});

    render(
      <PlayerPanel
        jobId="job-789"
        media={media}
        chunks={[]}
        mediaComplete
        isLoading={false}
        error={null}
        bookMetadata={{ book_title: 'Example Title', book_author: 'Jane Doe' }}
      />,
    );

    const coverImage = screen.getByTestId('player-cover-image') as HTMLImageElement;
    expect(coverImage).toBeInTheDocument();
    expect(coverImage.src).toContain('/pipelines/job-789/cover');
    expect(coverImage.alt).toBe('Cover of Example Title by Jane Doe');
  });

  it('toggles immersive mode from the header controls', async () => {
    const user = userEvent.setup();
    const media = createMediaState({
      video: [
        {
          type: 'video',
          name: 'Clip',
          url: 'https://example.com/video/clip.mp4',
          source: 'completed'
        }
      ]
    });

    render(
      <PlayerPanel jobId="job-900" media={media} chunks={[]} mediaComplete={false} isLoading={false} error={null} />,
    );

    const toggle = screen.getByTestId('player-panel-immersive-toggle');
    expect(toggle).toHaveAttribute('aria-pressed', 'false');
    expect(document.querySelector('.player-panel--immersive')).toBeNull();

    await user.click(toggle);
    await waitFor(() => {
      expect(toggle).toHaveAttribute('aria-pressed', 'true');
    });
    await waitFor(() => {
      expect(requestFullscreenMock).toHaveBeenCalled();
    });
    expect(document.querySelector('.player-panel--immersive')).not.toBeNull();

    await user.click(toggle);
    expect(toggle).toHaveAttribute('aria-pressed', 'false');
    await waitFor(() => {
      expect(exitFullscreenMock).toHaveBeenCalled();
    });
    expect(document.querySelector('.player-panel--immersive')).toBeNull();
  });
});
