import { describe, expect, it } from 'vitest';
import type { PipelineStatusResponse } from '../../api/dtos';
import { BOOK_NARRATION_SECTION_META, DEFAULT_FORM_STATE } from '../book-narration/bookNarrationFormDefaults';
import {
  applyBookNarrationForcedBaseOutput,
  applyBookNarrationGeneratedSourceDefaults,
  applyBookNarrationImageDefaults,
  applyBookNarrationPrefillInputFile,
  applyBookNarrationPrefillParameters,
  applyBookNarrationTemplateFormState,
  applyBookNarrationVoiceOverride,
  buildBookNarrationInitialFormState,
  applyBookNarrationFieldChange,
  canApplyBookNarrationFieldChange,
  compactBookNarrationPipelineDefaults,
  extractBookMetadata,
  normalizeBookNarrationPath,
  normalizeTargetLanguages,
  preserveBookNarrationUserEditedFields,
  resolveBookNarrationMissingRequirements,
  resolveBookNarrationSharedPreferenceUpdate,
  resolveBookNarrationTemplateFormStateApplication,
  resolveBookNarrationVoiceOverrideLanguages,
  resolveBookNarrationSubmitPresentation,
  resolveBookNarrationSectionMeta,
  resolveLatestBookNarrationJobSelection,
  resolveLatestBookNarrationJobSettings,
  resolveStartFromNarrationHistory,
  restoreBookNarrationEditedImageDefaults,
  selectPreferredPipelineEbook,
  targetLanguageFieldsFromLanguages,
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
  it('selects the latest modified pipeline EPUB entry for default narration source', () => {
    expect(
      selectPreferredPipelineEbook([
        {
          name: 'folder',
          path: '/books/folder',
          type: 'directory',
          modified_at: '2026-06-24T12:00:00Z',
        },
        {
          name: 'older.epub',
          path: '/books/z-older.epub',
          type: 'file',
          modified_at: '2026-06-23T12:00:00Z',
        },
        {
          name: 'newer.epub',
          path: '/books/a-newer.epub',
          type: 'file',
          modified_at: '2026-06-24T12:00:00Z',
        },
      ]),
    )?.toMatchObject({
      path: '/books/a-newer.epub',
    });
  });

  it('breaks pipeline EPUB modified-time ties by path', () => {
    expect(
      selectPreferredPipelineEbook([
        {
          name: 'z.epub',
          path: '/books/z.epub',
          type: 'file',
          modified_at: '2026-06-24T12:00:00Z',
        },
        {
          name: 'a.epub',
          path: '/books/a.epub',
          type: 'file',
          modified_at: '2026-06-24T12:00:00Z',
        },
      ]),
    )?.toMatchObject({
      path: '/books/a.epub',
    });
  });

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

describe('bookNarrationFormUtils voice override languages', () => {
  it('deduplicates source and target languages by resolved catalog code', () => {
    expect(
      resolveBookNarrationVoiceOverrideLanguages(' English ', [
        'Arabic',
        'english',
        'German',
        'Arabic',
      ]),
    ).toEqual([
      { label: 'English', code: 'en' },
      { label: 'Arabic', code: 'ar' },
      { label: 'German', code: 'de' },
    ]);
  });

  it('keeps uncataloged language labels selectable for manual voice overrides', () => {
    expect(
      resolveBookNarrationVoiceOverrideLanguages('', [
        'Custom Dialect',
        ' custom dialect ',
        'Another Variant',
      ]),
    ).toEqual([
      { label: 'Custom Dialect', code: null },
      { label: 'Another Variant', code: null },
    ]);
  });
});

describe('bookNarrationFormUtils voice override edits', () => {
  it('adds and trims a voice override without mutating the previous state', () => {
    const previous = {
      ...DEFAULT_FORM_STATE,
      voice_overrides: { ar: 'old-arabic-voice' },
    };

    const next = applyBookNarrationVoiceOverride(previous, ' de ', '  Anna  ');

    expect(next).not.toBe(previous);
    expect(next.voice_overrides).toEqual({
      ar: 'old-arabic-voice',
      de: 'Anna',
    });
    expect(previous.voice_overrides).toEqual({ ar: 'old-arabic-voice' });
  });

  it('removes a voice override when the new voice is blank', () => {
    const previous = {
      ...DEFAULT_FORM_STATE,
      voice_overrides: { de: 'Anna', ar: 'Majed' },
    };

    expect(applyBookNarrationVoiceOverride(previous, ' de ', '   ')).toMatchObject({
      voice_overrides: { ar: 'Majed' },
    });
  });

  it('returns the same state for blank language codes and unchanged overrides', () => {
    const previous = {
      ...DEFAULT_FORM_STATE,
      voice_overrides: { de: 'Anna' },
    };

    expect(applyBookNarrationVoiceOverride(previous, '   ', 'Thomas')).toBe(previous);
    expect(applyBookNarrationVoiceOverride(previous, 'de', ' Anna ')).toBe(previous);
    expect(applyBookNarrationVoiceOverride(previous, 'it', '   ')).toBe(previous);
  });
});

describe('bookNarrationFormUtils source/output state updates', () => {
  it('resets generated-source sentence bounds without mutating previous state', () => {
    const previous = {
      ...DEFAULT_FORM_STATE,
      start_sentence: 34,
      end_sentence: '89',
    };

    const next = applyBookNarrationGeneratedSourceDefaults(previous);

    expect(next).not.toBe(previous);
    expect(next).toMatchObject({
      start_sentence: 1,
      end_sentence: '',
    });
    expect(previous).toMatchObject({
      start_sentence: 34,
      end_sentence: '89',
    });
  });

  it('keeps generated-source state identity when sentence bounds are already reset', () => {
    const previous = {
      ...DEFAULT_FORM_STATE,
      start_sentence: 1,
      end_sentence: '',
    };

    expect(applyBookNarrationGeneratedSourceDefaults(previous)).toBe(previous);
  });

  it('applies forced output names and preserves identity for unchanged or absent values', () => {
    const previous = {
      ...DEFAULT_FORM_STATE,
      base_output_file: 'draft-output',
    };

    expect(applyBookNarrationForcedBaseOutput(previous, 'forced-output')).toMatchObject({
      base_output_file: 'forced-output',
    });
    expect(applyBookNarrationForcedBaseOutput(previous, 'draft-output')).toBe(previous);
    expect(applyBookNarrationForcedBaseOutput(previous, null)).toBe(previous);
    expect(applyBookNarrationForcedBaseOutput(previous, undefined)).toBe(previous);
  });

  it('blocks direct output field edits when an output name is forced', () => {
    expect(canApplyBookNarrationFieldChange('base_output_file', 'forced-output')).toBe(false);
    expect(canApplyBookNarrationFieldChange('input_file', 'forced-output')).toBe(true);
    expect(canApplyBookNarrationFieldChange('base_output_file', null)).toBe(true);
    expect(canApplyBookNarrationFieldChange('base_output_file', undefined)).toBe(true);
  });

  it('applies generic form field changes with identity preservation', () => {
    const previous = {
      ...DEFAULT_FORM_STATE,
      input_language: 'English',
      target_languages: ['Arabic'],
    };

    expect(applyBookNarrationFieldChange(previous, 'input_language', 'English')).toBe(previous);
    expect(applyBookNarrationFieldChange(previous, 'input_language', 'Spanish')).toMatchObject({
      input_language: 'Spanish',
    });

    const nextTargets = ['German'];
    const next = applyBookNarrationFieldChange(previous, 'target_languages', nextTargets);
    expect(next).not.toBe(previous);
    expect(next.target_languages).toBe(nextTargets);
  });
});

describe('bookNarrationFormUtils template form-state application', () => {
  it('normalizes template target languages and resolves shared preference updates', () => {
    const { appliedFormState, sharedPreferenceUpdate } =
      resolveBookNarrationTemplateFormStateApplication({
        formState: {
          input_language: 'Spanish',
          target_languages: [' German ', 'French', 'german', 'Italian'],
          enable_lookup_cache: true,
        },
        sharedTargetLanguages: ['Arabic'],
      });

    expect(appliedFormState).toMatchObject({
      input_language: 'Spanish',
      target_languages: ['German'],
      custom_target_languages: 'French, Italian',
      enable_lookup_cache: true,
    });
    expect(sharedPreferenceUpdate).toEqual({
      inputLanguage: 'Spanish',
      targetLanguages: ['German', 'French', 'Italian'],
      enableLookupCache: true,
    });
  });

  it('preserves existing shared targets when normalized template targets match', () => {
    const { sharedPreferenceUpdate } = resolveBookNarrationTemplateFormStateApplication({
      formState: {
        target_languages: ['German', 'French'],
      },
      sharedTargetLanguages: ['German', 'French'],
    });

    expect(sharedPreferenceUpdate).toBeNull();
  });

  it('merges template state while keeping forced output names authoritative', () => {
    const previous = {
      ...DEFAULT_FORM_STATE,
      input_file: '/books/old.epub',
      base_output_file: 'previous-output',
      input_language: 'English',
    };

    expect(
      applyBookNarrationTemplateFormState(
        previous,
        {
          input_file: '/books/template.epub',
          base_output_file: 'template-output',
          input_language: 'Spanish',
        },
        'forced-output',
      ),
    ).toMatchObject({
      input_file: '/books/template.epub',
      base_output_file: 'forced-output',
      input_language: 'Spanish',
    });

    expect(
      applyBookNarrationTemplateFormState(previous, { input_file: '/books/template.epub' }, null),
    ).toMatchObject({
      input_file: '/books/template.epub',
      base_output_file: 'previous-output',
    });
  });
});

describe('bookNarrationFormUtils prefill helpers', () => {
  it('applies prefilled input files with derived output, cached metadata, and history start', () => {
    const previous = {
      ...DEFAULT_FORM_STATE,
      input_file: '/books/old-title.epub',
      base_output_file: 'old-title',
      book_metadata: '{}',
      start_sentence: 1,
    };

    expect(
      applyBookNarrationPrefillInputFile({
        previous,
        inputFile: '/books/New Title.epub',
        cachedBookMetadata: '{ "book_title": "New Title" }',
        suggestedStartSentence: 44,
      }),
    ).toMatchObject({
      input_file: '/books/New Title.epub',
      base_output_file: 'new-title',
      book_metadata: '{ "book_title": "New Title" }',
      start_sentence: 44,
    });
  });

  it('preserves manually edited output names and honors forced output names for prefilled inputs', () => {
    const previous = {
      ...DEFAULT_FORM_STATE,
      input_file: '/books/old-title.epub',
      base_output_file: 'manual-output',
      book_metadata: '{ "book_title": "Old" }',
      start_sentence: 12,
    };

    expect(
      applyBookNarrationPrefillInputFile({
        previous,
        inputFile: '/books/new-title.epub',
      }),
    ).toMatchObject({
      input_file: '/books/new-title.epub',
      base_output_file: 'manual-output',
      book_metadata: '{}',
      start_sentence: DEFAULT_FORM_STATE.start_sentence,
    });

    expect(
      applyBookNarrationPrefillInputFile({
        previous,
        inputFile: '/books/new-title.epub',
        forcedBaseOutputFile: 'forced-output',
      }),
    ).toMatchObject({
      base_output_file: 'forced-output',
    });
  });

  it('keeps prefilled input state identity when the input path is unchanged', () => {
    const previous = {
      ...DEFAULT_FORM_STATE,
      input_file: '/books/current.epub',
      base_output_file: 'current',
    };

    expect(
      applyBookNarrationPrefillInputFile({
        previous,
        inputFile: '/books/current.epub',
        cachedBookMetadata: '{ "book_title": "Ignored" }',
        suggestedStartSentence: 99,
      }),
    ).toBe(previous);
  });

  it('maps rerun parameters into form state while preserving additional target languages', () => {
    const previous = {
      ...DEFAULT_FORM_STATE,
      input_file: '/old/input.epub',
      base_output_file: 'old-output',
      book_metadata: '{\n  "book_title": "Stale Book"\n}',
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
        target_languages: [' ', ' German ', 'French', 'german', 'Italian'],
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
      book_metadata: '{}',
      input_language: 'Spanish',
      target_languages: ['German'],
      custom_target_languages: 'French, Italian',
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
      book_metadata: '{\n  "book_title": "Keep Book"\n}',
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
      book_metadata: '{\n  "book_title": "Keep Book"\n}',
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
        target_languages: [' German ', '', 'French', 'german', null, 'Arabic'],
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

  it('splits normalized target languages into primary and additional form fields', () => {
    expect(targetLanguageFieldsFromLanguages([' German ', 'French', 'german', '', 'Italian'])).toEqual({
      target_languages: ['German'],
      custom_target_languages: 'French, Italian',
    });
  });

  it('builds initial form state from shared language and lookup defaults', () => {
    expect(
      buildBookNarrationInitialFormState({
        forcedBaseOutputFile: 'forced-output',
        sharedInputLanguage: 'Turkish',
        sharedTargetLanguages: ['Dutch', 'Italian', 'dutch'],
        sharedEnableLookupCache: false,
      }),
    ).toMatchObject({
      base_output_file: 'forced-output',
      input_language: 'Turkish',
      target_languages: ['Dutch'],
      custom_target_languages: 'Italian',
      enable_lookup_cache: false,
    });
  });

  it('builds isolated initial form collections from defaults', () => {
    const first = buildBookNarrationInitialFormState();
    const second = buildBookNarrationInitialFormState();

    first.target_languages.push('German');
    first.image_api_base_urls.push('http://example.invalid');
    first.voice_overrides.de = 'voice';

    expect(second.target_languages).toEqual(DEFAULT_FORM_STATE.target_languages);
    expect(second.image_api_base_urls).toEqual(DEFAULT_FORM_STATE.image_api_base_urls);
    expect(second.voice_overrides).toEqual({});
  });

  it('resolves shared language preference updates from direct form edits', () => {
    expect(
      resolveBookNarrationSharedPreferenceUpdate({
        key: 'input_language',
        value: 'Turkish',
        formState: DEFAULT_FORM_STATE,
        sharedTargetLanguages: DEFAULT_FORM_STATE.target_languages,
      }),
    ).toEqual({ inputLanguage: 'Turkish' });

    expect(
      resolveBookNarrationSharedPreferenceUpdate({
        key: 'enable_lookup_cache',
        value: false,
        formState: DEFAULT_FORM_STATE,
        sharedTargetLanguages: DEFAULT_FORM_STATE.target_languages,
      }),
    ).toEqual({ enableLookupCache: false });
  });

  it('combines primary and manual targets for shared language preferences', () => {
    const formState = {
      ...DEFAULT_FORM_STATE,
      target_languages: ['Dutch'],
      custom_target_languages: 'Italian, dutch',
    };

    expect(
      resolveBookNarrationSharedPreferenceUpdate({
        key: 'target_languages',
        value: ['German', 'Dutch'],
        formState,
        sharedTargetLanguages: ['Dutch'],
      }),
    ).toEqual({ targetLanguages: ['German', 'Dutch', 'Italian'] });

    expect(
      resolveBookNarrationSharedPreferenceUpdate({
        key: 'custom_target_languages',
        value: 'Italian, German',
        formState,
        sharedTargetLanguages: ['Dutch'],
      }),
    ).toEqual({ targetLanguages: ['Dutch', 'Italian', 'German'] });
  });

  it('does not emit shared target preference updates when normalized targets already match', () => {
    expect(
      resolveBookNarrationSharedPreferenceUpdate({
        key: 'custom_target_languages',
        value: ' Italian ',
        formState: {
          ...DEFAULT_FORM_STATE,
          target_languages: ['Dutch'],
        },
        sharedTargetLanguages: ['Dutch', 'Italian'],
      }),
    ).toBeNull();
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

  it('builds submit presentation state from section copy, requirements, and intake state', () => {
    expect(
      resolveBookNarrationSubmitPresentation({
        activeSection: 'language',
        sectionMeta: BOOK_NARRATION_SECTION_META,
        formState: {
          ...DEFAULT_FORM_STATE,
          input_file: '',
          base_output_file: '',
          target_languages: [],
        },
        normalizedTargetLanguages: [],
        isGeneratedSource: false,
        chapterSelectionMode: 'chapters',
        hasChapterSelection: false,
        isSubmitting: false,
        isIntakeAtCapacity: false,
        submitLabel: 'Start narration',
      }),
    ).toMatchObject({
      headerTitle: BOOK_NARRATION_SECTION_META.language.title,
      headerDescription: BOOK_NARRATION_SECTION_META.language.description,
      missingRequirements: [
        'an input EPUB',
        'a base output path',
        'at least one target language',
        'a chapter selection',
      ],
      hasMissingRequirements: true,
      missingRequirementText:
        'an input EPUB, a base output path, at least one target language, and a chapter selection',
      isSubmitDisabled: true,
      submitText: 'Start narration',
    });
  });

  it('uses the default submit label and disables for capacity when requirements are satisfied', () => {
    expect(
      resolveBookNarrationSubmitPresentation({
        activeSection: 'submit',
        sectionMeta: {
          ...BOOK_NARRATION_SECTION_META,
          submit: { title: '', description: '' },
        },
        formState: {
          ...DEFAULT_FORM_STATE,
          input_file: '/books/source.epub',
          base_output_file: 'book-output',
        },
        normalizedTargetLanguages: ['Arabic'],
        isGeneratedSource: false,
        chapterSelectionMode: 'range',
        hasChapterSelection: false,
        isSubmitting: false,
        isIntakeAtCapacity: true,
        submitLabel: null,
      }),
    ).toMatchObject({
      headerTitle: '',
      headerDescription: '',
      missingRequirements: [],
      hasMissingRequirements: false,
      missingRequirementText: '',
      isSubmitDisabled: true,
      submitText: 'Submit job',
    });
  });
});
