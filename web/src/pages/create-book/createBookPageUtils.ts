import type { PipelineRequestPayload } from '../../api/dtos';
import type {
  BookCreationOptionsResponse,
  BookGenerationJobRequest,
} from '../../api/createBook';
import type { BookNarrationPipelineDefaults } from '../../components/book-narration/bookNarrationFormTypes';

export type GeneratorFormState = {
  topic: string;
  book_name: string;
  genre: string;
  author: string;
  num_sentences: number;
};

export type GeneratorEditedField = keyof GeneratorFormState;

export const DEFAULT_GENERATOR_STATE: GeneratorFormState = {
  topic: '',
  book_name: '',
  genre: '',
  author: 'Me',
  num_sentences: 30,
};

export const FALLBACK_SENTENCE_BOUNDS = {
  min: 1,
  max: 500,
  default: DEFAULT_GENERATOR_STATE.num_sentences,
};

export function deriveBaseOutputName(value: string): string {
  const withoutExtension = value.replace(/\.[^/.]+$/, '');
  const normalized = withoutExtension
    .trim()
    .replace(/[^A-Za-z0-9]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .toLowerCase();
  if (normalized) {
    return normalized;
  }
  if (withoutExtension.trim()) {
    return withoutExtension.trim();
  }
  return 'generated-book';
}

export function normalizeSentenceCount(
  value: number,
  bounds: BookCreationOptionsResponse['sentence_bounds'] = FALLBACK_SENTENCE_BOUNDS,
): number {
  const coerced = Number.isFinite(value) ? value : DEFAULT_GENERATOR_STATE.num_sentences;
  return Math.max(bounds.min, Math.min(bounds.max, Math.trunc(coerced)));
}

export function resolveGeneratorDefaults({
  previous,
  options,
  editedFields,
}: {
  previous: GeneratorFormState;
  options: BookCreationOptionsResponse;
  editedFields: Iterable<GeneratorEditedField>;
}): GeneratorFormState {
  const edited = editedFields instanceof Set ? editedFields : new Set(editedFields);
  const nextBounds = options.sentence_bounds;
  const nextDefaultCount = normalizeSentenceCount(nextBounds.default, nextBounds);

  return {
    ...previous,
    topic: edited.has('topic') ? previous.topic : options.defaults.topic || DEFAULT_GENERATOR_STATE.topic,
    book_name: edited.has('book_name')
      ? previous.book_name
      : options.defaults.book_name || DEFAULT_GENERATOR_STATE.book_name,
    genre: edited.has('genre') ? previous.genre : options.defaults.genre || DEFAULT_GENERATOR_STATE.genre,
    author: edited.has('author') ? previous.author : options.defaults.author || DEFAULT_GENERATOR_STATE.author,
    num_sentences: edited.has('num_sentences')
      ? normalizeSentenceCount(previous.num_sentences, nextBounds)
      : nextDefaultCount,
  };
}

export function buildGeneratedSourceImageDefaults(options: BookCreationOptionsResponse | null) {
  return {
    add_images: options?.generated_source_defaults.add_images ?? false,
    image_prompt_pipeline: options?.generated_source_defaults.image_prompt_pipeline ?? 'prompt_plan',
    image_style_template: options?.generated_source_defaults.image_style_template ?? 'wireframe',
    image_prompt_context_sentences: options?.generated_source_defaults.image_prompt_context_sentences ?? 0,
    image_width: options?.generated_source_defaults.image_width ?? '256',
    image_height: options?.generated_source_defaults.image_height ?? '256',
  };
}

function normalizeDefaultTargetLanguages(
  defaults: BookCreationOptionsResponse['defaults'],
): string[] | undefined {
  const candidates = [
    ...(defaults.target_languages ?? []),
    ...(defaults.output_languages ?? []),
    defaults.output_language,
  ];
  const seen = new Set<string>();
  const languages: string[] = [];
  for (const candidate of candidates) {
    const language = candidate?.trim();
    if (!language) {
      continue;
    }
    const key = language.toLowerCase();
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    languages.push(language);
  }
  return languages.length > 0 ? languages : undefined;
}

export function buildGeneratedSourcePipelineDefaults(
  options: BookCreationOptionsResponse | null,
): BookNarrationPipelineDefaults | null {
  if (!options) {
    return null;
  }
  const pipelineDefaults = options.pipeline_defaults;
  const promptDefaults = options.defaults;
  return {
    ...pipelineDefaults,
    input_language: promptDefaults.input_language || undefined,
    target_languages: normalizeDefaultTargetLanguages(promptDefaults),
    selected_voice: promptDefaults.voice || pipelineDefaults.selected_voice,
  };
}

export function buildBookGenerationJobRequest({
  generatorState,
  pipelinePayload,
  sentenceBounds,
  forcedBaseOutput,
}: {
  generatorState: GeneratorFormState;
  pipelinePayload: PipelineRequestPayload;
  sentenceBounds: BookCreationOptionsResponse['sentence_bounds'];
  forcedBaseOutput: string;
}): BookGenerationJobRequest {
  const trimmedTopic = generatorState.topic.trim();
  const trimmedBookName = generatorState.book_name.trim();
  const trimmedGenre = generatorState.genre.trim();
  const trimmedAuthor = generatorState.author.trim() || 'Me';
  const sentenceCount = normalizeSentenceCount(generatorState.num_sentences, sentenceBounds);
  const normalizedBaseOutput = deriveBaseOutputName(trimmedBookName || trimmedTopic || forcedBaseOutput);

  return {
    generator: {
      topic: trimmedTopic,
      book_name: trimmedBookName,
      genre: trimmedGenre,
      author: trimmedAuthor,
      num_sentences: sentenceCount,
      input_language: pipelinePayload.inputs.input_language,
      output_language:
        (pipelinePayload.inputs.target_languages && pipelinePayload.inputs.target_languages[0]) ||
        pipelinePayload.inputs.input_language,
      voice: pipelinePayload.inputs.selected_voice || null,
    },
    pipeline: {
      ...pipelinePayload,
      inputs: {
        ...pipelinePayload.inputs,
        base_output_file: normalizedBaseOutput,
      },
    },
  };
}
