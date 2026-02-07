import { formatLanguageWithFlag } from '../../utils/languages';
import { formatModelLabel } from '../../utils/modelInfo';
import type {
  PipelineJobStatus,
  PipelineStatusResponse,
} from '../../api/dtos';
import { IMAGE_API_NODE_OPTIONS } from '../../constants/imageNodes';

export const TERMINAL_STATES: PipelineJobStatus[] = ['completed', 'failed', 'cancelled'];
const GOOGLE_TRANSLATION_PROVIDER_ALIASES = new Set([
  'google',
  'googletrans',
  'googletranslate',
  'google-translate',
  'gtranslate',
  'gtrans',
]);
const TRANSLITERATION_PYTHON_ALIASES = new Set(['python', 'python-module', 'module', 'local-module']);
const TRANSLITERATION_DEFAULT_ALIASES = new Set(['default', 'llm', 'ollama']);

const METADATA_LABELS: Record<string, string> = {
  book_title: 'Title',
  book_author: 'Author',
  book_year: 'Publication year',
  book_summary: 'Summary',
  book_cover_file: 'Cover file',
  book_isbn: 'ISBN',
  book_genre: 'Genre',
  book_genres: 'Genres',
  book_publisher: 'Publisher',
  book_pages: 'Pages',
  openlibrary_book_url: 'OpenLibrary',
};

// Keys that represent interesting book metadata to display prominently
export const BOOK_METADATA_DISPLAY_KEYS = new Set([
  'book_title',
  'book_author',
  'book_year',
  'book_summary',
  'book_isbn',
  'book_genre',
  'book_genres',
  'book_publisher',
  'book_pages',
  'openlibrary_book_url',
]);

// Keys that are technical/internal and should be hidden in raw payload
export const TECHNICAL_METADATA_KEYS = new Set([
  'input_language',
  'target_language',
  'target_languages',
  'translation_provider',
  'translation_model',
  'translation_language',
  'transliteration_mode',
  'original_language',
  'job_label',
  'book_cover_file',
  'job_cover_asset',
  'media_metadata_lookup',
  'book_metadata_lookup',
  'enrichment_source',
  'enrichment_confidence',
]);

