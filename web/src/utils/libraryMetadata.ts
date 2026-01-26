import type { LibraryItem } from '../api/dtos';
import { appendAccessToken, resolveLibraryMediaUrl } from '../api/client';

function cloneRecord(source: Record<string, unknown>): Record<string, unknown> {
  return { ...source };
}

function readNestedValue(source: unknown, path: string[]): unknown {
  let current: unknown = source;
  for (const key of path) {
    if (!current || typeof current !== 'object') {
      return null;
    }
    const record = current as Record<string, unknown>;
    current = record[key];
  }
  return current;
}

function normaliseMetadataText(value: unknown): string | null {
  if (typeof value === 'string') {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value.toString();
  }
  return null;
}

function extractFirstString(value: unknown): string | null {
  if (Array.isArray(value)) {
    for (const entry of value) {
      const normalised = normaliseMetadataText(entry);
      if (normalised) {
        return normalised;
      }
    }
  }
  return normaliseMetadataText(value);
}

function extractLibraryJobLanguages(item: LibraryItem): {
  inputLanguage: string | null;
  originalLanguage: string | null;
  targetLanguages: string[];
  targetLanguage: string | null;
} {
  const metadata = item.metadata as Record<string, unknown> | null | undefined;
  if (!metadata || typeof metadata !== 'object') {
    return { inputLanguage: null, originalLanguage: null, targetLanguages: [], targetLanguage: null };
  }

  const requestCandidates = [
    ['request', 'config'],
    ['request', 'inputs'],
    ['request', 'options'],
    ['resume_context', 'config'],
    ['resume_context', 'inputs'],
    ['resume_context', 'options'],
    ['request_payload', 'config'],
    ['request_payload', 'inputs'],
    ['request_payload', 'options'],
    ['parameters'],
  ] as const;

  const readAny = (key: string): unknown => {
    const direct = readNestedValue(metadata, [key]);
    if (direct != null) {
      return direct;
    }
    const camel = readNestedValue(metadata, [key.replace(/_([a-z])/g, (_, char: string) => char.toUpperCase())]);
    if (camel != null) {
      return camel;
    }
    return null;
  };

  const readAnyNested = (path: readonly string[], key: string): unknown => {
    const direct = readNestedValue(metadata, [...path, key]);
    if (direct != null) {
      return direct;
    }
    const camelKey = key.replace(/_([a-z])/g, (_, char: string) => char.toUpperCase());
    const camel = readNestedValue(metadata, [...path, camelKey]);
    if (camel != null) {
      return camel;
    }
    return null;
  };

  const inputLanguage =
    extractFirstString(readAny('input_language')) ??
    extractFirstString(readAny('original_language')) ??
    requestCandidates
      .map((path) => extractFirstString(readAnyNested(path, 'input_language')))
      .find((value) => Boolean(value)) ??
    null;

  const originalLanguage =
    extractFirstString(readAny('original_language')) ??
    requestCandidates
      .map((path) => extractFirstString(readAnyNested(path, 'original_language')))
      .find((value) => Boolean(value)) ??
    inputLanguage ??
    null;

  const rawTargets =
    readAny('target_languages') ??
    readAny('translation_languages') ??
    requestCandidates
      .map((path) => readAnyNested(path, 'target_languages'))
      .find((value) => value != null) ??
    requestCandidates
      .map((path) => readAnyNested(path, 'target_language'))
      .find((value) => value != null) ??
    requestCandidates
      .map((path) => readAnyNested(path, 'translation_language'))
      .find((value) => value != null) ??
    null;

  const targetLanguages: string[] = [];
  if (Array.isArray(rawTargets)) {
    for (const entry of rawTargets) {
      const normalised = normaliseMetadataText(entry);
      if (normalised) {
        targetLanguages.push(normalised);
      }
    }
  } else {
    const single = extractFirstString(rawTargets);
    if (single) {
      targetLanguages.push(single);
    }
  }

  const targetLanguage =
    extractFirstString(readAny('target_language')) ??
    extractFirstString(readAny('translation_language')) ??
    requestCandidates
      .map((path) => extractFirstString(readAnyNested(path, 'target_language')))
      .find((value) => Boolean(value)) ??
    requestCandidates
      .map((path) => extractFirstString(readAnyNested(path, 'translation_language')))
      .find((value) => Boolean(value)) ??
    targetLanguages[0] ??
    (normaliseMetadataText(item.language) && item.language.trim().toLowerCase() !== 'unknown'
      ? item.language.trim()
      : null);

  return { inputLanguage, originalLanguage, targetLanguages, targetLanguage };
}

