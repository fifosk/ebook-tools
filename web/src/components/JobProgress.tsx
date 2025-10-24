import { useCallback, useEffect, useMemo, useState } from 'react';
import { usePipelineEvents } from '../hooks/usePipelineEvents';
import {
  PipelineJobStatus,
  PipelineStatusResponse,
  ProgressEventPayload
} from '../api/dtos';
import { buildBatchSlidePreviewUrls, buildStorageUrl } from '../api/client';

const TERMINAL_STATES: PipelineJobStatus[] = ['completed', 'failed', 'cancelled'];

type Props = {
  jobId: string;
  status: PipelineStatusResponse | undefined;
  latestEvent: ProgressEventPayload | undefined;
  onEvent: (event: ProgressEventPayload) => void;
  onPause: () => void;
  onResume: () => void;
  onCancel: () => void;
  onDelete: () => void;
  onReload: () => void;
  isReloading?: boolean;
  isMutating?: boolean;
};

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return '—';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

const METADATA_LABELS: Record<string, string> = {
  book_title: 'Title',
  book_author: 'Author',
  book_year: 'Publication year',
  book_summary: 'Summary',
  book_cover_file: 'Cover file'
};

const TUNING_LABELS: Record<string, string> = {
  hardware_profile: 'Hardware profile',
  detected_cpu_cores: 'Detected CPU cores',
  detected_memory_gib: 'Detected memory (GiB)',
  pipeline_mode: 'Pipeline mode enabled',
  thread_count: 'Translation threads',
  translation_pool_workers: 'Translation pool workers',
  translation_pool_mode: 'Worker pool mode',
  queue_size: 'Translation queue size',
  job_worker_slots: 'Job worker slots',
  job_max_workers: 'Configured job workers',
  slide_parallelism: 'Slide parallelism',
  slide_parallel_workers: 'Slide workers'
};

const TUNING_ORDER: string[] = [
  'hardware_profile',
  'detected_cpu_cores',
  'detected_memory_gib',
  'pipeline_mode',
  'thread_count',
  'translation_pool_workers',
  'translation_pool_mode',
  'queue_size',
  'job_worker_slots',
  'job_max_workers',
  'slide_parallelism',
  'slide_parallel_workers'
];

function formatMetadataLabel(key: string): string {
  return METADATA_LABELS[key] ?? key.replace(/_/g, ' ');
}

function normalizeMetadataValue(value: unknown): string {
  if (value === null || value === undefined) {
    return '';
  }
  if (typeof value === 'string') {
    return value.trim();
  }
  return String(value);
}

function formatTuningLabel(key: string): string {
  return TUNING_LABELS[key] ?? key.replace(/_/g, ' ');
}

function formatTuningValue(value: unknown): string {
  if (value === null || value === undefined) {
    return '';
  }
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) {
      return value.toString();
    }
    return Number.isInteger(value) ? value.toString() : value.toFixed(1);
  }
  if (typeof value === 'string') {
    return value;
  }
  return JSON.stringify(value);
}

type CoverAsset =
  | { type: 'external'; url: string }
  | { type: 'storage'; path: string; raw: string }
  | null;

type SlidePreviewState = {
  batchEntry: string | null;
  batchIndex: number | null;
  candidates: string[];
  candidateIndex: number;
  cacheBuster: number;
  status: 'idle' | 'loading' | 'success' | 'error';
};

type BatchPreviewMetadata = {
  entry: string;
  indexHint: number | null;
} | null;

function parseBatchIndex(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return Math.max(1, Math.trunc(value));
  }
  if (typeof value === 'string') {
    const parsed = parseInt(value, 10);
    if (!Number.isNaN(parsed) && parsed > 0) {
      return parsed;
    }
  }
  return null;
}

