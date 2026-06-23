import { describe, expect, it } from 'vitest';
import type { PipelineStatusResponse } from '../../api/dtos';
import { DEFAULT_FORM_STATE } from '../book-narration/bookNarrationFormDefaults';
import {
  applyBookNarrationPrefillParameters,
  normalizeBookNarrationPath,
  resolveLatestBookNarrationJobSelection,
  resolveLatestBookNarrationJobSettings,
  resolveStartFromNarrationHistory,
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
