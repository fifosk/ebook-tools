import { describe, expect, it } from 'vitest';
import type { PipelineStatusResponse } from '../../api/dtos';
import { BOOK_NARRATION_SECTION_META, DEFAULT_FORM_STATE } from '../book-narration/bookNarrationFormDefaults';
import {
  applyBookNarrationImageDefaults,
  applyBookNarrationPrefillParameters,
  compactBookNarrationPipelineDefaults,
  extractBookMetadata,
  normalizeBookNarrationPath,
  normalizeTargetLanguages,
  preserveBookNarrationUserEditedFields,
  resolveBookNarrationMissingRequirements,
  resolveBookNarrationSectionMeta,
  resolveLatestBookNarrationJobSelection,
  resolveLatestBookNarrationJobSettings,
  resolveStartFromNarrationHistory,
  restoreBookNarrationEditedImageDefaults,
  targetLanguagesFromBookNarrationConfig,
} from '../book-narration/bookNarrationFormUtils';

function makeJob(
  id: string,
  createdAt: string,
  parameters: PipelineStatusResponse['parameters'],
  jobType: PipelineStatusResponse['job_type'] = 'pipeline',
): PipelineStatusResponse {
  return {
    job_id: id,
    job_type: jobType,
    status: 'completed',
    created_at: createdAt,
    started_at: null,
    completed_at: createdAt,
    result: null,
    generated_files: null,
    error: null,
    parameters,
    latest_event: null,
    tuning: null,
    user_id: 'user',
  };
}

describe('bookNarrationFormUtils recent-job helpers', () => {
  it('normalizes paths for recent-job matching', () => {
    expect(normalizeBookNarrationPath(' /Volumes/Books/Example.EPUB/// ')).toBe('/volumes/books/example.epub');
    expect(normalizeBookNarrationPath('')).toBeNull();
    expect(normalizeBookNarrationPath(null)).toBeNull();
  });

  it('resolves start sentence from the newest matching narration job history', () => {
    const jobs = [
      makeJob('old', '2026-06-20T10:00:00Z', {
        input_file: '/books/example.epub',
        end_sentence: 30,
      }),
      makeJob('subtitle', '2026-06-22T10:00:00Z', {
        input_file: '/books/example.epub',
        end_sentence: 300,
      }, 'subtitle'),
      makeJob('new', '2026-06-21T10:00:00Z', {
        input_file: '/BOOKS/EXAMPLE.EPUB/',
        start_sentence: 12,
      }),
    ];

    expect(resolveStartFromNarrationHistory('/books/example.epub', jobs)).toBe(7);
  });

  it('clamps inferred start sentence to the first sentence', () => {
    const jobs = [
      makeJob('early', '2026-06-21T10:00:00Z', {
        input_file: '/books/start.epub',
        end_sentence: 3,
      }),
    ];

    expect(resolveStartFromNarrationHistory('/books/start.epub', jobs)).toBe(1);
  });

  it('returns the newest reusable input/base selection', () => {
    const jobs = [
      makeJob('without-files', '2026-06-23T10:00:00Z', {}),
      makeJob('subtitle', '2026-06-23T11:00:00Z', {
        input_file: '/subtitles/clip.ass',
      }, 'subtitle'),
      makeJob('older', '2026-06-22T10:00:00Z', {
        input_file: '/books/older.epub',
        base_output_file: 'older-output',
      }),
      makeJob('newer', '2026-06-23T09:00:00Z', {
        input_file: '/books/newer.epub',
        base_output_file: 'newer-output',
      }),
    ];

    expect(resolveLatestBookNarrationJobSelection(jobs)).toEqual({
      input: '/books/newer.epub',
      base: 'newer-output',
    });
  });

  it('returns newest reusable language and lookup-cache settings', () => {
    const jobs = [
      makeJob('older', '2026-06-22T10:00:00Z', {
        input_language: 'English',
        target_languages: ['Arabic'],
        enable_lookup_cache: true,
      }),
      makeJob('newer', '2026-06-23T09:00:00Z', {
        source_language: 'Spanish',
        target_languages: ['German', 'French'],
        enable_lookup_cache: false,
      }),
    ];

    expect(resolveLatestBookNarrationJobSettings(jobs)).toEqual({
      inputLanguage: 'Spanish',
      targetLanguages: ['German', 'French'],
      enableLookupCache: false,
    });
  });
});

