import { useMemo } from 'react';
import { usePipelineEvents } from '../hooks/usePipelineEvents';
import {
  PipelineJobStatus,
  PipelineStatusResponse,
  ProgressEventPayload
} from '../api/dtos';
import { resolveMediaCompletion } from '../utils/mediaFormatters';

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
  onMoveToLibrary?: () => void;
  isReloading?: boolean;
  isMutating?: boolean;
  canManage: boolean;
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

const CREATION_METADATA_KEYS = new Set([
  'creation_summary',
  'creation_messages',
  'creation_warnings',
  'creation_sentences_preview'
]);

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

function normaliseStringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((entry) => {
      if (typeof entry === 'string') {
        return entry.trim();
      }
      if (entry === null || entry === undefined) {
        return '';
      }
      return String(entry).trim();
    })
    .filter((entry) => entry.length > 0);
}

function formatMetadataValue(key: string, value: unknown): string {
  const normalized = normalizeMetadataValue(value);
  if (!normalized) {
    return '';
  }
  return normalized;
}

type JobParameterEntry = {
  key: string;
  label: string;
  value: string;
};

function coerceNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function resolveGeneratedChunks(status: PipelineStatusResponse | undefined): Record<string, unknown>[] {
  const chunks: Record<string, unknown>[] = [];
  if (!status) {
    return chunks;
  }
  const candidates = [status.generated_files, status.result?.generated_files];
  for (const candidate of candidates) {
    if (!candidate || typeof candidate !== 'object') {
      continue;
    }
    const records = (candidate as Record<string, unknown>).chunks;
    if (Array.isArray(records)) {
      for (const entry of records) {
        if (entry && typeof entry === 'object') {
          chunks.push(entry as Record<string, unknown>);
        }
      }
    }
  }
  return chunks;
}

function resolveSentenceRange(status: PipelineStatusResponse | undefined): {
  start: number | null;
  end: number | null;
} {
  const chunks = resolveGeneratedChunks(status);
  let minStart: number | null = null;
  let maxEnd: number | null = null;
  for (const chunk of chunks) {
    const rawStart = chunk['start_sentence'] ?? chunk['startSentence'];
    const rawEnd = chunk['end_sentence'] ?? chunk['endSentence'];
    const startValue = coerceNumber(rawStart);
    const endValue = coerceNumber(rawEnd);
    if (startValue !== null && (minStart === null || startValue < minStart)) {
      minStart = startValue;
    }
    if (endValue !== null && (maxEnd === null || endValue > maxEnd)) {
      maxEnd = endValue;
    }
  }
  return { start: minStart, end: maxEnd };
}

function getStringField(
  source: Record<string, unknown> | null | undefined,
  key: string
): string | null {
  if (!source) {
    return null;
  }
  const value = source[key];
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

function extractVoiceOverrides(
  source: Record<string, unknown> | null | undefined
): Record<string, string> {
  if (!source) {
    return {};
  }
  const raw = source['voice_overrides'];
  if (!raw || typeof raw !== 'object') {
    return {};
  }
  const normalized: Record<string, string> = {};
  for (const [code, voice] of Object.entries(raw as Record<string, unknown>)) {
    if (typeof code !== 'string') {
      continue;
    }
    if (typeof voice !== 'string' || !voice.trim()) {
      continue;
    }
    const trimmedCode = code.trim();
    if (!trimmedCode) {
      continue;
    }
    normalized[trimmedCode] = voice.trim();
  }
  return normalized;
}

function formatVoiceOverrides(overrides: Record<string, string> | undefined): string | null {
  if (!overrides) {
    return null;
  }
  const entries = Object.entries(overrides);
  if (entries.length === 0) {
    return null;
  }
  return entries
    .map(([code, voice]) => `${code}: ${voice}`)
    .join(', ');
}

function formatLanguageList(values: string[] | undefined): string | null {
  if (!values || values.length === 0) {
    return null;
  }
  return values.join(', ');
}

function formatTimeOffset(seconds: number | null | undefined): string | null {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds)) {
    return null;
  }
  const totalSeconds = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const remainingSeconds = totalSeconds % 60;
  const parts = [
    minutes.toString().padStart(2, '0'),
    remainingSeconds.toString().padStart(2, '0')
  ];
  if (hours > 0) {
    parts.unshift(hours.toString().padStart(2, '0'));
  }
  return parts.join(':');
}

function resolveSubtitleMetadata(
  status: PipelineStatusResponse | undefined
): Record<string, unknown> | null {
  if (!status || status.job_type !== 'subtitle') {
    return null;
  }
  const rawResult = status.result as Record<string, unknown> | null;
  if (!rawResult) {
    return null;
  }
  const subtitleSection = rawResult['subtitle'];
  if (!subtitleSection || typeof subtitleSection !== 'object') {
    return null;
  }
  const metadata = (subtitleSection as Record<string, unknown>)['metadata'];
  return metadata && typeof metadata === 'object' ? (metadata as Record<string, unknown>) : null;
}

