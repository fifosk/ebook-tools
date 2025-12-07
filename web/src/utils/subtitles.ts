import {
  DEFAULT_LANGUAGE_FLAG,
  resolveLanguageCode,
  resolveLanguageFlag,
  resolveLanguageName
} from '../constants/languageCodes';
import { normalizeLanguageLabel } from './languages';

const LANGUAGE_TOKEN_PATTERN = /^[A-Za-z0-9_-]{1,16}$/;

function basename(path: string): string {
  return path.split(/[\\/]/).filter(Boolean).pop() || '';
}

function stem(filename: string): string {
  if (!filename.includes('.')) {
    return filename;
  }
  return filename.slice(0, filename.lastIndexOf('.'));
}

const IGNORED_LANGUAGE_TOKENS = new Set([
  'hdr',
  'hdr10',
  'hdr10+',
  'dv',
  'vision',
  'web',
  'webrip',
  'bluray',
  'bdrip',
  'remux',
  'repack',
  'x264',
  'x265',
  'h264',
  'h265',
  'hevc',
  'aac',
  'ddp',
  'dd+',
  'dts',
  'atmos',
  'watcher',
  'dsnp',
  'hmax',
  'imax',
  'sub',
  'subs',
  'sub2',
  'dub',
  'dual',
  'multi',
  'drt',
  'ass',
  'srt',
  'vtt'
]);

function looksLikeResolution(token: string): boolean {
  return /^\d{3,4}p$/i.test(token) || /^\d{3,4}$/i.test(token);
}

function normalizeLanguageToken(token: string): string {
  const trimmed = token.trim();
  if (!trimmed) {
    return '';
  }
  const lowered = trimmed.toLowerCase();
  const withoutDigits = lowered.replace(/\d+$/, '');
  const suffixMatch = withoutDigits.match(/^(.*?)(?:subs?|subtitles?)$/);
  if (suffixMatch && suffixMatch[1]) {
    return suffixMatch[1];
  }
  return withoutDigits || lowered;
}

function collectLanguageTokens(stemValue: string): string[] {
  if (!stemValue) {
    return [];
  }
  const candidates: string[] = [];
  const dotted = stemValue.split('.').filter(Boolean);
  for (let i = dotted.length - 1; i >= 0; i -= 1) {
    const part = dotted[i];
    const normalizedPart = normalizeLanguageToken(part);
    if (normalizedPart) {
      candidates.push(normalizedPart);
    }
    const subParts = part.split(/[_-]/).filter(Boolean);
    for (let j = subParts.length - 1; j >= 0; j -= 1) {
      const sub = normalizeLanguageToken(subParts[j]);
      if (sub) {
        candidates.push(sub);
      }
    }
  }

  const bracketMatch = stemValue.match(/\(([^()]{1,24})\)\s*$/);
  if (bracketMatch && bracketMatch[1]) {
    candidates.unshift(normalizeLanguageToken(bracketMatch[1]));
  }

  const seen = new Set<string>();
  return candidates.filter((token) => {
    const normalized = token.trim();
    if (!normalized) {
      return false;
    }
    if (normalized.length < 2) {
      return false;
    }
    if (IGNORED_LANGUAGE_TOKENS.has(normalized)) {
      return false;
    }
    if (looksLikeResolution(normalized)) {
      return false;
    }
    if (seen.has(normalized)) {
      return false;
    }
    seen.add(normalized);
    return true;
  });
}

export function inferSubtitleLanguageFromPath(path: string | null | undefined): string | null {
  const filename = basename(path ?? '');
  const stemValue = stem(filename);
  const tokens = collectLanguageTokens(stemValue);
  for (const token of tokens) {
    const trimmed = token.trim();
    if (!trimmed) {
      continue;
    }
    const resolvedCode = resolveLanguageCode(trimmed);
    if (resolvedCode) {
      return resolvedCode;
    }
    const friendly = resolveLanguageName(trimmed);
    if (friendly) {
      return resolveLanguageCode(friendly) ?? friendly;
    }
    if (LANGUAGE_TOKEN_PATTERN.test(trimmed)) {
      return trimmed;
    }
  }
  const alphaTokens = Array.from(stemValue.matchAll(/[A-Za-z]{2,12}/g)).map((match) => match[0]);
  for (let i = alphaTokens.length - 1; i >= 0; i -= 1) {
    const token = normalizeLanguageToken(alphaTokens[i]);
    if (!token || token.length < 2 || IGNORED_LANGUAGE_TOKENS.has(token)) {
      continue;
    }
    const resolvedCode = resolveLanguageCode(token);
    if (resolvedCode) {
      return resolvedCode;
    }
    const friendly = resolveLanguageName(token);
    if (friendly) {
      return resolveLanguageCode(friendly) ?? friendly;
    }
    if (LANGUAGE_TOKEN_PATTERN.test(token)) {
      return token;
    }
  }
  return null;
}

export function resolveSubtitleLanguageCandidate(
  language?: string | null,
  path?: string | null,
  filename?: string | null
): string {
  const candidates = [
    inferSubtitleLanguageFromPath(path),
    inferSubtitleLanguageFromPath(filename),
    language
  ];
  for (const candidate of candidates) {
    const normalized = (candidate ?? '').trim();
    if (!normalized) {
      continue;
    }
    const resolvedCode = resolveLanguageCode(normalized);
    if (resolvedCode) {
      return resolvedCode;
    }
    if (LANGUAGE_TOKEN_PATTERN.test(normalized)) {
      return normalized;
    }
  }
  return '';
}

export function resolveSubtitleLanguageLabel(
  language?: string | null,
  path?: string | null,
  filename?: string | null
): string {
  const candidate = resolveSubtitleLanguageCandidate(language, path, filename);
  return normalizeLanguageLabel(candidate);
}

export function subtitleLanguageDetail(
  language?: string | null,
  path?: string | null,
  filename?: string | null
): string {
  const candidate =
    resolveSubtitleLanguageCandidate(language, path, filename) || language || '';
  if (!candidate) {
    return 'Unknown language';
  }
  const friendly = normalizeLanguageLabel(candidate);
  if (!friendly) {
    return 'Unknown language';
  }
  if (friendly.toLowerCase() === candidate.toLowerCase()) {
    return friendly;
  }
  return `${friendly} (${candidate})`;
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

export function resolveSubtitleFlag(
  language?: string | null,
  path?: string | null,
  filename?: string | null
): string {
  const candidate = resolveSubtitleLanguageCandidate(language, path, filename);
  return resolveLanguageFlag(candidate) ?? DEFAULT_LANGUAGE_FLAG;
}
