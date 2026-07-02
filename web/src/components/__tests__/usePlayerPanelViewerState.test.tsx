import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { LiveMediaChunk } from '../../hooks/useLiveMedia';
import { usePlayerPanelViewerState } from '../player-panel/usePlayerPanelViewerState';

const wakeLockMock = vi.hoisted(() => ({
  useWakeLock: vi.fn(),
}));

vi.mock('../../hooks/useWakeLock', () => ({
  useWakeLock: wakeLockMock.useWakeLock,
}));

type HookArgs = Parameters<typeof usePlayerPanelViewerState>[0];

function chunk(overrides: Partial<LiveMediaChunk> = {}): LiveMediaChunk {
  return {
    chunkId: 'chunk-1',
    rangeFragment: 'range-1',
    startSentence: 1,
    endSentence: 2,
    files: [],
    sentences: [
      {
        original: { text: 'Original line' },
        translation: { text: 'Translation line' },
      },
    ],
    ...overrides,
  } as LiveMediaChunk;
}

function args(overrides: Partial<HookArgs> = {}): HookArgs {
  return {
    mediaTextCount: 1,
    mediaAudioCount: 1,
    mediaVideoCount: 0,
    isLoading: false,
    hasInlineAudioControls: true,
    isInlineAudioPlaying: false,
    origin: 'job',
    showBackToLibrary: false,
    textPreview: null,
    textLoading: false,
    textError: null,
    resolvedActiveTextChunk: chunk(),
    hasInteractiveChunks: true,
    hasSelectedItem: true,
    ...overrides,
  };
}

describe('usePlayerPanelViewerState', () => {
  afterEach(() => {
    window.localStorage.clear();
    wakeLockMock.useWakeLock.mockClear();
  });

  it('builds document content from chunk sentence fallback when no preview is loaded', () => {
    const { result } = renderHook(() => usePlayerPanelViewerState(args()));

    expect(result.current.canRenderInteractiveViewer).toBe(true);
    expect(result.current.interactiveViewerContent).toBe('Original line\nTranslation line');
    expect(result.current.shouldShowInteractiveViewer).toBe(true);
    expect(result.current.isPlaybackDisabled).toBe(false);
    expect(result.current.isFullscreenDisabled).toBe(false);
  });

  it('prefers preview content and surfaces loading/error placeholders outside fullscreen', () => {
    const { result } = renderHook(() =>
      usePlayerPanelViewerState(args({
        textPreview: { content: 'Preview text', raw: '<p>Preview text</p>' },
        resolvedActiveTextChunk: null,
        hasInteractiveChunks: false,
        textLoading: true,
        textError: 'Failed',
      })),
    );

    expect(result.current.interactiveViewerContent).toBe('Preview text');
    expect(result.current.interactiveViewerRaw).toBe('<p>Preview text</p>');
    expect(result.current.shouldShowLoadingPlaceholder).toBe(true);
    expect(result.current.shouldShowStandaloneError).toBe(true);
  });

  it('owns fullscreen preference and chrome back-to-library/wake-lock state', () => {
    const { result } = renderHook(() =>
      usePlayerPanelViewerState(args({
        isInlineAudioPlaying: true,
        origin: 'library',
        showBackToLibrary: true,
      })),
    );

    expect(result.current.shouldShowBackToLibrary).toBe(true);
    expect(wakeLockMock.useWakeLock).toHaveBeenLastCalledWith(true);

    act(() => {
      result.current.handleInteractiveFullscreenToggle();
    });

    expect(result.current.isInteractiveFullscreen).toBe(true);
    expect(result.current.shouldShowInteractiveViewer).toBe(true);

    act(() => {
      result.current.handleExitInteractiveFullscreen();
    });

    expect(result.current.isInteractiveFullscreen).toBe(false);
  });
});
