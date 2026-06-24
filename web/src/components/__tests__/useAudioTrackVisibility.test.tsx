import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import {
  ORIGINAL_AUDIO_VISIBILITY_KEY,
  TRANSLATION_AUDIO_VISIBILITY_KEY,
  useAudioTrackVisibility
} from '../player-panel/useAudioTrackVisibility';

describe('useAudioTrackVisibility', () => {
  afterEach(() => {
    window.localStorage.clear();
  });

  it('defaults both audio tracks to visible and persists that default', () => {
    const { result } = renderHook(() => useAudioTrackVisibility());

    expect(result.current.showOriginalAudio).toBe(true);
    expect(result.current.showTranslationAudio).toBe(true);
    expect(window.localStorage.getItem(ORIGINAL_AUDIO_VISIBILITY_KEY)).toBe('true');
    expect(window.localStorage.getItem(TRANSLATION_AUDIO_VISIBILITY_KEY)).toBe('true');
  });

  it('loads stored track visibility values', () => {
    window.localStorage.setItem(ORIGINAL_AUDIO_VISIBILITY_KEY, 'false');
    window.localStorage.setItem(TRANSLATION_AUDIO_VISIBILITY_KEY, 'true');

    const { result } = renderHook(() => useAudioTrackVisibility());

    expect(result.current.showOriginalAudio).toBe(false);
    expect(result.current.showTranslationAudio).toBe(true);
  });

  it('persists visibility changes', () => {
    const { result } = renderHook(() => useAudioTrackVisibility());

    act(() => {
      result.current.setShowOriginalAudio(false);
      result.current.setShowTranslationAudio(false);
    });

    expect(window.localStorage.getItem(ORIGINAL_AUDIO_VISIBILITY_KEY)).toBe('false');
    expect(window.localStorage.getItem(TRANSLATION_AUDIO_VISIBILITY_KEY)).toBe('false');
  });
});
