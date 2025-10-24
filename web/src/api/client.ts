import {
  PipelineDefaultsResponse,
  PipelineFileBrowserResponse,
  PipelineFileEntry,
  PipelineJobActionResponse,
  PipelineJobListResponse,
  PipelineRequestPayload,
  PipelineStatusResponse,
  PipelineSubmissionResponse
} from './dtos';

const API_BASE_URL = resolveApiBaseUrl();
const STORAGE_BASE_URL = resolveStorageBaseUrl();

function resolveApiBaseUrl(): string {
  const explicit = (import.meta.env.VITE_API_BASE_URL ?? '').trim().replace(/\/$/, '');
  if (explicit) {
    return explicit;
  }

  if (typeof window !== 'undefined') {
    const url = new URL(window.location.href);
    if (url.port === '5173') {
      url.port = '8000';
      return url.origin.replace(/\/$/, '');
    }
    return url.origin.replace(/\/$/, '');
  }

  return '';
}

function resolveStorageBaseUrl(): string {
  const explicit = (import.meta.env.VITE_STORAGE_BASE_URL ?? '').trim().replace(/\/$/, '');
  if (explicit) {
    return explicit;
  }

  const inferred = (import.meta.env.VITE_API_BASE_URL ?? '').trim().replace(/\/$/, '');
  if (inferred) {
    return inferred;
  }

  return API_BASE_URL;
}

