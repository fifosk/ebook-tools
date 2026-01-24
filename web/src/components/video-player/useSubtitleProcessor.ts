/**
 * Hook for processing subtitle tracks with style injection and cue visibility filtering.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  type CueVisibility,
  type SubtitleTrack,
  EMPTY_VTT_DATA_URL,
  decodeDataUrl,
  filterCueTextByVisibility,
  injectVttCueStyle,
  isAssSubtitleTrack,
  isVttSubtitleTrack,
  sanitiseOpacity,
  sanitiseOpacityPercent,
  selectAssSubtitleTrack,
  selectPrimarySubtitleTrack,
} from './utils';

export interface UseSubtitleProcessorOptions {
  tracks: SubtitleTrack[];
  subtitlesEnabled: boolean;
  subtitleScale: number;
  subtitleBackgroundOpacity?: number | null;
  cueVisibility: CueVisibility;
  isSafari: boolean;
  isFileProtocol: boolean;
  activeFileId: string | null;
}

export interface SubtitleProcessorState {
  processedSubtitleUrl: string;
  activeSubtitleTrack: SubtitleTrack | null;
  overlaySubtitleTrack: SubtitleTrack | null;
  subtitleOverlayActive: boolean;
  setSubtitleOverlayActive: (active: boolean) => void;
  disableNativeTrack: boolean;
  resolvedSubtitleBackgroundOpacity: number | null;
  resolvedSubtitleBackgroundOpacityPercent: number | null;
  subtitleRevision: number;
  applySubtitleTrack: (track: SubtitleTrack | null) => void;
  subtitleTrackElementRef: React.RefObject<HTMLTrackElement>;
  pendingSubtitleTrackRef: React.MutableRefObject<SubtitleTrack | null>;
  cueTextCacheRef: React.MutableRefObject<WeakMap<TextTrackCue, string>>;
}

export function useSubtitleProcessor({
  tracks,
  subtitlesEnabled,
  subtitleScale,
  subtitleBackgroundOpacity,
  cueVisibility,
  isSafari,
  isFileProtocol,
  activeFileId,
}: UseSubtitleProcessorOptions): SubtitleProcessorState {
  const subtitleTrackElementRef = useRef<HTMLTrackElement>(null);
  const pendingSubtitleTrackRef = useRef<SubtitleTrack | null>(null);
  const cueTextCacheRef = useRef<WeakMap<TextTrackCue, string>>(new WeakMap());

  const [subtitleRevision, setSubtitleRevision] = useState(0);
  const [subtitleOverlayActive, setSubtitleOverlayActive] = useState(false);
  const [processedSubtitleUrl, setProcessedSubtitleUrl] = useState<string>(EMPTY_VTT_DATA_URL);

  const activeSubtitleTrack = useMemo(() => selectPrimarySubtitleTrack(tracks), [tracks]);
  const overlaySubtitleTrack = useMemo(() => selectAssSubtitleTrack(tracks), [tracks]);

  const resolvedSubtitleBackgroundOpacity = useMemo(
    () => sanitiseOpacity(subtitleBackgroundOpacity),
    [subtitleBackgroundOpacity],
  );
  const resolvedSubtitleBackgroundOpacityPercent = useMemo(
    () => sanitiseOpacityPercent(subtitleBackgroundOpacity),
    [subtitleBackgroundOpacity],
  );

  const hasAssOverlay = Boolean(overlaySubtitleTrack);
  const disableNativeTrack = subtitleOverlayActive || (isSafari && hasAssOverlay);

  // Process subtitle URL with style injection
  useEffect(() => {
    if (!subtitlesEnabled || !activeSubtitleTrack?.url || disableNativeTrack) {
      setProcessedSubtitleUrl(EMPTY_VTT_DATA_URL);
      return;
    }

    if (resolvedSubtitleBackgroundOpacityPercent === null) {
      setProcessedSubtitleUrl(activeSubtitleTrack.url);
      return;
    }

    const candidate = activeSubtitleTrack.url ?? '';
    if (!isVttSubtitleTrack(activeSubtitleTrack)) {
      setProcessedSubtitleUrl(activeSubtitleTrack.url);
      return;
    }

    const controller = new AbortController();
    let revokedUrl: string | null = null;

    const run = async () => {
      try {
        if (candidate.startsWith('data:')) {
          const raw = decodeDataUrl(candidate);
          if (!raw) {
            setProcessedSubtitleUrl(activeSubtitleTrack.url);
            return;
          }
          const vtt = injectVttCueStyle(raw, resolvedSubtitleBackgroundOpacityPercent, subtitleScale);
          const blob = new Blob([vtt], { type: 'text/vtt' });
          const objectUrl = URL.createObjectURL(blob);
          revokedUrl = objectUrl;
          setProcessedSubtitleUrl(objectUrl);
          return;
        }
        if (isFileProtocol || typeof fetch !== 'function') {
          setProcessedSubtitleUrl(activeSubtitleTrack.url);
          return;
        }
        const response = await fetch(activeSubtitleTrack.url, { signal: controller.signal });
        if (!response.ok) {
          setProcessedSubtitleUrl(activeSubtitleTrack.url);
          return;
        }
        const raw = await response.text();
        const vtt = injectVttCueStyle(raw, resolvedSubtitleBackgroundOpacityPercent, subtitleScale);
        const blob = new Blob([vtt], { type: 'text/vtt' });
        const objectUrl = URL.createObjectURL(blob);
        revokedUrl = objectUrl;
        setProcessedSubtitleUrl(objectUrl);
      } catch (error) {
        void error;
        setProcessedSubtitleUrl(activeSubtitleTrack.url);
      }
    };

    void run();

    return () => {
      controller.abort();
      if (revokedUrl) {
        URL.revokeObjectURL(revokedUrl);
      }
    };
  }, [
    activeSubtitleTrack?.format,
    activeSubtitleTrack?.url,
    disableNativeTrack,
    isFileProtocol,
    resolvedSubtitleBackgroundOpacityPercent,
    subtitleScale,
    subtitlesEnabled,
  ]);

  const applySubtitleTrack = useCallback(
    (track: SubtitleTrack | null) => {
      const trackElement = subtitleTrackElementRef.current;
      if (!trackElement) {
        return;
      }

      const nextLanguage = track?.language || 'und';
      const nextKind = track?.kind || 'subtitles';
      const nextLabel = track?.label || 'Subtitles';

      try {
        trackElement.kind = nextKind;
        trackElement.label = nextLabel;
        trackElement.srclang = nextLanguage;
        trackElement.default = true;
      } catch (error) {
        // Ignore attribute failures in unsupported environments.
      }

      const nextSrc =
        subtitlesEnabled && track?.url && !disableNativeTrack ? processedSubtitleUrl : EMPTY_VTT_DATA_URL;
      const wantsEnabled = Boolean(
        subtitlesEnabled && track?.url && nextSrc !== EMPTY_VTT_DATA_URL && !disableNativeTrack && !isAssSubtitleTrack(track),
      );

      const setTrackSrc = (src: string) => {
        if (trackElement.getAttribute('src') !== src) {
          trackElement.setAttribute('src', src);
        }
        try {
          // Some browsers (notably iOS Safari) behave more consistently when using the property setter.
          trackElement.src = src;
        } catch (error) {
          void error;
        }
      };

      const bumpRevision = () => {
        setSubtitleRevision((value) => value + 1);
      };

      const applyEnabledMode = () => {
        try {
          const textTrack = trackElement.track;
          textTrack.mode = 'hidden';
          const show = () => {
            try {
              textTrack.mode = 'showing';
            } catch (error) {
              void error;
            }
          };
          show();
          if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
            window.requestAnimationFrame(show);
          }
          setTimeout(show, 0);
        } catch (error) {
          // Ignore text track mode failures in unsupported environments.
        }
      };

      const applyDisabledMode = () => {
        try {
          const textTrack = trackElement.track;
          textTrack.mode = 'disabled';
        } catch (error) {
          // Ignore text track mode failures in unsupported environments.
        }
      };

      const previousSrc = trackElement.getAttribute('src') ?? '';
      const needsReload = wantsEnabled && previousSrc === EMPTY_VTT_DATA_URL && nextSrc !== EMPTY_VTT_DATA_URL;

      if (needsReload) {
        // Safari can fail to restore cues after disabling a track unless the source is reloaded asynchronously.
        setTrackSrc(EMPTY_VTT_DATA_URL);
        applyDisabledMode();
        const scheduleApply = () => {
          setTrackSrc(nextSrc);
          applyEnabledMode();
          bumpRevision();
        };
        if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
          window.requestAnimationFrame(scheduleApply);
        } else {
          setTimeout(scheduleApply, 0);
        }
        return;
      }

      setTrackSrc(nextSrc);
      if (!wantsEnabled) {
        applyDisabledMode();
      } else {
        applyEnabledMode();
      }
      bumpRevision();
    },
    [disableNativeTrack, processedSubtitleUrl, subtitlesEnabled],
  );

  return {
    processedSubtitleUrl,
    activeSubtitleTrack,
    overlaySubtitleTrack,
    subtitleOverlayActive,
    setSubtitleOverlayActive,
    disableNativeTrack,
    resolvedSubtitleBackgroundOpacity,
    resolvedSubtitleBackgroundOpacityPercent,
    subtitleRevision,
    applySubtitleTrack,
    subtitleTrackElementRef,
    pendingSubtitleTrackRef,
    cueTextCacheRef,
  };
}

/**
 * Hook to apply cue visibility filtering to active text tracks.
 */
