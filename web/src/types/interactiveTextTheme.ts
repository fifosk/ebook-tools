export type InteractiveTextTheme = {
  background: string;
  original: string;
  originalActive: string;
  translation: string;
  transliteration: string;
  highlight: string;
};

export const DEFAULT_INTERACTIVE_TEXT_THEME: InteractiveTextTheme = {
  background: '#0f172a',
  original: '#ffd400',
  originalActive: '#ffd400',
  translation: '#f8b44c',
  transliteration: '#6ee7b7',
  highlight: '#ff8c00',
};

export function normalizeHexColor(value: string | null | undefined, fallback: string): string {
  if (!value) {
    return fallback;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return fallback;
  }
  const lowered = trimmed.toLowerCase();
  const match = lowered.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/);
  if (!match) {
    return fallback;
  }
  const digits = match[1];
  if (digits.length === 3) {
    const expanded = digits
      .split('')
      .map((part) => part + part)
      .join('');
    return `#${expanded}`;
  }
  return `#${digits}`;
}

export function loadInteractiveTextTheme(storageKey: string): InteractiveTextTheme {
  if (typeof window === 'undefined') {
    return DEFAULT_INTERACTIVE_TEXT_THEME;
  }
  const stored = window.localStorage.getItem(storageKey);
  if (!stored) {
    return DEFAULT_INTERACTIVE_TEXT_THEME;
  }
  try {
    const parsed = JSON.parse(stored) as Record<string, unknown>;
    return {
      background: normalizeHexColor(parsed.background as string, DEFAULT_INTERACTIVE_TEXT_THEME.background),
      original: normalizeHexColor(parsed.original as string, DEFAULT_INTERACTIVE_TEXT_THEME.original),
      originalActive: normalizeHexColor(parsed.originalActive as string, DEFAULT_INTERACTIVE_TEXT_THEME.originalActive),
      translation: normalizeHexColor(parsed.translation as string, DEFAULT_INTERACTIVE_TEXT_THEME.translation),
      transliteration: normalizeHexColor(parsed.transliteration as string, DEFAULT_INTERACTIVE_TEXT_THEME.transliteration),
      highlight: normalizeHexColor(parsed.highlight as string, DEFAULT_INTERACTIVE_TEXT_THEME.highlight),
    };
  } catch {
    return DEFAULT_INTERACTIVE_TEXT_THEME;
  }
}
