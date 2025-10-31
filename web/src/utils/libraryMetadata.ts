import type { LibraryItem } from '../api/dtos';
import { appendAccessToken, resolveLibraryMediaUrl } from '../api/client';

function cloneRecord(source: Record<string, unknown>): Record<string, unknown> {
  return { ...source };
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
  const coverUrl = resolveLibraryCoverUrl(item, base);
  if (!base && !coverUrl) {
    return null;
  }
  const payload = cloneRecord(base ?? {});
  if (coverUrl) {
    payload['job_cover_asset_url'] = coverUrl;
  }
  return payload;
}