function withBase(path: string): string {
  if (!path.startsWith('/')) {
    return `${API_BASE_URL}/${path}`;
  }
  return `${API_BASE_URL}${path}`;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function submitPipeline(
  payload: PipelineRequestPayload
): Promise<PipelineSubmissionResponse> {
  const response = await fetch(withBase('/pipelines'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  return handleResponse<PipelineSubmissionResponse>(response);
}

export async function fetchPipelineStatus(jobId: string): Promise<PipelineStatusResponse> {
  const response = await fetch(withBase(`/pipelines/${jobId}`));
  return handleResponse<PipelineStatusResponse>(response);
}

export async function fetchJobs(): Promise<PipelineStatusResponse[]> {
  const response = await fetch(withBase('/pipelines/jobs'));
  const payload = await handleResponse<PipelineJobListResponse>(response);
  return payload.jobs;
}

async function postJobAction(jobId: string, action: string): Promise<PipelineJobActionResponse> {
  const response = await fetch(withBase(`/pipelines/jobs/${jobId}/${action}`), {
    method: 'POST'
  });
  return handleResponse<PipelineJobActionResponse>(response);
}

export async function pauseJob(jobId: string): Promise<PipelineJobActionResponse> {
  return postJobAction(jobId, 'pause');
}

export async function resumeJob(jobId: string): Promise<PipelineJobActionResponse> {
  return postJobAction(jobId, 'resume');
}

export async function cancelJob(jobId: string): Promise<PipelineJobActionResponse> {
  return postJobAction(jobId, 'cancel');
}

export async function deleteJob(jobId: string): Promise<PipelineJobActionResponse> {
  return postJobAction(jobId, 'delete');
}

export async function refreshPipelineMetadata(jobId: string): Promise<PipelineStatusResponse> {
  const response = await fetch(withBase(`/pipelines/${jobId}/metadata/refresh`), {
    method: 'POST'
  });
  return handleResponse<PipelineStatusResponse>(response);
}

export function buildEventStreamUrl(jobId: string): string {
  return withBase(`/pipelines/${jobId}/events`);
}

export function buildStorageUrl(path: string): string {
  if (!STORAGE_BASE_URL) {
    throw new Error('VITE_STORAGE_BASE_URL is not configured.');
  }
  if (!path) {
    return STORAGE_BASE_URL;
  }
  if (!path.startsWith('/')) {
    return `${STORAGE_BASE_URL}/${path}`;
  }
  return `${STORAGE_BASE_URL}${path}`;
}

function isAbsoluteUrl(path: string): boolean {
  const lower = path.trim().toLowerCase();
  return lower.startsWith('http://') || lower.startsWith('https://') || lower.startsWith('data:') || lower.startsWith('blob:');
}

function stripQueryAndFragment(path: string): string {
  const match = path.match(/^[^?#]*/u);
  return match ? match[0] : path;
}

function stripDriveLetter(path: string): string {
  return path.replace(/^[A-Za-z]:/, '');
}

function normalisePath(path: string): string {
  return stripQueryAndFragment(path.replace(/\\+/g, '/'));
}

export function buildApiUrl(path: string): string {
  const base = (API_BASE_URL ?? '').trim().replace(/\/+$/, '');
  const trimmed = (path ?? '').trim();

  if (!trimmed) {
    return base;
  }

  const normalisedPath = trimmed.replace(/^\/+/, '');

  if (!base) {
    return trimmed.startsWith('/') ? trimmed : `/${normalisedPath}`;
  }

  return `${base}/${normalisedPath}`;
}

export function normaliseStorageRelativePath(rawPath: string): string {
  const normalised = normalisePath(rawPath ?? '');
  if (!normalised) {
    return '';
  }

  const withoutDrive = stripDriveLetter(normalised);
  const segments = withoutDrive
    .split('/')
    .map((segment) => segment.trim())
    .filter((segment) => segment.length > 0);

  if (segments.length === 0) {
    return '';
  }

  const lowered = segments.map((segment) => segment.toLowerCase());
  const runtimeIndex = lowered.lastIndexOf('runtime');
  if (runtimeIndex >= 0) {
    return segments.slice(runtimeIndex).join('/');
  }

  const booksIndex = lowered.lastIndexOf('books');
  if (booksIndex >= 0) {
    return segments.slice(booksIndex).join('/');
  }

  const storageIndex = lowered.lastIndexOf('storage');
  if (storageIndex >= 0 && storageIndex + 1 < segments.length) {
    return segments.slice(storageIndex + 1).join('/');
  }

  const outputIndex = lowered.lastIndexOf('outputs');
  if (outputIndex >= 0) {
    return segments.slice(outputIndex).join('/');
  }

  return segments.join('/');
}

function padSlideIndex(index: number): string {
  if (!Number.isFinite(index) || index <= 0) {
    return '0001';
  }
  return Math.max(1, Math.trunc(index)).toString().padStart(4, '0');
}

export function buildBatchSlidePreviewUrls(entry: string, options?: { slideIndex?: number }): string[] {
  const rawEntry = (entry ?? '').trim();
  if (!rawEntry) {
    return [];
  }

  const slideIndex = options?.slideIndex ?? 1;
  const slideToken = padSlideIndex(slideIndex);
  const normalisedEntry = normalisePath(rawEntry);
  if (!normalisedEntry) {
    return [];
  }

  const candidates = new Set<string>();
  const pushCandidate = (candidate: string | null | undefined) => {
    if (!candidate) {
      return;
    }
    const trimmed = normalisePath(candidate.trim());
    if (!trimmed) {
      return;
    }
    if (candidates.has(trimmed)) {
      return;
    }
    candidates.add(trimmed);
  };

  const ensureSlideSuffix = (base: string) => {
    const cleaned = base.replace(/\/+$/u, '');
    if (!cleaned) {
      return null;
    }
    return `${cleaned}/${slideToken}.png`;
  };

  const extensionMatch = normalisedEntry.match(/\.([a-z0-9]+)$/iu);
  const extension = extensionMatch ? extensionMatch[1].toLowerCase() : '';

  if (extension === 'png' || extension === 'jpg' || extension === 'jpeg' || extension === 'webp') {
    pushCandidate(normalisedEntry);
  } else if (extension === 'mp4' || extension === 'mov' || extension === 'm4v') {
    const directory = normalisedEntry.replace(/\/[^/]*$/u, '');
    const slideDir = directory ? `${directory}/slides` : 'slides';
    pushCandidate(`${slideDir}/${slideToken}.png`);
    pushCandidate(`${directory}/${slideToken}.png`);
    pushCandidate(normalisedEntry.replace(/\.[a-z0-9]+$/iu, '.png'));
  } else if (normalisedEntry.includes('/slides/')) {
    const base = normalisedEntry.replace(/\/+$/u, '');
    if (base.match(/\.png$/iu)) {
      pushCandidate(base);
    } else {
      pushCandidate(`${base}/${slideToken}.png`);
    }
  } else {
    pushCandidate(ensureSlideSuffix(normalisedEntry));
    pushCandidate(`${normalisedEntry.replace(/\/+$/u, '')}/${slideToken}.png`);
  }

  const resolved: string[] = [];
  const resolvedSet = new Set<string>();
  const pushResolved = (value: string | null | undefined) => {
    const trimmed = value ? value.trim() : '';
    if (!trimmed || resolvedSet.has(trimmed)) {
      return;
    }
    resolvedSet.add(trimmed);
    resolved.push(trimmed);
  };

  for (const candidate of candidates) {
    if (!candidate) {
      continue;
    }
    if (isAbsoluteUrl(candidate)) {
      pushResolved(candidate);
      continue;
    }
    const storageRelative = normaliseStorageRelativePath(candidate);
    const relativeWithoutLeading = storageRelative.replace(/^\/+/, '');
    const candidateWithoutLeading = candidate.replace(/^\/+/, '');

    if (storageRelative) {
      try {
        pushResolved(buildStorageUrl(storageRelative));
      } catch (error) {
        console.warn('Unable to build storage URL for batch slide preview', error);
      }
      pushResolved(buildApiUrl(`storage/${relativeWithoutLeading}`));
      pushResolved(buildApiUrl(storageRelative));
      pushResolved(`/storage/${relativeWithoutLeading}`);
      pushResolved(`/${relativeWithoutLeading}`);
    }

    if (candidate.startsWith('/')) {
      pushResolved(buildApiUrl(candidate));
      pushResolved(candidate);
    } else {
      pushResolved(buildApiUrl(candidateWithoutLeading));
      pushResolved(`/${candidateWithoutLeading}`);
      pushResolved(candidateWithoutLeading);
    }
  }

  return resolved;
}

export async function fetchPipelineFiles(): Promise<PipelineFileBrowserResponse> {
  const response = await fetch(withBase('/pipelines/files'));
  return handleResponse<PipelineFileBrowserResponse>(response);
}

export async function fetchPipelineDefaults(): Promise<PipelineDefaultsResponse> {
  const response = await fetch(withBase('/pipelines/defaults'));
  return handleResponse<PipelineDefaultsResponse>(response);
}

export async function uploadEpubFile(file: File): Promise<PipelineFileEntry> {
  const formData = new FormData();
  formData.append('file', file, file.name);

  const response = await fetch(withBase('/pipelines/files/upload'), {
    method: 'POST',
    body: formData
  });

  return handleResponse<PipelineFileEntry>(response);
}
