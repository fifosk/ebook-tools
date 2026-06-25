import { describe, expect, it } from 'vitest';
import type { PipelineStatusResponse } from '../../api/dtos';
import { buildJobParameterEntries } from '../job-progress/jobProgressParameters';

function status(overrides: Partial<PipelineStatusResponse>): PipelineStatusResponse {
  return {
    job_id: 'job-parameters',
    job_type: 'pipeline',
    status: 'completed',
    created_at: '2026-06-25T08:00:00Z',
    started_at: '2026-06-25T08:01:00Z',
    completed_at: '2026-06-25T08:02:00Z',
    result: null,
    error: null,
    latest_event: null,
    tuning: null,
    ...overrides,
  };
}

function valuesByKey(entries: ReturnType<typeof buildJobParameterEntries>): Map<string, string> {
  return new Map(entries.map((entry) => [entry.key, String(entry.value)]));
}

describe('buildJobParameterEntries', () => {
  it('summarizes book pipeline language, model, image, fallback, and voice settings', () => {
    const entries = valuesByKey(
      buildJobParameterEntries(
        status({
          parameters: {
            target_languages: ['Spanish', 'French'],
            start_sentence: 12,
            end_sentence: 48,
            llm_model: 'ollama_cloud:qwen3:30b',
            translation_provider: 'llm',
            translation_batch_size: 8,
            transliteration_mode: 'default',
            transliteration_module: 'icu',
            add_images: true,
            selected_voice: 'Monica',
            voice_overrides: {
              es: 'Lucia',
            },
          },
          result: {
            success: true,
            refined_updated: false,
            stitched_documents: {},
            book_metadata: {
              input_language: 'English',
              original_language: 'English',
              translation_provider: 'llm',
              translation_model: 'ollama_local:old-default:7b',
              transliteration_mode: 'default',
            },
            pipeline_config: {
              image_api_base_url: 'http://image-node.local:7860',
              generate_audio: true,
              selected_voice: 'Monica',
            },
          },
          generated_files: {
            translation_fallback: {
              fallback_model: 'ollama_cloud:fallback:20b',
              scope: 'translation',
            },
            image_prompt_plan_summary: {
              status: 'ready',
              quality: {
                total_sentences: 10,
                final_fallback: 2,
                llm_coverage_rate: 0.8,
                retry_attempts: 1,
                retry_requested: 2,
                retry_recovered: 1,
                retry_success_rate: 0.5,
                llm_requests: 3,
              },
            },
          },
          image_generation: {
            enabled: true,
            expected: 10,
            generated: 4,
            percent: 40,
            pending: 6,
            batch_size: 3,
          },
          retry_summary: {
            image: { timeout: 2 },
            translation: { timeout: 1 },
          },
        }),
      ),
    );

    expect(entries.get('pipeline-target-languages')).toContain('Spanish');
    expect(entries.get('pipeline-target-languages')).toContain('French');
    expect(entries.get('pipeline-source-language')).toBe('English');
    expect(entries.get('pipeline-original-language')).toBe('English');
    expect(entries.get('pipeline-translation-provider')).toBe('LLM (ollama_cloud:qwen3:30b (30B))');
    expect(entries.get('pipeline-translation-fallback-model')).toBe('ollama_cloud:fallback:20b (20B)');
    expect(entries.get('pipeline-translation-batch-size')).toBe('8');
    expect(entries.get('pipeline-start-sentence')).toBe('12');
    expect(entries.get('pipeline-end-sentence')).toBe('48');
    expect(entries.get('pipeline-image-generation')).toBe(
      '40% generated, 6 pending, batch 3, retries timeout (2), 2 failures',
    );
    expect(entries.get('pipeline-image-api')).toBe('http://image-node.local:7860');
    expect(entries.get('pipeline-image-prompt-plan')).toBe(
      'READY, LLM 8/10 (80%), fallbacks 2, retries 1 (recovered 1/2, 50%), LLM calls 3',
    );
    expect(entries.get('pipeline-voice-overrides')).toBe('es: Lucia');
    expect(entries.get('pipeline-translation-retry-summary')).toBe('timeout (1)');
  });

  it('summarizes subtitle translation, origin, offset, track, and narration settings', () => {
    const entries = valuesByKey(
      buildJobParameterEntries(
        status({
          job_type: 'subtitle',
          parameters: {
            target_languages: ['Slovak'],
            translation_provider: 'googletrans',
            transliteration_mode: 'python',
            transliteration_model: 'uroman',
            transliteration_module: 'subtitle.romanize',
            llm_model: 'lmstudio_local:qwen2.5:14b',
            start_sentence: 3,
            end_sentence: 22,
            start_time_offset_seconds: 65,
            end_time_offset_seconds: 125,
          },
          result: {
            subtitle: {
              metadata: {
                detected_language: 'English',
                detected_language_code: 'en',
                origin_translation: {
                  active: true,
                  source_language: 'Czech',
                  source_language_code: 'cs',
                  target_language: 'English',
                  target_language_code: 'en',
                },
                subtitle_tracks: 'en, es',
                narration_language_code: 'sk',
              },
            },
          },
        }),
      ),
    );

    expect(entries.get('subtitle-translation-language')).toBe('Slovak');
    expect(entries.get('subtitle-translation-provider')).toBe('Google Translate (googletrans)');
    expect(entries.get('subtitle-transliteration-mode')).toBe('Python module');
    expect(entries.get('subtitle-transliteration-model')).toBe('uroman');
    expect(entries.get('subtitle-transliteration-module')).toBe('subtitle.romanize');
    expect(entries.get('subtitle-detected-language')).toBe('English (en)');
    expect(entries.get('subtitle-origin-translation')).toContain('Active');
    expect(entries.get('subtitle-origin-translation')).toContain('cs');
    expect(entries.get('subtitle-origin-translation')).toContain('en');
    expect(entries.get('subtitle-llm-model')).toBe('lmstudio_local:qwen2.5:14b (14B)');
    expect(entries.get('subtitle-start-sentence')).toBe('3');
    expect(entries.get('subtitle-end-sentence')).toBe('22');
    expect(entries.get('subtitle-start-offset')).toBe('01:05');
    expect(entries.get('subtitle-end-offset')).toBe('02:05');
    expect(entries.get('subtitle-track-languages')).toContain('English');
    expect(entries.get('subtitle-track-languages')).toContain('Spanish');
    expect(entries.get('subtitle-narration-language')).toBe('sk');
  });
});