function buildJobParameterEntries(status: PipelineStatusResponse | undefined): JobParameterEntry[] {
  if (!status) {
    return [];
  }
  const entries: JobParameterEntry[] = [];
  const parameters = status.parameters ?? null;
  const pipelineConfig =
    status.result && status.result.pipeline_config && typeof status.result.pipeline_config === 'object'
      ? (status.result.pipeline_config as Record<string, unknown>)
      : null;
  const languageValues = (parameters?.target_languages ?? []).filter(
    (value): value is string => typeof value === 'string' && value.trim().length > 0
  );
  const sentenceRange = resolveSentenceRange(status);
  const startSentence = parameters?.start_sentence ?? sentenceRange.start;
  const endSentence = parameters?.end_sentence ?? sentenceRange.end;
  const llmModel = parameters?.llm_model ?? getStringField(pipelineConfig, 'ollama_model');

  if (status.job_type === 'subtitle') {
    const subtitleMetadata = resolveSubtitleMetadata(status);
    const translationLanguage =
      languageValues[0] ?? getStringField(subtitleMetadata, 'target_language');
    if (translationLanguage) {
      entries.push({
        key: 'subtitle-translation-language',
        label: 'Translation language',
        value: translationLanguage
      });
    }
    if (llmModel) {
      entries.push({ key: 'subtitle-llm-model', label: 'LLM model', value: llmModel });
    }
    if (startSentence !== null) {
      entries.push({
        key: 'subtitle-start-sentence',
        label: 'Start sentence',
        value: startSentence.toString()
      });
    }
    if (endSentence !== null) {
      entries.push({
        key: 'subtitle-end-sentence',
        label: 'End sentence',
        value: endSentence.toString()
      });
    }
    const startTimeLabel =
      getStringField(subtitleMetadata, 'start_time_offset_label') ??
      formatTimeOffset(parameters?.start_time_offset_seconds);
    if (startTimeLabel) {
      entries.push({
        key: 'subtitle-start-time',
        label: 'Start time',
        value: startTimeLabel
      });
    }
    const endTimeLabel =
      getStringField(subtitleMetadata, 'end_time_offset_label') ??
      formatTimeOffset(parameters?.end_time_offset_seconds);
    if (endTimeLabel) {
      entries.push({
        key: 'subtitle-end-time',
        label: 'End time',
        value: endTimeLabel
      });
    }
    return entries;
  }

  const languageList = formatLanguageList(languageValues);
  if (languageList) {
    entries.push({ key: 'pipeline-target-languages', label: 'Target languages', value: languageList });
  }
  if (llmModel) {
    entries.push({ key: 'pipeline-llm-model', label: 'LLM model', value: llmModel });
  }
  if (startSentence !== null) {
    entries.push({
      key: 'pipeline-start-sentence',
      label: 'Start sentence',
      value: startSentence.toString()
    });
  }
  if (endSentence !== null) {
    entries.push({
      key: 'pipeline-end-sentence',
      label: 'End sentence',
      value: endSentence.toString()
    });
  }
  const audioMode = parameters?.audio_mode ?? getStringField(pipelineConfig, 'audio_mode');
  if (audioMode) {
    entries.push({ key: 'pipeline-audio-mode', label: 'Voice mode', value: audioMode });
  }
  const selectedVoice =
    parameters?.selected_voice ?? getStringField(pipelineConfig, 'selected_voice');
  if (selectedVoice) {
    entries.push({ key: 'pipeline-selected-voice', label: 'Selected voice', value: selectedVoice });
  }
  const parameterOverrides =
    parameters?.voice_overrides && Object.keys(parameters.voice_overrides).length > 0
      ? parameters.voice_overrides
      : undefined;
  const configOverrides = extractVoiceOverrides(pipelineConfig);
  const voiceOverrideText = formatVoiceOverrides(parameterOverrides ?? configOverrides);
  if (voiceOverrideText) {
    entries.push({
      key: 'pipeline-voice-overrides',
      label: 'Voice overrides',
      value: voiceOverrideText
    });
  }
  return entries;
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
  onMoveToLibrary,
  isReloading = false,
  isMutating = false,
  canManage
}: Props) {
  const statusValue = status?.status ?? 'pending';
  const jobType = status?.job_type ?? 'pipeline';
  const isPipelineJob = jobType === 'pipeline';
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
  const creationSummaryRaw = metadata['creation_summary'];
  const metadataEntries = Object.entries(metadata).filter(([key, value]) => {
    if (key === 'job_cover_asset' || CREATION_METADATA_KEYS.has(key)) {
      return false;
    }
    const normalized = normalizeMetadataValue(value);
    return normalized.length > 0;
  });
  const creationSummary = useMemo(() => {
    if (!creationSummaryRaw || typeof creationSummaryRaw !== 'object') {
      return null;
    }
    const summary = creationSummaryRaw as Record<string, unknown>;
    const messages = normaliseStringList(summary['messages']);
    const warnings = normaliseStringList(summary['warnings']);
    const sentencesPreview = normaliseStringList(summary['sentences_preview']);
    const epubPath = typeof summary['epub_path'] === 'string' ? summary['epub_path'].trim() : null;
    if (!messages.length && !warnings.length && !sentencesPreview.length && !epubPath) {
      return null;
    }
    return {
      messages,
      warnings,
      sentencesPreview,
      epubPath: epubPath && epubPath.length > 0 ? epubPath : null
    };
  }, [creationSummaryRaw]);
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

  const canPause =
    isPipelineJob && canManage && !isTerminal && statusValue !== 'paused' && statusValue !== 'pausing';
  const canResume = isPipelineJob && canManage && statusValue === 'paused';
  const canCancel = canManage && !isTerminal;
  const canDelete = canManage && isTerminal;
  const mediaCompleted = useMemo(() => resolveMediaCompletion(status), [status]);
  const isLibraryCandidate =
    isPipelineJob && (statusValue === 'completed' || (statusValue === 'paused' && mediaCompleted === true));
  const shouldRenderLibraryButton = Boolean(onMoveToLibrary) && canManage && isPipelineJob;
  const canMoveToLibrary = shouldRenderLibraryButton && isLibraryCandidate;
  const libraryButtonTitle =
    shouldRenderLibraryButton && !isLibraryCandidate
      ? 'Media generation is still finalizing.'
      : undefined;
  const showLibraryReadyNotice = canManage && isLibraryCandidate;
  const jobParameterEntries = useMemo(() => buildJobParameterEntries(status), [status]);

  return (
    <div className="job-card" aria-live="polite">
      <div className="job-card__header">
        <div className="job-card__header-title">
          <h3>Job {jobId}</h3>
          <span className="job-card__badge">{jobType}</span>
        </div>
        <div className="job-card__header-actions">
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
            {shouldRenderLibraryButton ? (
              <button
                type="button"
                className="link-button"
                onClick={() => onMoveToLibrary?.()}
                disabled={isMutating || !canMoveToLibrary}
                title={libraryButtonTitle}
              >
                Move to library
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
        {mediaCompleted !== null ? (
          <>
            <br />
            <strong>Media finalized:</strong> {mediaCompleted ? 'Yes' : 'In progress'}
          </>
        ) : null}
      </p>
      {jobParameterEntries.length > 0 ? (
        <div className="job-card__section">
          <h4>Job parameters</h4>
          <dl className="metadata-grid">
            {jobParameterEntries.map((entry) => (
              <div key={entry.key} className="metadata-grid__row">
                <dt>{entry.label}</dt>
                <dd>{entry.value}</dd>
              </div>
            ))}
          </dl>
        </div>
      ) : null}
      {status?.error ? <div className="alert">{status.error}</div> : null}
      {showLibraryReadyNotice ? (
        <div className="notice notice--success" role="status">
          Media generation finished. Move this job into the library when you're ready.
        </div>
      ) : null}
      {statusValue === 'pausing' ? (
        <div className="notice notice--info" role="status">
          Pause requested. Completing in-flight media generation before the job fully pauses.
        </div>
      ) : null}
      {statusValue === 'paused' && mediaCompleted === false ? (
        <div className="notice notice--warning" role="status">
          Some media is still finalizing. Generated files shown below reflect the latest available output.
        </div>
      ) : null}
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
      {creationSummary ? (
        <div className="job-card__section">
          <h4>Book creation summary</h4>
          {creationSummary.epubPath ? (
            <p>
              <strong>Seed EPUB:</strong> {creationSummary.epubPath}
            </p>
          ) : null}
          {creationSummary.messages.length ? (
            <ul style={{ marginTop: '0.5rem', marginBottom: creationSummary.warnings.length ? 0.5 : 0, paddingLeft: '1.25rem' }}>
              {creationSummary.messages.map((message, index) => (
                <li key={`creation-message-${index}`}>{message}</li>
              ))}
            </ul>
          ) : null}
          {creationSummary.sentencesPreview.length ? (
            <p style={{ marginTop: '0.5rem', marginBottom: creationSummary.warnings.length ? 0.5 : 0 }}>
              <strong>Sample sentences:</strong> {creationSummary.sentencesPreview.join(' ')}
            </p>
          ) : null}
          {creationSummary.warnings.length ? (
            <div className="notice notice--warning" role="alert" style={{ marginTop: '0.5rem' }}>
              <ul style={{ margin: 0, paddingLeft: '1.25rem' }}>
                {creationSummary.warnings.map((warning, index) => (
                  <li key={`creation-warning-${index}`}>{warning}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
      <div className="job-card__section">
        <h4>Book metadata</h4>
        {metadataEntries.length > 0 ? (
          <dl className="metadata-grid">
            {metadataEntries.map(([key, value]) => {
              const formatted = formatMetadataValue(key, value);
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
          <p className="job-card__metadata-empty">Metadata is not available yet.</p>
        )}
        <button
          type="button"
          className="link-button"
          onClick={onReload}
          disabled={!canManage || isReloading || isMutating}
          aria-busy={isReloading || isMutating}
          data-variant="metadata-action"
        >
          {isReloading ? 'Reloading…' : 'Reload metadata'}
        </button>
      </div>
    </div>
  );
}

export default JobProgress;
