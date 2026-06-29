import { act, renderHook } from '@testing-library/react';
import { useState, type KeyboardEvent as ReactKeyboardEvent, type MutableRefObject } from 'react';
import { describe, expect, it, vi } from 'vitest';
import type { AssSubtitleCue } from '../../../lib/subtitles';
import type { SubtitleTokenSelection } from '../subtitleTrackOverlayUtils';
import { useSubtitleTokenNavigation } from '../useSubtitleTokenNavigation';

const TRACKS: AssSubtitleCue['tracks'] = {
  original: { tokens: ['source', 'line'], currentIndex: 0 },
  translation: { tokens: ['een', 'twee', 'drie', 'vier'], currentIndex: 1 },
  transliteration: { tokens: ['translit'], currentIndex: 0 },
};

const ACTIVE_CUE: AssSubtitleCue = {
  start: 1,
  end: 3,
  tracks: TRACKS,
};

function rect(left: number, top: number): DOMRect {
  return {
    x: left,
    y: top,
    left,
    top,
    right: left + 10,
    bottom: top + 10,
    width: 10,
    height: 10,
    toJSON: () => ({}),
  };
}

function setRect(element: HTMLElement, value: DOMRect): void {
  Object.defineProperty(element, 'getBoundingClientRect', {
    configurable: true,
    value: () => value,
  });
}

function keyEvent(key: string, code = key) {
  return {
    key,
    code,
    preventDefault: vi.fn(),
  } as unknown as ReactKeyboardEvent<HTMLDivElement>;
}

function useHarness({
  initialSelection = null,
  isPlaying = false,
  linguistEnabled = true,
  consumeIgnoredClick = () => false,
  openLinguistBubbleForRect = vi.fn(),
}: {
  initialSelection?: SubtitleTokenSelection | null;
  isPlaying?: boolean;
  linguistEnabled?: boolean;
  consumeIgnoredClick?: () => boolean;
  openLinguistBubbleForRect?: ReturnType<typeof vi.fn>;
} = {}) {
  const [selection, setSelection] = useState<SubtitleTokenSelection | null>(initialSelection);
  const [overlay] = useState(() => document.createElement('div'));
  const overlayRef = { current: overlay } as MutableRefObject<HTMLDivElement | null>;
  const hook = useSubtitleTokenNavigation({
    overlayRef,
    overlayActive: true,
    activeCue: ACTIVE_CUE,
    subtitleScale: 1,
    cueVisibility: { original: true, translation: true, transliteration: true },
    tracks: TRACKS,
    visibleTracks: ['original', 'transliteration', 'translation'],
    selection,
    setSelection,
    isPlaying,
    linguistEnabled,
    consumeIgnoredClick,
    resumePlaybackAndDefocus: vi.fn(),
    requestPositionUpdate: vi.fn(),
    openLinguistBubbleForRect,
  });
  return {
    ...hook,
    selection,
    overlay,
    openLinguistBubbleForRect,
  };
}

function attachTranslationTokens(overlay: HTMLElement): HTMLDivElement {
  const container = document.createElement('div');
  container.dataset.track = 'translation';
  setRect(container, rect(0, 0));
  [0, 1, 2, 3].forEach((index) => {
    const token = document.createElement('button');
    token.dataset.subtitleTokenIndex = String(index);
    setRect(token, rect(index % 2 === 0 ? 0 : 20, index < 2 ? 0 : 20));
    container.appendChild(token);
  });
  overlay.appendChild(container);
  return container;
}

describe('useSubtitleTokenNavigation', () => {
  it('rebuilds token line maps and moves horizontally within the current visual line', () => {
    const { result } = renderHook(() =>
      useHarness({ initialSelection: { track: 'translation', index: 1 } }),
    );
    const container = attachTranslationTokens(result.current.overlay);
    result.current.trackRefs.current.translation = container;

    act(() => {
      result.current.rebuildLineMaps();
      result.current.handleKeyDown(keyEvent('ArrowRight'));
    });

    expect(result.current.selection).toEqual({ track: 'translation', index: 0 });
  });

  it('opens lookup for the selected token with Enter and focuses the overlay', () => {
    const openLinguistBubbleForRect = vi.fn();
    const { result } = renderHook(() =>
      useHarness({
        initialSelection: { track: 'translation', index: 2 },
        openLinguistBubbleForRect,
      }),
    );
    const container = attachTranslationTokens(result.current.overlay);
    result.current.trackRefs.current.translation = container;
    const focus = vi.spyOn(result.current.overlay, 'focus').mockImplementation(() => undefined);
    const enter = keyEvent('Enter');

    act(() => {
      result.current.handleKeyDown(enter);
    });

    expect(openLinguistBubbleForRect).toHaveBeenCalledWith(
      'drie',
      expect.objectContaining({ top: 20 }),
      'click',
      'translation',
      expect.any(HTMLElement),
    );
    expect(result.current.selection).toEqual({ track: 'translation', index: 2 });
    expect(enter.preventDefault).toHaveBeenCalledTimes(1);
    expect(focus).toHaveBeenCalledTimes(1);
  });

  it('activates clicked tokens and ignores the click immediately after a drag', () => {
    const consumeIgnoredClick = vi.fn(() => true);
    const openLinguistBubbleForRect = vi.fn();
    const { result, rerender } = renderHook(
      ({ ignoreClick }) =>
        useHarness({
          consumeIgnoredClick: ignoreClick ? consumeIgnoredClick : () => false,
          openLinguistBubbleForRect,
        }),
      { initialProps: { ignoreClick: true } },
    );
    const token = document.createElement('button');
    setRect(token, rect(5, 6));

    act(() => {
      result.current.handleTokenClick('translation', 1, token);
    });

    expect(consumeIgnoredClick).toHaveBeenCalledTimes(1);
    expect(openLinguistBubbleForRect).not.toHaveBeenCalled();

    rerender({ ignoreClick: false });
    act(() => {
      result.current.handleTokenClick('translation', 1, token);
    });

    expect(openLinguistBubbleForRect).toHaveBeenCalledWith(
      'twee',
      expect.objectContaining({ left: 5 }),
      'click',
      'translation',
      token,
    );
    expect(result.current.selection).toEqual({ track: 'translation', index: 1 });
  });
});
