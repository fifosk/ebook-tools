import type { CreationTemplatePayload } from '../../api/dtos';
import { sanitizeTemplateValue } from '../../utils/creationTemplateSanitizer';
import type { BookNarrationFormSection, FormState } from './bookNarrationFormTypes';
import {
  basenameFromPath,
  normalizeTextValue,
  parseJsonField
} from './bookNarrationUtils';

type BuildBookNarrationTemplateOptions = {
  formState: FormState;
  normalizedTargetLanguages: string[];
  sourceMode: 'upload' | 'generated';
  activeSection: BookNarrationFormSection;
};

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
  activeSection
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

  return {
    name: deriveBookNarrationTemplateName(formState, sourceMode),
    mode: sourceMode === 'generated' ? 'generated_book' : 'narrate_ebook',
    payload: {
      kind: 'book_narration_form',
      source: 'web',
      version: 1,
      source_mode: sourceMode,
      active_section: activeSection,
      form_state: safeFormState
    }
  };
}
