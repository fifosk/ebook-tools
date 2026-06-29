import { act, renderHook, waitFor } from '@testing-library/react';
import type { MutableRefObject } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { SubtitleTrack } from '../../../lib/subtitles';
import { useAssSubtitleCues } from '../useAssSubtitleCues';

const ASS_PAYLOAD = [
  '[Events]',
  'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text',
  'Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,hello {\\b1}world{\\b0}\\Nhola mundo',
].join('\n');

function dataTrack(payload = ASS_PAYLOAD): SubtitleTrack {
  return {
    url: `data:text/ass;charset=utf-8,${encodeURIComponent(payload)}`,
    format: 'ass',
    language: 'nl',
  };
}

function videoRef(): MutableRefObject<HTMLVideoElement | null> {
  return { current: document.createElement('video') };
}

describe('useAssSubtitleCues', () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('parses ASS cues from data URLs when loading is immediate', async () => {
    const { result } = renderHook(() =>
      useAssSubtitleCues({
        videoRef: videoRef(),
        track: dataTrack(),
        enabled: true,
        deferLoadUntilPlay: false,
      }),
    );

    await waitFor(() => expect(result.current.cues).toHaveLength(1));
    expect(result.current.shouldLoadAss).toBe(true);
    expect(result.current.overlayActive).toBe(true);
    expect(result.current.cues[0]?.tracks.translation?.tokens).toEqual(['hola', 'mundo']);
    expect(result.current.cues[0]?.tracks.original?.currentIndex).toBe(1);
  });

  it('defers parsing until video metadata has settled', async () => {
    vi.useFakeTimers();
    const ref = videoRef();
    const { result } = renderHook(() =>
      useAssSubtitleCues({
        videoRef: ref,
        track: dataTrack(),
        enabled: true,
        deferLoadUntilPlay: true,
      }),
    );

    expect(result.current.shouldLoadAss).toBe(false);
    expect(result.current.overlayActive).toBe(false);

    await act(async () => {
      ref.current?.dispatchEvent(new Event('loadedmetadata'));
      await vi.advanceTimersByTimeAsync(750);
    });
    vi.useRealTimers();

    await waitFor(() => expect(result.current.cues).toHaveLength(1));
    expect(result.current.shouldLoadAss).toBe(true);
  });

  it('clears cues when disabled after a successful load', async () => {
    const ref = videoRef();
    const { result, rerender } = renderHook(
      ({ enabled }) =>
        useAssSubtitleCues({
          videoRef: ref,
          track: dataTrack(),
          enabled,
          deferLoadUntilPlay: false,
        }),
      { initialProps: { enabled: true } },
    );

    await waitFor(() => expect(result.current.cues).toHaveLength(1));

    rerender({ enabled: false });

    await waitFor(() => expect(result.current.cues).toHaveLength(0));
    expect(result.current.shouldLoadAss).toBe(false);
    expect(result.current.overlayActive).toBe(false);
  });

  it('returns an inactive overlay when remote ASS fetching fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: false, text: async () => ASS_PAYLOAD })),
    );

    const { result } = renderHook(() =>
      useAssSubtitleCues({
        videoRef: videoRef(),
        track: { url: '/missing.ass', format: 'ass' },
        enabled: true,
        deferLoadUntilPlay: false,
      }),
    );

    await waitFor(() => expect(result.current.shouldLoadAss).toBe(true));
    expect(result.current.cues).toEqual([]);
    expect(result.current.overlayActive).toBe(false);
  });
});
