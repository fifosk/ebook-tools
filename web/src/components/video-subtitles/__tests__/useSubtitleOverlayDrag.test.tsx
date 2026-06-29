import { act, renderHook } from '@testing-library/react';
import type { MutableRefObject, PointerEvent as ReactPointerEvent } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useSubtitleOverlayDrag } from '../useSubtitleOverlayDrag';

const STORAGE_KEY = 'video.subtitle.verticalOffset';

function pointerEvent({
  pointerId = 1,
  clientX = 0,
  clientY = 0,
  button = 0,
  isPrimary = true,
  target = document.createElement('div'),
}: Partial<ReactPointerEvent<HTMLDivElement>> = {}): ReactPointerEvent<HTMLDivElement> {
  return {
    pointerId,
    clientX,
    clientY,
    button,
    isPrimary,
    target,
    preventDefault: vi.fn(),
  } as unknown as ReactPointerEvent<HTMLDivElement>;
}

function overlayRef(parentHeight = 400): MutableRefObject<HTMLDivElement | null> {
  const parent = document.createElement('div');
  const overlay = document.createElement('div');
  Object.defineProperty(parent, 'getBoundingClientRect', {
    configurable: true,
    value: () => ({ height: parentHeight }),
  });
  parent.appendChild(overlay);
  return { current: overlay };
}

describe('useSubtitleOverlayDrag', () => {
  afterEach(() => {
    window.localStorage.clear();
    vi.restoreAllMocks();
  });

  it('loads and clamps the persisted subtitle offset when the overlay activates', () => {
    window.localStorage.setItem(STORAGE_KEY, '-1000');
    const ref = overlayRef(400);

    const { result } = renderHook(() =>
      useSubtitleOverlayDrag({ overlayRef: ref, overlayActive: true }),
    );

    expect(result.current.verticalOffset).toBe(-180);
    expect(result.current.isDraggingSubtitles).toBe(false);
  });

  it('tracks vertical drags, stores the final offset, and suppresses the following click', () => {
    const ref = overlayRef(500);
    const { result } = renderHook(() =>
      useSubtitleOverlayDrag({ overlayRef: ref, overlayActive: true }),
    );
    const down = pointerEvent({ pointerId: 5, clientX: 10, clientY: 20 });
    const move = pointerEvent({ pointerId: 5, clientX: 12, clientY: -60 });
    const up = pointerEvent({ pointerId: 5, clientX: 12, clientY: -60 });

    act(() => {
      result.current.handleSubtitlePointerDown(down);
      result.current.handleSubtitlePointerMove(move);
    });

    expect(result.current.verticalOffset).toBe(-80);
    expect(result.current.isDraggingSubtitles).toBe(true);
    expect(move.preventDefault).toHaveBeenCalled();

    act(() => {
      result.current.handleSubtitlePointerEnd(up);
    });

    expect(result.current.isDraggingSubtitles).toBe(false);
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe('-80');
    expect(result.current.consumeIgnoredClick()).toBe(true);
    expect(result.current.consumeIgnoredClick()).toBe(false);
  });

  it('ignores inactive, non-primary, bubble, and horizontal pointer gestures', () => {
    const ref = overlayRef(500);
    const bubbleButton = document.createElement('button');
    const bubble = document.createElement('div');
    bubble.className = 'player-panel__my-linguist-bubble';
    bubble.appendChild(bubbleButton);

    const inactive = renderHook(() =>
      useSubtitleOverlayDrag({ overlayRef: ref, overlayActive: false }),
    );
    act(() => {
      inactive.result.current.handleSubtitlePointerDown(pointerEvent({ clientY: 20 }));
      inactive.result.current.handleSubtitlePointerMove(pointerEvent({ clientY: -80 }));
    });
    expect(inactive.result.current.verticalOffset).toBe(0);

    const { result } = renderHook(() =>
      useSubtitleOverlayDrag({ overlayRef: ref, overlayActive: true }),
    );
    act(() => {
      result.current.handleSubtitlePointerDown(pointerEvent({ isPrimary: false, clientY: 20 }));
      result.current.handleSubtitlePointerMove(pointerEvent({ clientY: -80 }));
      result.current.handleSubtitlePointerDown(pointerEvent({ target: bubbleButton, clientY: 20 }));
      result.current.handleSubtitlePointerMove(pointerEvent({ clientY: -80 }));
      result.current.handleSubtitlePointerDown(pointerEvent({ clientX: 0, clientY: 0 }));
      result.current.handleSubtitlePointerMove(pointerEvent({ clientX: 80, clientY: 5 }));
    });

    expect(result.current.verticalOffset).toBe(0);
    expect(result.current.isDraggingSubtitles).toBe(false);
    expect(result.current.consumeIgnoredClick()).toBe(false);
  });
});
