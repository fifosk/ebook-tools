import { useCallback, useEffect, useState } from 'react';
import type { InteractiveTextTheme } from '../../types/interactiveTextTheme';
import { DEFAULT_INTERACTIVE_TEXT_THEME, loadInteractiveTextTheme } from '../../types/interactiveTextTheme';
import {
  DEFAULT_INTERACTIVE_FONT_SCALE_PERCENT,
  DEFAULT_INTERACTIVE_TEXT_BG_OPACITY_PERCENT,
  DEFAULT_INTERACTIVE_TEXT_SENTENCE_CARD_OPACITY_PERCENT,
  DEFAULT_TRANSLATION_SPEED,
  FONT_SCALE_MAX,
  FONT_SCALE_MIN,
  FONT_SCALE_STEP,
  TRANSLATION_SPEED_STEP,
  normaliseTranslationSpeed,
  type TranslationSpeed,
} from './constants';

type CueVisibility = {
  original: boolean;
  transliteration: boolean;
  translation: boolean;
};

type UseInteractiveTextSettingsResult = {
  interactiveTextVisibility: CueVisibility;
  toggleInteractiveTextLayer: (key: keyof CueVisibility) => void;
  translationSpeed: TranslationSpeed;
  setTranslationSpeed: (speed: TranslationSpeed) => void;
  adjustTranslationSpeed: (direction: 'faster' | 'slower') => void;
  fontScalePercent: number;
  setFontScalePercent: (percent: number) => void;
  adjustFontScale: (direction: 'increase' | 'decrease') => void;
  interactiveTextTheme: InteractiveTextTheme;
  setInteractiveTextTheme: (theme: InteractiveTextTheme) => void;
  interactiveBackgroundOpacityPercent: number;
  setInteractiveBackgroundOpacityPercent: (value: number) => void;
  interactiveSentenceCardOpacityPercent: number;
  setInteractiveSentenceCardOpacityPercent: (value: number) => void;
  resetInteractiveTextSettings: () => void;
};

const FONT_SCALE_STORAGE_KEY = 'player-panel.fontScalePercent';
const INTERACTIVE_TEXT_VISIBILITY_STORAGE_KEY = 'player-panel.interactiveText.visibility';
const INTERACTIVE_TEXT_THEME_STORAGE_KEY = 'player-panel.interactiveText.theme';
const INTERACTIVE_TEXT_BG_OPACITY_STORAGE_KEY = 'player-panel.interactiveText.backgroundOpacityPercent';
const INTERACTIVE_TEXT_SENTENCE_CARD_OPACITY_STORAGE_KEY = 'player-panel.interactiveText.sentenceCardOpacityPercent';
const clampFontScalePercent = (value: number) =>
  Math.min(Math.max(value, FONT_SCALE_MIN), FONT_SCALE_MAX);
const clampPercent = (value: number) => Math.round(Math.min(Math.max(value, 0), 100));

