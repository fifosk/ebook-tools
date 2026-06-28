import type {
  AcquisitionCandidate,
  CreationTemplateEntry,
  CreationTemplatePayload
} from '../../api/dtos';
import { sanitizeTemplateValue } from '../../utils/creationTemplateSanitizer';
import type { BookNarrationFormSection, FormState } from './bookNarrationFormTypes';
import {
  BOOK_NARRATION_TAB_SECTIONS,
  DEFAULT_FORM_STATE
} from './bookNarrationFormDefaults';
import {
  basenameFromPath,
  isRecord,
  normalizeTextValue,
  parseJsonField
} from './bookNarrationUtils';

type BuildBookNarrationTemplateOptions = {
  formState: FormState;
  normalizedTargetLanguages: string[];
  sourceMode: 'upload' | 'generated';
  activeSection: BookNarrationFormSection;
  payloadExtras?: Record<string, unknown> | null;
};

export type AppliedBookNarrationTemplate = {
  formState: Partial<FormState>;
  activeSection: BookNarrationFormSection | null;
  discoveryState: Record<string, unknown> | null;
};

function cleanDiscoveryText(value: string | null | undefined): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}

export function buildBookDiscoveryTemplateState(
  candidate: AcquisitionCandidate,
  {
    query,
    provider,
    selectedPath,
    preparedMetadata
  }: {
    query: string;
    provider: string;
    selectedPath?: string | null;
    preparedMetadata?: Record<string, unknown> | null;
  }
): Record<string, unknown> {
  const preparedSourceProvider = normalizeTextValue(preparedMetadata?.source_provider);
  const preparedAcquisitionProvider = normalizeTextValue(preparedMetadata?.acquisition_provider);
  const preparedCandidateId = normalizeTextValue(preparedMetadata?.acquisition_candidate_id);
  const preparedSourceKind = normalizeTextValue(preparedMetadata?.source_kind);
  const state: Record<string, unknown> = {
    media_kind: 'book',
    provider: candidate.provider,
    candidate_id: candidate.candidate_id,
    title: candidate.title,
    rights: candidate.rights,
    capabilities: candidate.capabilities,
    selected_provider: provider
  };
  const normalizedQuery = cleanDiscoveryText(query);
  const normalizedSelectedPath = cleanDiscoveryText(selectedPath);
  const localPath = cleanDiscoveryText(candidate.local_path);
  const sourceUrl = cleanDiscoveryText(candidate.source_url);
  const coverUrl = cleanDiscoveryText(candidate.cover_url);
  const language = cleanDiscoveryText(candidate.language);
  if (normalizedQuery) {
    state.query = normalizedQuery;
  }
  if (normalizedSelectedPath) {
    state.selected_path = normalizedSelectedPath;
  }
  if (preparedSourceProvider) {
    state.source_provider = preparedSourceProvider;
  }
  if (preparedAcquisitionProvider) {
    state.acquisition_provider = preparedAcquisitionProvider;
  }
  if (preparedCandidateId) {
    state.acquisition_candidate_id = preparedCandidateId;
  }
  if (preparedSourceKind) {
    state.source_kind = preparedSourceKind;
  }
  if (localPath) {
    state.local_path = localPath;
  }
  if (sourceUrl) {
    state.source_url = sourceUrl;
  }
  if (coverUrl) {
    state.cover_url = coverUrl;
  }
  if (language) {
    state.language = language;
  }
  if (typeof candidate.year === 'number') {
    state.year = candidate.year;
  }
  return state;
}

function sanitizeJsonField(label: string, value: string): string {
  const parsed = parseJsonField(label, value);
  const sanitized = sanitizeTemplateValue(parsed);
  return JSON.stringify(sanitized, null, 2);
}

function metadataForTemplateName(formState: FormState): Record<string, unknown> {
  try {
    return parseJsonField('book_metadata', formState.book_metadata);
  } catch (error) {
    return {};
  }
}

export function deriveBookNarrationTemplateName(
  formState: FormState,
  sourceMode: 'upload' | 'generated'
): string {
  const metadata = metadataForTemplateName(formState);
  const title = normalizeTextValue(metadata.book_title);
  if (title) {
    return title;
  }

  const outputStem = formState.base_output_file.trim();
  if (outputStem) {
    return outputStem;
  }

  const inputName = basenameFromPath(formState.input_file);
  if (inputName) {
    return inputName.replace(/\.[^.]+$/, '');
  }

  return sourceMode === 'generated' ? 'Generated book template' : 'Narrate Ebook template';
}

