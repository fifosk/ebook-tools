import { useEffect, useMemo, useState } from 'react';
import { usePipelineEvents } from '../hooks/usePipelineEvents';
import { appendAccessToken, resolveJobCoverUrl } from '../api/client';
import {
  AccessPolicyUpdatePayload,
  PipelineResponsePayload,
  PipelineStatusResponse,
  ProgressEventPayload
} from '../api/dtos';
import { resolveMediaCompletion } from '../utils/mediaFormatters';
import { getStatusGlyph } from '../utils/status';
import { resolveImageNodeLabel } from '../constants/imageNodes';
import AccessPolicyEditor from './access/AccessPolicyEditor';
import { JobProgressMediaMetadata } from './job-progress/JobProgressMediaMetadata';
import { buildJobParameterEntries } from './job-progress/jobProgressParameters';
import {
  CREATION_METADATA_KEYS,
  TERMINAL_STATES,
  buildImageClusterNodes,
  coerceNumber,
  coerceRecord,
  formatDate,
  formatFallbackValue,
  formatMetadataLabel,
  formatMetadataValue,
  formatSeconds,
  formatSecondsPerImage,
  formatTuningDescription,
  formatTuningLabel,
  formatTuningValue,
  formatTranslationProviderLabel,
  normaliseStringList,
  normalizeMetadataValue,
  normalizeTranslationProvider,
  normalizeTextValue,
  resolveImageClusterSummary,
  sortTuningEntries,
} from './job-progress/jobProgressUtils';

type Props = {
  jobId: string;
  status: PipelineStatusResponse | undefined;
  latestEvent: ProgressEventPayload | undefined;
  onEvent: (event: ProgressEventPayload) => void;
  onPause: () => void;
  onResume: () => void;
  onCancel: () => void;
  onDelete: () => void;
  onRestart: () => void;
  onReload: () => void;
  onCopy?: () => void;
  onMoveToLibrary?: () => void;
  onUpdateAccess?: (payload: AccessPolicyUpdatePayload) => Promise<void>;
  isReloading?: boolean;
  isMutating?: boolean;
  canManage: boolean;
};

