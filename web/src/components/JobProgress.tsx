import { useCallback, useEffect, useMemo, useState } from 'react';
import { useJobEventsWithRetry } from '../hooks/useJobEventsWithRetry';
import { appendAccessToken, resolveJobCoverUrl } from '../api/client';
import {
  AccessPolicyUpdatePayload,
  PipelineResponsePayload,
  PipelineStatusResponse,
  ProgressEventPayload
} from '../api/dtos';
import { resolveMediaCompletion } from '../utils/mediaFormatters';
import { getStatusGlyph } from '../utils/status';
import {
  JobProgressCreationSummary,
  parseJobProgressCreationSummary
} from './job-progress/JobProgressCreationSummary';
import { JobProgressHeader } from './job-progress/JobProgressHeader';
import { JobProgressLatestSection } from './job-progress/JobProgressLatestSection';
import { JobProgressMediaMetadata } from './job-progress/JobProgressMediaMetadata';
import { JobProgressMetadataSection } from './job-progress/JobProgressMetadataSection';
import { JobProgressOverviewSection } from './job-progress/JobProgressOverviewSection';
import { JobProgressPermissionsSection } from './job-progress/JobProgressPermissionsSection';
import { JobProgressStageSection } from './job-progress/JobProgressStageSection';
import { JobProgressTabs, type JobProgressTab } from './job-progress/JobProgressTabs';
import { JobProgressTimingSummary } from './job-progress/JobProgressTimingSummary';
import { resolveProgressStage } from '../utils/progressEvents';
import { buildJobParameterEntries } from './job-progress/jobProgressParameters';
import {
  TERMINAL_STATES,
  areTranslationsUnavailable,
  buildBatchProgress,
  buildBatchStatEntries,
  buildFallbackEntries,
  buildImageClusterNodes,
  buildParallelismEntries,
  coerceNumber,
  formatTuningValue,
  isNarratedSubtitleJobStatus,
  normalizeTranslationProvider,
  normalizeTextValue,
  resolveGeneratedFileRecord,
  resolveImageClusterSummary,
  resolveLookupCacheBuildingProgress,
  resolveLookupCacheProgress,
  resolveJobMetadataEntries,
  resolveMediaStageProgress,
  resolvePlayableStageProgress,
  resolveTranslationStageProgress,
  sortTuningEntries,
} from './job-progress/jobProgressUtils';
import { useJobProgressMetadataLookup } from './job-progress/useJobProgressMetadataLookup';

