import { act, renderHook } from '@testing-library/react';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import type { LiveMediaChunk } from '../../hooks/useLiveMedia';
import { usePendingChunkSelection } from '../player-panel/usePendingChunkSelection';
import type { PendingChunkSelection } from '../player-panel/usePlayerPanelSelectionState';

function chunk(overrides: Partial<LiveMediaChunk> = {}): LiveMediaChunk {
  return {
    chunkId: 'chunk-1',
    rangeFragment: 'range-1',
    startSentence: 1,
    endSentence: 2,
    files: [],
    ...overrides,
  };
}

function renderPendingChunkSelection(
  initialSelection: PendingChunkSelection | null,
  chunks: LiveMediaChunk[] = [chunk()],
) {
  const activateChunk = vi.fn(() => true);
  const hook = renderHook(() => {
    const [pendingChunkSelection, setPendingChunkSelection] = useState<PendingChunkSelection | null>(
      initialSelection,
    );

    usePendingChunkSelection({
      chunks,
      pendingChunkSelection,
      setPendingChunkSelection,
      activateChunk,
    });

    return {
      pendingChunkSelection,
      setPendingChunkSelection,
    };
  });

  return {
    ...hook,
    activateChunk,
  };
}

describe('usePendingChunkSelection', () => {
  it('activates a valid pending chunk and clears the request', () => {
    const { result, activateChunk } = renderPendingChunkSelection({ index: 0, token: 1 });

    expect(activateChunk).toHaveBeenCalledWith(expect.objectContaining({ chunkId: 'chunk-1' }), {
      scrollRatio: 0,
    });
    expect(result.current.pendingChunkSelection).toBeNull();
  });

  it('clears out-of-range pending selections without activating a chunk', () => {
    const { result, activateChunk } = renderPendingChunkSelection({ index: 2, token: 1 }, [
      chunk({ chunkId: 'chunk-1' }),
    ]);

    expect(activateChunk).not.toHaveBeenCalled();
    expect(result.current.pendingChunkSelection).toBeNull();
  });

  it('waits until a pending selection is provided', () => {
    const { result, activateChunk } = renderPendingChunkSelection(null, [
      chunk({ chunkId: 'chunk-1' }),
      chunk({ chunkId: 'chunk-2' }),
    ]);

    expect(activateChunk).not.toHaveBeenCalled();

    act(() => {
      result.current.setPendingChunkSelection({ index: 1, token: 2 });
    });

    expect(activateChunk).toHaveBeenCalledWith(expect.objectContaining({ chunkId: 'chunk-2' }), {
      scrollRatio: 0,
    });
    expect(result.current.pendingChunkSelection).toBeNull();
  });
});
