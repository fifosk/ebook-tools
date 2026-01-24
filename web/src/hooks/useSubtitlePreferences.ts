/**
 * Hook for managing subtitle display preferences with localStorage persistence.
 *
 * Consolidates subtitle-related state: visibility toggles, scale settings,
 * and background opacity. All preferences are persisted per-job in localStorage.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';

// Scale constants
const SUBTITLE_SCALE_DEFAULT = 1;
const SUBTITLE_SCALE_MIN = 0.5;
const SUBTITLE_SCALE_MAX = 2;
const SUBTITLE_SCALE_FULLSCREEN_DEFAULT = 1.35;
const SUBTITLE_SCALE_FULLSCREEN_MIN = 0.75;
const SUBTITLE_SCALE_FULLSCREEN_MAX = 4;
const SUBTITLE_BACKGROUND_OPACITY_DEFAULT = 70;

export interface CueVisibility {
  original: boolean;
  transliteration: boolean;
  translation: boolean;
}

export interface SubtitlePreferences {
  // Subtitle visibility
  subtitlesEnabled: boolean;
  setSubtitlesEnabled: (enabled: boolean) => void;
  toggleSubtitles: () => void;

  // Cue layer visibility
  cueVisibility: CueVisibility;
  toggleCueVisibility: (key: keyof CueVisibility) => void;

  // Scale settings
  subtitleScale: number;
  fullscreenSubtitleScale: number;
  setSubtitleScale: (scale: number) => void;
  setFullscreenSubtitleScale: (scale: number) => void;
  adjustSubtitleScale: (direction: 'increase' | 'decrease', isFullscreen: boolean, step: number) => void;

  // Background opacity
  subtitleBackgroundOpacityPercent: number;
  setSubtitleBackgroundOpacityPercent: (percent: number) => void;

  // Computed active values based on fullscreen state
  getActiveScale: (isFullscreen: boolean) => number;
  getActiveScaleMin: (isFullscreen: boolean) => number;
  getActiveScaleMax: (isFullscreen: boolean) => number;

  // Constants for external use
  constants: {
    SUBTITLE_SCALE_MIN: number;
    SUBTITLE_SCALE_MAX: number;
    SUBTITLE_SCALE_FULLSCREEN_MIN: number;
    SUBTITLE_SCALE_FULLSCREEN_MAX: number;
  };
}

interface UseSubtitlePreferencesOptions {
  jobId: string;
}

export function useSubtitlePreferences({ jobId }: UseSubtitlePreferencesOptions): SubtitlePreferences {
  // State
  const [subtitlesEnabled, setSubtitlesEnabled] = useState(true);
  const [cueVisibility, setCueVisibility] = useState<CueVisibility>({
    original: true,
    transliteration: true,
    translation: true,
  });
  const [subtitleScale, setSubtitleScaleState] = useState(SUBTITLE_SCALE_DEFAULT);
  const [fullscreenSubtitleScale, setFullscreenSubtitleScaleState] = useState(SUBTITLE_SCALE_FULLSCREEN_DEFAULT);
  const [subtitleBackgroundOpacityPercent, setSubtitleBackgroundOpacityPercentState] = useState(
    SUBTITLE_BACKGROUND_OPACITY_DEFAULT
  );

  // Storage keys
  const cuePreferenceKey = useMemo(() => `youtube-dub-cue-preference-${jobId}`, [jobId]);
  const subtitleScaleKey = useMemo(() => `youtube-dub-subtitle-scale-${jobId}`, [jobId]);
  const fullscreenSubtitleScaleKey = useMemo(() => `youtube-dub-subtitle-scale-fullscreen-${jobId}`, [jobId]);
  const subtitleBackgroundOpacityKey = useMemo(() => `youtube-dub-subtitle-bg-opacity-${jobId}`, [jobId]);

  // Toggle functions
  const toggleSubtitles = useCallback(() => {
    setSubtitlesEnabled((current) => !current);
  }, []);

  const toggleCueVisibility = useCallback((key: keyof CueVisibility) => {
    setCueVisibility((current) => ({ ...current, [key]: !current[key] }));
  }, []);

  // Scale setters with clamping
  const setSubtitleScale = useCallback((value: number) => {
    if (!Number.isFinite(value)) return;
    const clamped = Math.min(Math.max(value, SUBTITLE_SCALE_MIN), SUBTITLE_SCALE_MAX);
    setSubtitleScaleState(clamped);
  }, []);

  const setFullscreenSubtitleScale = useCallback((value: number) => {
    if (!Number.isFinite(value)) return;
    const clamped = Math.min(Math.max(value, SUBTITLE_SCALE_FULLSCREEN_MIN), SUBTITLE_SCALE_FULLSCREEN_MAX);
    setFullscreenSubtitleScaleState(clamped);
  }, []);

  const setSubtitleBackgroundOpacityPercent = useCallback((value: number) => {
    if (!Number.isFinite(value)) return;
    const clamped = Math.min(Math.max(value, 0), 100);
    const snapped = Math.round(clamped / 10) * 10;
    setSubtitleBackgroundOpacityPercentState(snapped);
  }, []);

  const adjustSubtitleScale = useCallback(
    (direction: 'increase' | 'decrease', isFullscreen: boolean, step: number) => {
      const min = isFullscreen ? SUBTITLE_SCALE_FULLSCREEN_MIN : SUBTITLE_SCALE_MIN;
      const max = isFullscreen ? SUBTITLE_SCALE_FULLSCREEN_MAX : SUBTITLE_SCALE_MAX;
      const setter = isFullscreen ? setFullscreenSubtitleScaleState : setSubtitleScaleState;
      setter((current) => {
        const delta = direction === 'increase' ? step : -step;
        const next = Math.min(Math.max(current + delta, min), max);
        const snapped = Math.round(next * 100) / 100;
        return Math.abs(snapped - current) < 1e-4 ? current : snapped;
      });
    },
    []
  );

  // Computed getters
  const getActiveScale = useCallback(
    (isFullscreen: boolean) => (isFullscreen ? fullscreenSubtitleScale : subtitleScale),
    [fullscreenSubtitleScale, subtitleScale]
  );

  const getActiveScaleMin = useCallback(
    (isFullscreen: boolean) => (isFullscreen ? SUBTITLE_SCALE_FULLSCREEN_MIN : SUBTITLE_SCALE_MIN),
    []
  );

  const getActiveScaleMax = useCallback(
    (isFullscreen: boolean) => (isFullscreen ? SUBTITLE_SCALE_FULLSCREEN_MAX : SUBTITLE_SCALE_MAX),
    []
  );

  // Load cue visibility from localStorage
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const stored = window.localStorage.getItem(cuePreferenceKey);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed && typeof parsed === 'object') {
          setCueVisibility((current) => ({
            original: typeof parsed.original === 'boolean' ? parsed.original : current.original,
            transliteration:
              typeof parsed.transliteration === 'boolean' ? parsed.transliteration : current.transliteration,
            translation: typeof parsed.translation === 'boolean' ? parsed.translation : current.translation,
          }));
        }
      }
    } catch {
      // Ignore parse errors
    }
  }, [cuePreferenceKey]);

  // Reset scales when job changes
  useEffect(() => {
    if (typeof window === 'undefined') return;
    setSubtitleScaleState(SUBTITLE_SCALE_DEFAULT);
  }, [subtitleScaleKey]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    setFullscreenSubtitleScaleState(SUBTITLE_SCALE_FULLSCREEN_DEFAULT);
  }, [fullscreenSubtitleScaleKey]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    setSubtitleBackgroundOpacityPercentState(SUBTITLE_BACKGROUND_OPACITY_DEFAULT);
  }, [subtitleBackgroundOpacityKey]);

  // Load subtitle scale from localStorage
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const stored = window.localStorage.getItem(subtitleScaleKey);
      if (!stored) return;
      const parsed = Number(stored);
      if (!Number.isFinite(parsed)) return;
      setSubtitleScaleState((current) => {
        const next = Math.min(Math.max(parsed, SUBTITLE_SCALE_MIN), SUBTITLE_SCALE_MAX);
        return Math.abs(next - current) < 1e-3 ? current : next;
      });
    } catch {
      // Ignore parse errors
    }
  }, [subtitleScaleKey]);

  // Load fullscreen subtitle scale from localStorage
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const stored = window.localStorage.getItem(fullscreenSubtitleScaleKey);
      if (!stored) return;
      const parsed = Number(stored);
      if (!Number.isFinite(parsed)) return;
      setFullscreenSubtitleScaleState((current) => {
        const next = Math.min(Math.max(parsed, SUBTITLE_SCALE_FULLSCREEN_MIN), SUBTITLE_SCALE_FULLSCREEN_MAX);
        return Math.abs(next - current) < 1e-3 ? current : next;
      });
    } catch {
      // Ignore parse errors
    }
  }, [fullscreenSubtitleScaleKey]);

  // Load background opacity from localStorage
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const stored = window.localStorage.getItem(subtitleBackgroundOpacityKey);
      if (!stored) return;
      const parsed = Number(stored);
      if (!Number.isFinite(parsed)) return;
      setSubtitleBackgroundOpacityPercentState((current) => {
        const clamped = Math.min(Math.max(parsed, 0), 100);
        const next = Math.round(clamped / 10) * 10;
        return next === current ? current : next;
      });
    } catch {
      // Ignore parse errors
    }
  }, [subtitleBackgroundOpacityKey]);

  // Save cue visibility to localStorage
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.setItem(cuePreferenceKey, JSON.stringify(cueVisibility));
    } catch {
      // Ignore storage errors
    }
  }, [cuePreferenceKey, cueVisibility]);

  // Save subtitle scale to localStorage
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.setItem(subtitleScaleKey, subtitleScale.toString());
    } catch {
      // Ignore storage errors
    }
  }, [subtitleScale, subtitleScaleKey]);

  // Save fullscreen subtitle scale to localStorage
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.setItem(fullscreenSubtitleScaleKey, fullscreenSubtitleScale.toString());
    } catch {
      // Ignore storage errors
    }
  }, [fullscreenSubtitleScale, fullscreenSubtitleScaleKey]);

  // Save background opacity to localStorage
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.setItem(subtitleBackgroundOpacityKey, subtitleBackgroundOpacityPercent.toString());
    } catch {
      // Ignore storage errors
    }
  }, [subtitleBackgroundOpacityKey, subtitleBackgroundOpacityPercent]);

  return {
    subtitlesEnabled,
    setSubtitlesEnabled,
    toggleSubtitles,
    cueVisibility,
    toggleCueVisibility,
    subtitleScale,
    fullscreenSubtitleScale,
    setSubtitleScale,
    setFullscreenSubtitleScale,
    adjustSubtitleScale,
    subtitleBackgroundOpacityPercent,
    setSubtitleBackgroundOpacityPercent,
    getActiveScale,
    getActiveScaleMin,
    getActiveScaleMax,
    constants: {
      SUBTITLE_SCALE_MIN,
      SUBTITLE_SCALE_MAX,
      SUBTITLE_SCALE_FULLSCREEN_MIN,
      SUBTITLE_SCALE_FULLSCREEN_MAX,
    },
  };
}