export const CREATION_METADATA_KEYS = new Set([
  'creation_summary',
  'creation_messages',
  'creation_warnings',
  'creation_sentences_preview',
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
};

const TUNING_DESCRIPTIONS: Record<string, string> = {
  hardware_profile: 'Hardware profile used to pick tuning defaults.',
  detected_cpu_cores: 'Auto-detected CPU cores used for sizing workers.',
  detected_memory_gib: 'Auto-detected RAM used for sizing workers.',
  pipeline_mode: 'Streams translation and media together for faster first output.',
  thread_count: 'Caps translation and audio worker threads (parallel LLM and TTS calls).',
  translation_pool_workers: 'Actual translation worker threads in use (parallel LLM calls).',
  translation_pool_mode: 'Worker pool implementation used for translations.',
  queue_size: 'Buffer between translation and media workers; larger means more in-flight tasks.',
  job_worker_slots: 'Max concurrent jobs the server can execute.',
  job_max_workers: 'Configured job concurrency limit (may be capped by hardware).',
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
];

export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return '—';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

export function formatMetadataLabel(key: string): string {
  return METADATA_LABELS[key] ?? key.replace(/_/g, ' ');
}

export function normalizeMetadataValue(value: unknown): string {
  if (value === null || value === undefined) {
    return '';
  }
  if (typeof value === 'string') {
    return value.trim();
  }
  if (Array.isArray(value)) {
    const items = value
      .map((entry) => (typeof entry === 'string' ? entry.trim() : String(entry)))
      .filter((entry) => entry.length > 0);
    return items.join(', ');
  }
  return String(value);
}

export function normalizeTranslationProvider(value: unknown): string | null {
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

export function normalizeTransliterationMode(value: unknown): string | null {
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

export function formatTranslationProviderLabel(
  provider: string | null,
  translationModel: string | null,
  llmModel: string | null,
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

export function formatTransliterationModeLabel(mode: string | null): string | null {
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

export function formatTuningLabel(key: string): string {
  return TUNING_LABELS[key] ?? key.replace(/_/g, ' ');
}

export function formatTuningDescription(key: string): string | null {
  return TUNING_DESCRIPTIONS[key] ?? null;
}

export function formatTuningValue(value: unknown): string {
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

export function formatFallbackValue(value: Record<string, unknown>): string {
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

export function normaliseStringList(value: unknown): string[] {
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

/**
 * Format a list of genres/categories for display.
 * Returns null if no valid genres, otherwise returns comma-separated string.
 * Limits to maxItems (default 5) to avoid overly long lists.
 */
export function formatGenreList(value: unknown, maxItems: number = 5): string | null {
  const items = normaliseStringList(value);
  if (items.length === 0) {
    return null;
  }
  const limited = items.slice(0, maxItems);
  return limited.join(', ');
}

export function formatMetadataValue(key: string, value: unknown): string {
  const normalized = normalizeMetadataValue(value);
  if (!normalized) {
    return '';
  }
  return normalized;
}

export function coerceRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : null;
}

export function normalizeTextValue(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export function formatEpisodeCode(season: number | null, episode: number | null): string | null {
  if (!season || !episode) {
    return null;
  }
  if (!Number.isInteger(season) || !Number.isInteger(episode) || season <= 0 || episode <= 0) {
    return null;
  }
  return `S${season.toString().padStart(2, '0')}E${episode.toString().padStart(2, '0')}`;
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

export function formatRetryCounts(counts?: Record<string, number> | null): string | null {
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

export function coerceNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

export function resolveGeneratedChunks(
  status: PipelineStatusResponse | undefined,
): Record<string, unknown>[] {
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

export function resolveGeneratedFiles(
  status: PipelineStatusResponse | undefined,
): Record<string, unknown>[] {
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

export function resolveImagePromptPlanSummary(
  status: PipelineStatusResponse | undefined,
): Record<string, unknown> | null {
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

export type ImageClusterNodeSummary = {
  baseUrl: string;
  active: boolean;
  processed: number | null;
  avgSecondsPerImage: number | null;
};

export function resolveImageClusterSummary(
  status: PipelineStatusResponse | undefined,
): Record<string, unknown> | null {
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

export function normalizeBaseUrl(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  return trimmed.replace(/\/+$/, '');
}

export function resolveImageClusterBaseUrls(
  config: Record<string, unknown> | null,
): string[] {
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

export function buildImageClusterNodes(
  summary: Record<string, unknown> | null,
  config: Record<string, unknown> | null,
  enabled: boolean,
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

export function formatPercent(rate: number | null, fallback: string = '—'): string {
  if (rate === null) {
    return fallback;
  }
  if (!Number.isFinite(rate)) {
    return fallback;
  }
  const value = Math.max(0, Math.min(rate, 1));
  return `${Math.round(value * 100)}%`;
}

export function formatSecondsPerImage(value: number | null): string {
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

export function formatSeconds(value: number | null, suffix: string = 's'): string {
  if (value === null || !Number.isFinite(value) || value <= 0) {
    return `— ${suffix}`;
  }
  if (value < 1) {
    return `${value.toFixed(2)} ${suffix}`;
  }
  if (value < 10) {
    return `${value.toFixed(1)} ${suffix}`;
  }
  return `${Math.round(value)} ${suffix}`;
}

export function countGeneratedImages(status: PipelineStatusResponse | undefined): number {
  const files = resolveGeneratedFiles(status);
  let count = 0;
  for (const entry of files) {
    const typeValue = typeof entry.type === 'string' ? entry.type.trim().toLowerCase() : '';
    const pathValue = typeof entry.path === 'string' ? entry.path.toLowerCase() : '';
    if (typeValue === 'image') {
      count += 1;
      continue;
    }
    if (
      pathValue.includes('/images/') &&
      (pathValue.endsWith('.png') || pathValue.endsWith('.jpg') || pathValue.endsWith('.jpeg'))
    ) {
      count += 1;
    }
  }
  return count;
}

export function sumRetryCounts(bucket: Record<string, number> | null | undefined): number {
  if (!bucket) {
    return 0;
  }
  return Object.values(bucket).reduce((sum, count) => {
    if (typeof count !== 'number' || !Number.isFinite(count)) {
      return sum;
    }
    return sum + Math.max(0, count);
  }, 0);
}

export function resolveSentenceRange(
  status: PipelineStatusResponse | undefined,
): { start: number | null; end: number | null } {
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

export function getStringField(
  source: Record<string, unknown> | null | undefined,
  key: string,
): string | null {
  if (!source) {
    return null;
  }
  const value = source[key];
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

export function extractVoiceOverrides(
  source: Record<string, unknown> | null | undefined,
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

export function formatVoiceOverrides(
  overrides: Record<string, string> | undefined,
): string | null {
  if (!overrides) {
    return null;
  }
  const entries = Object.entries(overrides);
  if (entries.length === 0) {
    return null;
  }
  return entries.map(([code, voice]) => `${code}: ${voice}`).join(', ');
}

export function formatLanguageList(values: string[] | undefined): string | null {
  if (!values || values.length === 0) {
    return null;
  }
  return values.map((value) => formatLanguageWithFlag(value) || value).join(', ');
}

export function formatTimeOffset(seconds: number | null | undefined): string | null {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds)) {
    return null;
  }
  const totalSeconds = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const remainingSeconds = totalSeconds % 60;
  const parts = [minutes.toString().padStart(2, '0'), remainingSeconds.toString().padStart(2, '0')];
  if (hours > 0) {
    parts.unshift(hours.toString().padStart(2, '0'));
  }
  return parts.join(':');
}

export function resolveSubtitleMetadata(
  status: PipelineStatusResponse | undefined,
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

export function sortTuningEntries(entries: [string, unknown][]): [string, unknown][] {
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