describe('bookNarrationFormUtils prefill helpers', () => {
  it('maps rerun parameters into form state using the current single-target language contract', () => {
    const previous = {
      ...DEFAULT_FORM_STATE,
      input_file: '/old/input.epub',
      base_output_file: 'old-output',
      custom_target_languages: 'Italian',
      include_transliteration: true,
      add_images: false,
      voice_overrides: { ar: 'old-voice' },
    };

    const next = applyBookNarrationPrefillParameters(
      previous,
      {
        input_file: ' /books/new.epub ',
        base_output_file: ' rerun-output ',
        input_language: ' Spanish ',
        target_languages: [' ', ' German ', 'French'],
        start_sentence: 12,
        end_sentence: 34,
        sentences_per_output_file: 8,
        audio_mode: ' 2 ',
        audio_bitrate_kbps: 129.9,
        selected_voice: ' macOS-auto ',
        enable_transliteration: false,
        translation_provider: ' googletrans ',
        translation_batch_size: 0,
        transliteration_mode: ' python ',
        transliteration_model: ' model-a ',
        tempo: 1.25,
        add_images: true,
        voice_overrides: { es: 'voice-es' },
      },
      'forced-output',
    );

    expect(next).toMatchObject({
      input_file: '/books/new.epub',
      base_output_file: 'forced-output',
      input_language: 'Spanish',
      target_languages: ['German'],
      custom_target_languages: '',
      start_sentence: 12,
      end_sentence: '34',
      sentences_per_output_file: 8,
      audio_mode: '2',
      audio_bitrate_kbps: '129',
      selected_voice: 'macOS-auto',
      include_transliteration: false,
      translation_provider: 'googletrans',
      translation_batch_size: 1,
      transliteration_mode: 'python',
      transliteration_model: 'model-a',
      tempo: 1.25,
      add_images: true,
      voice_overrides: { es: 'voice-es' },
    });
  });

  it('keeps previous values when rerun parameters are blank or invalid', () => {
    const previous = {
      ...DEFAULT_FORM_STATE,
      input_file: '/old/input.epub',
      base_output_file: 'old-output',
      input_language: 'English',
      target_languages: ['Arabic'],
      start_sentence: 10,
      end_sentence: '20',
      audio_bitrate_kbps: '96',
      voice_overrides: { ar: 'old-voice' },
    };

    const next = applyBookNarrationPrefillParameters(
      previous,
      {
        input_file: '   ',
        base_output_file: '',
        input_language: '',
        target_languages: [' '],
        start_sentence: Number.NaN,
        end_sentence: null,
        audio_bitrate_kbps: null,
        selected_voice: '',
        translation_batch_size: Number.NaN,
        transliteration_model: ' ',
      },
      null,
    );

    expect(next).toMatchObject({
      input_file: '/old/input.epub',
      base_output_file: 'old-output',
      input_language: 'English',
      target_languages: ['Arabic'],
      custom_target_languages: '',
      start_sentence: 10,
      end_sentence: '20',
      audio_bitrate_kbps: '96',
      voice_overrides: { ar: 'old-voice' },
    });
  });
});

