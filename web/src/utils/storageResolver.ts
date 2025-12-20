const STORAGE_BASE_URL_ERROR = 'VITE_STORAGE_BASE_URL is not configured.';

function normaliseBaseUrl(value: string | null | undefined): string {
  if (!value) {
    return '';
  }
  return value.trim().replace(/\/+$/, '');
}

function ensureStoragePath(baseUrl: string): string {
  if (!baseUrl) {
    return '';
  }

  const normalised = normaliseBaseUrl(baseUrl);
  if (!normalised) {
    return '';
  }

  if (/\/storage\/jobs$/i.test(normalised)) {
    return normalised;
  }

  if (/\/storage$/i.test(normalised)) {
    return `${normalised}/jobs`;
  }

  return `${normalised}/storage/jobs`;
}

function normaliseJobId(value: string | null | undefined): string {
  if (!value) {
    return '';
  }
  return value.trim().replace(/^\/+/, '').replace(/\/+$/, '');
}

function normaliseFileName(value: string | null | undefined): string {
  if (!value) {
    return '';
  }
  return value.trim().replace(/^\/+/, '');
}

function readEnv(key: string): string {
  const env = import.meta.env as Record<string, string | undefined>;
  return env?.[key] ?? '';
}

function resolveWindowOrigin(): string {
  if (typeof window === 'undefined') {
    return '';
  }
  try {
    const url = new URL(window.location.href);
    if (url.port === '5173') {
      url.port = '8000';
    }
    return url.origin.replace(/\/+$/, '');
  } catch (error) {
    console.warn('Unable to resolve window origin for storage base URL', error);
    return '';
  }
}

export function resolveStorageBaseUrl(apiBaseUrl?: string | null | undefined): string {
  const explicit = normaliseBaseUrl(readEnv('VITE_STORAGE_BASE_URL'));
  if (explicit) {
    return explicit;
  }

  const inferred = normaliseBaseUrl(readEnv('VITE_API_BASE_URL'));
  if (inferred) {
    return ensureStoragePath(inferred);
  }

  const fallback = normaliseBaseUrl(apiBaseUrl);
  if (fallback) {
    return ensureStoragePath(fallback);
  }

  return ensureStoragePath(resolveWindowOrigin());
}

export function resolve(
  jobId: string | null | undefined,
  fileName: string | null | undefined,
  baseUrlOverride?: string | null | undefined,
  apiBaseUrl?: string | null | undefined
): string {
  const overrideBase = normaliseBaseUrl(baseUrlOverride);
  const baseUrl = overrideBase || resolveStorageBaseUrl(apiBaseUrl);

  if (!baseUrl) {
    throw new Error(STORAGE_BASE_URL_ERROR);
  }

  const jobSegment = normaliseJobId(jobId);
  const fileSegment = normaliseFileName(fileName);

  if (jobSegment && fileSegment) {
    return `${baseUrl}/${jobSegment}/${fileSegment}`;
  }
  if (jobSegment) {
    return `${baseUrl}/${jobSegment}`;
  }
  if (fileSegment) {
    return `${baseUrl}/${fileSegment}`;
  }
  return baseUrl;
}

export function coerceExportPath(
  value: string | null | undefined,
  jobId?: string | null
): string | null {
  if (!value) {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  if (trimmed.startsWith('data:') || trimmed.startsWith('blob:')) {
    return trimmed;
  }
  if (/^[a-z]+:\/\//i.test(trimmed)) {
    return trimmed;
  }

  const normalised = trimmed.replace(/\\+/g, '/');
  const [pathPart, hashPart] = normalised.split('#', 2);
  const [pathOnly, queryPart] = pathPart.split('?', 2);

  let relative = pathOnly.replace(/^\/+/, '');
  const safeJobId = (jobId ?? '').trim().replace(/^\/+/, '').replace(/\/+$/, '');
  if (safeJobId) {
    const marker = `/${safeJobId}/`;
    const markerIndex = relative.indexOf(marker);
    if (markerIndex >= 0) {
      relative = relative.slice(markerIndex + marker.length);
    } else if (relative.startsWith(`${safeJobId}/`)) {
      relative = relative.slice(safeJobId.length + 1);
    }
  }

  const segments = relative.split('/').filter((segment) => segment && segment !== '.' && segment !== '..');
  const mediaIndex = segments.indexOf('media');
  const metadataIndex = segments.indexOf('metadata');
  if (mediaIndex >= 0) {
    relative = segments.slice(mediaIndex).join('/');
  } else if (metadataIndex >= 0) {
    relative = segments.slice(metadataIndex).join('/');
  } else {
    relative = segments.join('/');
  }

  if (!relative) {
    return null;
  }

  let result = relative;
  if (queryPart) {
    result = `${result}?${queryPart}`;
  }
  if (hashPart) {
    result = `${result}#${hashPart}`;
  }
  return result;
}
