const STORAGE_BASE_URL_ERROR = 'VITE_STORAGE_BASE_URL is not configured.';

function normaliseBaseUrl(value: string | null | undefined): string {
  if (!value) {
    return '';
  }
  return value.trim().replace(/\/+$/, '');
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
    return inferred;
  }

  const fallback = normaliseBaseUrl(apiBaseUrl);
  if (fallback) {
    return fallback;
  }

  return resolveWindowOrigin();
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