describe('bookNarrationFormUtils form state helpers', () => {
  it('compacts optional pipeline defaults into a config map without nullish values', () => {
    expect(compactBookNarrationPipelineDefaults(null)).toBeNull();
    expect(compactBookNarrationPipelineDefaults({})).toBeNull();

    expect(
      compactBookNarrationPipelineDefaults({
        input_language: 'Spanish',
        target_languages: ['German'],
        audio_bitrate_kbps: null,
        output_pdf: false,
        tempo: 0,
      }),
    ).toEqual({
      input_language: 'Spanish',
      target_languages: ['German'],
      output_pdf: false,
      tempo: 0,
    });
  });

  it('normalizes target languages from config while preserving first-seen order', () => {
    expect(targetLanguagesFromBookNarrationConfig({ target_languages: 'German' })).toEqual([]);
    expect(
      targetLanguagesFromBookNarrationConfig({
        target_languages: [' German ', '', 'French', 'German', null, 'Arabic'],
      }),
    ).toEqual(['German', 'French', 'Arabic']);
  });

  it('normalizes manually combined target languages while preserving unique order', () => {
    expect(normalizeTargetLanguages([' German ', 'French', 'german', '', 'Arabic'])).toEqual([
      'German',
      'French',
      'Arabic',
    ]);
  });

  it('extracts Web-aligned genre and ISBN metadata from flat defaults', () => {
    expect(
      extractBookMetadata({
        book_title: 'Example Book',
        book_author: 'Jane Doe',
        book_genre: 'Adventure',
        book_genres: ['Adventure', 'Fantasy'],
        book_language: 'eng',
        book_isbn: '9780140328721',
        isbn: 'legacy-isbn',
        genre: 'legacy-genre',
        language: 'legacy-language',
      }),
    ).toEqual({
      book_title: 'Example Book',
      book_author: 'Jane Doe',
      book_genre: 'Adventure',
      book_genres: ['Adventure', 'Fantasy'],
      book_language: 'eng',
      book_isbn: '9780140328721',
      isbn: 'legacy-isbn',
      genre: 'legacy-genre',
      language: 'legacy-language',
    });
  });

  it('applies backend image defaults while preserving user-edited image fields', () => {
    const previous = {
      ...DEFAULT_FORM_STATE,
      add_images: false,
      image_prompt_pipeline: 'prompt_plan',
      image_style_template: 'comics',
      image_prompt_context_sentences: 2,
      image_width: '',
      image_height: '',
    };

    const next = applyBookNarrationImageDefaults({
      state: previous,
      imageDefaults: {
        add_images: true,
        image_prompt_pipeline: 'visual-canon',
        image_style_template: 'watercolor',
        image_prompt_context_sentences: 99,
        image_width: '1024',
        image_height: '768',
      },
      editedFields: new Set(['image_width']),
    });

    expect(next).toMatchObject({
      add_images: true,
      image_prompt_pipeline: 'visual_canon',
      image_style_template: 'watercolor',
      image_prompt_context_sentences: 50,
      image_width: '',
      image_height: '768',
    });
  });

  it('does not apply add-images defaults when rerun prefill already controls that field', () => {
    const previous = {
      ...DEFAULT_FORM_STATE,
      add_images: false,
      image_prompt_pipeline: 'prompt_plan',
    };

    const next = applyBookNarrationImageDefaults({
      state: previous,
      imageDefaults: {
        add_images: true,
        image_prompt_pipeline: 'canon',
        image_style_template: previous.image_style_template,
        image_prompt_context_sentences: previous.image_prompt_context_sentences,
        image_width: previous.image_width,
        image_height: previous.image_height,
      },
      editedFields: [],
      allowAddImagesDefault: false,
    });

    expect(next.add_images).toBe(false);
    expect(next.image_prompt_pipeline).toBe('visual_canon');
  });

  it('returns the original form state object when image defaults do not change values', () => {
    const previous = {
      ...DEFAULT_FORM_STATE,
      add_images: true,
      image_prompt_pipeline: 'visual_canon',
      image_style_template: 'watercolor',
      image_prompt_context_sentences: 8,
      image_width: '512',
      image_height: '768',
    };

    const next = applyBookNarrationImageDefaults({
      state: previous,
      imageDefaults: {
        add_images: true,
        image_prompt_pipeline: 'visual_canon',
        image_style_template: 'watercolor',
        image_prompt_context_sentences: 8,
        image_width: '512',
        image_height: '768',
      },
      editedFields: [],
    });

    expect(next).toBe(previous);
  });

  it('restores only edited image-default fields after config defaults are applied', () => {
    const previous = {
      ...DEFAULT_FORM_STATE,
      add_images: false,
      image_prompt_pipeline: 'prompt_plan',
      image_style_template: 'comics',
      image_prompt_context_sentences: 3,
      image_width: '256',
      image_height: '512',
    };
    const next = {
      ...previous,
      add_images: true,
      image_prompt_pipeline: 'visual_canon',
      image_style_template: 'watercolor',
      image_prompt_context_sentences: 9,
      image_width: '1024',
      image_height: '768',
    };

    const restored = restoreBookNarrationEditedImageDefaults(
      previous,
      next,
      new Set(['add_images', 'image_width', 'image_height']),
    );

    expect(restored).toMatchObject({
      add_images: false,
      image_prompt_pipeline: 'visual_canon',
      image_style_template: 'watercolor',
      image_prompt_context_sentences: 9,
      image_width: '256',
      image_height: '512',
    });
  });

  it('returns the current form state object when no edited image fields changed', () => {
    const previous = {
      ...DEFAULT_FORM_STATE,
      image_width: '512',
    };
    const next = {
      ...previous,
      input_language: 'Spanish',
    };

    expect(restoreBookNarrationEditedImageDefaults(previous, next, ['image_width'])).toBe(next);
    expect(restoreBookNarrationEditedImageDefaults(previous, next, [])).toBe(next);
  });

  it('merges section metadata overrides without mutating defaults', () => {
    const result = resolveBookNarrationSectionMeta(BOOK_NARRATION_SECTION_META, {
      source: { title: 'Pick source', description: 'Override source copy.' },
      images: { title: 'Image plan' },
    });

    expect(result.source).toEqual({
      title: 'Pick source',
      description: 'Override source copy.',
    });
    expect(result.images).toEqual({
      ...BOOK_NARRATION_SECTION_META.images,
      title: 'Image plan',
    });
    expect(BOOK_NARRATION_SECTION_META.source.title).toBe('Source');
  });

  it('preserves user-edited fields when defaults or prefill state are applied', () => {
    const previous = {
      ...DEFAULT_FORM_STATE,
      input_file: '/books/user.epub',
      base_output_file: 'user-output',
      input_language: 'English',
    };
    const next = {
      ...previous,
      input_file: '/books/prefill.epub',
      base_output_file: 'prefill-output',
      input_language: 'Spanish',
    };

    expect(preserveBookNarrationUserEditedFields(previous, next, [])).toBe(next);
    expect(preserveBookNarrationUserEditedFields(previous, next, new Set(['input_file', 'input_language']))).toMatchObject({
      input_file: '/books/user.epub',
      base_output_file: 'prefill-output',
      input_language: 'English',
    });
  });

  it('resolves missing requirements for upload and generated-source jobs', () => {
    expect(
      resolveBookNarrationMissingRequirements({
        formState: { ...DEFAULT_FORM_STATE, input_file: '', base_output_file: '', target_languages: [] },
        normalizedTargetLanguages: [],
        isGeneratedSource: false,
        chapterSelectionMode: 'chapters',
        hasChapterSelection: false,
      }),
    ).toEqual(['an input EPUB', 'a base output path', 'at least one target language', 'a chapter selection']);

    expect(
      resolveBookNarrationMissingRequirements({
        formState: { ...DEFAULT_FORM_STATE, input_file: '', base_output_file: 'generated-book' },
        normalizedTargetLanguages: ['Arabic'],
        isGeneratedSource: true,
        chapterSelectionMode: 'chapters',
        hasChapterSelection: false,
      }),
    ).toEqual([]);
  });
});
