import type { LiveMediaState } from '../../hooks/useLiveMedia';

export const MEDIA_CATEGORIES = ['text', 'audio', 'video'] as const;
export type MediaCategory = (typeof MEDIA_CATEGORIES)[number];
export type NavigationIntent = 'first' | 'previous' | 'next' | 'last';

export interface TabDefinition {
  key: MediaCategory;
  label: string;
  emptyMessage: string;
}

export const TAB_DEFINITIONS: TabDefinition[] = [
  { key: 'text', label: 'Interactive Reader', emptyMessage: 'No interactive reader media yet.' },
  { key: 'video', label: 'Video', emptyMessage: 'No video media yet.' },
];

export const DEFAULT_COVER_URL = '/assets/default-cover.png';

export function selectInitialTab(media: LiveMediaState): MediaCategory {
  const populated = TAB_DEFINITIONS.find((tab) => media[tab.key].length > 0);
  return populated?.key ?? 'text';
}

export type TranslationSpeed = number;

export const TRANSLATION_SPEED_MIN: TranslationSpeed = 0.5;
export const TRANSLATION_SPEED_MAX: TranslationSpeed = 2;
export const TRANSLATION_SPEED_STEP: TranslationSpeed = 0.25;
export const DEFAULT_TRANSLATION_SPEED: TranslationSpeed = 1;

export function normaliseTranslationSpeed(value: number): TranslationSpeed {
  if (!Number.isFinite(value)) {
    return DEFAULT_TRANSLATION_SPEED;
  }
  const clamped = Math.min(TRANSLATION_SPEED_MAX, Math.max(TRANSLATION_SPEED_MIN, value));
  const stepCount = Math.round((clamped - TRANSLATION_SPEED_MIN) / TRANSLATION_SPEED_STEP);
  const snapped = TRANSLATION_SPEED_MIN + stepCount * TRANSLATION_SPEED_STEP;
  const rounded = Math.round(snapped * 100) / 100;
  if (!Number.isFinite(rounded)) {
    return DEFAULT_TRANSLATION_SPEED;
  }
  return rounded as TranslationSpeed;
}

export function formatTranslationSpeedLabel(value: number): string {
  const normalised = normaliseTranslationSpeed(value);
  const formatted =
    Number.isInteger(normalised) && normalised >= 1
      ? normalised.toString()
      : normalised.toFixed(2).replace(/0+$/, '').replace(/\.$/, '');
  return `${formatted}×`;
}