export function useInteractiveTextSettings(): UseInteractiveTextSettingsResult {
  const [interactiveTextVisibility, setInteractiveTextVisibility] = useState<CueVisibility>(() => {
    const fallback = { original: true, transliteration: true, translation: true };
    if (typeof window === 'undefined') {
      return fallback;
    }
    const stored = window.localStorage.getItem(INTERACTIVE_TEXT_VISIBILITY_STORAGE_KEY);
    if (!stored) {
      return fallback;
    }
    try {
      const parsed = JSON.parse(stored) as Record<string, unknown>;
      return {
        original: typeof parsed.original === 'boolean' ? parsed.original : fallback.original,
        transliteration:
          typeof parsed.transliteration === 'boolean' ? parsed.transliteration : fallback.transliteration,
        translation: typeof parsed.translation === 'boolean' ? parsed.translation : fallback.translation,
      };
    } catch {
      return fallback;
    }
  });
  const [translationSpeed, setTranslationSpeedState] = useState<TranslationSpeed>(DEFAULT_TRANSLATION_SPEED);
  const [fontScalePercent, setFontScalePercentState] = useState<number>(() => {
    if (typeof window === 'undefined') {
      return DEFAULT_INTERACTIVE_FONT_SCALE_PERCENT;
    }
    const raw = Number.parseFloat(window.localStorage.getItem(FONT_SCALE_STORAGE_KEY) ?? '');
    return Number.isFinite(raw) ? clampFontScalePercent(raw) : DEFAULT_INTERACTIVE_FONT_SCALE_PERCENT;
  });
  const [interactiveTextTheme, setInteractiveTextThemeState] = useState<InteractiveTextTheme>(() =>
    loadInteractiveTextTheme(INTERACTIVE_TEXT_THEME_STORAGE_KEY),
  );
  const [interactiveBackgroundOpacityPercent, setInteractiveBackgroundOpacityPercentState] = useState<number>(() => {
    if (typeof window === 'undefined') {
      return DEFAULT_INTERACTIVE_TEXT_BG_OPACITY_PERCENT;
    }
    const raw = Number.parseFloat(window.localStorage.getItem(INTERACTIVE_TEXT_BG_OPACITY_STORAGE_KEY) ?? '');
    if (!Number.isFinite(raw)) {
      return DEFAULT_INTERACTIVE_TEXT_BG_OPACITY_PERCENT;
    }
    return clampPercent(raw);
  });
  const [interactiveSentenceCardOpacityPercent, setInteractiveSentenceCardOpacityPercentState] = useState<number>(() => {
    if (typeof window === 'undefined') {
      return DEFAULT_INTERACTIVE_TEXT_SENTENCE_CARD_OPACITY_PERCENT;
    }
    const raw = Number.parseFloat(window.localStorage.getItem(INTERACTIVE_TEXT_SENTENCE_CARD_OPACITY_STORAGE_KEY) ?? '');
    if (!Number.isFinite(raw)) {
      return DEFAULT_INTERACTIVE_TEXT_SENTENCE_CARD_OPACITY_PERCENT;
    }
    return clampPercent(raw);
  });

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    window.localStorage.setItem(INTERACTIVE_TEXT_VISIBILITY_STORAGE_KEY, JSON.stringify(interactiveTextVisibility));
  }, [interactiveTextVisibility]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    window.localStorage.setItem(FONT_SCALE_STORAGE_KEY, String(fontScalePercent));
  }, [fontScalePercent]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    window.localStorage.setItem(INTERACTIVE_TEXT_THEME_STORAGE_KEY, JSON.stringify(interactiveTextTheme));
  }, [interactiveTextTheme]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    window.localStorage.setItem(INTERACTIVE_TEXT_BG_OPACITY_STORAGE_KEY, String(interactiveBackgroundOpacityPercent));
  }, [interactiveBackgroundOpacityPercent]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    window.localStorage.setItem(
      INTERACTIVE_TEXT_SENTENCE_CARD_OPACITY_STORAGE_KEY,
      String(interactiveSentenceCardOpacityPercent),
    );
  }, [interactiveSentenceCardOpacityPercent]);

  const toggleInteractiveTextLayer = useCallback((key: keyof CueVisibility) => {
    setInteractiveTextVisibility((current) => ({ ...current, [key]: !current[key] }));
  }, []);

  const setTranslationSpeed = useCallback((speed: TranslationSpeed) => {
    setTranslationSpeedState(normaliseTranslationSpeed(speed));
  }, []);

  const adjustTranslationSpeed = useCallback((direction: 'faster' | 'slower') => {
    setTranslationSpeedState((current) => {
      const delta = direction === 'faster' ? TRANSLATION_SPEED_STEP : -TRANSLATION_SPEED_STEP;
      return normaliseTranslationSpeed(current + delta);
    });
  }, []);

  const setFontScalePercent = useCallback((percent: number) => {
    setFontScalePercentState(clampFontScalePercent(percent));
  }, []);

  const adjustFontScale = useCallback((direction: 'increase' | 'decrease') => {
    setFontScalePercentState((current) => {
      const delta = direction === 'increase' ? FONT_SCALE_STEP : -FONT_SCALE_STEP;
      return clampFontScalePercent(current + delta);
    });
  }, []);

  const setInteractiveTextTheme = useCallback((theme: InteractiveTextTheme) => {
    setInteractiveTextThemeState(theme);
  }, []);

  const setInteractiveBackgroundOpacityPercent = useCallback((value: number) => {
    setInteractiveBackgroundOpacityPercentState(clampPercent(value));
  }, []);

  const setInteractiveSentenceCardOpacityPercent = useCallback((value: number) => {
    setInteractiveSentenceCardOpacityPercentState(clampPercent(value));
  }, []);

  const resetInteractiveTextSettings = useCallback(() => {
    setTranslationSpeedState(DEFAULT_TRANSLATION_SPEED);
    setFontScalePercentState(DEFAULT_INTERACTIVE_FONT_SCALE_PERCENT);
    setInteractiveTextThemeState(DEFAULT_INTERACTIVE_TEXT_THEME);
    setInteractiveBackgroundOpacityPercentState(DEFAULT_INTERACTIVE_TEXT_BG_OPACITY_PERCENT);
    setInteractiveSentenceCardOpacityPercentState(DEFAULT_INTERACTIVE_TEXT_SENTENCE_CARD_OPACITY_PERCENT);
  }, []);

  return {
    interactiveTextVisibility,
    toggleInteractiveTextLayer,
    translationSpeed,
    setTranslationSpeed,
    adjustTranslationSpeed,
    fontScalePercent,
    setFontScalePercent,
    adjustFontScale,
    interactiveTextTheme,
    setInteractiveTextTheme,
    interactiveBackgroundOpacityPercent,
    setInteractiveBackgroundOpacityPercent,
    interactiveSentenceCardOpacityPercent,
    setInteractiveSentenceCardOpacityPercent,
    resetInteractiveTextSettings,
  };
}
