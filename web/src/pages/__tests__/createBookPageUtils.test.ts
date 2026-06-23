import { describe, expect, it } from 'vitest';
import type { BookCreationOptionsResponse } from '../../api/createBook';
import type { PipelineRequestPayload } from '../../api/dtos';
import {
  buildBookGenerationJobRequest,
  buildGeneratedSourceImageDefaults,
  buildGeneratedSourcePipelineDefaults,
  DEFAULT_GENERATOR_STATE,
  deriveBaseOutputName,
  normalizeSentenceCount,
  resolveGeneratorDefaults,
} from '../create-book/createBookPageUtils';

const creationOptions: BookCreationOptionsResponse = {
  sentence_bounds: {
    min: 3,
    max: 120,
    default: 45,
  },
  defaults: {
    topic: 'Backend topic',
    book_name: 'Backend Book',
    genre: 'Backend genre',
    author: 'Pipeline Author',
    input_language: 'English',
    output_language: 'Arabic',
    voice: 'gTTS',
  },
  pipeline_defaults: {
    sentences_per_output_file: 12,
    audio_mode: '2',
    audio_bitrate_kbps: 128,
    written_mode: '3',
    selected_voice: 'macOS-auto',
    generate_audio: false,
    output_html: true,
    output_pdf: false,
    include_transliteration: false,
    translation_provider: 'googletrans',
    translation_batch_size: 8,
    transliteration_mode: 'python',
    enable_lookup_cache: false,
    lookup_cache_batch_size: 6,
    tempo: 1.1,
  },
  generated_source_defaults: {
    add_images: true,
    image_prompt_pipeline: 'prompt_plan',
    image_style_template: 'ink',
    image_prompt_context_sentences: 1,
    image_width: '384',
    image_height: '512',
  },
  supported_input_languages: ['English'],
  supported_output_languages: ['Arabic'],
  supported_voices: ['gTTS'],
};

describe('createBookPageUtils', () => {
  it('derives filesystem-friendly base output names', () => {
    expect(deriveBaseOutputName('  My Book: Arabic/Slovak!  ')).toBe('my-book-arabic-slovak');
    expect(deriveBaseOutputName('imports/Demo.epub')).toBe('imports-demo');
    expect(deriveBaseOutputName('   ')).toBe('generated-book');
  });

  it('applies backend generator defaults while preserving edited fields', () => {
    const resolved = resolveGeneratorDefaults({
      previous: {
        ...DEFAULT_GENERATOR_STATE,
        topic: '',
        book_name: 'Edited title',
        num_sentences: 999,
      },
      options: creationOptions,
      editedFields: ['topic', 'book_name', 'num_sentences'],
    });

    expect(resolved.topic).toBe('');
    expect(resolved.book_name).toBe('Edited title');
    expect(resolved.genre).toBe('Backend genre');
    expect(resolved.author).toBe('Pipeline Author');
    expect(resolved.num_sentences).toBe(120);
  });

  it('normalizes generated source defaults from backend options', () => {
    expect(buildGeneratedSourceImageDefaults(creationOptions)).toEqual({
      add_images: true,
      image_prompt_pipeline: 'prompt_plan',
      image_style_template: 'ink',
      image_prompt_context_sentences: 1,
      image_width: '384',
      image_height: '512',
    });
    expect(buildGeneratedSourcePipelineDefaults(creationOptions)).toMatchObject({
      input_language: 'English',
      target_languages: ['Arabic'],
      selected_voice: 'gTTS',
      translation_provider: 'googletrans',
      enable_lookup_cache: false,
    });
  });

  it('builds generated book job requests with trimmed generator values and clamped counts', () => {
    const pipelinePayload: PipelineRequestPayload = {
      config: {},
      environment_overrides: {},
      pipeline_overrides: {},
      inputs: {
        input_file: 'generated/source.epub',
        base_output_file: 'ignored',
        input_language: 'English',
        target_languages: ['Arabic'],
        sentences_per_output_file: 12,
        start_sentence: 1,
        end_sentence: null,
        stitch_full: true,
        generate_audio: true,
        audio_mode: '2',
        written_mode: '3',
        selected_voice: 'gTTS',
        output_html: true,
        output_pdf: false,
        add_images: false,
        include_transliteration: true,
        tempo: 1,
        book_metadata: {},
      },
      correlation_id: 'web-create-book',
    };

    const payload = buildBookGenerationJobRequest({
      generatorState: {
        topic: '  Portable clients  ',
        book_name: ' Native Creation ',
        genre: ' technical ',
        author: ' ',
        num_sentences: 999,
      },
      pipelinePayload,
      sentenceBounds: creationOptions.sentence_bounds,
      forcedBaseOutput: 'fallback',
    });

    expect(payload.generator).toMatchObject({
      topic: 'Portable clients',
      book_name: 'Native Creation',
      genre: 'technical',
      author: 'Me',
      num_sentences: 120,
      input_language: 'English',
      output_language: 'Arabic',
      voice: 'gTTS',
    });
    expect(payload.pipeline.inputs.base_output_file).toBe('native-creation');
    expect(normalizeSentenceCount(Number.NaN, creationOptions.sentence_bounds)).toBe(30);
  });
});