function extractBatchPreviewMetadata(metadata: Record<string, unknown> | null | undefined): BatchPreviewMetadata {
  if (!metadata) {
    return null;
  }

  const indexCandidates = ['batch_index', 'batch_number', 'batch_no', 'batch_id', 'batch'];
  let indexHint: number | null = null;
  for (const key of indexCandidates) {
    if (key in metadata) {
      indexHint = parseBatchIndex(metadata[key]);
      if (indexHint !== null) {
        break;
      }
    }
  }

  const pathKeys = [
    'batch_video_path',
    'batch_video_file',
    'batch_video',
    'batch_output_path',
    'batch_output_dir',
    'batch_path',
    'batch_directory',
    'batch_dir',
    'video_path',
    'slides_path',
    'slide_preview',
    'slide_preview_path',
    'batch_preview',
    'preview_path'
  ];

  for (const key of pathKeys) {
    const value = metadata[key];
    if (typeof value === 'string') {
      const trimmed = value.trim();
      if (trimmed) {
        return { entry: trimmed, indexHint };
      }
    }
  }

  const arrayCandidates = ['batch_video_files', 'batch_previews'];
  for (const key of arrayCandidates) {
    const value = metadata[key];
    if (Array.isArray(value)) {
      const strings = value.filter((item): item is string => typeof item === 'string');
      if (strings.length > 0) {
        const last = strings[strings.length - 1].trim();
        if (last) {
          return { entry: last, indexHint: indexHint ?? parseBatchIndex(strings.length) };
        }
      }
    }
  }

  for (const value of Object.values(metadata)) {
    if (typeof value === 'string') {
      const trimmed = value.trim();
      if (!trimmed) {
        continue;
      }
      if (/\.mp4(?:$|[?#])/iu.test(trimmed) || /\/slides\//iu.test(trimmed) || /\.png(?:$|[?#])/iu.test(trimmed)) {
        return { entry: trimmed, indexHint };
      }
    } else if (Array.isArray(value)) {
      const match = value.find((item) => typeof item === 'string' && /\.mp4|\/slides\//iu.test(item));
      if (typeof match === 'string') {
        const trimmed = match.trim();
        if (trimmed) {
          return { entry: trimmed, indexHint };
        }
      }
    }
  }

  return null;
}

function normalisePreviewSource(entry: string | null): string {
  if (!entry) {
    return '';
  }
  return entry.replace(/\\+/g, '/').replace(/[?#].*$/u, '').trim();
}

function resolvePreviewBatchLabel(entry: string | null, index: number | null): string {
  if (index !== null) {
    return `Batch ${index}`;
  }
  const source = normalisePreviewSource(entry);
  if (source) {
    const segments = source.split('/').filter((segment) => segment.length > 0);
    if (segments.length > 0) {
      const last = segments[segments.length - 1];
      return last.replace(/\.[^.]+$/u, '') || 'Latest batch';
    }
  }
  return 'Latest batch';
}

function isExternalAsset(path: string): boolean {
  const lower = path.trim().toLowerCase();
  return lower.startsWith('http://') || lower.startsWith('https://') || lower.startsWith('data:');
}

function normaliseStoragePath(path: string): string {
  const normalised = path.replace(/\\/g, '/').trim();
  if (!normalised) {
    return '';
  }

  const withoutDrive = normalised.replace(/^[A-Za-z]:/, '');
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

  const storageIndex = lowered.indexOf('storage');
  if (storageIndex >= 0 && storageIndex + 1 < segments.length) {
    return segments.slice(storageIndex + 1).join('/');
  }

  const outputIndex = lowered.indexOf('output');
  if (outputIndex >= 0 && outputIndex + 1 < segments.length) {
    return segments.slice(outputIndex + 1).join('/');
  }

  return segments.join('/');
}

function resolveCoverAsset(metadata: Record<string, unknown>): CoverAsset {
  const rawValue = metadata['book_cover_file'];
  if (typeof rawValue !== 'string') {
    return null;
  }
  const trimmed = rawValue.trim();
  if (!trimmed) {
    return null;
  }
  if (isExternalAsset(trimmed)) {
    return { type: 'external', url: trimmed };
  }
  const relative = normaliseStoragePath(trimmed);
  if (!relative) {
    return { type: 'storage', path: '', raw: trimmed };
  }
  return { type: 'storage', path: relative, raw: trimmed };
}

function formatMetadataValue(key: string, value: unknown, coverAsset: CoverAsset): string {
  const normalized = normalizeMetadataValue(value);
  if (!normalized) {
    return '';
  }
  if (key === 'book_cover_file' && coverAsset) {
    if (coverAsset.type === 'external') {
      return coverAsset.url;
    }
    const relative = coverAsset.path.trim();
    if (relative) {
      return `storage/${relative.replace(/^\/+/, '')}`;
    }
    return coverAsset.raw || normalized;
  }
  return normalized;
}

function sortTuningEntries(entries: [string, unknown][]): [string, unknown][] {
  const order = new Map<string, number>(TUNING_ORDER.map((key, index) => [key, index]));
  return entries
    .slice()
    .sort((a, b) => {
      const rankA = order.get(a[0]) ?? Number.MAX_SAFE_INTEGER;
      const rankB = order.get(b[0]) ?? Number.MAX_SAFE_INTEGER;
      if (rankA === rankB) {
        return a[0].localeCompare(b[0]);
      }
      return rankA - rankB;
    });
}

export function JobProgress({
  jobId,
  status,
  latestEvent,
  onEvent,
  onPause,
  onResume,
  onCancel,
  onDelete,
  onReload,
  isReloading = false,
  isMutating = false
}: Props) {
  const statusValue = status?.status ?? 'pending';
  const isTerminal = useMemo(() => {
    if (!status) {
      return false;
    }
    return TERMINAL_STATES.includes(status.status);
  }, [status]);

  usePipelineEvents(jobId, !isTerminal, onEvent);

  const event = latestEvent ?? status?.latest_event ?? undefined;
  const bookMetadata = status?.result?.book_metadata ?? null;
  const metadata = bookMetadata ?? {};
  const metadataEntries = Object.entries(metadata).filter(([, value]) => {
    const normalized = normalizeMetadataValue(value);
    return normalized.length > 0;
  });
  const coverAsset = useMemo(() => resolveCoverAsset(metadata), [metadata]);
  const coverSources = useMemo(() => {
    if (!coverAsset) {
      return [] as string[];
    }
    if (coverAsset.type === 'external') {
      return [coverAsset.url];
    }

    const sources: string[] = [];
    const unique = new Set<string>();

    const push = (candidate: string | null | undefined) => {
      const trimmed = candidate?.trim();
      if (!trimmed) {
        return;
      }
      if (unique.has(trimmed)) {
        return;
      }
      unique.add(trimmed);
      sources.push(trimmed);
    };

    const normalisedPath = coverAsset.path.trim();
    if (normalisedPath) {
      try {
        push(buildStorageUrl(normalisedPath));
      } catch (error) {
        console.warn('Unable to build storage URL for cover image', error);
      }

      const stripped = normalisedPath.replace(/^\/+/, '');
      push(`/storage/${stripped}`);
      push(`/${stripped}`);
    }

    const rawValue = coverAsset.raw.trim();
    if (rawValue) {
      if (isExternalAsset(rawValue)) {
        push(rawValue);
      } else if (rawValue.startsWith('/')) {
        push(rawValue);
      } else {
        push(`/${rawValue}`);
      }
    }

    return sources;
  }, [coverAsset]);
  const [coverSourceIndex, setCoverSourceIndex] = useState(0);
  const coverUrl = coverSources[coverSourceIndex] ?? null;
  const [coverFailed, setCoverFailed] = useState(false);
  useEffect(() => {
    setCoverSourceIndex(0);
    setCoverFailed(false);
  }, [coverSources, bookMetadata]);
  const handleCoverError = useCallback(() => {
    setCoverSourceIndex((currentIndex) => {
      const nextIndex = currentIndex + 1;
      if (nextIndex >= coverSources.length) {
        setCoverFailed(true);
        return currentIndex;
      }
      return nextIndex;
    });
  }, [coverSources.length]);
  const handleCoverRetry = useCallback(() => {
    setCoverFailed(false);
    setCoverSourceIndex(0);
  }, []);
  const coverAltText = useMemo(() => {
    const title = normalizeMetadataValue(metadata['book_title']);
    const author = normalizeMetadataValue(metadata['book_author']);
    if (title && author) {
      return `Cover of ${title} by ${author}`;
    }
    if (title) {
      return `Cover of ${title}`;
    }
    if (author) {
      return `Book cover for ${author}`;
    }
    return 'Book cover preview';
  }, [metadata]);
  const coverPlaceholderMessage = useMemo(() => {
    if (coverFailed) {
      return 'Cover preview could not be loaded.';
    }
    if (coverAsset) {
      return 'Cover preview is not available.';
    }
    return 'Cover image not provided yet.';
  }, [coverAsset, coverFailed]);
  const tuningEntries = useMemo(() => {
    const tuning = status?.tuning ?? null;
    if (!tuning) {
      return [];
    }
    const filtered = Object.entries(tuning).filter(([, value]) => {
      if (value === null || value === undefined) {
        return false;
      }
      const formatted = formatTuningValue(value);
      return formatted.length > 0;
    });
    return sortTuningEntries(filtered);
  }, [status?.tuning]);
  const translations = status?.result?.written_blocks ?? [];
  const translationsUnavailable = Array.isArray(translations)
    ? translations.length > 0 && translations.every((block) => {
        if (typeof block !== 'string') {
          return false;
        }
        const cleaned = block.trim();
        return cleaned.length === 0 || cleaned.toUpperCase() === 'N/A';
      })
    : false;

  const [previewState, setPreviewState] = useState<SlidePreviewState>({
    batchEntry: null,
    batchIndex: null,
    candidates: [],
    candidateIndex: 0,
    cacheBuster: 0,
    status: 'idle'
  });

  const setPreviewFromEntry = useCallback((entry: string, indexHint?: number | null) => {
    const trimmedEntry = entry.trim();
    if (!trimmedEntry) {
      return;
    }
    const safeIndex = indexHint !== undefined && indexHint !== null ? parseBatchIndex(indexHint) : null;

    setPreviewState((prev) => {
      const nextIndex =
        safeIndex !== null
          ? safeIndex
          : prev.batchEntry && prev.batchEntry !== trimmedEntry
            ? prev.batchIndex !== null
              ? prev.batchIndex + 1
              : null
            : prev.batchIndex;

      if (prev.batchEntry === trimmedEntry) {
        if (prev.batchIndex === nextIndex) {
          return prev;
        }
        return { ...prev, batchIndex: nextIndex };
      }

      const candidates = buildBatchSlidePreviewUrls(trimmedEntry);
      return {
        batchEntry: trimmedEntry,
        batchIndex: nextIndex,
        candidates,
        candidateIndex: 0,
        cacheBuster: Date.now(),
        status: candidates.length > 0 ? 'loading' : 'error'
      };
    });
  }, []);

  const previewMetadata = useMemo(() => extractBatchPreviewMetadata(event?.metadata ?? null), [event?.metadata]);

  useEffect(() => {
    if (!status?.result?.batch_video_files) {
      return;
    }
    const entries = status.result.batch_video_files.filter((item): item is string => typeof item === 'string' && item.trim().length > 0);
    if (entries.length === 0) {
      return;
    }
    const latestEntry = entries[entries.length - 1];
    setPreviewFromEntry(latestEntry, parseBatchIndex(entries.length));
  }, [status?.result?.batch_video_files, setPreviewFromEntry]);

  useEffect(() => {
    if (!previewMetadata) {
      return;
    }
    setPreviewFromEntry(previewMetadata.entry, previewMetadata.indexHint);
  }, [previewMetadata, setPreviewFromEntry]);

  const previewSrc = useMemo(() => {
    const candidate = previewState.candidates[previewState.candidateIndex];
    if (!candidate) {
      return null;
    }
    if (!previewState.cacheBuster) {
      return candidate;
    }
    const separator = candidate.includes('?') ? '&' : '?';
    return `${candidate}${separator}cb=${previewState.cacheBuster}`;
  }, [previewState.candidates, previewState.candidateIndex, previewState.cacheBuster]);

  const previewSource = useMemo(() => normalisePreviewSource(previewState.batchEntry), [previewState.batchEntry]);
  const previewBatchLabel = useMemo(
    () => resolvePreviewBatchLabel(previewState.batchEntry, previewState.batchIndex),
    [previewState.batchEntry, previewState.batchIndex]
  );
  const previewAltText = useMemo(() => `Slide preview for ${previewBatchLabel}`, [previewBatchLabel]);
  const previewUpdatedAt = useMemo(() => {
    if (!previewState.cacheBuster) {
      return null;
    }
    const timestamp = new Date(previewState.cacheBuster);
    if (Number.isNaN(timestamp.getTime())) {
      return null;
    }
    return timestamp.toLocaleTimeString();
  }, [previewState.cacheBuster]);

  const handlePreviewError = useCallback(() => {
    setPreviewState((prev) => {
      if (prev.candidates.length === 0) {
        if (prev.status === 'error') {
          return prev;
        }
        return { ...prev, status: 'error' };
      }
      const nextIndex = prev.candidateIndex + 1;
      if (nextIndex < prev.candidates.length) {
        return {
          ...prev,
          candidateIndex: nextIndex,
          cacheBuster: Date.now(),
          status: 'loading'
        };
      }
      return { ...prev, status: 'error' };
    });
  }, []);

  const handlePreviewLoad = useCallback(() => {
    setPreviewState((prev) => {
      if (prev.status === 'success') {
        return prev;
      }
      return { ...prev, status: 'success' };
    });
  }, []);

  const handlePreviewRetry = useCallback(() => {
    setPreviewState((prev) => {
      if (!prev.batchEntry) {
        return prev;
      }
      const candidates = prev.candidates.length > 0 ? prev.candidates : buildBatchSlidePreviewUrls(prev.batchEntry);
      if (candidates.length === 0) {
        return { ...prev, candidates: [], status: 'error', cacheBuster: Date.now() };
      }
      return {
        ...prev,
        candidates,
        candidateIndex: 0,
        cacheBuster: Date.now(),
        status: 'loading'
      };
    });
  }, []);

  const previewStatusMessage = useMemo(() => {
    switch (previewState.status) {
      case 'loading':
        return `Slide preview is loading for ${previewBatchLabel}…`;
      case 'error':
        return 'Slide preview is not available yet. The slide image may still be rendering.';
      case 'success':
        if (previewUpdatedAt) {
          return `Slide preview refreshed for ${previewBatchLabel} at ${previewUpdatedAt}.`;
        }
        return `Slide preview refreshed for ${previewBatchLabel}.`;
      default:
        return 'Slide preview will appear once the first batch finishes rendering.';
    }
  }, [previewBatchLabel, previewState.status, previewUpdatedAt]);

  const previewStatusRole = previewState.status === 'error' ? 'alert' : 'status';
  const showPreviewRetry = previewState.status === 'error' && !!previewState.batchEntry;
  const previewFrameState = previewState.batchEntry ? previewState.status : 'idle';

  const canPause = !isTerminal && statusValue !== 'paused';
  const canResume = statusValue === 'paused';
  const canCancel = !isTerminal;
  const canDelete = isTerminal;

  return (
    <div className="job-card" aria-live="polite">
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '0.75rem',
          flexWrap: 'wrap'
        }}
      >
        <div style={{ flexGrow: 1 }}>
          <h3 style={{ marginTop: 0 }}>Job {jobId}</h3>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          <span className="job-status" data-state={statusValue}>
            {statusValue}
          </span>
          <div className="job-actions" aria-label={`Actions for job ${jobId}`} aria-busy={isMutating}>
            {canPause ? (
              <button type="button" className="link-button" onClick={onPause} disabled={isMutating}>
                Pause
              </button>
            ) : null}
            {canResume ? (
              <button type="button" className="link-button" onClick={onResume} disabled={isMutating}>
                Resume
              </button>
            ) : null}
            {canCancel ? (
              <button type="button" className="link-button" onClick={onCancel} disabled={isMutating}>
                Cancel
              </button>
            ) : null}
            {canDelete ? (
              <button type="button" className="link-button" onClick={onDelete} disabled={isMutating}>
                Delete
              </button>
            ) : null}
          </div>
        </div>
      </div>
      <p>
        <strong>Created:</strong> {formatDate(status?.created_at ?? null)}
        <br />
        <strong>Started:</strong> {formatDate(status?.started_at)}
        <br />
        <strong>Completed:</strong> {formatDate(status?.completed_at)}
      </p>
      {status?.error ? <div className="alert">{status.error}</div> : null}
      {tuningEntries.length > 0 ? (
        <div>
          <h4>Performance tuning</h4>
          <div className="progress-grid">
            {tuningEntries.map(([key, value]) => (
              <div className="progress-metric" key={key}>
                <strong>{formatTuningLabel(key)}</strong>
                <span>{formatTuningValue(value)}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}
      {translationsUnavailable ? (
        <div className="alert" role="status">
          Translated content was not returned by the LLM. Verify your model configuration and try reloading once the
          metadata has been refreshed.
        </div>
      ) : null}
      {event ? (
        <div>
          <h4>Latest progress</h4>
          <div className="progress-grid">
            <div className="progress-metric">
              <strong>Event</strong>
              <span>{event.event_type}</span>
            </div>
            <div className="progress-metric">
              <strong>Completed</strong>
              <span>
                {event.snapshot.completed}
                {event.snapshot.total !== null ? ` / ${event.snapshot.total}` : ''}
              </span>
            </div>
            <div className="progress-metric">
              <strong>Speed</strong>
              <span>{event.snapshot.speed.toFixed(2)} items/s</span>
            </div>
            <div className="progress-metric">
              <strong>Elapsed</strong>
              <span>{event.snapshot.elapsed.toFixed(2)} s</span>
            </div>
            <div className="progress-metric">
              <strong>ETA</strong>
              <span>
                {event.snapshot.eta !== null ? `${event.snapshot.eta.toFixed(2)} s` : '—'}
              </span>
            </div>
          </div>
          {event.error ? <div className="alert">{event.error}</div> : null}
        </div>
      ) : (
        <p>No progress events received yet.</p>
      )}
      <div className="slide-preview-card" data-state={previewFrameState} aria-live="polite">
        <div className="slide-preview-card__header">
          <div>
            <h4 style={{ marginTop: 0, marginBottom: '0.25rem' }}>Slide preview</h4>
            <span className="slide-preview-card__label">{previewBatchLabel}</span>
          </div>
          {showPreviewRetry ? (
            <button type="button" className="link-button" onClick={handlePreviewRetry}>
              Retry preview
            </button>
          ) : null}
        </div>
        <div className="slide-preview-card__frame" data-state={previewFrameState} aria-busy={previewState.status === 'loading'}>
          {previewSrc ? (
            <img src={previewSrc} alt={previewAltText} onError={handlePreviewError} onLoad={handlePreviewLoad} />
          ) : (
            <div className="slide-preview-card__placeholder" role="status">
              <span>{previewState.status === 'loading' ? 'Loading preview…' : 'Preview will appear after the first batch is ready.'}</span>
            </div>
          )}
        </div>
        <p className="slide-preview-card__status" role={previewStatusRole}>
          {previewStatusMessage}
        </p>
        {previewSource ? (
          <div className="slide-preview-card__meta">
            <span className="slide-preview-card__meta-label">Source</span>
            <code className="slide-preview-card__meta-value">{previewSource}</code>
          </div>
        ) : null}
      </div>
      <div style={{ marginTop: '1rem' }}>
        <h4>Book metadata</h4>
        <div className="metadata-cover-preview">
          {coverUrl && !coverFailed ? (
            <img src={coverUrl} alt={coverAltText} onError={handleCoverError} />
          ) : (
            <div className="metadata-cover-preview__placeholder" role="status" aria-live="polite">
              <span>{coverPlaceholderMessage}</span>
              {coverFailed && coverUrl ? (
                <button type="button" className="link-button" onClick={handleCoverRetry}>
                  Retry preview
                </button>
              ) : null}
            </div>
          )}
        </div>
        {metadataEntries.length > 0 ? (
          <dl className="metadata-grid">
            {metadataEntries.map(([key, value]) => {
              const formatted = formatMetadataValue(key, value, coverAsset);
              if (!formatted) {
                return null;
              }
              return (
                <div key={key} className="metadata-grid__row">
                  <dt>{formatMetadataLabel(key)}</dt>
                  <dd>{formatted}</dd>
                </div>
              );
            })}
          </dl>
        ) : (
          <p style={{ marginTop: 0 }}>Metadata is not available yet.</p>
        )}
        <button
          type="button"
          className="link-button"
          onClick={onReload}
          disabled={isReloading || isMutating}
          aria-busy={isReloading || isMutating}
          style={{ marginTop: '0.5rem' }}
        >
          {isReloading ? 'Reloading…' : 'Reload metadata'}
        </button>
      </div>
      {status?.result ? (
        <details style={{ marginTop: '1rem' }}>
          <summary>View pipeline result payload</summary>
          <pre style={{ overflowX: 'auto' }}>{JSON.stringify(status.result, null, 2)}</pre>
        </details>
      ) : null}
    </div>
  );
}

export default JobProgress;