export function extractLibraryBookMetadata(
  item: LibraryItem | null | undefined,
): Record<string, unknown> | null {
  if (!item) {
    return null;
  }
  const payload = item.metadata ?? null;
  if (!payload || typeof payload !== 'object') {
    return null;
  }
  const record = payload as Record<string, unknown>;
  const direct = record['book_metadata'];
  if (direct && typeof direct === 'object') {
    return cloneRecord(direct as Record<string, unknown>);
  }
  const nestedResult = record['result'];
  if (nestedResult && typeof nestedResult === 'object') {
    const candidate = (nestedResult as Record<string, unknown>)['book_metadata'];
    if (candidate && typeof candidate === 'object') {
      return cloneRecord(candidate as Record<string, unknown>);
    }
  }
  return null;
}

export function resolveLibraryCoverUrl(
  item: LibraryItem,
  bookMetadata: Record<string, unknown> | null | undefined,
): string | null {
  const jobId = (item.jobId ?? '').trim();
  if (!jobId) {
    return null;
  }
  const candidates: string[] = [];
  if (item.coverPath) {
    candidates.push(item.coverPath);
  }
  const pushCandidate = (value: unknown) => {
    if (typeof value !== 'string') {
      return;
    }
    const trimmed = value.trim();
    if (!trimmed) {
      return;
    }
    candidates.push(trimmed);
  };

  if (bookMetadata) {
    pushCandidate(bookMetadata['job_cover_asset']);
    pushCandidate(bookMetadata['book_cover_file']);
    pushCandidate(bookMetadata['job_cover_asset_url']);
    // Fallback to enrichment cover URL if local covers aren't available
    pushCandidate(bookMetadata['book_cover_url']);
  }

  const metadataRecord = item.metadata ?? {};
  if (metadataRecord && typeof metadataRecord === 'object') {
    pushCandidate((metadataRecord as Record<string, unknown>)['job_cover_asset']);
  }

  for (const candidate of candidates) {
    if (candidate.includes('/pipelines/')) {
      continue;
    }
    if (/^[a-z]+:\/\//i.test(candidate)) {
      return appendAccessToken(candidate);
    }
    if (candidate.startsWith('/api/library/')) {
      return appendAccessToken(candidate);
    }
    const resolved = resolveLibraryMediaUrl(jobId, candidate);
    if (resolved) {
      return resolved;
    }
  }
  return null;
}

export function buildLibraryBookMetadata(
  item: LibraryItem | null | undefined,
): Record<string, unknown> | null {
  if (!item) {
    return null;
  }
  const base = extractLibraryBookMetadata(item);
  if ((item.itemType ?? 'book') === 'video') {
    return base ?? {};
  }
  const coverUrl = resolveLibraryCoverUrl(item, base);
  if (!base && !coverUrl) {
    return null;
  }
  const payload = cloneRecord(base ?? {});
  const languages = extractLibraryJobLanguages(item);
  if (languages.inputLanguage && payload['input_language'] == null) {
    payload['input_language'] = languages.inputLanguage;
  }
  if (languages.originalLanguage && payload['original_language'] == null) {
    payload['original_language'] = languages.originalLanguage;
  }
  if (languages.targetLanguage) {
    if (payload['target_language'] == null) {
      payload['target_language'] = languages.targetLanguage;
    }
    if (payload['translation_language'] == null) {
      payload['translation_language'] = languages.targetLanguage;
    }
  }
  if (languages.targetLanguages.length > 0 && payload['target_languages'] == null) {
    payload['target_languages'] = languages.targetLanguages;
  }
  if (coverUrl) {
    payload['job_cover_asset_url'] = coverUrl;
  }
  return payload;
}
