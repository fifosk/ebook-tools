import {
  DEFAULT_START_TIME,
  MAX_ASS_EMPHASIS,
  MAX_ASS_FONT_SIZE,
  MIN_ASS_EMPHASIS,
  MIN_ASS_FONT_SIZE
} from './subtitleToolConfig';
import type { SubtitleOutputFormat, SubtitleSourceMode } from './subtitleToolTypes';

export function normalizeLanguageInput(value: string): string {
  return value.trim() || '';
}

type ParsedTimecode = {
  seconds: number;
  normalized: string;
};

function parseAbsoluteTimecode(value: string): ParsedTimecode | null {
  const trimmed = value.trim();
  const match = trimmed.match(/^(\d+):(\d{1,2})(?::(\d{1,2}))?$/);
  if (!match) {
    return null;
  }
  const [, primary, secondary, tertiary] = match;
  const first = Number(primary);
  const second = Number(secondary);
  const third = typeof tertiary === 'string' ? Number(tertiary) : null;

  if ([first, second, third ?? 0].some((component) => !Number.isInteger(component) || component < 0)) {
    return null;
  }
  if (third !== null) {
    if (second >= 60 || third >= 60) {
      return null;
    }
    const hours = first;
    const minutes = second;
    const seconds = third;
    const normalized = [hours, minutes, seconds]
      .map((component) => component.toString().padStart(2, '0'))
      .join(':');
    return {
      seconds: hours * 3600 + minutes * 60 + seconds,
      normalized
    };
  }

  if (second >= 60) {
    return null;
  }
  const minutes = first;
  const seconds = second;
  return {
    seconds: minutes * 60 + seconds,
    normalized: `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
  };
}

function formatRelativeDuration(totalSeconds: number): string {
  const clamped = Math.max(0, Math.floor(totalSeconds));
  if (clamped >= 3600) {
    const hours = Math.floor(clamped / 3600);
    const remainder = clamped % 3600;
    const minutes = Math.floor(remainder / 60);
    const seconds = remainder % 60;
    return [hours, minutes, seconds].map((component) => component.toString().padStart(2, '0')).join(':');
  }
  const minutes = Math.floor(clamped / 60);
  const seconds = clamped % 60;
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

function parseRelativeTimecode(value: string): ParsedTimecode | null {
  const trimmed = value.trim();
  if (/^\d+$/.test(trimmed)) {
    const minutes = Number(trimmed);
    if (!Number.isInteger(minutes) || minutes < 0) {
      return null;
    }
    const totalSeconds = minutes * 60;
    return {
      seconds: totalSeconds,
      normalized: formatRelativeDuration(totalSeconds)
    };
  }
  const absolute = parseAbsoluteTimecode(trimmed);
  if (!absolute) {
    return null;
  }
  return {
    seconds: absolute.seconds,
    normalized: formatRelativeDuration(absolute.seconds)
  };
}

export function normalizeSubtitleTimecodeInput(
  value: string,
  options: { allowRelative?: boolean; emptyValue?: string } = {}
): string | null {
  const { allowRelative = false, emptyValue = '' } = options;
  const trimmed = value.trim();
  if (!trimmed) {
    return emptyValue;
  }
  if (allowRelative && trimmed.startsWith('+')) {
    const relative = parseRelativeTimecode(trimmed.slice(1));
    if (!relative) {
      return null;
    }
    return `+${relative.normalized}`;
  }
  const absolute = parseAbsoluteTimecode(trimmed);
  if (!absolute) {
    return null;
  }
  return absolute.normalized;
}

export function formatTimecodeFromSeconds(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value) || value < 0) {
    return '';
  }
  const totalSeconds = Math.floor(value);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (hours > 0) {
    return [hours, minutes, seconds].map((component) => component.toString().padStart(2, '0')).join(':');
  }
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

function normalizeOptionalText(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const cleaned = value.trim();
  return cleaned.length > 0 ? cleaned : null;
}

export type SubtitleSubmitInput = {
  inputLanguage: string;
  targetLanguage: string;
  isAssSelection: boolean;
  sourceMode: SubtitleSourceMode;
  selectedSource: string;
  hasUploadFile: boolean;
  startTime: string;
  endTime: string;
  outputFormat: SubtitleOutputFormat;
  assFontSize: number | '';
  assEmphasis: number | '';
  selectedModel: string;
  translationProvider: string;
  transliterationMode: string;
  transliterationModel: string;
  workerCount: number | '';
  batchSize: number | '';
  translationBatchSize: number | '';
};

export type ResolvedSubtitleSubmitValues = {
  originalLanguage: string;
  targetLanguage: string;
  normalizedStartTime: string;
  normalizedEndTime: string;
  resolvedAssFontSize: number | null;
  resolvedAssEmphasis: number | null;
  selectedModel: string | null;
  translationProvider: string | null;
  transliterationMode: string | null;
  transliterationModel: string | null;
  sourcePath: string | null;
  workerCount: number | null;
  batchSize: number | null;
  translationBatchSize: number | null;
};

export type SubtitleSubmitFormDataInput = {
  values: ResolvedSubtitleSubmitValues;
  enableTransliteration: boolean;
  enableHighlight: boolean;
  showOriginal: boolean;
  generateAudioBook: boolean;
  outputFormat: SubtitleOutputFormat;
  mirrorToSourceDir: boolean;
  uploadFile?: File | null;
  mediaMetadataDraft?: Record<string, unknown> | null;
};

export type SubtitleSubmitResolution =
  | { ok: true; values: ResolvedSubtitleSubmitValues }
  | { ok: false; error: string };

export function resolveSubtitleSubmitValues(input: SubtitleSubmitInput): SubtitleSubmitResolution {
  const originalLanguage = normalizeLanguageInput(input.inputLanguage);
  if (!originalLanguage) {
    return { ok: false, error: 'Choose an original language.' };
  }
  if (input.isAssSelection) {
    return {
      ok: false,
      error: 'Generated ASS files cannot be used as sources. Choose the original SRT/VTT or upload a new subtitle.'
    };
  }
  const targetLanguage = normalizeLanguageInput(input.targetLanguage);
  if (!targetLanguage) {
    return { ok: false, error: 'Choose a target language.' };
  }
  const sourcePath = input.selectedSource.trim();
  if (input.sourceMode === 'existing' && !sourcePath) {
    return { ok: false, error: 'Select a subtitle file to process.' };
  }
  if (input.sourceMode === 'upload' && !input.hasUploadFile) {
    return { ok: false, error: 'Choose a subtitle file to upload.' };
  }

  const normalizedStartTime = normalizeSubtitleTimecodeInput(input.startTime, {
    emptyValue: DEFAULT_START_TIME
  });
  if (normalizedStartTime === null) {
    return { ok: false, error: 'Enter a valid start time in MM:SS or HH:MM:SS format.' };
  }
  const normalizedEndTime = normalizeSubtitleTimecodeInput(input.endTime, {
    allowRelative: true,
    emptyValue: ''
  });
  if (normalizedEndTime === null) {
    return { ok: false, error: 'Enter a valid end time in MM:SS, HH:MM:SS, or +offset format.' };
  }

  let resolvedAssFontSize: number | null = null;
  let resolvedAssEmphasis: number | null = null;
  if (input.outputFormat === 'ass') {
    if (typeof input.assFontSize !== 'number' || Number.isNaN(input.assFontSize)) {
      return { ok: false, error: 'Enter a numeric ASS base font size.' };
    }
    resolvedAssFontSize = Math.max(
      MIN_ASS_FONT_SIZE,
      Math.min(MAX_ASS_FONT_SIZE, Math.round(input.assFontSize))
    );

    if (typeof input.assEmphasis !== 'number' || Number.isNaN(input.assEmphasis)) {
      return { ok: false, error: 'Enter a numeric ASS emphasis scale.' };
    }
    resolvedAssEmphasis = Math.max(
      MIN_ASS_EMPHASIS,
      Math.min(MAX_ASS_EMPHASIS, Math.round(input.assEmphasis * 100) / 100)
    );
  }

  return {
    ok: true,
    values: {
      originalLanguage,
      targetLanguage,
      normalizedStartTime,
      normalizedEndTime,
      resolvedAssFontSize,
      resolvedAssEmphasis,
      selectedModel: normalizeOptionalText(input.selectedModel),
      translationProvider: normalizeOptionalText(input.translationProvider),
      transliterationMode: normalizeOptionalText(input.transliterationMode),
      transliterationModel: normalizeOptionalText(input.transliterationModel),
      sourcePath: input.sourceMode === 'existing' ? sourcePath : null,
      workerCount: typeof input.workerCount === 'number' && input.workerCount > 0 ? input.workerCount : null,
      batchSize: typeof input.batchSize === 'number' && input.batchSize > 0 ? input.batchSize : null,
      translationBatchSize:
        typeof input.translationBatchSize === 'number' && input.translationBatchSize > 0
          ? input.translationBatchSize
          : null
    }
  };
}

export function buildSubtitleSubmitFormData(input: SubtitleSubmitFormDataInput): FormData {
  const { values } = input;
  const formData = new FormData();
  formData.append('input_language', values.originalLanguage);
  formData.append('original_language', values.originalLanguage);
  formData.append('target_language', values.targetLanguage);
  formData.append('enable_transliteration', String(input.enableTransliteration));
  formData.append('highlight', String(input.enableHighlight));
  formData.append('show_original', String(input.showOriginal));
  formData.append('generate_audio_book', String(input.generateAudioBook));
  formData.append('output_format', input.outputFormat);
  formData.append('mirror_batches_to_source_dir', String(input.mirrorToSourceDir));
  formData.append('start_time', values.normalizedStartTime);
  if (values.resolvedAssFontSize !== null) {
    formData.append('ass_font_size', String(values.resolvedAssFontSize));
  }
  if (values.resolvedAssEmphasis !== null) {
    formData.append('ass_emphasis_scale', String(values.resolvedAssEmphasis));
  }
  if (values.selectedModel) {
    formData.append('llm_model', values.selectedModel);
  }
  if (values.translationProvider) {
    formData.append('translation_provider', values.translationProvider);
  }
  if (values.transliterationMode) {
    formData.append('transliteration_mode', values.transliterationMode);
  }
  if (values.transliterationModel) {
    formData.append('transliteration_model', values.transliterationModel);
  }
  if (values.normalizedEndTime) {
    formData.append('end_time', values.normalizedEndTime);
  }
  if (values.sourcePath) {
    formData.append('source_path', values.sourcePath);
  } else if (input.uploadFile) {
    formData.append('file', input.uploadFile, input.uploadFile.name);
  }
  if (values.workerCount !== null) {
    formData.append('worker_count', String(values.workerCount));
  }
  if (values.batchSize !== null) {
    formData.append('batch_size', String(values.batchSize));
  }
  if (values.translationBatchSize !== null) {
    formData.append('translation_batch_size', String(values.translationBatchSize));
  }
  if (input.mediaMetadataDraft) {
    formData.append('media_metadata_json', JSON.stringify(input.mediaMetadataDraft));
  }
  return formData;
}
