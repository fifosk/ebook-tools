import { resolveLanguageName } from '../constants/languageCodes';

const LANGUAGE_TOKEN_PATTERN = /^[A-Za-z0-9_-]{1,16}$/;

export function inferSubtitleLanguageFromPath(path: string | null | undefined): string | null {
  const normalized = (path ?? '').split(/[\\/]/).filter(Boolean).pop() || '';
  if (!normalized.includes('.')) {
    return null;
  }
  const stem = normalized.slice(0, normalized.lastIndexOf('.'));
  const tokens = stem.split('.').filter(Boolean);
  if (tokens.length === 0) {
    return null;
  }
  const candidate = tokens[tokens.length - 1];
  if (LANGUAGE_TOKEN_PATTERN.test(candidate)) {
    return candidate;
  }
  return null;
}

export function subtitleLanguageDetail(language?: string | null): string {
  if (!language) {
    return 'Unknown language';
  }
  const friendly = resolveLanguageName(language) || language;
  if (friendly.toLowerCase() === language.toLowerCase()) {
    return friendly;
  }
  return `${friendly} (${language})`;
}

export function subtitleFormatFromPath(path: string | null | undefined): string {
  if (!path) {
    return '';
  }
  const match = path.trim().match(/\.([^.\\/]+)$/);
  if (!match) {
    return '';
  }
  return match[1].toLowerCase();
}
