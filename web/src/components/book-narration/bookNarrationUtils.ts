import { withBase } from '../../api/client';

export function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('Unable to read cover image data'));
    reader.onload = () => resolve(typeof reader.result === 'string' ? reader.result : '');
    reader.readAsDataURL(blob);
  });
}

export function normalizeIsbnCandidate(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  const cleaned = value.replace(/[^0-9Xx]/g, '').toUpperCase();
  if (cleaned.length === 10 || cleaned.length === 13) {
    return cleaned;
  }
  return null;
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function coerceRecord(value: unknown): Record<string, unknown> | null {
  return isRecord(value) ? value : null;
}

export function normalizeTextValue(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export function parseJsonField(label: string, value: string): Record<string, unknown> {
  if (!value.trim()) {
    return {};
  }

  try {
    const parsed = JSON.parse(value);
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      throw new Error(`${label} must be an object`);
    }
    return parsed as Record<string, unknown>;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`Invalid JSON for ${label}: ${message}`);
  }
}

export function basenameFromPath(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) {
    return '';
  }
  const parts = trimmed.split(/[/\\]/);
  return parts[parts.length - 1] || trimmed;
}

export function resolveCoverPreviewUrlFromCoverFile(coverFile: string | null): string | null {
  const trimmed = coverFile?.trim() ?? '';
  if (!trimmed) {
    return null;
  }
  if (/^https?:\/\//i.test(trimmed)) {
    return trimmed;
  }

  const normalised = trimmed.replace(/\\/g, '/');
  const storagePrefix = '/storage/covers/';
  const storageIndex = normalised.lastIndexOf(storagePrefix);
  if (storageIndex >= 0) {
    return withBase(normalised.slice(storageIndex));
  }
  const storageRelativeIndex = normalised.lastIndexOf('storage/covers/');
  if (storageRelativeIndex >= 0) {
    return withBase(`/${normalised.slice(storageRelativeIndex)}`);
  }

  const filename = basenameFromPath(normalised);
  if (!filename) {
    return null;
  }
  return withBase(`/storage/covers/${encodeURIComponent(filename)}`);
}