export function buildBookNarrationTemplatePayload({
  formState,
  normalizedTargetLanguages,
  sourceMode,
  activeSection,
  payloadExtras = null
}: BuildBookNarrationTemplateOptions): CreationTemplatePayload {
  const safeFormState: FormState = {
    ...formState,
    target_languages: normalizedTargetLanguages,
    custom_target_languages: '',
    config: sanitizeJsonField('config', formState.config),
    environment_overrides: '{}',
    pipeline_overrides: sanitizeJsonField('pipeline_overrides', formState.pipeline_overrides),
    book_metadata: sanitizeJsonField('book_metadata', formState.book_metadata)
  };

  const safePayloadExtras = sanitizeTemplateExtras(payloadExtras);

  return {
    name: deriveBookNarrationTemplateName(formState, sourceMode),
    mode: sourceMode === 'generated' ? 'generated_book' : 'narrate_ebook',
    payload: {
      kind: 'book_narration_form',
      source: 'web',
      version: 1,
      source_mode: sourceMode,
      ...safePayloadExtras,
      active_section: activeSection,
      form_state: safeFormState
    }
  };
}

function sanitizeTemplateExtras(value: Record<string, unknown> | null): Record<string, unknown> {
  if (!value) {
    return {};
  }
  const sanitized = sanitizeTemplateValue(value);
  if (!isRecord(sanitized)) {
    return {};
  }
  const safe: Record<string, unknown> = {};
  for (const [key, entry] of Object.entries(sanitized)) {
    if (
      key === 'kind' ||
      key === 'source' ||
      key === 'version' ||
      key === 'source_mode' ||
      key === 'active_section' ||
      key === 'form_state'
    ) {
      continue;
    }
    safe[key] = entry;
  }
  return safe;
}

function sanitizedDiscoveryState(value: unknown): Record<string, unknown> | null {
  if (!isRecord(value)) {
    return null;
  }
  const sanitized = sanitizeTemplateValue(value);
  return isRecord(sanitized) && Object.keys(sanitized).length > 0 ? sanitized : null;
}

function templateSourceModeForMode(mode: CreationTemplateEntry['mode']): 'upload' | 'generated' | null {
  if (mode === 'generated_book') {
    return 'generated';
  }
  if (mode === 'narrate_ebook') {
    return 'upload';
  }
  return null;
}

function coerceStringArray(value: unknown): string[] | null {
  if (!Array.isArray(value)) {
    return null;
  }
  const entries = value
    .map((entry) => (typeof entry === 'string' ? entry.trim() : ''))
    .filter(Boolean);
  return entries.length > 0 ? entries : [];
}

function coerceStringMap(value: unknown): Record<string, string> | null {
  if (!isRecord(value)) {
    return null;
  }
  const next: Record<string, string> = {};
  for (const [key, entry] of Object.entries(value)) {
    const cleanKey = key.trim();
    if (!cleanKey || typeof entry !== 'string') {
      continue;
    }
    const cleanValue = entry.trim();
    if (cleanValue) {
      next[cleanKey] = cleanValue;
    }
  }
  return next;
}

function coerceFormStateValue(
  key: keyof FormState,
  value: unknown,
  defaultValue: FormState[keyof FormState]
): FormState[keyof FormState] | null {
  if (typeof defaultValue === 'string') {
    return typeof value === 'string' ? value : null;
  }
  if (typeof defaultValue === 'number') {
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value;
    }
    if (typeof value === 'string') {
      const parsed = Number(value.trim());
      return Number.isFinite(parsed) ? parsed : null;
    }
    return null;
  }
  if (typeof defaultValue === 'boolean') {
    return typeof value === 'boolean' ? value : null;
  }
  if (Array.isArray(defaultValue)) {
    return coerceStringArray(value);
  }
  if (key === 'voice_overrides') {
    return coerceStringMap(value);
  }
  return null;
}

export function extractBookNarrationTemplateFormState(
  template: CreationTemplateEntry | null | undefined,
  sourceMode: 'upload' | 'generated'
): AppliedBookNarrationTemplate | null {
  if (!template) {
    return null;
  }
  const expectedMode = templateSourceModeForMode(template.mode);
  if (expectedMode !== sourceMode) {
    return null;
  }
  const payload = template.payload;
  if (!isRecord(payload) || payload.kind !== 'book_narration_form') {
    return null;
  }
  if (typeof payload.source_mode === 'string' && payload.source_mode !== sourceMode) {
    return null;
  }
  if (!isRecord(payload.form_state)) {
    return null;
  }

  const formState: Partial<FormState> = {};
  for (const [key, defaultValue] of Object.entries(DEFAULT_FORM_STATE) as [
    keyof FormState,
    FormState[keyof FormState]
  ][]) {
    if (!(key in payload.form_state)) {
      continue;
    }
    const value = coerceFormStateValue(key, payload.form_state[key], defaultValue);
    if (value !== null) {
      formState[key] = value as never;
    }
  }

  const activeSection =
    typeof payload.active_section === 'string' &&
    BOOK_NARRATION_TAB_SECTIONS.includes(payload.active_section as BookNarrationFormSection)
      ? (payload.active_section as BookNarrationFormSection)
      : null;
  const discoveryState = sanitizedDiscoveryState(payload.discovery_state);

  return Object.keys(formState).length > 0 || activeSection || discoveryState
    ? { formState, activeSection, discoveryState }
    : null;
}
