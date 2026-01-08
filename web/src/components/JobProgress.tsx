import { useEffect, useMemo, useState } from 'react';
import { usePipelineEvents } from '../hooks/usePipelineEvents';
import { formatLanguageWithFlag } from '../utils/languages';
import {
  appendAccessToken,
  fetchSubtitleTvMetadata,
  lookupSubtitleTvMetadata,
  fetchYoutubeVideoMetadata,
  lookupYoutubeVideoMetadata,
  resolveJobCoverUrl
} from '../api/client';
import {
  PipelineJobStatus,
  PipelineResponsePayload,
  PipelineStatusResponse,
  ProgressEventPayload,
  SubtitleTvMetadataResponse,
  YoutubeVideoMetadataResponse
} from '../api/dtos';
import { resolveMediaCompletion } from '../utils/mediaFormatters';
import { getStatusGlyph } from '../utils/status';
import { formatModelLabel } from '../utils/modelInfo';
import { IMAGE_API_NODE_OPTIONS, resolveImageNodeLabel } from '../constants/imageNodes';

const TERMINAL_STATES: PipelineJobStatus[] = ['completed', 'failed', 'cancelled'];
const GOOGLE_TRANSLATION_PROVIDER_ALIASES = new Set([
  'google',
  'googletrans',
  'googletranslate',
  'google-translate',
  'gtranslate',
  'gtrans'
]);
const TRANSLITERATION_PYTHON_ALIASES = new Set(['python', 'python-module', 'module', 'local-module']);
const TRANSLITERATION_DEFAULT_ALIASES = new Set(['default', 'llm', 'ollama']);
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
  isReloading?: boolean;
  isMutating?: boolean;
  canManage: boolean;
};

type SubtitleJobTab = 'overview' | 'metadata';

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
  pipeline_mode: 'Book mode enabled',
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

function normalizeTranslationProvider(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const normalized = value.trim().toLowerCase();
  if (!normalized) {
    return null;
  }
  if (GOOGLE_TRANSLATION_PROVIDER_ALIASES.has(normalized)) {
    return 'googletrans';
  }
  if (normalized === 'llm' || normalized === 'ollama' || normalized === 'default') {
    return 'llm';
  }
  return normalized;
}

function normalizeTransliterationMode(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const normalized = value.trim().toLowerCase().replace('_', '-');
  if (!normalized) {
    return null;
  }
  if (TRANSLITERATION_PYTHON_ALIASES.has(normalized)) {
    return 'python';
  }
  if (TRANSLITERATION_DEFAULT_ALIASES.has(normalized)) {
    return 'default';
  }
  if (normalized.startsWith('local-gemma3') || normalized === 'gemma3-12b') {
    return 'default';
  }
  return normalized;
}

function formatTranslationProviderLabel(
  provider: string | null,
  translationModel: string | null,
  llmModel: string | null
): string | null {
  if (!provider) {
    return null;
  }
  if (provider === 'googletrans') {
    return 'Google Translate (googletrans)';
  }
  if (provider === 'llm') {
    const modelLabel = formatModelLabel(translationModel ?? llmModel);
    return modelLabel ? `LLM (${modelLabel})` : 'LLM';
  }
  return provider;
}

