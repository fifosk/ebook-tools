import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchBookCreationOptions } from '../../api/createBook';
import {
  DEFAULT_FLUSH_SENTENCES,
  DEFAULT_ORIGINAL_MIX_PERCENT,
  DEFAULT_TARGET_HEIGHT
} from '../video-dubbing/videoDubbingConfig';
import { useVideoDubbingOutputState } from '../video-dubbing/useVideoDubbingOutputState';

vi.mock('../../api/createBook', () => ({
  fetchBookCreationOptions: vi.fn()
}));

const mockFetchBookCreationOptions = vi.mocked(fetchBookCreationOptions);

function creationOptions(overrides: Record<string, unknown> = {}) {
  return {
    youtube_dub_defaults: {
      original_mix_percent: 8,
      flush_sentences: 6,
      translation_batch_size: 5,
      target_height: 720,
      preserve_aspect_ratio: false,
      split_batches: false,
      stitch_batches: false,
      ...overrides
    }
  } as Awaited<ReturnType<typeof fetchBookCreationOptions>>;
}

describe('useVideoDubbingOutputState', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchBookCreationOptions.mockResolvedValue(creationOptions());
  });

  it('loads backend YouTube dubbing defaults when there is no prefill', async () => {
    const { result } = renderHook(() => useVideoDubbingOutputState());

    await waitFor(() => expect(result.current.originalMixPercent).toBe(8));

    expect(mockFetchBookCreationOptions).toHaveBeenCalledTimes(1);
    expect(result.current.flushSentences).toBe(6);
    expect(result.current.translationBatchSize).toBe(5);
    expect(result.current.targetHeight).toBe(720);
    expect(result.current.preserveAspectRatio).toBe(false);
    expect(result.current.splitBatches).toBe(false);
    expect(result.current.stitchBatches).toBe(false);
  });

  it('preserves user edits that happen before backend defaults resolve', async () => {
    let resolveOptions: (value: Awaited<ReturnType<typeof fetchBookCreationOptions>>) => void = () => {};
    mockFetchBookCreationOptions.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveOptions = resolve;
      })
    );

    const { result } = renderHook(() => useVideoDubbingOutputState());

    act(() => {
      result.current.setOriginalMixPercent(22);
      result.current.setTargetHeight(320);
    });

    await act(async () => {
      resolveOptions(creationOptions());
    });

    expect(result.current.originalMixPercent).toBe(22);
    expect(result.current.targetHeight).toBe(320);
    expect(result.current.flushSentences).toBe(6);
    expect(result.current.translationBatchSize).toBe(5);
  });

  it('applies output values from job prefill and skips backend defaults', async () => {
    const { result } = renderHook(() =>
      useVideoDubbingOutputState({
        prefillParameters: {
          start_time_offset_seconds: 65,
          end_time_offset_seconds: 3661,
          original_mix_percent: 13,
          flush_sentences: 9,
          translation_batch_size: 4,
          target_height: 720,
          preserve_aspect_ratio: false,
          split_batches: false,
          include_transliteration: false
        }
      })
    );

    await waitFor(() => expect(result.current.startOffset).toBe('01:05'));

    expect(mockFetchBookCreationOptions).not.toHaveBeenCalled();
    expect(result.current.endOffset).toBe('01:01:01');
    expect(result.current.originalMixPercent).toBe(13);
    expect(result.current.flushSentences).toBe(9);
    expect(result.current.translationBatchSize).toBe(4);
    expect(result.current.targetHeight).toBe(720);
    expect(result.current.preserveAspectRatio).toBe(false);
    expect(result.current.splitBatches).toBe(false);
    expect(result.current.includeTransliteration).toBe(false);
    expect(result.current.stitchBatches).toBe(true);
    expect(result.current.enableLookupCache).toBe(true);
  });

  it('starts from built-in defaults before async defaults arrive', () => {
    mockFetchBookCreationOptions.mockReturnValueOnce(new Promise(() => {}));

    const { result } = renderHook(() => useVideoDubbingOutputState());

    expect(result.current.originalMixPercent).toBe(DEFAULT_ORIGINAL_MIX_PERCENT);
    expect(result.current.flushSentences).toBe(DEFAULT_FLUSH_SENTENCES);
    expect(result.current.targetHeight).toBe(DEFAULT_TARGET_HEIGHT);
  });
});
