import { useEffect, useState } from 'react';
import type { MutableRefObject } from 'react';
import {
  decodeDataUrl,
  isAssSubtitleTrack,
  parseAssSubtitles,
  type AssSubtitleCue,
  type SubtitleTrack,
} from '../../lib/subtitles';

type UseAssSubtitleCuesOptions = {
  videoRef: MutableRefObject<HTMLVideoElement | null>;
  track: SubtitleTrack | null;
  enabled: boolean;
  deferLoadUntilPlay: boolean;
};

type UseAssSubtitleCuesResult = {
  cues: AssSubtitleCue[];
  shouldLoadAss: boolean;
  overlayActive: boolean;
};

export function useAssSubtitleCues({
  videoRef,
  track,
  enabled,
  deferLoadUntilPlay,
}: UseAssSubtitleCuesOptions): UseAssSubtitleCuesResult {
  const [assReadyToLoad, setAssReadyToLoad] = useState(!deferLoadUntilPlay);
  const [cues, setCues] = useState<AssSubtitleCue[]>([]);
  const shouldLoadAss = enabled && assReadyToLoad && isAssSubtitleTrack(track);
  const overlayActive = enabled && shouldLoadAss && cues.length > 0;

  useEffect(() => {
    setAssReadyToLoad(!deferLoadUntilPlay);
  }, [deferLoadUntilPlay, track?.format, track?.url]);

  useEffect(() => {
    if (!deferLoadUntilPlay || assReadyToLoad) {
      return;
    }
    const video = videoRef.current;
    if (!video) {
      return;
    }
    let timeoutId: number | null = null;
    const markReady = () => {
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId);
        timeoutId = null;
      }
      setAssReadyToLoad(true);
    };
    const handlePlay = () => {
      markReady();
    };
    const handleLoadedMetadata = () => {
      if (timeoutId !== null) {
        return;
      }
      timeoutId = window.setTimeout(markReady, 750);
    };
    video.addEventListener('play', handlePlay);
    video.addEventListener('loadedmetadata', handleLoadedMetadata);
    return () => {
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('loadedmetadata', handleLoadedMetadata);
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [assReadyToLoad, deferLoadUntilPlay, videoRef]);

  useEffect(() => {
    if (!shouldLoadAss || typeof fetch !== 'function' || typeof window === 'undefined') {
      setCues([]);
      return;
    }
    const controller = new AbortController();
    const run = async () => {
      try {
        const raw =
          track!.url.startsWith('data:')
            ? decodeDataUrl(track!.url)
            : await (async () => {
                const resolved = new URL(track!.url, window.location.href).toString();
                const response = await fetch(resolved, { signal: controller.signal });
                if (!response.ok) {
                  return null;
                }
                return response.text();
              })();
        if (!raw) {
          setCues([]);
          return;
        }
        const parsed = parseAssSubtitles(raw);
        setCues(parsed);
      } catch (error) {
        void error;
        setCues([]);
      }
    };
    void run();
    return () => controller.abort();
  }, [shouldLoadAss, track?.url]);

  return { cues, shouldLoadAss, overlayActive };
}
