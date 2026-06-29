import { act, renderHook } from '@testing-library/react';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import type { LiveMediaChunk, LiveMediaItem } from '../../hooks/useLiveMedia';
import type { MediaCategory } from '../player-panel/constants';
import { usePlayerPanelTextActivation } from '../player-panel/usePlayerPanelTextActivation';

type SelectionState = Record<MediaCategory, string | null>;

function chunk(overrides: Partial<LiveMediaChunk> = {}): LiveMediaChunk {
  return {
    chunkId: 'chunk-1',
    rangeFragment: 'range-1',
    startSentence: 1,
    endSentence: 2,
    files: [
      {
        type: 'text',
        url: '/media/range-1.html',
        name: 'range-1.html',
        source: 'completed',
      },
    ],
    ...overrides,
  };
}

function item(overrides: Partial<LiveMediaItem> = {}): LiveMediaItem {
  return {
    ...overrides,
    type: overrides.type ?? 'text',
    url: overrides.url ?? '/media/standalone.html',
    name: overrides.name ?? 'standalone.html',
    source: overrides.source ?? 'completed',
  };
}

function renderTextActivation(overrides: Partial<Parameters<typeof usePlayerPanelTextActivation>[0]> = {}) {
  const activateChunk = vi.fn(() => true);
  const deriveBaseId = vi.fn((mediaItem: LiveMediaItem) => mediaItem.name?.replace(/\.[^.]+$/, '') ?? null);
  const requestAutoPlay = vi.fn();
  const initialSelection: SelectionState = { text: null, audio: null, video: null };

  const hook = renderHook(() => {
    const [selectedItemIds, setSelectedItemIds] = useState<SelectionState>(initialSelection);
    const [pendingTextScrollRatio, setPendingTextScrollRatio] = useState<number | null>(null);
    const activateTextItem = usePlayerPanelTextActivation({
      chunks: [chunk()],
      deriveBaseId,
      activateChunk,
      setSelectedItemIds,
      setPendingTextScrollRatio,
      requestAutoPlay,
      ...overrides,
    });
    return {
      activateTextItem,
      selectedItemIds,
      pendingTextScrollRatio,
    };
  });

  return {
    ...hook,
    activateChunk,
    deriveBaseId,
    requestAutoPlay,
  };
}

describe('usePlayerPanelTextActivation', () => {
  it('delegates matching text items to chunk activation', () => {
    const { result, activateChunk, requestAutoPlay } = renderTextActivation();

    let activated = false;
    act(() => {
      activated = result.current.activateTextItem(item({ url: '/media/range-1.html', name: 'range-1.html' }), {
        autoPlay: true,
        scrollRatio: 0,
      });
    });

    expect(activated).toBe(true);
    expect(activateChunk).toHaveBeenCalledWith(expect.objectContaining({ chunkId: 'chunk-1' }), {
      autoPlay: true,
      scrollRatio: 0,
    });
    expect(requestAutoPlay).not.toHaveBeenCalled();
    expect(result.current.selectedItemIds.text).toBeNull();
  });

  it('selects standalone text items and clamps scroll requests', () => {
    const { result, activateChunk, requestAutoPlay } = renderTextActivation({
      chunks: [],
    });

    let activated = true;
    act(() => {
      activated = result.current.activateTextItem(item(), {
        autoPlay: true,
        scrollRatio: 1.5,
      });
    });

    expect(activated).toBe(false);
    expect(activateChunk).not.toHaveBeenCalled();
    expect(result.current.selectedItemIds.text).toBe('/media/standalone.html');
    expect(result.current.pendingTextScrollRatio).toBe(1);
    expect(requestAutoPlay).toHaveBeenCalledTimes(1);
  });

  it('ignores missing text urls', () => {
    const { result, activateChunk, requestAutoPlay } = renderTextActivation();

    let activated = true;
    act(() => {
      activated = result.current.activateTextItem(item({ url: '' }));
    });

    expect(activated).toBe(false);
    expect(activateChunk).not.toHaveBeenCalled();
    expect(requestAutoPlay).not.toHaveBeenCalled();
    expect(result.current.selectedItemIds.text).toBeNull();
  });
});