type SubtitleJobTab = 'overview' | 'metadata';
type BookJobTab = 'overview' | 'metadata' | 'permissions';
export function JobProgress({
  jobId,
  status,
  latestEvent,
  onEvent,
  onPause,
  onResume,
  onCancel,
  onDelete,
  onRestart,
  onReload,
  onCopy,
  onMoveToLibrary,
  onUpdateAccess,
  isReloading = false,
  isMutating = false,
  canManage
}: Props) {
  const statusValue = status?.status ?? 'pending';
  const jobType = status?.job_type ?? 'pipeline';
  const isBookJob = jobType === 'pipeline' || jobType === 'book';
  const isPipelineLikeJob = isBookJob;
  const isSubtitleJob = jobType === 'subtitle';
  const supportsTvMetadata = isSubtitleJob || jobType === 'youtube_dub';
  const supportsYoutubeMetadata = jobType === 'youtube_dub';
  const isNarratedSubtitleJob = useMemo(() => {
    if (jobType !== 'subtitle') {
      return false;
    }
    const result = status?.result;
    if (!result || typeof result !== 'object') {
      return false;
    }
    const subtitleSection = (result as Record<string, unknown>)['subtitle'];
    if (!subtitleSection || typeof subtitleSection !== 'object') {
      return false;
    }
    const subtitleMetadata = (subtitleSection as Record<string, unknown>)['metadata'];
    if (!subtitleMetadata || typeof subtitleMetadata !== 'object') {
      return false;
    }
    return (subtitleMetadata as Record<string, unknown>)['generate_audio_book'] === true;
  }, [jobType, status?.result]);
  const isLibraryMovableJob = isPipelineLikeJob || jobType === 'youtube_dub' || isNarratedSubtitleJob;
  const isTerminal = useMemo(() => {
    if (!status) {
      return false;
    }
    return TERMINAL_STATES.includes(status.status);
  }, [status]);

  usePipelineEvents(jobId, !isTerminal, onEvent);

  const pipelineResult =
    isPipelineLikeJob && status?.result && typeof status.result === 'object'
      ? (status.result as PipelineResponsePayload)
      : null;
  const pipelineConfig =
    pipelineResult && pipelineResult.pipeline_config && typeof pipelineResult.pipeline_config === 'object'
      ? (pipelineResult.pipeline_config as Record<string, unknown>)
      : null;
  const subtitleResult =
    isSubtitleJob && status?.result && typeof status.result === 'object'
      ? (status.result as Record<string, unknown>)
      : null;
  const event = latestEvent ?? status?.latest_event ?? undefined;
  const subtitleBookMetadata =
    subtitleResult && typeof subtitleResult.book_metadata === 'object'
      ? (subtitleResult.book_metadata as Record<string, unknown>)
      : null;
  const rawMetadata = isPipelineLikeJob ? pipelineResult?.book_metadata ?? null : subtitleBookMetadata;
  const metadata = rawMetadata ?? {};
  const bookTitle = useMemo(() => normalizeTextValue(metadata['book_title']) ?? null, [metadata]);
  const bookAuthor = useMemo(() => normalizeTextValue(metadata['book_author']) ?? null, [metadata]);
  const openlibraryWorkUrl = useMemo(
    () => normalizeTextValue(metadata['openlibrary_work_url']) ?? null,
    [metadata]
  );
  const openlibraryBookUrl = useMemo(
    () => normalizeTextValue(metadata['openlibrary_book_url']) ?? null,
    [metadata]
  );
  const openlibraryLink = openlibraryBookUrl ?? openlibraryWorkUrl;
  const shouldShowCoverPreview = useMemo(() => {
    if (!isPipelineLikeJob) {
      return false;
    }
    return Boolean(
      normalizeTextValue(metadata['job_cover_asset']) ||
        normalizeTextValue(metadata['book_cover_file']) ||
        normalizeTextValue(metadata['cover_url']) ||
        normalizeTextValue(metadata['job_cover_asset_url'])
    );
  }, [isPipelineLikeJob, metadata]);
  const coverUrl = useMemo(() => {
    if (!shouldShowCoverPreview) {
      return null;
    }
    const metadataCoverUrl = normalizeTextValue(metadata['job_cover_asset_url']);
    if (metadataCoverUrl) {
      return appendAccessToken(metadataCoverUrl);
    }
    const url = resolveJobCoverUrl(jobId);
    return url ? appendAccessToken(url) : null;
  }, [jobId, metadata, shouldShowCoverPreview]);
  const [coverFailed, setCoverFailed] = useState(false);
  useEffect(() => {
    setCoverFailed(false);
  }, [coverUrl]);
  const coverAltText = useMemo(() => {
    if (bookTitle && bookAuthor) {
      return `Cover of ${bookTitle} by ${bookAuthor}`;
    }
    if (bookTitle) {
      return `Cover of ${bookTitle}`;
    }
    return 'Book cover';
  }, [bookAuthor, bookTitle]);
  const creationSummaryRaw = metadata['creation_summary'];
  const metadataEntries = Object.entries(metadata).filter(([key, value]) => {
    if (key === 'job_cover_asset' || key === 'book_metadata_lookup' || CREATION_METADATA_KEYS.has(key)) {
      return false;
    }
    if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
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
  const parallelismEntries = useMemo(() => {
    const entries: Array<{ label: string; value: string; hint?: string }> = [];
    const tuning = status?.tuning ?? null;
    const tuningRecord = coerceRecord(tuning);
    const threadCount =
      coerceNumber(tuningRecord?.thread_count) ?? coerceNumber(pipelineConfig?.thread_count);
    const translationPool =
      coerceNumber(tuningRecord?.translation_pool_workers) ?? threadCount;
    const translationProviderRaw =
      status?.parameters?.translation_provider ?? metadata['translation_provider'] ?? null;
    const translationProvider = normalizeTranslationProvider(translationProviderRaw);
    const translationModel = normalizeTextValue(metadata['translation_model']);
    const llmModel = normalizeTextValue(status?.parameters?.llm_model);
    const providerLabel =
      formatTranslationProviderLabel(
        translationProvider,
        translationModel,
        llmModel
      ) ?? 'Text translation';
    const llmSourceRaw = pipelineConfig?.llm_source;
    const llmSource = typeof llmSourceRaw === 'string' ? llmSourceRaw.trim().toLowerCase() : null;
    const batchSize = coerceNumber(status?.parameters?.translation_batch_size);
    if (translationPool !== null) {
      const hintParts = ['Controlled by Worker threads'];
      if (translationProvider === 'llm' && llmSource) {
        hintParts.push(`LLM source: ${llmSource}`);
      }
      if (batchSize !== null && batchSize > 1) {
        hintParts.push(`Batch size: ${batchSize} sentences/request`);
        if (translationProvider === 'llm' && llmSource === 'local') {
          hintParts.push('Local LLM batching caps to 1 call');
        }
      }
      entries.push({
        label: `${providerLabel} parallel calls`,
        value: formatTuningValue(translationPool),
        hint: hintParts.join('. ')
      });
    }
    if (threadCount !== null) {
      const audioHintParts = ['Controlled by Worker threads'];
      const selectedVoice = normalizeTextValue(
        status?.parameters?.selected_voice ?? pipelineConfig?.selected_voice
      );
      const generateAudio = pipelineConfig?.generate_audio;
      if (selectedVoice) {
        audioHintParts.push(`Voice: ${selectedVoice}`);
      }
      if (generateAudio === false) {
        audioHintParts.push('Audio disabled for this job');
      }
      entries.push({
        label: 'TTS parallel calls',
        value: formatTuningValue(threadCount),
        hint: audioHintParts.join('. ')
      });
    }
    return entries;
  }, [
    metadata,
    pipelineConfig?.generate_audio,
    pipelineConfig?.llm_source,
    pipelineConfig?.selected_voice,
    pipelineConfig?.thread_count,
    status?.parameters?.llm_model,
    status?.parameters?.selected_voice,
    status?.parameters?.translation_batch_size,
    status?.parameters?.translation_provider,
    status?.tuning
  ]);
  const fallbackEntries = useMemo(() => {
    const generated = coerceRecord(status?.generated_files);
    if (!generated) {
      return [];
    }
    const entries: Array<[string, string]> = [];
    const translationFallback = coerceRecord(generated['translation_fallback']);
    if (translationFallback) {
      const value = formatFallbackValue(translationFallback);
      if (value) {
        entries.push(['Translation fallback', value]);
      }
    }
    const ttsFallback = coerceRecord(generated['tts_fallback']);
    if (ttsFallback) {
      const value = formatFallbackValue(ttsFallback);
      if (value) {
        entries.push(['TTS fallback', value]);
      }
    }
    return entries;
  }, [status?.generated_files]);
  const translations = pipelineResult?.written_blocks ?? [];
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
    isBookJob && canManage && !isTerminal && statusValue !== 'paused' && statusValue !== 'pausing';
  const canResume = isBookJob && canManage && statusValue === 'paused';
  const canCancel = canManage && !isTerminal;
  const canDelete = canManage && isTerminal;
  const canRestart =
    isBookJob &&
    canManage &&
    statusValue !== 'running' &&
    statusValue !== 'pending' &&
    statusValue !== 'pausing';
  const canCopy = Boolean(onCopy);
  const mediaCompleted = useMemo(() => resolveMediaCompletion(status), [status]);
  const isLibraryCandidate =
    isLibraryMovableJob && (statusValue === 'completed' || (statusValue === 'paused' && mediaCompleted === true));
  const shouldRenderLibraryButton = Boolean(onMoveToLibrary) && canManage && isLibraryMovableJob;
  const canMoveToLibrary = shouldRenderLibraryButton && isLibraryCandidate;
  const libraryButtonTitle =
    shouldRenderLibraryButton && !isLibraryCandidate
      ? 'Media generation is still finalizing.'
      : undefined;
  const showLibraryReadyNotice = canManage && isLibraryCandidate;
  const jobParameterEntries = useMemo(() => buildJobParameterEntries(status), [status]);
  const batchStats = useMemo(() => {
    const generated = status?.generated_files;
    if (!generated || typeof generated !== 'object') {
      return null;
    }
    return coerceRecord((generated as Record<string, unknown>)['translation_batch_stats']);
  }, [status?.generated_files]);
  const batchStatEntries = useMemo(() => {
    const entries: [string, string][] = [];
    const configuredBatchSize = coerceNumber(status?.parameters?.translation_batch_size);
    const statsBatchSize = coerceNumber(batchStats?.['batch_size']);
    const resolvedBatchSize = statsBatchSize ?? configuredBatchSize;
    if (resolvedBatchSize !== null && resolvedBatchSize > 1) {
      entries.push(['Batch size', resolvedBatchSize.toString()]);
    }
    if (!batchStats) {
      if (resolvedBatchSize !== null && resolvedBatchSize > 1) {
        entries.push(['Batches completed', '0']);
        entries.push(['Items translated', '0']);
      }
      return entries;
    }
    const batches = coerceNumber(batchStats['batches_completed']);
    if (batches !== null) {
      entries.push(['Batches completed', batches.toString()]);
    }
    const items = coerceNumber(batchStats['items_completed']);
    if (items !== null) {
      entries.push(['Items translated', items.toString()]);
    }
    const avgBatch = coerceNumber(batchStats['avg_batch_seconds']);
    if (avgBatch !== null) {
      entries.push(['Avg batch time', formatSeconds(avgBatch, 's/batch')]);
    }
    const avgItem = coerceNumber(batchStats['avg_item_seconds']);
    if (avgItem !== null) {
      entries.push(['Avg item time', formatSeconds(avgItem, 's/item')]);
    }
    const lastBatch = coerceNumber(batchStats['last_batch_seconds']);
    const lastItems = coerceNumber(batchStats['last_batch_items']);
    if (lastBatch !== null) {
      const suffix =
        lastItems !== null ? ` (${lastItems} sentence${lastItems === 1 ? '' : 's'})` : '';
      entries.push(['Last batch time', `${formatSeconds(lastBatch, 's/batch')}${suffix}`]);
    }
    return entries;
  }, [batchStats, status?.parameters?.translation_batch_size]);
  const statusGlyph = getStatusGlyph(statusValue);
  const jobLabel = useMemo(() => normalizeTextValue(status?.job_label) ?? null, [status?.job_label]);
  const ownerId = typeof status?.user_id === 'string' ? status.user_id : null;
  const accessPolicy = status?.access ?? null;
  const accessDefaultVisibility = ownerId ? 'private' : 'public';

  const imageGenerationEnabled = useMemo(() => {
    const parametersEnabled = status?.parameters?.add_images;
    if (typeof parametersEnabled === 'boolean') {
      return parametersEnabled;
    }
    if (status?.image_generation && typeof status.image_generation.enabled === 'boolean') {
      return status.image_generation.enabled;
    }
    return false;
  }, [status?.parameters?.add_images, status?.image_generation]);
  const imageClusterSummary = useMemo(() => resolveImageClusterSummary(status), [status]);
  const imageClusterNodes = useMemo(
    () => buildImageClusterNodes(imageClusterSummary, pipelineConfig, imageGenerationEnabled),
    [imageClusterSummary, pipelineConfig, imageGenerationEnabled]
  );
  const [subtitleTab, setSubtitleTab] = useState<SubtitleJobTab>('overview');
  const [bookTab, setBookTab] = useState<BookJobTab>('overview');
  useEffect(() => {
    if (!supportsTvMetadata) {
      setSubtitleTab('overview');
    }
  }, [supportsTvMetadata]);
  useEffect(() => {
    if (!isBookJob) {
      setBookTab('overview');
    }
  }, [isBookJob]);
  const showMediaMetadata = supportsTvMetadata && subtitleTab === 'metadata';
  const showOverviewSections = !isBookJob || bookTab === 'overview';
  const showMetadataSections = !isBookJob || bookTab === 'metadata';
  const showPermissionsSections = !isBookJob || bookTab === 'permissions';

  return (
    <div className="job-card" aria-live="polite">
      <div className="job-card__header">
        <div className="job-card__header-title">
          <h3>{jobLabel ? `Job ${jobId} — ${jobLabel}` : `Job ${jobId}`}</h3>
          <span className="job-card__badge">{jobType}</span>
        </div>
        <div className="job-card__header-actions">
          <span className="job-status" data-state={statusValue} title={statusGlyph.label} aria-label={statusGlyph.label}>
            {statusGlyph.icon}
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
            {canRestart ? (
              <button type="button" className="link-button" onClick={onRestart} disabled={isMutating}>
                Restart
              </button>
            ) : null}
            {canCopy ? (
              <button type="button" className="link-button" onClick={onCopy} disabled={isMutating}>
                Copy
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
      <JobProgressMediaMetadata
        jobId={jobId}
        supportsTvMetadata={supportsTvMetadata}
        supportsYoutubeMetadata={supportsYoutubeMetadata}
        subtitleTab={subtitleTab}
        onTabChange={setSubtitleTab}
        canManage={canManage}
        onReload={onReload}
      />
      {isBookJob ? (
        <div className="job-card__tabs" role="tablist" aria-label="Book job tabs">
          <button
            type="button"
            role="tab"
            aria-selected={bookTab === 'overview'}
            className={`job-card__tab ${bookTab === 'overview' ? 'is-active' : ''}`}
            onClick={() => setBookTab('overview')}
          >
            Overview
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={bookTab === 'metadata'}
            className={`job-card__tab ${bookTab === 'metadata' ? 'is-active' : ''}`}
            onClick={() => setBookTab('metadata')}
          >
            Metadata
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={bookTab === 'permissions'}
            className={`job-card__tab ${bookTab === 'permissions' ? 'is-active' : ''}`}
            onClick={() => setBookTab('permissions')}
          >
            Permissions
          </button>
        </div>
      ) : null}
      {showOverviewSections && jobParameterEntries.length > 0 ? (
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
      {showPermissionsSections ? (
        <div className="job-card__section">
          <AccessPolicyEditor
            policy={accessPolicy}
            ownerId={ownerId}
            defaultVisibility={accessDefaultVisibility}
            canEdit={canManage}
            onSave={onUpdateAccess}
          />
        </div>
      ) : null}
      {showOverviewSections && isBookJob && imageClusterNodes.length > 0 ? (
        <div className="job-card__section">
          <h4>Image cluster</h4>
          <dl className="metadata-grid">
            {imageClusterNodes.map((node) => {
              const label = resolveImageNodeLabel(node.baseUrl) ?? node.baseUrl;
              const processedCount = typeof node.processed === 'number' ? node.processed : 0;
              const processedLabel = `${processedCount} image${processedCount === 1 ? '' : 's'}`;
              const statusLabel = node.active ? 'Active' : 'Inactive';
              const speedLabel = formatSecondsPerImage(node.avgSecondsPerImage);
              return (
                <div key={node.baseUrl} className="metadata-grid__row">
                  <dt>{label}</dt>
                  <dd>{`${statusLabel} • ${processedLabel} • ${speedLabel}`}</dd>
                </div>
              );
            })}
          </dl>
        </div>
      ) : null}
      {showOverviewSections && status?.error ? <div className="alert">{status.error}</div> : null}
      {showOverviewSections && showLibraryReadyNotice ? (
        <div className="notice notice--success" role="status">
          Media generation finished. Move this job into the library when you're ready.
        </div>
      ) : null}
      {showOverviewSections && statusValue === 'pausing' ? (
        <div className="notice notice--info" role="status">
          Pause requested. Completing in-flight media generation before the job fully pauses.
        </div>
      ) : null}
      {showOverviewSections && statusValue === 'paused' && mediaCompleted === false ? (
        <div className="notice notice--warning" role="status">
          Some media is still finalizing. Generated files shown below reflect the latest available output.
        </div>
      ) : null}
      {showOverviewSections && !showMediaMetadata && parallelismEntries.length > 0 ? (
        <div>
          <h4>Parallelism overview</h4>
          <div className="progress-grid">
            {parallelismEntries.map(({ label, value, hint }) => (
              <div className="progress-metric" key={label}>
                <strong>{label}</strong>
                <span>{value}</span>
                {hint ? <p className="progress-metric__hint">{hint}</p> : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}
      {showOverviewSections && !showMediaMetadata && tuningEntries.length > 0 ? (
        <div>
          <h4>Performance tuning</h4>
          <div className="progress-grid">
            {tuningEntries.map(([key, value]) => {
              const description = formatTuningDescription(key);
              return (
                <div className="progress-metric" key={key}>
                  <strong>{formatTuningLabel(key)}</strong>
                  <span>{formatTuningValue(value)}</span>
                  {description ? <p className="progress-metric__hint">{description}</p> : null}
                </div>
              );
            })}
          </div>
        </div>
      ) : null}
      {showOverviewSections && batchStatEntries.length > 0 ? (
        <div>
          <h4>LLM batch stats</h4>
          <div className="progress-grid">
            {batchStatEntries.map(([label, value]) => (
              <div className="progress-metric" key={label}>
                <strong>{label}</strong>
                <span>{value}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}
      {showOverviewSections && fallbackEntries.length > 0 ? (
        <div>
          <h4>Fallbacks</h4>
          <div className="progress-grid">
            {fallbackEntries.map(([label, value]) => (
              <div className="progress-metric" key={label}>
                <strong>{label}</strong>
                <span>{value}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}
      {showOverviewSections && translationsUnavailable ? (
        <div className="alert" role="status">
          Translated content was not returned by the LLM. Verify your model configuration and try reloading once the
          metadata has been refreshed.
        </div>
      ) : null}
      {showOverviewSections && event ? (
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
      ) : showOverviewSections ? (
        <p>No progress events received yet.</p>
      ) : null}
      {showMetadataSections && creationSummary ? (
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
      {isSubtitleJob && subtitleTab === 'metadata' ? null : !showMetadataSections ? null : (
        <div className="job-card__section">
          <h4>{isSubtitleJob ? 'Subtitle metadata' : 'Book metadata'}</h4>
          {shouldShowCoverPreview && coverUrl && !coverFailed ? (
            <div className="book-metadata-cover" aria-label="Book cover">
              {openlibraryLink ? (
                <a href={openlibraryLink} target="_blank" rel="noopener noreferrer">
                  <img
                    src={coverUrl}
                    alt={coverAltText}
                    loading="lazy"
                    decoding="async"
                    onError={() => setCoverFailed(true)}
                  />
                </a>
              ) : (
                <img
                  src={coverUrl}
                  alt={coverAltText}
                  loading="lazy"
                  decoding="async"
                  onError={() => setCoverFailed(true)}
                />
              )}
            </div>
          ) : null}
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
            {isReloading ? 'Reloading…' : isSubtitleJob ? 'Reload job' : 'Reload metadata'}
          </button>
        </div>
      )}
    </div>
  );
}

export default JobProgress;
