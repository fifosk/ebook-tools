import type { JobParameterSnapshot } from '../../api/dtos';
import { formatTimecodeFromSeconds } from './subtitleSubmitUtils';

function normalizeOptionalText(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const cleaned = value.trim();
  return cleaned.length > 0 ? cleaned : null;
}

function normalizeFiniteNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

export type SubtitlePrefillValues = {
  targetLanguage: string | null;
  inputLanguage: string | null;
  enableTransliteration: boolean | null;
  showOriginal: boolean | null;
  workerCount: number | null;
  batchSize: number | null;
  translationBatchSize: number | null;
  startTime: string | null;
  endTime: string | null;
  selectedModel: string | null;
  translationProvider: string | null;
  transliterationMode: string | null;
  transliterationModel: string | null;
  sourcePath: string | null;
};

export function resolveSubtitlePrefillValues(
  parameters: JobParameterSnapshot | null | undefined
): SubtitlePrefillValues {
  const targetLanguages = Array.isArray(parameters?.target_languages)
    ? parameters.target_languages
        .map((entry) => (typeof entry === 'string' ? entry.trim() : ''))
        .filter((entry) => entry.length > 0)
    : [];
  const subtitlePath =
    typeof parameters?.subtitle_path === 'string' ? parameters.subtitle_path.trim() : null;
  const fallbackInputFile =
    typeof parameters?.input_file === 'string' && parameters.input_file
      ? parameters.input_file.trim()
      : null;
  const sourcePath = subtitlePath !== null ? subtitlePath : fallbackInputFile;
  return {
    targetLanguage: targetLanguages[0] ?? null,
    inputLanguage: normalizeOptionalText(parameters?.input_language),
    enableTransliteration:
      typeof parameters?.enable_transliteration === 'boolean'
        ? parameters.enable_transliteration
        : null,
    showOriginal: typeof parameters?.show_original === 'boolean' ? parameters.show_original : null,
    workerCount: normalizeFiniteNumber(parameters?.worker_count),
    batchSize: normalizeFiniteNumber(parameters?.batch_size),
    translationBatchSize: normalizeFiniteNumber(parameters?.translation_batch_size),
    startTime:
      typeof parameters?.start_time_offset_seconds === 'number'
        ? formatTimecodeFromSeconds(parameters.start_time_offset_seconds)
        : null,
    endTime:
      typeof parameters?.end_time_offset_seconds === 'number'
        ? formatTimecodeFromSeconds(parameters.end_time_offset_seconds)
        : null,
    selectedModel: normalizeOptionalText(parameters?.llm_model),
    translationProvider: normalizeOptionalText(parameters?.translation_provider),
    transliterationMode: normalizeOptionalText(parameters?.transliteration_mode),
    transliterationModel: normalizeOptionalText(parameters?.transliteration_model),
    sourcePath: sourcePath && sourcePath.length > 0 ? sourcePath : null
  };
}
