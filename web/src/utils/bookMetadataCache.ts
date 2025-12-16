import { md5Hex } from './md5';

type BookMetadataCacheEntryV1 = {
  version: 1;
  normalized_input: string;
  updated_at: number;
  book_metadata_json: string;
  cover_source_url?: string;
  cover_data_url?: string;
};

const CACHE_PREFIX = 'ebookTools.bookMetadataCache.v1.';
const CACHE_INDEX_KEY = 'ebookTools.bookMetadataCache.v1.index';
const MAX_ENTRIES = 25;

function isBrowser(): boolean {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
}

function safeParseIndex(raw: string | null): string[] {
  if (!raw) {
    return [];
  }
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter((value): value is string => typeof value === 'string' && value.length > 0);
  } catch {
    return [];
  }
}

function safeWriteIndex(index: string[]): void {
  if (!isBrowser()) {
    return;
  }
  try {
    window.localStorage.setItem(CACHE_INDEX_KEY, JSON.stringify(index));
  } catch {
    // ignore
  }
}

function isEffectivelyEmptyBookMetadata(raw: string): boolean {
  const trimmed = raw.trim();
  if (!trimmed || trimmed === '{}' || trimmed === 'null') {
    return true;
  }
  try {
    const parsed = JSON.parse(trimmed);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return false;
    }
    return Object.keys(parsed as Record<string, unknown>).length === 0;
  } catch {
    return false;
  }
}

function buildCacheKey(normalizedInput: string): string {
  return `${CACHE_PREFIX}${md5Hex(normalizedInput)}`;
}

export function loadCachedBookMetadataJson(normalizedInput: string): string | null {
  if (!isBrowser()) {
    return null;
  }
  const trimmed = normalizedInput.trim();
  if (!trimmed) {
    return null;
  }
  const key = buildCacheKey(trimmed);
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as BookMetadataCacheEntryV1;
    if (!parsed || parsed.version !== 1) {
      return null;
    }
    if (typeof parsed.book_metadata_json !== 'string' || !parsed.book_metadata_json.trim()) {
      return null;
    }
    return parsed.book_metadata_json;
  } catch {
    return null;
  }
}

export function loadCachedBookCoverDataUrl(normalizedInput: string): string | null {
  if (!isBrowser()) {
    return null;
  }
  const trimmed = normalizedInput.trim();
  if (!trimmed) {
    return null;
  }
  const key = buildCacheKey(trimmed);
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as BookMetadataCacheEntryV1;
    if (!parsed || parsed.version !== 1) {
      return null;
    }
    if (typeof parsed.cover_data_url !== 'string' || !parsed.cover_data_url.trim()) {
      return null;
    }
    return parsed.cover_data_url;
  } catch {
    return null;
  }
}

export function loadCachedBookCoverSourceUrl(normalizedInput: string): string | null {
  if (!isBrowser()) {
    return null;
  }
  const trimmed = normalizedInput.trim();
  if (!trimmed) {
    return null;
  }
  const key = buildCacheKey(trimmed);
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as BookMetadataCacheEntryV1;
    if (!parsed || parsed.version !== 1) {
      return null;
    }
    if (typeof parsed.cover_source_url !== 'string' || !parsed.cover_source_url.trim()) {
      return null;
    }
    return parsed.cover_source_url;
  } catch {
    return null;
  }
}

export function persistCachedBookMetadataJson(normalizedInput: string, bookMetadataJson: string): void {
  if (!isBrowser()) {
    return;
  }
  const trimmedInput = normalizedInput.trim();
  if (!trimmedInput) {
    return;
  }
  const key = buildCacheKey(trimmedInput);
  const index = safeParseIndex(window.localStorage.getItem(CACHE_INDEX_KEY));

  if (isEffectivelyEmptyBookMetadata(bookMetadataJson)) {
    return;
  }

  let existing: BookMetadataCacheEntryV1 | null = null;
  try {
    const rawExisting = window.localStorage.getItem(key);
    if (rawExisting) {
      const parsed = JSON.parse(rawExisting) as BookMetadataCacheEntryV1;
      if (parsed?.version === 1) {
        existing = parsed;
      }
    }
  } catch {
    existing = null;
  }

  const entry: BookMetadataCacheEntryV1 = {
    version: 1,
    normalized_input: trimmedInput,
    updated_at: Date.now(),
    book_metadata_json: bookMetadataJson,
    cover_source_url: existing?.cover_source_url,
    cover_data_url: existing?.cover_data_url
  };

  try {
    window.localStorage.setItem(key, JSON.stringify(entry));
  } catch {
    return;
  }

  const nextIndex = [key, ...index.filter((existing) => existing !== key)];
  if (nextIndex.length > MAX_ENTRIES) {
    const evicted = nextIndex.slice(MAX_ENTRIES);
    evicted.forEach((victim) => {
      try {
        window.localStorage.removeItem(victim);
      } catch {
        // ignore
      }
    });
  }
  safeWriteIndex(nextIndex.slice(0, MAX_ENTRIES));
}

export function persistCachedBookCoverDataUrl(
  normalizedInput: string,
  coverSourceUrl: string,
  coverDataUrl: string,
): void {
  if (!isBrowser()) {
    return;
  }
  const trimmedInput = normalizedInput.trim();
  const trimmedSource = coverSourceUrl.trim();
  const trimmedData = coverDataUrl.trim();
  if (!trimmedInput || !trimmedSource || !trimmedData) {
    return;
  }

  const key = buildCacheKey(trimmedInput);
  const index = safeParseIndex(window.localStorage.getItem(CACHE_INDEX_KEY));

  let bookMetadataJson = '{}';
  try {
    const rawExisting = window.localStorage.getItem(key);
    if (rawExisting) {
      const parsed = JSON.parse(rawExisting) as BookMetadataCacheEntryV1;
      if (parsed?.version === 1 && typeof parsed.book_metadata_json === 'string' && parsed.book_metadata_json.trim()) {
        bookMetadataJson = parsed.book_metadata_json;
      }
    }
  } catch {
    // ignore
  }

  const entry: BookMetadataCacheEntryV1 = {
    version: 1,
    normalized_input: trimmedInput,
    updated_at: Date.now(),
    book_metadata_json: bookMetadataJson,
    cover_source_url: trimmedSource,
    cover_data_url: trimmedData
  };

  try {
    window.localStorage.setItem(key, JSON.stringify(entry));
  } catch {
    return;
  }

  const nextIndex = [key, ...index.filter((existing) => existing !== key)];
  if (nextIndex.length > MAX_ENTRIES) {
    const evicted = nextIndex.slice(MAX_ENTRIES);
    evicted.forEach((victim) => {
      try {
        window.localStorage.removeItem(victim);
      } catch {
        // ignore
      }
    });
  }
  safeWriteIndex(nextIndex.slice(0, MAX_ENTRIES));
}