type Props = {
  jobId: string;
  status: PipelineStatusResponse | undefined;
  latestEvent: ProgressEventPayload | undefined;
  latestTranslationEvent?: ProgressEventPayload;
  latestMediaEvent?: ProgressEventPayload;
  /** Event emitted when a batch is fully exported and playable */
  latestPlayableEvent?: ProgressEventPayload;
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

export function JobProgress({
  jobId,
  status,
  latestEvent,
  latestTranslationEvent,
  latestMediaEvent,
  latestPlayableEvent,
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
  const isVideoDubJob = jobType === 'youtube_dub';
  const supportsTvMetadata = isSubtitleJob || isVideoDubJob;
  const supportsYoutubeMetadata = isVideoDubJob;
  const isNarratedSubtitleJob = useMemo(() => isNarratedSubtitleJobStatus(status), [status]);
  const isLibraryMovableJob = isPipelineLikeJob || isVideoDubJob || isNarratedSubtitleJob;
  const isTerminal = useMemo(() => {
    if (!status) {
      return false;
    }
    return TERMINAL_STATES.includes(status.status);
  }, [status]);

  useJobEventsWithRetry({
    jobId,
    enabled: !isTerminal,
    onEvent,
    onError: (error) => {
      console.error('SSE connection error for job', jobId, error);
    },
    maxRetries: 5,
    retryDelayMs: 2000,
  });

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
  const statusEvent = status?.latest_event ?? undefined;
  const event = latestEvent ?? statusEvent ?? undefined;
  const eventStage = resolveProgressStage(event);
  const statusStage = resolveProgressStage(statusEvent);
  const translationEvent =
    latestTranslationEvent ??
    (eventStage === 'translation' ? event : undefined) ??
    (statusStage === 'translation' ? statusEvent : undefined);
  const mediaEvent =
    latestMediaEvent ??
    (eventStage === 'media' ? event : undefined) ??
    (statusStage === 'media' ? statusEvent : undefined);
  const subtitleMediaMetadata =
    subtitleResult && typeof (subtitleResult.media_metadata ?? subtitleResult.book_metadata) === 'object'
      ? ((subtitleResult.media_metadata ?? subtitleResult.book_metadata) as Record<string, unknown>)
      : null;
  const rawMetadata = isPipelineLikeJob ? pipelineResult?.book_metadata ?? null : subtitleMediaMetadata;
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
  const { displayEntries: metadataEntries, technicalEntries: technicalMetadataEntries } = useMemo(
    () => resolveJobMetadataEntries(metadata),
    [metadata]
  );
  const creationSummary = useMemo(
    () => parseJobProgressCreationSummary(metadata['creation_summary']),
    [metadata]
  );
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
  const translationProviderRaw =
    status?.parameters?.translation_provider ?? metadata['translation_provider'] ?? null;
  const translationProvider = normalizeTranslationProvider(translationProviderRaw) ?? 'llm';
  const configuredBatchSize = coerceNumber(status?.parameters?.translation_batch_size);
  const parallelismEntries = useMemo(() => {
    return buildParallelismEntries({
      tuning: status?.tuning ?? null,
      pipelineConfig,
      parameters: status?.parameters,
      metadata,
      translationProvider,
      configuredBatchSize,
    });
  }, [
    configuredBatchSize,
    metadata,
    pipelineConfig,
    status?.parameters,
    status?.tuning,
    translationProvider
  ]);
  const fallbackEntries = useMemo(() => {
    return buildFallbackEntries(status?.generated_files);
  }, [status?.generated_files]);
  const translations = pipelineResult?.written_blocks ?? [];
  const translationsUnavailable = areTranslationsUnavailable(translations);

  const translationBatchStats = useMemo(() => {
    return resolveGeneratedFileRecord(status?.generated_files, 'translation_batch_stats');
  }, [status?.generated_files]);
  const transliterationBatchStats = useMemo(() => {
    return resolveGeneratedFileRecord(status?.generated_files, 'transliteration_batch_stats');
  }, [status?.generated_files]);
  const mediaBatchStats = useMemo(() => {
    return resolveGeneratedFileRecord(status?.generated_files, 'media_batch_stats');
  }, [status?.generated_files]);
  const lookupCacheStats = useMemo(() => {
    return resolveGeneratedFileRecord(status?.generated_files, 'lookup_cache');
  }, [status?.generated_files]);
  const translationBatchSize =
    coerceNumber(translationBatchStats?.['batch_size']) ?? configuredBatchSize;
  const useBatchProgress =
    Boolean(translationBatchStats || transliterationBatchStats || mediaBatchStats) ||
    (translationBatchSize !== null && translationBatchSize > 1 && translationProvider === 'llm');
  const translationBatchProgress = useMemo(
    () => (useBatchProgress ? buildBatchProgress(translationBatchStats) : null),
    [translationBatchStats, useBatchProgress]
  );
  const transliterationBatchProgress = useMemo(
    () => (useBatchProgress ? buildBatchProgress(transliterationBatchStats) : null),
    [transliterationBatchStats, useBatchProgress]
  );
  const mediaBatchProgress = useMemo(
    () => (useBatchProgress ? buildBatchProgress(mediaBatchStats) : null),
    [mediaBatchStats, useBatchProgress]
  );
  const lookupCacheProgress = useMemo(() => {
    return resolveLookupCacheProgress(lookupCacheStats);
  }, [lookupCacheStats]);
  const translationProgress = useMemo(() => {
    return resolveTranslationStageProgress(translationEvent, useBatchProgress);
  }, [translationEvent, useBatchProgress]);
  const mediaProgress = useMemo(() => {
    return resolveMediaStageProgress(mediaEvent, useBatchProgress);
  }, [mediaEvent, useBatchProgress]);
  // Playable progress tracks fully exported sentences (ready for interactive player)
  const playableProgress = useMemo(() => {
    return resolvePlayableStageProgress({ latestPlayableEvent, mediaBatchStats });
  }, [latestPlayableEvent, mediaBatchStats]);
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
  const batchStatEntries = useMemo(() => {
    return buildBatchStatEntries(translationBatchSize, translationBatchStats);
  }, [translationBatchSize, translationBatchStats]);
  const showBatchStageProgress =
    useBatchProgress &&
    Boolean(translationBatchProgress || transliterationBatchProgress || mediaBatchProgress);
  // Show playable progress when we have playable events or batch stats
  const showPlayableProgress = Boolean(playableProgress);
  // Show lookup cache progress when cache was built
  const showLookupCacheProgress = Boolean(lookupCacheProgress);
  // Track lookup cache building status and progress from SSE events
  const lookupCacheBuildingProgress = useMemo(() => {
    return resolveLookupCacheBuildingProgress(event?.metadata);
  }, [event?.metadata]);
  const showLookupCacheBuilding = lookupCacheBuildingProgress !== null && !showLookupCacheProgress;
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
  const [jobTab, setJobTab] = useState<JobProgressTab>('overview');
  const showMetadataSections = jobTab === 'metadata';
  const showMediaMetadata = supportsTvMetadata && showMetadataSections;
  const showOverviewSections = jobTab === 'overview';
  const showPermissionsSections = jobTab === 'permissions';

  const {
    isbnLookupQuery,
    setIsbnLookupQuery,
    isLookingUp,
    lookupError,
    lookupResult,
    existingIsbn,
    handleLookupMetadata,
    handleClearMetadata
  } = useJobProgressMetadataLookup({ jobId, metadata, onReload });

  return (
    <div className="job-card" aria-live="polite">
      <JobProgressHeader
        jobId={jobId}
        jobLabel={jobLabel}
        jobType={jobType}
        statusValue={statusValue}
        statusGlyph={statusGlyph}
        canPause={canPause}
        canResume={canResume}
        canCancel={canCancel}
        canRestart={canRestart}
        canCopy={canCopy}
        shouldRenderLibraryButton={shouldRenderLibraryButton}
        canMoveToLibrary={canMoveToLibrary}
        canDelete={canDelete}
        isMutating={isMutating}
        libraryButtonTitle={libraryButtonTitle}
        onPause={onPause}
        onResume={onResume}
        onCancel={onCancel}
        onRestart={onRestart}
        onDelete={onDelete}
        onCopy={onCopy}
        onMoveToLibrary={onMoveToLibrary}
      />
      <JobProgressTimingSummary
        createdAt={status?.created_at}
        startedAt={status?.started_at}
        completedAt={status?.completed_at}
        mediaCompleted={mediaCompleted}
      />
      <JobProgressTabs activeTab={jobTab} onChange={setJobTab} />
      {showMetadataSections ? (
        <JobProgressMediaMetadata
          jobId={jobId}
          supportsTvMetadata={supportsTvMetadata}
          supportsYoutubeMetadata={supportsYoutubeMetadata}
          showMetadata={showMediaMetadata}
          canManage={canManage}
          onReload={onReload}
        />
      ) : null}
      {showOverviewSections ? (
        <JobProgressOverviewSection
          jobParameterEntries={jobParameterEntries}
          isBookJob={isBookJob}
          imageClusterNodes={imageClusterNodes}
          statusError={status?.error}
          showLibraryReadyNotice={showLibraryReadyNotice}
          statusValue={statusValue}
          mediaCompleted={mediaCompleted}
          batchStatEntries={batchStatEntries}
          parallelismEntries={parallelismEntries}
          tuningEntries={tuningEntries}
          fallbackEntries={fallbackEntries}
        />
      ) : null}
      {showPermissionsSections ? (
        <JobProgressPermissionsSection
          policy={accessPolicy}
          ownerId={ownerId}
          defaultVisibility={accessDefaultVisibility}
          canEdit={canManage}
          onSave={onUpdateAccess}
        />
      ) : null}
      {showOverviewSections ? (
        <JobProgressStageSection
          playableProgress={playableProgress}
          lookupCacheBuildingProgress={lookupCacheBuildingProgress}
          lookupCacheProgress={lookupCacheProgress}
          translationBatchProgress={translationBatchProgress}
          transliterationBatchProgress={transliterationBatchProgress}
          mediaBatchProgress={mediaBatchProgress}
          translationProgress={translationProgress}
          mediaProgress={mediaProgress}
          showBatchStageProgress={showBatchStageProgress}
          showLookupCacheBuilding={showLookupCacheBuilding}
          showLookupCacheProgress={showLookupCacheProgress}
          showPlayableProgress={showPlayableProgress}
        />
      ) : null}
      {showOverviewSections && translationsUnavailable ? (
        <div className="alert" role="status">
          Translated content was not returned by the LLM. Verify your model configuration and try reloading once the
          metadata has been refreshed.
        </div>
      ) : null}
      {showOverviewSections ? (
        <JobProgressLatestSection
          event={event}
          latestPlayableEvent={latestPlayableEvent}
          playableProgress={playableProgress}
        />
      ) : null}
      {showMetadataSections && creationSummary ? (
        <JobProgressCreationSummary summary={creationSummary} />
      ) : null}
      {showMetadataSections && !isVideoDubJob ? (
        <JobProgressMetadataSection
          isSubtitleJob={isSubtitleJob}
          isBookJob={isBookJob}
          shouldShowCoverPreview={shouldShowCoverPreview}
          coverUrl={coverUrl}
          coverFailed={coverFailed}
          coverAltText={coverAltText}
          openlibraryLink={openlibraryLink}
          metadataEntries={metadataEntries}
          technicalMetadataEntries={technicalMetadataEntries}
          isbnLookupQuery={isbnLookupQuery}
          existingIsbn={existingIsbn}
          isLookingUp={isLookingUp}
          lookupError={lookupError}
          lookupResult={lookupResult}
          canManage={canManage}
          isReloading={isReloading}
          isMutating={isMutating}
          onCoverError={() => setCoverFailed(true)}
          onIsbnLookupQueryChange={setIsbnLookupQuery}
          onLookupMetadata={(force) => void handleLookupMetadata(force)}
          onClearMetadata={() => void handleClearMetadata()}
          onReload={onReload}
        />
      ) : null}
    </div>
  );
}

export default JobProgress;