function formatTransliterationModeLabel(mode: string | null): string | null {
  if (!mode) {
    return null;
  }
  if (mode === 'python') {
    return 'Python module';
  }
  if (mode === 'default') {
    return 'LLM';
  }
  return mode;
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

function formatFallbackValue(value: Record<string, unknown>): string {
  const parts: string[] = [];
  const scope = normalizeTextValue(value['scope'] ?? null);
  if (scope && scope !== 'translation') {
    parts.push(`scope ${scope}`);
  }
  const model = normalizeTextValue(value['fallback_model'] ?? null);
  if (model) {
    parts.push(`model ${model}`);
  }
  const voice = normalizeTextValue(value['fallback_voice'] ?? null);
  if (voice) {
    parts.push(`voice ${voice}`);
  }
  const sourceProvider = normalizeTextValue(value['source_provider'] ?? null);
  if (sourceProvider) {
    parts.push(`source ${sourceProvider}`);
  }
  const sourceVoice = normalizeTextValue(value['source_voice'] ?? null);
  if (sourceVoice) {
    parts.push(`source ${sourceVoice}`);
  }
  const trigger = normalizeTextValue(value['trigger'] ?? null);
  if (trigger) {
    parts.push(`trigger ${trigger}`);
  }
  const elapsed = value['elapsed_seconds'];
  if (typeof elapsed === 'number' && Number.isFinite(elapsed)) {
    parts.push(`elapsed ${elapsed.toFixed(1)} s`);
  }
  const reason = normalizeTextValue(value['reason'] ?? null);
  if (reason) {
    parts.push(reason);
  }
  return parts.join(' | ');
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

function coerceRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : null;
}

function normalizeTextValue(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function formatEpisodeCode(season: number | null, episode: number | null): string | null {
  if (!season || !episode) {
    return null;
  }
  if (!Number.isInteger(season) || !Number.isInteger(episode) || season <= 0 || episode <= 0) {
    return null;
  }
  return `S${season.toString().padStart(2, '0')}E${episode.toString().padStart(2, '0')}`;
}

type JobParameterEntry = {
  key: string;
  label: string;
  value: React.ReactNode;
};

function formatRetryCounts(counts?: Record<string, number> | null): string | null {
  if (!counts) {
    return null;
  }
  const parts = Object.entries(counts)
    .filter(([, count]) => typeof count === 'number' && count > 0)
    .sort((a, b) => {
      const delta = (b[1] || 0) - (a[1] || 0);
      return delta !== 0 ? delta : a[0].localeCompare(b[0]);
    })
    .map(([reason, count]) => `${reason} (${count})`);
  return parts.length ? parts.join(', ') : null;
}

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
  const seenChunkIds = new Set<string>();
  if (!status) {
    return chunks;
  }
  const resultGenerated =
    status.result && typeof status.result === 'object'
      ? (status.result as Record<string, unknown>)['generated_files']
      : undefined;
  const candidates = [status.generated_files, resultGenerated];
  for (const candidate of candidates) {
    if (!candidate || typeof candidate !== 'object') {
      continue;
    }
    const records = (candidate as Record<string, unknown>).chunks;
    if (Array.isArray(records)) {
      for (const entry of records) {
        if (entry && typeof entry === 'object') {
          const record = entry as Record<string, unknown>;
          const rawChunkId = record.chunk_id ?? record.chunkId;
          const chunkId = typeof rawChunkId === 'string' ? rawChunkId.trim() : '';
          if (chunkId) {
            if (seenChunkIds.has(chunkId)) {
              continue;
            }
            seenChunkIds.add(chunkId);
          }
          chunks.push(record);
        }
      }
    }
  }
  return chunks;
}

function resolveGeneratedFiles(status: PipelineStatusResponse | undefined): Record<string, unknown>[] {
  const files: Record<string, unknown>[] = [];
  const seenKeys = new Set<string>();
  if (!status) {
    return files;
  }
  const resultGenerated =
    status.result && typeof status.result === 'object'
      ? (status.result as Record<string, unknown>)['generated_files']
      : undefined;
  const candidates = [status.generated_files, resultGenerated];
  for (const candidate of candidates) {
    if (!candidate || typeof candidate !== 'object') {
      continue;
    }
    const records = (candidate as Record<string, unknown>).files;
    if (Array.isArray(records)) {
      for (const entry of records) {
        if (entry && typeof entry === 'object') {
          const record = entry as Record<string, unknown>;
          const pathValue = typeof record.path === 'string' ? record.path.trim() : '';
          const typeValue = typeof record.type === 'string' ? record.type.trim() : '';
          const key = `${typeValue}\u0000${pathValue}`;
          if (pathValue || typeValue) {
            if (seenKeys.has(key)) {
              continue;
            }
            seenKeys.add(key);
          }
          files.push(record);
        }
      }
    }
  }
  return files;
}

function resolveImagePromptPlanSummary(status: PipelineStatusResponse | undefined): Record<string, unknown> | null {
  if (!status) {
    return null;
  }
  const resultGenerated =
    status.result && typeof status.result === 'object'
      ? (status.result as Record<string, unknown>)['generated_files']
      : undefined;
  const candidates = [status.generated_files, resultGenerated];
  for (const candidate of candidates) {
    const record = coerceRecord(candidate);
    if (!record) {
      continue;
    }
    const summary = coerceRecord(record['image_prompt_plan_summary']);
    if (summary) {
      return summary;
    }
  }
  return null;
}

type ImageClusterNodeSummary = {
  baseUrl: string;
  active: boolean;
  processed: number | null;
  avgSecondsPerImage: number | null;
};

function resolveImageClusterSummary(status: PipelineStatusResponse | undefined): Record<string, unknown> | null {
  if (!status) {
    return null;
  }
  const resultGenerated =
    status.result && typeof status.result === 'object'
      ? (status.result as Record<string, unknown>)['generated_files']
      : undefined;
  const candidates = [status.generated_files, resultGenerated];
  for (const candidate of candidates) {
    const record = coerceRecord(candidate);
    if (!record) {
      continue;
    }
    const summary = coerceRecord(record['image_cluster']);
    if (summary) {
      return summary;
    }
  }
  return null;
}

function normalizeBaseUrl(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  return trimmed.replace(/\/+$/, '');
}

function resolveImageClusterBaseUrls(config: Record<string, unknown> | null): string[] {
  if (!config) {
    return [];
  }
  const urlsRaw = config['image_api_base_urls'];
  const baseUrls: string[] = [];
  if (Array.isArray(urlsRaw)) {
    for (const entry of urlsRaw) {
      const normalized = normalizeBaseUrl(entry);
      if (normalized) {
        baseUrls.push(normalized);
      }
    }
  } else if (typeof urlsRaw === 'string') {
    const normalized = normalizeBaseUrl(urlsRaw);
    if (normalized) {
      baseUrls.push(normalized);
    }
  }

  const fallback = normalizeBaseUrl(config['image_api_base_url']);
  if (fallback) {
    baseUrls.push(fallback);
  }

  const seen = new Set<string>();
  const deduped: string[] = [];
  for (const entry of baseUrls) {
    if (seen.has(entry)) {
      continue;
    }
    seen.add(entry);
    deduped.push(entry);
  }
  return deduped;
}

function buildImageClusterNodes(
  summary: Record<string, unknown> | null,
  config: Record<string, unknown> | null,
  enabled: boolean
): ImageClusterNodeSummary[] {
  const nodes: ImageClusterNodeSummary[] = [];
  const summaryRecord = summary ? coerceRecord(summary) : null;
  const rawNodes = summaryRecord && Array.isArray(summaryRecord['nodes']) ? summaryRecord['nodes'] : [];
  const statsByUrl = new Map<string, Record<string, unknown>>();
  if (Array.isArray(rawNodes)) {
    for (const entry of rawNodes) {
      if (!entry || typeof entry !== 'object') {
        continue;
      }
      const record = entry as Record<string, unknown>;
      const url = normalizeBaseUrl(record['base_url'] ?? record['baseUrl']);
      if (!url) {
        continue;
      }
      statsByUrl.set(url, record);
    }
  }

  const configuredUrls = resolveImageClusterBaseUrls(config);
  if (!enabled && statsByUrl.size === 0) {
    return nodes;
  }
  if (statsByUrl.size === 0 && configuredUrls.length === 0) {
    return nodes;
  }

  const configuredSet = new Set(configuredUrls);
  const knownUrls = new Set<string>();
  for (const option of IMAGE_API_NODE_OPTIONS) {
    const url = normalizeBaseUrl(option.value);
    if (!url) {
      continue;
    }
    knownUrls.add(url);
    const stats = statsByUrl.get(url) ?? {};
    const activeOverride = typeof stats['active'] === 'boolean' ? (stats['active'] as boolean) : null;
    const processed = coerceNumber(stats['processed']);
    const avgSeconds = coerceNumber(stats['avg_seconds_per_image'] ?? stats['avgSecondsPerImage']);
    nodes.push({
      baseUrl: url,
      active: activeOverride ?? configuredSet.has(url),
      processed: processed ?? 0,
      avgSecondsPerImage: avgSeconds,
    });
  }

  for (const [url, stats] of statsByUrl.entries()) {
    if (knownUrls.has(url)) {
      continue;
    }
    const activeOverride = typeof stats['active'] === 'boolean' ? (stats['active'] as boolean) : null;
    const processed = coerceNumber(stats['processed']);
    const avgSeconds = coerceNumber(stats['avg_seconds_per_image'] ?? stats['avgSecondsPerImage']);
    nodes.push({
      baseUrl: url,
      active: activeOverride ?? configuredSet.has(url),
      processed: processed ?? 0,
      avgSecondsPerImage: avgSeconds,
    });
  }

  for (const url of configuredUrls) {
    if (knownUrls.has(url)) {
      continue;
    }
    if (nodes.some((node) => node.baseUrl === url)) {
      continue;
    }
    nodes.push({
      baseUrl: url,
      active: configuredSet.has(url),
      processed: 0,
      avgSecondsPerImage: null,
    });
  }

  return nodes;
}

function formatPercent(rate: number | null, fallback: string = '—'): string {
  if (rate === null) {
    return fallback;
  }
  if (!Number.isFinite(rate)) {
    return fallback;
  }
  const value = Math.max(0, Math.min(rate, 1));
  return `${Math.round(value * 100)}%`;
}

function formatSecondsPerImage(value: number | null): string {
  if (value === null || !Number.isFinite(value) || value <= 0) {
    return '— s/image';
  }
  if (value < 1) {
    return `${value.toFixed(2)} s/image`;
  }
  if (value < 10) {
    return `${value.toFixed(1)} s/image`;
  }
  return `${Math.round(value)} s/image`;
}

function countGeneratedImages(status: PipelineStatusResponse | undefined): number {
  const files = resolveGeneratedFiles(status);
  let count = 0;
  for (const entry of files) {
    const typeValue = typeof entry.type === 'string' ? entry.type.trim().toLowerCase() : '';
    const pathValue = typeof entry.path === 'string' ? entry.path.toLowerCase() : '';
    if (typeValue === 'image') {
      count += 1;
      continue;
    }
    if (pathValue.includes('/images/') && (pathValue.endsWith('.png') || pathValue.endsWith('.jpg') || pathValue.endsWith('.jpeg'))) {
      count += 1;
    }
  }
  return count;
}

function sumRetryCounts(bucket: Record<string, number> | null | undefined): number {
  if (!bucket) {
    return 0;
  }
  let total = 0;
  for (const value of Object.values(bucket)) {
    if (typeof value === 'number' && Number.isFinite(value)) {
      total += value;
    }
  }
  return total;
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
  return values.map((value) => formatLanguageWithFlag(value) || value).join(', ');
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
  const isPipelineLike = status.job_type === 'pipeline' || status.job_type === 'book';
  const pipelineResult =
    isPipelineLike && status.result && typeof status.result === 'object'
      ? (status.result as PipelineResponsePayload)
      : null;
  const pipelineConfig =
    pipelineResult && pipelineResult.pipeline_config && typeof pipelineResult.pipeline_config === 'object'
      ? (pipelineResult.pipeline_config as Record<string, unknown>)
      : null;
  const pipelineMetadata =
    pipelineResult && pipelineResult.book_metadata && typeof pipelineResult.book_metadata === 'object'
      ? (pipelineResult.book_metadata as Record<string, unknown>)
      : null;
  const languageValues = (parameters?.target_languages ?? []).filter(
    (value): value is string => typeof value === 'string' && value.trim().length > 0
  );
  const sentenceRange = resolveSentenceRange(status);
  const startSentence = parameters?.start_sentence ?? sentenceRange.start;
  const endSentence = parameters?.end_sentence ?? sentenceRange.end;
  const llmModelRaw = parameters?.llm_model ?? getStringField(pipelineConfig, 'ollama_model');
  const llmModel = formatModelLabel(llmModelRaw);
  const translationProviderRaw =
    parameters?.translation_provider ?? getStringField(pipelineMetadata, 'translation_provider');
  const translationProvider = normalizeTranslationProvider(translationProviderRaw);
  const translationModel = getStringField(pipelineMetadata, 'translation_model');
  const translationModelLabel = translationModel ? formatModelLabel(translationModel) : null;
  const translationProviderLabel = formatTranslationProviderLabel(
    translationProvider,
    translationModel,
    llmModelRaw
  );
  const transliterationModeRaw =
    parameters?.transliteration_mode ?? getStringField(pipelineMetadata, 'transliteration_mode');
  const transliterationMode = normalizeTransliterationMode(transliterationModeRaw);
  const transliterationModelRaw =
    parameters?.transliteration_model ?? getStringField(pipelineMetadata, 'transliteration_model');
  const transliterationModule =
    parameters?.transliteration_module ?? getStringField(pipelineMetadata, 'transliteration_module');
  const resolvedTransliterationModel =
    transliterationModelRaw ?? (transliterationMode === 'default' ? llmModelRaw : null);
  const transliterationModelLabel = resolvedTransliterationModel
    ? formatModelLabel(resolvedTransliterationModel)
    : null;
  const transliterationModeLabel = formatTransliterationModeLabel(transliterationMode);
  const showTransliterationModel =
    Boolean(transliterationModelLabel) &&
    (transliterationMode !== 'default' || translationProvider === 'googletrans');
  const retrySummary = status.retry_summary ?? null;
  const imageStats = status.image_generation ?? null;
  const imageEnabled = parameters?.add_images ?? (imageStats ? imageStats.enabled : null);
  const imageApiBaseUrl = getStringField(pipelineConfig, 'image_api_base_url');
  const generatedImageCount = countGeneratedImages(status);
  const expectedImages =
    imageStats && typeof imageStats.expected === 'number' && Number.isFinite(imageStats.expected)
      ? imageStats.expected
      : null;
  const resolvedGeneratedImages =
    imageStats && typeof imageStats.generated === 'number' && Number.isFinite(imageStats.generated)
      ? imageStats.generated
      : generatedImageCount;
  const imagePercent =
    imageStats && typeof imageStats.percent === 'number' && Number.isFinite(imageStats.percent)
      ? imageStats.percent
      : expectedImages !== null && expectedImages > 0
        ? Math.round((resolvedGeneratedImages / expectedImages) * 100)
        : null;
  const imagePending =
    imageStats && typeof imageStats.pending === 'number' && Number.isFinite(imageStats.pending)
      ? imageStats.pending
      : null;
  const imageBatchSize =
    imageStats && typeof imageStats.batch_size === 'number' && Number.isFinite(imageStats.batch_size)
      ? imageStats.batch_size
      : null;
  const imagePromptPlanSummary = resolveImagePromptPlanSummary(status);
  const imagePromptPlanQuality = imagePromptPlanSummary ? coerceRecord(imagePromptPlanSummary['quality']) : null;
  const imageRetryCounts =
    retrySummary && typeof retrySummary === 'object'
      ? (retrySummary as Record<string, Record<string, number>>).image
      : null;
  const imageRetryDetails = formatRetryCounts(imageRetryCounts);
  const imageErrors = sumRetryCounts(imageRetryCounts);

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
    if (translationProviderLabel) {
      entries.push({
        key: 'subtitle-translation-provider',
        label: 'Translation provider',
        value: translationProviderLabel
      });
    }
    if (translationModelLabel && translationProvider === 'googletrans') {
      entries.push({
        key: 'subtitle-translation-model',
        label: 'Translation model',
        value: translationModelLabel
      });
    }
    if (transliterationModeLabel) {
      entries.push({
        key: 'subtitle-transliteration-mode',
        label: 'Transliteration mode',
        value: transliterationModeLabel
      });
    }
    if (showTransliterationModel) {
      entries.push({
        key: 'subtitle-transliteration-model',
        label: 'Transliteration model',
        value: transliterationModelLabel
      });
    }
    if (transliterationModule) {
      entries.push({
        key: 'subtitle-transliteration-module',
        label: 'Transliteration module',
        value: transliterationModule
      });
    }
    const detectedLanguage = getStringField(subtitleMetadata, 'detected_language');
    const detectedLanguageCode = getStringField(subtitleMetadata, 'detected_language_code');
    if (detectedLanguage || detectedLanguageCode) {
      const detectedLabel = detectedLanguageCode
        ? `${detectedLanguage ?? 'Detected'} (${detectedLanguageCode})`
        : detectedLanguage;
      entries.push({
        key: 'subtitle-detected-language',
        label: 'Detected language',
        value: detectedLabel ?? 'Unknown'
      });
    }
    const originTranslation =
      subtitleMetadata && typeof subtitleMetadata['origin_translation'] === 'object'
        ? (subtitleMetadata['origin_translation'] as Record<string, unknown>)
        : null;
    const originTranslationActive =
      typeof originTranslation?.['active'] === 'boolean'
        ? (originTranslation['active'] as boolean)
        : Boolean(subtitleMetadata?.['origin_translation_applied']);
    const originSource =
      getStringField(originTranslation, 'source_language') ??
      getStringField(subtitleMetadata, 'translation_source_language');
    const originSourceCode =
      getStringField(originTranslation, 'source_language_code') ??
      getStringField(subtitleMetadata, 'translation_source_language_code');
    const originTarget =
      getStringField(originTranslation, 'target_language') ??
      getStringField(subtitleMetadata, 'original_language');
    const originTargetCode =
      getStringField(originTranslation, 'target_language_code') ??
      getStringField(subtitleMetadata, 'original_language_code');
    const originFromLabel = originSourceCode ?? originSource ?? 'source';
    const originToLabel = originTargetCode ?? originTarget ?? 'origin';
    entries.push({
      key: 'subtitle-origin-translation',
      label: 'Origin translation',
      value: originTranslationActive
        ? `Active (${originFromLabel} → ${originToLabel})`
        : `Matched (${originFromLabel} → ${originToLabel})`
    });
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
    if (retrySummary && typeof retrySummary === 'object') {
      const translationRetries = formatRetryCounts(
        (retrySummary as Record<string, Record<string, number>>).translation
      );
      if (translationRetries) {
        entries.push({
          key: 'subtitle-translation-retry-summary',
          label: 'Translation retries',
          value: translationRetries
        });
      }
      const transliterationRetries = formatRetryCounts(
        (retrySummary as Record<string, Record<string, number>>).transliteration
      );
      if (transliterationRetries) {
        entries.push({
          key: 'subtitle-transliteration-retry-summary',
          label: 'Transliteration retries',
          value: transliterationRetries
        });
      }
    }
    return entries;
  }

  if (status.job_type === 'youtube_dub') {
    const videoPath = parameters?.video_path ?? parameters?.input_file;
    const subtitlePath = parameters?.subtitle_path;
    const voice = parameters?.selected_voice;
    const tempo = parameters?.tempo;
    const readingSpeed = parameters?.macos_reading_speed;
    const targetLanguage = languageValues[0];
    const resultSection =
      status.result && typeof status.result === 'object'
        ? (status.result as Record<string, unknown>)['youtube_dub']
        : null;
    const outputPath =
      resultSection && typeof resultSection === 'object'
        ? ((resultSection as Record<string, unknown>).output_path as string | undefined)
        : null;

    if (targetLanguage) {
      entries.push({
        key: 'youtube-dub-target-language',
        label: 'Target language',
        value: targetLanguage
      });
    }
    if (translationProviderLabel) {
      entries.push({
        key: 'youtube-dub-translation-provider',
        label: 'Translation provider',
        value: translationProviderLabel
      });
    }
    if (translationModelLabel && translationProvider === 'googletrans') {
      entries.push({
        key: 'youtube-dub-translation-model',
        label: 'Translation model',
        value: translationModelLabel
      });
    }
    if (transliterationModeLabel) {
      entries.push({
        key: 'youtube-dub-transliteration-mode',
        label: 'Transliteration mode',
        value: transliterationModeLabel
      });
    }
    if (showTransliterationModel) {
      entries.push({
        key: 'youtube-dub-transliteration-model',
        label: 'Transliteration model',
        value: transliterationModelLabel
      });
    }
    if (transliterationModule) {
      entries.push({
        key: 'youtube-dub-transliteration-module',
        label: 'Transliteration module',
        value: transliterationModule
      });
    }
    if (voice) {
      entries.push({
        key: 'youtube-dub-voice',
        label: 'Voice',
        value: voice
      });
    }
    if (tempo !== null && tempo !== undefined) {
      entries.push({
        key: 'youtube-dub-tempo',
        label: 'Tempo',
        value: Number.isFinite(tempo) ? `${tempo}×` : String(tempo)
      });
    }
    if (readingSpeed !== null && readingSpeed !== undefined) {
      entries.push({
        key: 'youtube-dub-reading-speed',
        label: 'Reading speed',
        value: `${readingSpeed} WPM`
      });
    }
    if (videoPath) {
      entries.push({
        key: 'youtube-dub-video',
        label: 'Video file',
        value: videoPath
      });
    }
    if (subtitlePath) {
      entries.push({
        key: 'youtube-dub-subtitle',
        label: 'Subtitle',
        value: subtitlePath
      });
    }
    if (outputPath) {
      entries.push({
        key: 'youtube-dub-output',
        label: 'Output',
        value: outputPath
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
  if (translationProviderLabel) {
    entries.push({
      key: 'pipeline-translation-provider',
      label: 'Translation provider',
      value: translationProviderLabel
    });
  }
  if (translationModelLabel && translationProvider === 'googletrans') {
    entries.push({
      key: 'pipeline-translation-model',
      label: 'Translation model',
      value: translationModelLabel
    });
  }
  if (transliterationModeLabel) {
    entries.push({
      key: 'pipeline-transliteration-mode',
      label: 'Transliteration mode',
      value: transliterationModeLabel
    });
  }
  if (showTransliterationModel) {
    entries.push({
      key: 'pipeline-transliteration-model',
      label: 'Transliteration model',
      value: transliterationModelLabel
    });
  }
  if (transliterationModule) {
    entries.push({
      key: 'pipeline-transliteration-module',
      label: 'Transliteration module',
      value: transliterationModule
    });
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
  if (imageEnabled !== null || generatedImageCount > 0 || imageErrors > 0 || imagePromptPlanQuality) {
    const enabledLabel = imageEnabled === true ? 'On' : imageEnabled === false ? 'Off' : 'Unknown';
    const progressLabel =
      expectedImages !== null ? `${resolvedGeneratedImages}/${expectedImages}` : `${resolvedGeneratedImages}`;
    const percentLabel = imagePercent !== null ? `${imagePercent}%` : null;
    const generatedLabel = percentLabel ? `${progressLabel} (${percentLabel})` : progressLabel;
    const suffixParts: string[] = [];
    suffixParts.push(`generated ${generatedLabel}`);
    if (imagePending !== null && imagePending > 0) {
      suffixParts.push(`pending ${imagePending}`);
    }
    if (imageBatchSize !== null && imageBatchSize > 1) {
      suffixParts.push(`batch ${Math.round(imageBatchSize)}`);
    }
    if (imageErrors > 0) {
      suffixParts.push(`errors ${imageRetryDetails ?? imageErrors}`);
    }
    if (imageEnabled === true && !imageApiBaseUrl) {
      suffixParts.push('missing DrawThings URL');
    }
    entries.push({
      key: 'pipeline-add-images',
      label: 'Images',
      value: suffixParts.length > 0 ? `${enabledLabel} (${suffixParts.join(', ')})` : enabledLabel,
    });
    if (imageEnabled === true) {
      entries.push({
        key: 'pipeline-image-api',
        label: 'Image API',
        value: imageApiBaseUrl ?? 'Not configured',
      });
    }
    if (imagePromptPlanQuality) {
      const total = coerceNumber(imagePromptPlanQuality['total_sentences']);
      const fallbacks = coerceNumber(imagePromptPlanQuality['final_fallback']);
      const llmCoverageRate = coerceNumber(imagePromptPlanQuality['llm_coverage_rate']);
      const retryAttempts = coerceNumber(imagePromptPlanQuality['retry_attempts']);
      const retryRequested = coerceNumber(imagePromptPlanQuality['retry_requested']);
      const retryRecovered = coerceNumber(imagePromptPlanQuality['retry_recovered']);
      const retrySuccessRate = coerceNumber(imagePromptPlanQuality['retry_success_rate']);
      const llmRequests = coerceNumber(imagePromptPlanQuality['llm_requests']);
      const statusValueRaw =
        typeof imagePromptPlanSummary?.['status'] === 'string' ? (imagePromptPlanSummary['status'] as string).trim() : '';
      const statusLabel = statusValueRaw ? statusValueRaw.toUpperCase() : null;
      const errorMessage =
        typeof imagePromptPlanSummary?.['error'] === 'string' ? (imagePromptPlanSummary['error'] as string).trim() : null;

      const llmCount =
        total !== null && fallbacks !== null ? Math.max(0, Math.round(total - fallbacks)) : null;
      const coverageLabel =
        total !== null && llmCount !== null ? `${llmCount}/${Math.round(total)} (${formatPercent(llmCoverageRate)})` : null;

      const parts: string[] = [];
      if (statusLabel) {
        parts.push(statusLabel);
      }
      if (coverageLabel) {
        parts.push(`LLM ${coverageLabel}`);
      }
      if (fallbacks !== null) {
        parts.push(`fallbacks ${Math.round(fallbacks)}`);
      }
      if (retryAttempts !== null && retryAttempts > 0) {
        const recoveredLabel =
          retryRecovered !== null && retryRequested !== null ? `${Math.round(retryRecovered)}/${Math.round(retryRequested)}` : null;
        const successLabel = retrySuccessRate !== null ? formatPercent(retrySuccessRate) : null;
        if (recoveredLabel && successLabel) {
          parts.push(`retries ${Math.round(retryAttempts)} (recovered ${recoveredLabel}, ${successLabel})`);
        } else if (recoveredLabel) {
          parts.push(`retries ${Math.round(retryAttempts)} (recovered ${recoveredLabel})`);
        } else {
          parts.push(`retries ${Math.round(retryAttempts)}`);
        }
      }
      if (llmRequests !== null && llmRequests > 0) {
        parts.push(`LLM calls ${Math.round(llmRequests)}`);
      }
      if (errorMessage) {
        parts.push(`error: ${errorMessage}`);
      }

      entries.push({
        key: 'pipeline-image-prompt-plan',
        label: 'Prompt map quality',
        value: parts.length > 0 ? parts.join(', ') : '—',
      });
    }
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
  if (retrySummary && typeof retrySummary === 'object') {
    const translationRetries = formatRetryCounts(
      (retrySummary as Record<string, Record<string, number>>).translation
    );
    if (translationRetries) {
      entries.push({
        key: 'pipeline-translation-retry-summary',
        label: 'Translation retries',
        value: translationRetries
      });
    }
    const transliterationRetries = formatRetryCounts(
      (retrySummary as Record<string, Record<string, number>>).transliteration
    );
    if (transliterationRetries) {
      entries.push({
        key: 'pipeline-transliteration-retry-summary',
        label: 'Transliteration retries',
        value: transliterationRetries
      });
    }
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
  onRestart,
  onReload,
  onCopy,
  onMoveToLibrary,
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
  const statusGlyph = getStatusGlyph(statusValue);
  const jobLabel = useMemo(() => normalizeTextValue(status?.job_label) ?? null, [status?.job_label]);

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
  useEffect(() => {
    if (!supportsTvMetadata) {
      setSubtitleTab('overview');
    }
  }, [supportsTvMetadata]);

  const [tvMetadata, setTvMetadata] = useState<SubtitleTvMetadataResponse | null>(null);
  const [tvMetadataLoading, setTvMetadataLoading] = useState(false);
  const [tvMetadataMutating, setTvMetadataMutating] = useState(false);
  const [tvMetadataError, setTvMetadataError] = useState<string | null>(null);
  const [youtubeMetadata, setYoutubeMetadata] = useState<YoutubeVideoMetadataResponse | null>(null);
  const [youtubeMetadataLoading, setYoutubeMetadataLoading] = useState(false);
  const [youtubeMetadataMutating, setYoutubeMetadataMutating] = useState(false);
  const [youtubeMetadataError, setYoutubeMetadataError] = useState<string | null>(null);

  useEffect(() => {
    if (!supportsTvMetadata || subtitleTab !== 'metadata') {
      return;
    }
    let cancelled = false;
    setTvMetadataLoading(true);
    setTvMetadataError(null);
    fetchSubtitleTvMetadata(jobId)
      .then((payload) => {
        if (!cancelled) {
          setTvMetadata(payload);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : 'Unable to load TV metadata.';
          setTvMetadataError(message);
          setTvMetadata(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setTvMetadataLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [supportsTvMetadata, jobId, subtitleTab]);

  useEffect(() => {
    if (!supportsYoutubeMetadata || subtitleTab !== 'metadata') {
      return;
    }
    let cancelled = false;
    setYoutubeMetadataLoading(true);
    setYoutubeMetadataError(null);
    fetchYoutubeVideoMetadata(jobId)
      .then((payload) => {
        if (!cancelled) {
          setYoutubeMetadata(payload);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : 'Unable to load YouTube metadata.';
          setYoutubeMetadataError(message);
          setYoutubeMetadata(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setYoutubeMetadataLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [supportsYoutubeMetadata, jobId, subtitleTab]);

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
      {supportsTvMetadata ? (
        <div className="job-card__tabs" role="tablist" aria-label="Media job tabs">
          <button
            type="button"
            role="tab"
            aria-selected={subtitleTab === 'overview'}
            className={`job-card__tab ${subtitleTab === 'overview' ? 'is-active' : ''}`}
            onClick={() => setSubtitleTab('overview')}
          >
            Overview
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={subtitleTab === 'metadata'}
            className={`job-card__tab ${subtitleTab === 'metadata' ? 'is-active' : ''}`}
            onClick={() => setSubtitleTab('metadata')}
          >
            Metadata
          </button>
        </div>
      ) : null}
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
      {isBookJob && imageClusterNodes.length > 0 ? (
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
      {supportsTvMetadata && subtitleTab === 'metadata' ? (
        <div className="job-card__section">
          <h4>TV metadata</h4>
          {tvMetadataError ? <div className="alert">{tvMetadataError}</div> : null}
          {tvMetadataLoading ? <p>Loading metadata…</p> : null}
          {!tvMetadataLoading && tvMetadata ? (
            (() => {
              const mediaMetadata = tvMetadata.media_metadata ?? null;
              const media = coerceRecord(mediaMetadata);
              const show = media ? coerceRecord(media['show']) : null;
              const episode = media ? coerceRecord(media['episode']) : null;
              const errorMessage = normalizeTextValue(media ? media['error'] : null);
              const showName = normalizeTextValue(show ? show['name'] : null);
              const episodeName = normalizeTextValue(episode ? episode['name'] : null);
              const seasonNumber = typeof episode?.season === 'number' ? episode.season : null;
              const episodeNumber = typeof episode?.number === 'number' ? episode.number : null;
              const code = formatEpisodeCode(seasonNumber, episodeNumber);
              const airdate = normalizeTextValue(episode ? episode['airdate'] : null);
              const network = show ? coerceRecord(show['network']) : null;
              const networkName = normalizeTextValue(network ? network['name'] : null);
              const episodeUrl = normalizeTextValue(episode ? episode['url'] : null);
              const showImage = show ? coerceRecord(show['image']) : null;
              const showImageMedium = normalizeTextValue(showImage ? showImage['medium'] : null);
              const showImageOriginal = normalizeTextValue(showImage ? showImage['original'] : null);
              const showImageUrl = showImageMedium ?? showImageOriginal;
              const showImageLink = showImageOriginal ?? showImageMedium;
              const episodeImage = episode ? coerceRecord(episode['image']) : null;
              const episodeImageMedium = normalizeTextValue(episodeImage ? episodeImage['medium'] : null);
              const episodeImageOriginal = normalizeTextValue(episodeImage ? episodeImage['original'] : null);
              const episodeImageUrl = episodeImageMedium ?? episodeImageOriginal;
              const episodeImageLink = episodeImageOriginal ?? episodeImageMedium;

              const canLookup = canManage && !tvMetadataMutating;
              const hasLookupResult = Boolean(media && (showName || errorMessage));

              const handleLookup = async (force: boolean) => {
                setTvMetadataMutating(true);
                setTvMetadataError(null);
                try {
                  const payload = await lookupSubtitleTvMetadata(jobId, { force });
                  setTvMetadata(payload);
                  onReload();
                } catch (error) {
                  const message = error instanceof Error ? error.message : 'Unable to lookup TV metadata.';
                  setTvMetadataError(message);
                } finally {
                  setTvMetadataMutating(false);
                }
              };

              return (
                <>
                  {showImageUrl || episodeImageUrl ? (
                    <div className="tv-metadata-media" aria-label="TV images">
                      {showImageUrl ? (
                        <a
                          href={showImageLink ?? showImageUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="tv-metadata-media__poster"
                        >
                          <img
                            src={showImageUrl}
                            alt={showName ? `${showName} poster` : 'Show poster'}
                            loading="lazy"
                            decoding="async"
                          />
                        </a>
                      ) : null}
                      {episodeImageUrl ? (
                        <a
                          href={episodeImageLink ?? episodeImageUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="tv-metadata-media__still"
                        >
                          <img
                            src={episodeImageUrl}
                            alt={episodeName ? `${episodeName} still` : 'Episode still'}
                            loading="lazy"
                            decoding="async"
                          />
                        </a>
                      ) : null}
                    </div>
                  ) : null}
                  <dl className="metadata-grid">
                    {tvMetadata.source_name ? (
                      <div className="metadata-grid__row">
                        <dt>Source</dt>
                        <dd>{tvMetadata.source_name}</dd>
                      </div>
                    ) : null}
                    {tvMetadata.parsed ? (
                      <div className="metadata-grid__row">
                        <dt>Parsed</dt>
                        <dd>
                          {tvMetadata.parsed.series} {formatEpisodeCode(tvMetadata.parsed.season, tvMetadata.parsed.episode) ?? ''}
                        </dd>
                      </div>
                    ) : null}
                    {showName ? (
                      <div className="metadata-grid__row">
                        <dt>Show</dt>
                        <dd>{showName}</dd>
                      </div>
                    ) : null}
                    {code ? (
                      <div className="metadata-grid__row">
                        <dt>Episode</dt>
                        <dd>
                          {code}
                          {episodeName ? ` — ${episodeName}` : ''}
                        </dd>
                      </div>
                    ) : episodeName ? (
                      <div className="metadata-grid__row">
                        <dt>Episode</dt>
                        <dd>{episodeName}</dd>
                      </div>
                    ) : null}
                    {airdate ? (
                      <div className="metadata-grid__row">
                        <dt>Airdate</dt>
                        <dd>{airdate}</dd>
                      </div>
                    ) : null}
                    {networkName ? (
                      <div className="metadata-grid__row">
                        <dt>Network</dt>
                        <dd>{networkName}</dd>
                      </div>
                    ) : null}
                    {episodeUrl ? (
                      <div className="metadata-grid__row">
                        <dt>TVMaze</dt>
                        <dd>
                          <a href={episodeUrl} target="_blank" rel="noopener noreferrer">
                            Open episode page
                          </a>
                        </dd>
                      </div>
                    ) : null}
                  </dl>
                  {errorMessage ? <div className="notice notice--warning">{errorMessage}</div> : null}
                  <div className="job-card__tab-actions">
                    <button
                      type="button"
                      className="link-button"
                      onClick={() => handleLookup(false)}
                      disabled={!canLookup}
                      aria-busy={tvMetadataMutating}
                    >
                      {tvMetadataMutating ? 'Looking up…' : hasLookupResult ? 'Lookup (cached)' : 'Lookup on TVMaze'}
                    </button>
                    <button
                      type="button"
                      className="link-button"
                      onClick={() => handleLookup(true)}
                      disabled={!canLookup}
                      aria-busy={tvMetadataMutating}
                    >
                      Refresh
                    </button>
                  </div>
                  {media ? (
                    <details className="job-card__details">
                      <summary>Raw payload</summary>
                      <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(media, null, 2)}</pre>
                    </details>
                  ) : null}
                </>
              );
            })()
          ) : null}
          {!tvMetadataLoading && !tvMetadata ? <p>Metadata is not available yet.</p> : null}

          {supportsYoutubeMetadata ? (
            <div style={{ marginTop: '1.5rem' }}>
              <h4>YouTube metadata</h4>
              {youtubeMetadataError ? <div className="alert">{youtubeMetadataError}</div> : null}
              {youtubeMetadataLoading ? <p>Loading metadata…</p> : null}
              {!youtubeMetadataLoading && youtubeMetadata ? (
                (() => {
                  const youtube = coerceRecord(youtubeMetadata.youtube_metadata ?? null);
                  const title = normalizeTextValue(youtube ? youtube['title'] : null);
                  const channel =
                    normalizeTextValue(youtube ? youtube['channel'] : null) ??
                    normalizeTextValue(youtube ? youtube['uploader'] : null);
                  const webpageUrl = normalizeTextValue(youtube ? youtube['webpage_url'] : null);
                  const thumbnailUrl = normalizeTextValue(youtube ? youtube['thumbnail'] : null);
                  const summary = normalizeTextValue(youtube ? youtube['summary'] : null);
                  const errorMessage = normalizeTextValue(youtube ? youtube['error'] : null);
                  const rawPayload = youtube ? youtube['raw_payload'] : null;

                  const canLookup = canManage && !youtubeMetadataMutating;

                  const handleLookup = async (force: boolean) => {
                    setYoutubeMetadataMutating(true);
                    setYoutubeMetadataError(null);
                    try {
                      const payload = await lookupYoutubeVideoMetadata(jobId, { force });
                      setYoutubeMetadata(payload);
                      onReload();
                    } catch (error) {
                      const message = error instanceof Error ? error.message : 'Unable to lookup YouTube metadata.';
                      setYoutubeMetadataError(message);
                    } finally {
                      setYoutubeMetadataMutating(false);
                    }
                  };

                  return (
                    <>
                      {thumbnailUrl ? (
                        <div className="tv-metadata-media" aria-label="YouTube thumbnail">
                          <a
                            href={webpageUrl ?? thumbnailUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="tv-metadata-media__still"
                          >
                            <img
                              src={thumbnailUrl}
                              alt={title ? `${title} thumbnail` : 'YouTube thumbnail'}
                              loading="lazy"
                              decoding="async"
                            />
                          </a>
                        </div>
                      ) : null}
                      <dl className="metadata-grid">
                        {youtubeMetadata.source_name ? (
                          <div className="metadata-grid__row">
                            <dt>Source</dt>
                            <dd>{youtubeMetadata.source_name}</dd>
                          </div>
                        ) : null}
                        {youtubeMetadata.parsed ? (
                          <div className="metadata-grid__row">
                            <dt>Video id</dt>
                            <dd>{youtubeMetadata.parsed.video_id}</dd>
                          </div>
                        ) : null}
                        {title ? (
                          <div className="metadata-grid__row">
                            <dt>Title</dt>
                            <dd>{title}</dd>
                          </div>
                        ) : null}
                        {channel ? (
                          <div className="metadata-grid__row">
                            <dt>Channel</dt>
                            <dd>{channel}</dd>
                          </div>
                        ) : null}
                        {webpageUrl ? (
                          <div className="metadata-grid__row">
                            <dt>Link</dt>
                            <dd>
                              <a href={webpageUrl} target="_blank" rel="noopener noreferrer">
                                Open on YouTube
                              </a>
                            </dd>
                          </div>
                        ) : null}
                      </dl>
                      {summary ? <p>{summary}</p> : null}
                      {errorMessage ? <div className="notice notice--warning">{errorMessage}</div> : null}
                      <div className="job-card__tab-actions">
                        <button
                          type="button"
                          className="link-button"
                          onClick={() => handleLookup(false)}
                          disabled={!canLookup}
                          aria-busy={youtubeMetadataMutating}
                        >
                          {youtubeMetadataMutating ? 'Looking up…' : youtube ? 'Lookup (cached)' : 'Lookup via yt-dlp'}
                        </button>
                        <button
                          type="button"
                          className="link-button"
                          onClick={() => handleLookup(true)}
                          disabled={!canLookup}
                          aria-busy={youtubeMetadataMutating}
                        >
                          Refresh
                        </button>
                      </div>
                      {rawPayload ? (
                        <details className="job-card__details">
                          <summary>Raw payload</summary>
                          <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(rawPayload, null, 2)}</pre>
                        </details>
                      ) : null}
                    </>
                  );
                })()
              ) : null}
              {!youtubeMetadataLoading && !youtubeMetadata ? <p>Metadata is not available yet.</p> : null}
            </div>
          ) : null}
        </div>
      ) : tuningEntries.length > 0 ? (
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
      {fallbackEntries.length > 0 ? (
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
      {isSubtitleJob && subtitleTab === 'metadata' ? null : (
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
