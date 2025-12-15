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

  const inputLanguage =
    extractFirstString(readNestedValue(metadata, ['input_language'])) ??
    extractFirstString(readNestedValue(metadata, ['original_language'])) ??
    extractFirstString(readNestedValue(metadata, ['request', 'config', 'input_language'])) ??
    extractFirstString(readNestedValue(metadata, ['request', 'inputs', 'input_language'])) ??
    null;

  const originalLanguage =
    extractFirstString(readNestedValue(metadata, ['original_language'])) ??
    extractFirstString(readNestedValue(metadata, ['request', 'config', 'original_language'])) ??
    extractFirstString(readNestedValue(metadata, ['request', 'inputs', 'original_language'])) ??
    inputLanguage ??
    null;

  const rawTargets =
    readNestedValue(metadata, ['target_languages']) ??
    readNestedValue(metadata, ['translation_languages']) ??
    readNestedValue(metadata, ['request', 'config', 'target_languages']) ??
    readNestedValue(metadata, ['request', 'inputs', 'target_languages']) ??
    readNestedValue(metadata, ['request', 'config', 'target_language']) ??
    readNestedValue(metadata, ['request', 'inputs', 'target_language']) ??
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
    extractFirstString(readNestedValue(metadata, ['target_language'])) ??
    extractFirstString(readNestedValue(metadata, ['translation_language'])) ??
    extractFirstString(readNestedValue(metadata, ['request', 'config', 'target_language'])) ??
    extractFirstString(readNestedValue(metadata, ['request', 'inputs', 'target_language'])) ??
    targetLanguages[0] ??
    null;

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
