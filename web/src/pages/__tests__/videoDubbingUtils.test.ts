import { describe, expect, it } from 'vitest';
import type { VoiceInventoryResponse, YoutubeInlineSubtitleStream } from '../../api/dtos';
import {
  buildVoiceOptions,
  resolveVideoDubPrefill,
  resolveDefaultStreamLanguages
} from '../video-dubbing/videoDubbingUtils';

function stream(
  language: string | null,
  canExtract = true
): YoutubeInlineSubtitleStream {
  return {
    index: 0,
    position: 0,
    language,
    can_extract: canExtract
  };
}

describe('videoDubbingUtils', () => {
  it('prefers English extractable subtitle streams for inline extraction defaults', () => {
    const defaults = resolveDefaultStreamLanguages([
      stream('de'),
      stream('en-US'),
      stream('en-GB', false)
    ]);

    expect(Array.from(defaults)).toEqual(['en-US']);
  });

  it('selects a single non-English extractable stream when it is the only option', () => {
    const defaults = resolveDefaultStreamLanguages([
      stream('es'),
      stream('en', false)
    ]);

    expect(Array.from(defaults)).toEqual(['es']);
  });

  it('leaves stream selection empty when multiple non-English choices are available', () => {
    const defaults = resolveDefaultStreamLanguages([
      stream('es'),
      stream('fr')
    ]);

    expect(Array.from(defaults)).toEqual([]);
  });

  it('builds target-matched voice options from backend inventory', () => {
    const inventory: VoiceInventoryResponse = {
      macos: [
        { name: 'Monica', lang: 'es-MX', quality: 'Enhanced', gender: 'Female' },
        { name: 'Daniel', lang: 'en-GB', quality: 'Enhanced', gender: 'Male' }
      ],
      piper: [
        { name: 'en_US-lessac', lang: 'en_US', quality: 'medium' },
        { name: 'es_ES-sharvard', lang: 'es_ES', quality: 'high' }
      ],
      gtts: [
        { code: 'es', name: 'Spanish' },
        { code: 'es-US', name: 'Spanish (US)' },
        { code: 'en', name: 'English' }
      ]
    };

    const options = buildVoiceOptions(inventory, 'es-MX');

    expect(options).toContainEqual({
      value: 'Monica - es-MX - (Enhanced) - Female',
      label: 'Monica (es-MX, Female, Enhanced)'
    });
    expect(options).toContainEqual({ value: 'es_ES-sharvard', label: 'Piper: es_ES-sharvard' });
    expect(options).toContainEqual({ value: 'gTTS-es', label: 'gTTS (Spanish)' });
    expect(options).not.toContainEqual({ value: 'en_US-lessac', label: 'Piper: en_US-lessac' });
    expect(options.some((option) => option.value === 'gTTS-en')).toBe(false);
  });

  it('resolves complete job parameter snapshots into video dub prefill values', () => {
    expect(
      resolveVideoDubPrefill({
        input_file: ' /video/from-input.mkv ',
        video_path: ' /video/from-video-path.mkv ',
        subtitle_path: ' /subs/show.es.ass ',
        target_languages: [' Spanish ', 'German'],
        selected_voice: ' Monica ',
        start_time_offset_seconds: 65.9,
        end_time_offset_seconds: 3723,
        original_mix_percent: 12,
        flush_sentences: 7,
        translation_batch_size: 4,
        target_height: 720,
        preserve_aspect_ratio: false,
        split_batches: false,
        llm_model: ' gpt-4.1-mini ',
        translation_provider: ' llm ',
        transliteration_mode: ' always ',
        transliteration_model: ' uroman ',
        include_transliteration: false
      })
    ).toEqual({
      videoPath: '/video/from-input.mkv',
      subtitlePath: '/subs/show.es.ass',
      targetLanguage: 'Spanish',
      voice: 'Monica',
      startOffset: '01:05',
      endOffset: '01:02:03',
      originalMixPercent: 12,
      flushSentences: 7,
      translationBatchSize: 4,
      targetHeight: 720,
      preserveAspectRatio: false,
      splitBatches: false,
      llmModel: 'gpt-4.1-mini',
      translationProvider: 'llm',
      transliterationMode: 'always',
      transliterationModel: 'uroman',
      includeTransliteration: false
    });
  });

  it('keeps video dub prefill defaults for partial snapshots', () => {
    expect(
      resolveVideoDubPrefill({
        video_path: ' /video/from-fallback.mkv ',
        target_languages: [' ', 'French'],
        selected_voice: '   ',
        original_mix_percent: Number.NaN,
        target_height: null,
        preserve_aspect_ratio: null,
        split_batches: null,
        include_transliteration: null
      })
    ).toEqual({
      videoPath: '/video/from-fallback.mkv',
      subtitlePath: undefined,
      targetLanguage: 'French',
      voice: '',
      startOffset: undefined,
      endOffset: undefined,
      originalMixPercent: 5,
      flushSentences: undefined,
      translationBatchSize: undefined,
      targetHeight: 480,
      preserveAspectRatio: true,
      splitBatches: true,
      llmModel: undefined,
      translationProvider: undefined,
      transliterationMode: undefined,
      transliterationModel: undefined,
      includeTransliteration: true
    });
  });

  it('returns null when no video dub prefill snapshot is present', () => {
    expect(resolveVideoDubPrefill(null)).toBeNull();
    expect(resolveVideoDubPrefill(undefined)).toBeNull();
  });
});
