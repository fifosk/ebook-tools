import { TOP_LANGUAGES } from '../constants/menuOptions';
import {
  DEFAULT_LANGUAGE_FLAG,
  LANGUAGE_CODES,
  resolveLanguageCode as resolveCanonicalLanguageCode,
  resolveLanguageFlag,
  resolveLanguageName
} from '../constants/languageCodes';
import { prefersNativeEmojiFlags } from './emojiIcons';

function normalizeLanguageCodeCandidate(candidate: string): string {
  return candidate.replace('-', '_');
}

function looksLikeLanguageCode(candidate: string): boolean {
  const normalized = normalizeLanguageCodeCandidate(candidate.trim());
  if (!normalized) {
    return false;
  }
  if (normalized.length > 16) {
    return false;
  }
  return normalized.split('_').every((segment) => /^[A-Za-z0-9]+$/.test(segment));
}

export function normalizeLanguageLabel(value?: string | null): string {
  const trimmed = (value ?? '').trim();
  if (!trimmed) {
    return '';
  }
  const friendly = resolveLanguageName(trimmed);
  return friendly ?? trimmed;
}

export function resolveLanguageCode(value?: string | null): string {
  const trimmed = (value ?? '').trim();
  if (!trimmed) {
    return '';
  }
  const canonical = resolveCanonicalLanguageCode(trimmed);
  if (canonical) {
    return canonical;
  }
  for (const [name, code] of Object.entries(LANGUAGE_CODES)) {
    if (name.toLowerCase() === trimmed.toLowerCase()) {
      return code;
    }
  }
  if (looksLikeLanguageCode(trimmed)) {
    return trimmed.replace(/_/g, '-');
  }
  return trimmed;
}

type BuildLanguageOptionsArgs = {
  fetchedLanguages?: string[];
  preferredLanguages?: Array<string | null | undefined>;
  fallback?: string;
};

export function buildLanguageOptions({
  fetchedLanguages = [],
  preferredLanguages = [],
  fallback = 'English'
}: BuildLanguageOptionsArgs = {}): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  const append = (value?: string | null) => {
    const normalized = normalizeLanguageLabel(value);
    if (!normalized) {
      return;
    }
    const key = normalized.toLowerCase();
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    result.push(normalized);
  };

  fetchedLanguages.forEach(append);
  TOP_LANGUAGES.forEach(append);
  preferredLanguages.forEach(append);

  if (result.length === 0 && fallback) {
    append(fallback);
  }

  return result;
}

export function preferLanguageLabel(values: Array<string | null | undefined>): string {
  for (const value of values) {
    const normalized = normalizeLanguageLabel(value);
    if (normalized) {
      return normalized;
    }
  }
  return '';
}

export function formatLanguageWithFlag(value?: string | null): string {
  const label = normalizeLanguageLabel(value);
  if (!label) {
    return '';
  }
  if (!prefersNativeEmojiFlags()) {
    return label;
  }
  const flag = resolveLanguageFlag(value ?? label) ?? DEFAULT_LANGUAGE_FLAG;
  return `${flag} ${label}`;
}

export function formatLanguageOptionLabel(value?: string | null): string {
  const label = normalizeLanguageLabel(value);
  if (!label) {
    return '';
  }
  if (!prefersNativeEmojiFlags()) {
    return label;
  }
  const flag = resolveLanguageFlag(value ?? label) ?? DEFAULT_LANGUAGE_FLAG;
  return `${label} ${flag}`;
}

export function sortLanguageLabelsByName(values: string[]): string[] {
  const collator = new Intl.Collator(undefined, { sensitivity: 'base', numeric: true });
  return [...values].sort((left, right) => {
    const leftLabel = normalizeLanguageLabel(left) || left;
    const rightLabel = normalizeLanguageLabel(right) || right;
    const primary = collator.compare(leftLabel, rightLabel);
    if (primary !== 0) {
      return primary;
    }
    return collator.compare(left, right);
  });
}