export function useCueVisibilityFilter(
  videoRef: React.RefObject<HTMLVideoElement | null>,
  cueVisibility: CueVisibility,
  subtitlesEnabled: boolean,
  activeFileId: string | null,
  subtitleRevision: number,
  cueTextCacheRef: React.MutableRefObject<WeakMap<TextTrackCue, string>>,
): void {
  useEffect(() => {
    if (!subtitlesEnabled) {
      return;
    }
    const element = videoRef.current;
    if (!element || !element.textTracks) {
      return;
    }
    const track =
      Array.from(element.textTracks).find((item) => item.mode === 'showing' || item.mode === 'hidden') ??
      element.textTracks[0] ??
      null;
    if (!track) {
      return;
    }

    const cache = cueTextCacheRef.current;

    const applyCueVisibility = () => {
      const cues = track.cues;
      if (!cues) {
        return;
      }
      for (let index = 0; index < cues.length; index += 1) {
        const cue = cues[index];
        const cueWithText = cue as VTTCue & { text?: string };
        const baseText = cache.get(cue) ?? cueWithText.text ?? '';
        if (!cache.has(cue)) {
          cache.set(cue, baseText);
        }
        const filteredText = filterCueTextByVisibility(baseText, cueVisibility);
        if (cueWithText.text !== filteredText && typeof cueWithText.text === 'string') {
          cueWithText.text = filteredText;
        }
      }
    };

    applyCueVisibility();
    track.addEventListener('cuechange', applyCueVisibility);
    return () => {
      track.removeEventListener('cuechange', applyCueVisibility);
    };
  }, [cueVisibility, subtitlesEnabled, activeFileId, subtitleRevision, cueTextCacheRef, videoRef]);
}
