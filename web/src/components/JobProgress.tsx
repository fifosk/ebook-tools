import { useCallback, useEffect, useMemo, useState } from 'react';
import { useJobEventsWithRetry } from '../hooks/useJobEventsWithRetry';
import { appendAccessToken, clearBookMetadataCache, lookupBookOpenLibraryMetadata, resolveJobCoverUrl } from '../api/client';
import {
  AccessPolicyUpdatePayload,
  PipelineResponsePayload,
  PipelineStatusResponse,
  ProgressEventPayload
} from '../api/dtos';
import { resolveMediaCompletion } from '../utils/mediaFormatters';
import { getStatusGlyph } from '../utils/status';
import { resolveImageNodeLabel } from '../constants/imageNodes';
import { isLocalLlmProvider, splitLlmModelId } from '../utils/llmProviders';
import AccessPolicyEditor from './access/AccessPolicyEditor';
import { JobProgressMediaMetadata } from './job-progress/JobProgressMediaMetadata';
import { resolveProgressStage } from '../utils/progressEvents';
import { buildJobParameterEntries } from './job-progress/jobProgressParameters';
import { MetadataLookupRow } from './metadata/MetadataLookupRow';
import {
  BOOK_METADATA_DISPLAY_KEYS,
  CREATION_METADATA_KEYS,
  TECHNICAL_METADATA_KEYS,
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
  normalizeIsbnCandidate,
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

type JobTab = 'overview' | 'metadata' | 'permissions';
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
  // Split metadata into display (interesting) and technical entries
  const allMetadataEntries = Object.entries(metadata).filter(([key, value]) => {
    if (key === 'job_cover_asset' || key === 'book_metadata_lookup' || CREATION_METADATA_KEYS.has(key)) {
      return false;
    }
    if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
      return false;
    }
    const normalized = normalizeMetadataValue(value);
    return normalized.length > 0;
  });
  // Display entries: show prominently (book metadata fields)
  const metadataEntries = allMetadataEntries.filter(([key]) => BOOK_METADATA_DISPLAY_KEYS.has(key));
  // Technical entries: show in collapsed "Raw payload" section
  const technicalMetadataEntries = allMetadataEntries.filter(([key]) => !BOOK_METADATA_DISPLAY_KEYS.has(key));
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
  const translationProviderRaw =
    status?.parameters?.translation_provider ?? metadata['translation_provider'] ?? null;
  const translationProvider = normalizeTranslationProvider(translationProviderRaw) ?? 'llm';
  const configuredBatchSize = coerceNumber(status?.parameters?.translation_batch_size);
  const parallelismEntries = useMemo(() => {
    const entries: Array<{ label: string; value: string; hint?: string }> = [];
    const tuning = status?.tuning ?? null;
    const tuningRecord = coerceRecord(tuning);
    const threadCount =
      coerceNumber(tuningRecord?.thread_count) ?? coerceNumber(pipelineConfig?.thread_count);
    const translationPool =
      coerceNumber(tuningRecord?.translation_pool_workers) ?? threadCount;
    const translationModel = normalizeTextValue(metadata['translation_model']);
    const llmModel =
      normalizeTextValue(status?.parameters?.llm_model) ??
      normalizeTextValue(pipelineConfig?.ollama_model);
    const modelName = translationModel ?? llmModel;
    const modelInfo = splitLlmModelId(modelName);
    const modelProvider = modelInfo.provider;
    const modelBase = modelInfo.model ?? modelName;
    const providerLocalFlag = isLocalLlmProvider(modelProvider);
    const modelIsCloud =
      providerLocalFlag === false
        ? true
        : providerLocalFlag === true
          ? false
          : modelBase
            ? modelBase.toLowerCase().includes('cloud')
            : false;
    const providerLabel =
      formatTranslationProviderLabel(
        translationProvider,
        translationModel,
        llmModel
      ) ?? 'Text translation';
    const batchSize = configuredBatchSize;
    if (translationPool !== null) {
      const hintParts = ['Controlled by Worker threads'];
      if (translationProvider === 'llm' && modelName) {
        hintParts.push(`Model: ${modelName}`);
        if (modelProvider) {
          hintParts.push(`Provider: ${modelProvider}`);
        }
      }
      if (batchSize !== null && batchSize > 1) {
        hintParts.push(`Batch size: ${batchSize} sentences/request`);
        if (translationProvider === 'llm') {
          if (modelName) {
            hintParts.push(
              modelIsCloud
                ? "Model is cloud-backed (no local cap)"
                : "Model is local (batch calls capped to 1)"
            );
          } else {
            hintParts.push('Model not reported (local cap may apply)');
          }
        }
      }
      entries.push({
        label: `${providerLabel} parallel calls`,
        value: formatTuningValue(translationPool),
        hint: hintParts.join('. ')
      });
      if (translationProvider === 'llm' && batchSize !== null && batchSize > 1) {
        let capValue = 'Unknown';
        let capHint = 'Model not reported; unable to determine cap.';
        if (modelName) {
          capValue = modelIsCloud ? 'No' : 'Yes';
          capHint = modelIsCloud
            ? 'Cloud-backed model; batching is not capped.'
            : 'Local model; batching is capped to 1 parallel LLM call.';
        }
        entries.push({
          label: 'LLM batch cap applies',
          value: capValue,
          hint: capHint
        });
      }
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
    configuredBatchSize,
    metadata,
    pipelineConfig?.generate_audio,
    pipelineConfig?.ollama_model,
    pipelineConfig?.selected_voice,
    pipelineConfig?.thread_count,
    status?.parameters?.llm_model,
    status?.parameters?.selected_voice,
    status?.tuning,
    translationProvider
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

  const translationBatchStats = useMemo(() => {
    const generated = status?.generated_files;
    if (!generated || typeof generated !== 'object') {
      return null;
    }
    return coerceRecord((generated as Record<string, unknown>)['translation_batch_stats']);
  }, [status?.generated_files]);
  const transliterationBatchStats = useMemo(() => {
    const generated = status?.generated_files;
    if (!generated || typeof generated !== 'object') {
      return null;
    }
    return coerceRecord((generated as Record<string, unknown>)['transliteration_batch_stats']);
  }, [status?.generated_files]);
  const mediaBatchStats = useMemo(() => {
    const generated = status?.generated_files;
    if (!generated || typeof generated !== 'object') {
      return null;
    }
    return coerceRecord((generated as Record<string, unknown>)['media_batch_stats']);
  }, [status?.generated_files]);
  const lookupCacheStats = useMemo(() => {
    const generated = status?.generated_files;
    if (!generated || typeof generated !== 'object') {
      return null;
    }
    return coerceRecord((generated as Record<string, unknown>)['lookup_cache']);
  }, [status?.generated_files]);
  const translationBatchSize =
    coerceNumber(translationBatchStats?.['batch_size']) ?? configuredBatchSize;
  const useBatchProgress =
    Boolean(translationBatchStats || transliterationBatchStats || mediaBatchStats) ||
    (translationBatchSize !== null && translationBatchSize > 1 && translationProvider === 'llm');
  const buildBatchProgress = useCallback((stats: Record<string, unknown> | null) => {
    if (!stats) {
      return null;
    }
    const completed = coerceNumber(stats['batches_completed']);
    if (completed === null) {
      return null;
    }
    const total = coerceNumber(stats['batches_total']);
    return { completed, total };
  }, []);
  const translationBatchProgress = useMemo(
    () => (useBatchProgress ? buildBatchProgress(translationBatchStats) : null),
    [buildBatchProgress, translationBatchStats, useBatchProgress]
  );
  const transliterationBatchProgress = useMemo(
    () => (useBatchProgress ? buildBatchProgress(transliterationBatchStats) : null),
    [buildBatchProgress, transliterationBatchStats, useBatchProgress]
  );
  const mediaBatchProgress = useMemo(
    () => (useBatchProgress ? buildBatchProgress(mediaBatchStats) : null),
    [buildBatchProgress, mediaBatchStats, useBatchProgress]
  );
  const lookupCacheProgress = useMemo(() => {
    if (!lookupCacheStats) {
      return null;
    }
    const wordCount = coerceNumber(lookupCacheStats['word_count']);
    const llmCalls = coerceNumber(lookupCacheStats['llm_calls']);
    const skippedStopwords = coerceNumber(lookupCacheStats['skipped_stopwords']);
    const buildTimeSeconds = coerceNumber(lookupCacheStats['build_time_seconds']);
    if (wordCount === null) {
      return null;
    }
    return { wordCount, llmCalls, skippedStopwords, buildTimeSeconds };
  }, [lookupCacheStats]);
  const translationProgress = useMemo(() => {
    if (useBatchProgress || !translationEvent) {
      return null;
    }
    const meta = translationEvent.metadata;
    const metaRecord = meta && typeof meta === 'object' ? (meta as Record<string, unknown>) : null;
    const completed =
      coerceNumber(metaRecord?.translation_completed) ?? translationEvent.snapshot.completed;
    const total = coerceNumber(metaRecord?.translation_total) ?? translationEvent.snapshot.total;
    return { completed, total };
  }, [translationEvent, useBatchProgress]);
  const mediaProgress = useMemo(() => {
    if (useBatchProgress || !mediaEvent) {
      return null;
    }
    const { completed, total } = mediaEvent.snapshot;
    return { completed, total };
  }, [mediaEvent, useBatchProgress]);
  // Playable progress tracks fully exported sentences (ready for interactive player)
  const playableProgress = useMemo(() => {
    // First priority: use latestPlayableEvent snapshot
    if (latestPlayableEvent?.snapshot) {
      const { completed, total } = latestPlayableEvent.snapshot;
      if (
        typeof completed === 'number' &&
        typeof total === 'number' &&
        Number.isFinite(completed) &&
        Number.isFinite(total)
      ) {
        return { completed, total };
      }
    }
    // Fallback: use media_batch_stats.items_completed from generated_files
    if (mediaBatchStats) {
      const itemsCompleted = coerceNumber(mediaBatchStats['items_completed']);
      const itemsTotal = coerceNumber(mediaBatchStats['items_total']);
      if (itemsCompleted !== null && itemsTotal !== null) {
        return { completed: itemsCompleted, total: itemsTotal };
      }
    }
    return null;
  }, [latestPlayableEvent, mediaBatchStats]);
  const formatProgressValue = useCallback((progress: { completed: number; total: number | null }) => {
    const completedLabel =
      typeof progress.completed === 'number' && Number.isFinite(progress.completed)
        ? Math.max(0, Math.round(progress.completed)).toString()
        : '0';
    if (typeof progress.total === 'number' && Number.isFinite(progress.total)) {
      return `${completedLabel} / ${Math.max(0, Math.round(progress.total))}`;
    }
    return completedLabel;
  }, []);

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
    const entries: [string, string][] = [];
    const resolvedBatchSize = translationBatchSize;
    if (resolvedBatchSize !== null && resolvedBatchSize > 1) {
      entries.push(['Batch size', resolvedBatchSize.toString()]);
    }
    if (!translationBatchStats) {
      if (resolvedBatchSize !== null && resolvedBatchSize > 1) {
        entries.push(['Batches completed', '0']);
        entries.push(['Items translated', '0']);
      }
      return entries;
    }
    const batches = coerceNumber(translationBatchStats['batches_completed']);
    if (batches !== null) {
      entries.push(['Batches completed', batches.toString()]);
    }
    const items = coerceNumber(translationBatchStats['items_completed']);
    if (items !== null) {
      entries.push(['Items translated', items.toString()]);
    }
    const avgBatch = coerceNumber(translationBatchStats['avg_batch_seconds']);
    if (avgBatch !== null) {
      entries.push(['Avg batch time', formatSeconds(avgBatch, 's/batch')]);
    }
    const avgItem = coerceNumber(translationBatchStats['avg_item_seconds']);
    if (avgItem !== null) {
      entries.push(['Avg item time', formatSeconds(avgItem, 's/item')]);
    }
    const lastBatch = coerceNumber(translationBatchStats['last_batch_seconds']);
    const lastItems = coerceNumber(translationBatchStats['last_batch_items']);
    if (lastBatch !== null) {
      const suffix =
        lastItems !== null ? ` (${lastItems} sentence${lastItems === 1 ? '' : 's'})` : '';
      entries.push(['Last batch time', `${formatSeconds(lastBatch, 's/batch')}${suffix}`]);
    }
    return entries;
  }, [translationBatchSize, translationBatchStats]);
  const showBatchStageProgress =
    useBatchProgress &&
    Boolean(translationBatchProgress || transliterationBatchProgress || mediaBatchProgress);
  const showSentenceStageProgress =
    !useBatchProgress && Boolean(translationProgress || mediaProgress);
  // Show playable progress when we have playable events or batch stats
  const showPlayableProgress = Boolean(playableProgress);
  // Show lookup cache progress when cache was built
  const showLookupCacheProgress = Boolean(lookupCacheProgress);
  // Track lookup cache building status and progress from SSE events
  const lookupCacheBuildingProgress = useMemo(() => {
    const meta = event?.metadata;
    if (!meta || typeof meta !== 'object') {
      return null;
    }
    const metaRecord = meta as Record<string, unknown>;
    const status = metaRecord['lookup_cache_status'];
    // Extract detailed progress if available
    const progress = coerceRecord(metaRecord['lookup_cache_progress']);
    if (progress) {
      return {
        status: 'building' as const,
        batchesCompleted: coerceNumber(progress['batches_completed']),
        batchesTotal: coerceNumber(progress['batches_total']),
        wordsToLookup: coerceNumber(progress['words_to_lookup']),
        cachedEntries: coerceNumber(progress['cached_entries']),
        llmCalls: coerceNumber(progress['llm_calls']),
      };
    }
    // Only show building indicator if status is explicitly "building"
    if (status === 'building') {
      return {
        status: 'building' as const,
        batchesCompleted: null,
        batchesTotal: null,
        wordsToLookup: null,
        cachedEntries: null,
        llmCalls: null,
      };
    }
    return null;
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
  const [jobTab, setJobTab] = useState<JobTab>('overview');
  const showMetadataSections = jobTab === 'metadata';
  const showMediaMetadata = supportsTvMetadata && showMetadataSections;
  const showOverviewSections = jobTab === 'overview';
  const showPermissionsSections = jobTab === 'permissions';

  // Metadata lookup state (unified - replaces separate enrichment and lookup states)
  const [isbnLookupQuery, setIsbnLookupQuery] = useState('');
  const [isLookingUp, setIsLookingUp] = useState(false);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [lookupResult, setLookupResult] = useState<{
    success: boolean;
    source?: string | null;
    confidence?: string | null;
  } | null>(null);

  // Extract ISBN from existing metadata for auto-populating lookup
  const existingIsbn = useMemo(() => {
    return normalizeTextValue(metadata['book_isbn']) ?? normalizeTextValue(metadata['isbn']) ?? null;
  }, [metadata]);

  // Resolve final lookup query (ISBN input or existing ISBN from metadata)
  const resolvedLookupQuery = useMemo(() => {
    const inputIsbn = normalizeIsbnCandidate(isbnLookupQuery);
    if (inputIsbn) {
      return inputIsbn;
    }
    const metadataIsbn = normalizeIsbnCandidate(existingIsbn);
    if (metadataIsbn) {
      return metadataIsbn;
    }
    return isbnLookupQuery.trim();
  }, [isbnLookupQuery, existingIsbn]);

  const handleLookupMetadata = useCallback(async (force: boolean) => {
    setIsLookingUp(true);
    setLookupError(null);
    setLookupResult(null);
    try {
      const result = await lookupBookOpenLibraryMetadata(jobId, { force });
      const bookMetadata = result.book_metadata_lookup;
      const lookupBook = bookMetadata && typeof bookMetadata === 'object'
        ? (bookMetadata as Record<string, unknown>)['book']
        : null;
      const hasTitle = lookupBook && typeof lookupBook === 'object'
        ? Boolean((lookupBook as Record<string, unknown>)['title'])
        : false;
      const lookupErr = bookMetadata && typeof bookMetadata === 'object'
        ? (bookMetadata as Record<string, unknown>)['error']
        : null;
      // Extract source and confidence from response
      const provider = bookMetadata && typeof bookMetadata === 'object'
        ? (bookMetadata as Record<string, unknown>)['provider']
        : null;
      const confidence = bookMetadata && typeof bookMetadata === 'object'
        ? (bookMetadata as Record<string, unknown>)['confidence']
        : null;

      if (lookupErr && typeof lookupErr === 'string') {
        setLookupError(lookupErr);
        setLookupResult({ success: false });
      } else if (hasTitle) {
        setLookupResult({
          success: true,
          source: typeof provider === 'string' ? provider : null,
          confidence: typeof confidence === 'string' ? confidence : null,
        });
        onReload();
      } else {
        setLookupError('No book metadata found.');
        setLookupResult({ success: false });
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to lookup metadata';
      setLookupError(message);
      setLookupResult(null);
    } finally {
      setIsLookingUp(false);
    }
  }, [jobId, onReload]);

  const handleClearMetadata = useCallback(async () => {
    // Clear frontend lookup state
    setLookupResult(null);
    setLookupError(null);
    setIsbnLookupQuery('');

    // Clear backend cache for a fresh lookup
    const query = resolvedLookupQuery.trim();
    if (query) {
      try {
        await clearBookMetadataCache(query);
      } catch {
        // Ignore cache clear failures - frontend state is already cleared
      }
    }

    // Reload the job to refresh the display
    onReload();
  }, [resolvedLookupQuery, onReload]);

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
      <div className="job-card__tabs" role="tablist" aria-label="Job tabs">
        <button
          type="button"
          role="tab"
          aria-selected={jobTab === 'overview'}
          className={`job-card__tab ${jobTab === 'overview' ? 'is-active' : ''}`}
          onClick={() => setJobTab('overview')}
        >
          Overview
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={jobTab === 'metadata'}
          className={`job-card__tab ${jobTab === 'metadata' ? 'is-active' : ''}`}
          onClick={() => setJobTab('metadata')}
        >
          Metadata
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={jobTab === 'permissions'}
          className={`job-card__tab ${jobTab === 'permissions' ? 'is-active' : ''}`}
          onClick={() => setJobTab('permissions')}
        >
          Permissions
        </button>
      </div>
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
      {showOverviewSections && parallelismEntries.length > 0 ? (
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
      {showOverviewSections && !isBookJob && tuningEntries.length > 0 ? (
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
      {showOverviewSections && (showPlayableProgress || showBatchStageProgress || showSentenceStageProgress || showLookupCacheProgress || showLookupCacheBuilding) ? (
        <div>
          <h4>Stage progress</h4>
          <div className="progress-grid">
            {showPlayableProgress && playableProgress ? (
              <div className="progress-metric">
                <strong>Playable sentences</strong>
                <span>{formatProgressValue(playableProgress)}</span>
                <p className="progress-metric__hint">Sentences fully processed and ready for playback.</p>
              </div>
            ) : null}
            {showLookupCacheBuilding && lookupCacheBuildingProgress ? (
              <div className="progress-metric">
                <strong>Dictionary cache</strong>
                <span className="progress-metric__status progress-metric__status--building">
                  {lookupCacheBuildingProgress.cachedEntries !== null
                    ? `${lookupCacheBuildingProgress.cachedEntries} word${lookupCacheBuildingProgress.cachedEntries === 1 ? '' : 's'}`
                    : 'Building…'}
                </span>
                <p className="progress-metric__hint">
                  {lookupCacheBuildingProgress.batchesCompleted !== null && lookupCacheBuildingProgress.batchesTotal !== null
                    ? `Batch ${lookupCacheBuildingProgress.batchesCompleted} / ${lookupCacheBuildingProgress.batchesTotal}`
                    : 'Processing words'}
                  {lookupCacheBuildingProgress.wordsToLookup !== null
                    ? ` (${lookupCacheBuildingProgress.wordsToLookup} unique words)`
                    : ''}
                  . Playback is available.
                </p>
              </div>
            ) : null}
            {showLookupCacheProgress && lookupCacheProgress ? (
              <div className="progress-metric">
                <strong>Dictionary cache</strong>
                <span>
                  {lookupCacheProgress.wordCount} word{lookupCacheProgress.wordCount === 1 ? '' : 's'}
                  {lookupCacheProgress.skippedStopwords !== null
                    ? ` (${lookupCacheProgress.skippedStopwords} stopwords skipped)`
                    : ''}
                </span>
                <p className="progress-metric__hint">
                  Unique words cached for instant lookups.
                  {lookupCacheProgress.llmCalls !== null
                    ? ` ${lookupCacheProgress.llmCalls} LLM call${lookupCacheProgress.llmCalls === 1 ? '' : 's'}.`
                    : ''}
                  {lookupCacheProgress.buildTimeSeconds !== null
                    ? ` Built in ${formatSeconds(lookupCacheProgress.buildTimeSeconds, 's')}.`
                    : ''}
                </p>
              </div>
            ) : null}
            {showBatchStageProgress ? (
              <>
                {translationBatchProgress ? (
                  <div className="progress-metric">
                    <strong>Translation batches</strong>
                    <span>{formatProgressValue(translationBatchProgress)}</span>
                    <p className="progress-metric__hint">Counts completed translation batches.</p>
                  </div>
                ) : null}
                {transliterationBatchProgress ? (
                  <div className="progress-metric">
                    <strong>Transliteration batches</strong>
                    <span>{formatProgressValue(transliterationBatchProgress)}</span>
                    <p className="progress-metric__hint">Counts completed transliteration batches.</p>
                  </div>
                ) : null}
                {mediaBatchProgress ? (
                  <div className="progress-metric">
                    <strong>Media batches</strong>
                    <span>{formatProgressValue(mediaBatchProgress)}</span>
                    <p className="progress-metric__hint">Counts batches with finished media output.</p>
                  </div>
                ) : null}
              </>
            ) : null}
            {!showBatchStageProgress && translationProgress ? (
              <div className="progress-metric">
                <strong>Translation progress</strong>
                <span>{formatProgressValue(translationProgress)}</span>
                <p className="progress-metric__hint">Counts translated sentences (LLM/googletrans).</p>
              </div>
            ) : null}
            {!showBatchStageProgress && mediaProgress ? (
              <div className="progress-metric">
                <strong>Media progress</strong>
                <span>{formatProgressValue(mediaProgress)}</span>
                <p className="progress-metric__hint">Counts sentences with generated media output.</p>
              </div>
            ) : null}
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
                {playableProgress
                  ? `${playableProgress.completed}${playableProgress.total !== null ? ` / ${playableProgress.total}` : ''}`
                  : `${event.snapshot.completed}${event.snapshot.total !== null ? ` / ${event.snapshot.total}` : ''}`}
              </span>
            </div>
            <div className="progress-metric">
              <strong>Speed</strong>
              <span>
                {latestPlayableEvent?.snapshot
                  ? `${latestPlayableEvent.snapshot.speed.toFixed(2)} items/s`
                  : `${event.snapshot.speed.toFixed(2)} items/s`}
              </span>
            </div>
            <div className="progress-metric">
              <strong>Elapsed</strong>
              <span>{event.snapshot.elapsed.toFixed(2)} s</span>
            </div>
            <div className="progress-metric">
              <strong>ETA</strong>
              <span>
                {latestPlayableEvent?.snapshot?.eta !== null && latestPlayableEvent?.snapshot?.eta !== undefined
                  ? `${latestPlayableEvent.snapshot.eta.toFixed(2)} s`
                  : event.snapshot.eta !== null
                    ? `${event.snapshot.eta.toFixed(2)} s`
                    : '—'}
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
      {!showMetadataSections || isVideoDubJob ? null : (
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
          {isBookJob ? (
            <MetadataLookupRow
              query={isbnLookupQuery}
              onQueryChange={setIsbnLookupQuery}
              onLookup={(force) => void handleLookupMetadata(force)}
              onClear={() => void handleClearMetadata()}
              isLoading={isLookingUp}
              placeholder={existingIsbn ? existingIsbn : 'Title, author, or ISBN'}
              inputLabel="Lookup query"
              hasResult={!!lookupResult}
              disabled={!canManage || isReloading || isMutating}
            />
          ) : null}
          {lookupError ? (
            <div className="notice notice--warning" role="alert" style={{ marginBottom: '0.75rem' }}>
              {lookupError}
            </div>
          ) : null}
          {lookupResult?.success ? (
            <div className="notice notice--success" role="status" style={{ marginBottom: '0.75rem' }}>
              {`Metadata found from ${lookupResult.source ?? 'external source'}${lookupResult.confidence ? ` (confidence: ${lookupResult.confidence})` : ''}`}
            </div>
          ) : null}
          {technicalMetadataEntries.length > 0 ? (
            <details className="job-card__details">
              <summary>Technical parameters</summary>
              <dl className="metadata-grid">
                {technicalMetadataEntries.map(([key, value]) => {
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
            </details>
          ) : null}
          <div className="job-card__tab-actions">
            <button
              type="button"
              className="link-button"
              onClick={onReload}
              disabled={!canManage || isReloading || isMutating || isLookingUp}
              aria-busy={isReloading || isMutating}
              data-variant="metadata-action"
            >
              {isReloading ? 'Reloading…' : 'Reload job'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default JobProgress;
