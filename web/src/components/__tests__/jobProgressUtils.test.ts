import { describe, expect, it } from 'vitest';
import {
  areTranslationsUnavailable,
  buildBatchProgress,
  buildBatchStatEntries,
  buildFallbackEntries,
  buildParallelismEntries,
  formatProgressValue,
  resolveGeneratedFileRecord,
  resolveLookupCacheBuildingProgress,
  resolveLookupCacheProgress,
  resolveMediaStageProgress,
  resolvePlayableStageProgress,
  resolveTranslationStageProgress
} from '../job-progress/jobProgressUtils';

function progressEvent(overrides: Partial<{
  event_type: string;
  metadata: Record<string, unknown>;
  completed: number;
  total: number | null;
}> = {}) {
  return {
    event_type: overrides.event_type ?? 'progress',
    timestamp: 0,
    metadata: overrides.metadata ?? {},
    snapshot: {
      completed: overrides.completed ?? 0,
      total: overrides.total ?? null,
      elapsed: 0,
      speed: 0,
      eta: null,
    },
    error: null,
  };
}

describe('jobProgressUtils progress helpers', () => {
  it('builds fallback display rows from generated-file fallback records', () => {
    expect(
      buildFallbackEntries({
        translation_fallback: {
          fallback_model: 'gpt-4.1-mini',
          source_provider: 'ollama_local',
          trigger: 'timeout',
          elapsed_seconds: 12.345,
        },
        tts_fallback: {
          scope: 'media',
          fallback_voice: 'gTTS',
          source_voice: 'Alloy',
          reason: 'voice unavailable',
        },
      }),
    ).toEqual([
      ['Translation fallback', 'model gpt-4.1-mini | source ollama_local | trigger timeout | elapsed 12.3 s'],
      ['TTS fallback', 'scope media | voice gTTS | source Alloy | voice unavailable'],
    ]);
  });

  it('omits empty or malformed fallback rows', () => {
    expect(
      buildFallbackEntries({
        translation_fallback: {},
        tts_fallback: 'not-a-record',
      }),
    ).toEqual([]);
    expect(buildFallbackEntries(null)).toEqual([]);
  });

  it('detects placeholder-only translation blocks', () => {
    expect(areTranslationsUnavailable(['', '  n/a ', 'N/A'])).toBe(true);
    expect(areTranslationsUnavailable(['N/A', 'A translated sentence.'])).toBe(false);
    expect(areTranslationsUnavailable(['N/A', 42])).toBe(false);
    expect(areTranslationsUnavailable([])).toBe(false);
    expect(areTranslationsUnavailable(null)).toBe(false);
  });

  it('resolves generated-file stat records by key', () => {
    const generated = {
      translation_batch_stats: {
        batches_completed: 3,
        batches_total: 8
      },
      plain_value: 'ignored'
    };

    expect(resolveGeneratedFileRecord(generated, 'translation_batch_stats')).toEqual({
      batches_completed: 3,
      batches_total: 8
    });
    expect(resolveGeneratedFileRecord(generated, 'plain_value')).toBeNull();
    expect(resolveGeneratedFileRecord(null, 'translation_batch_stats')).toBeNull();
  });

  it('builds batch progress from completed and optional total counts', () => {
    expect(buildBatchProgress({ batches_completed: '4', batches_total: 9 })).toEqual({
      completed: 4,
      total: 9
    });
    expect(buildBatchProgress({ batches_total: 9 })).toBeNull();
  });

  it('resolves sentence-stage translation progress from metadata before snapshot counts', () => {
    expect(
      resolveTranslationStageProgress(
        progressEvent({
          completed: 1,
          total: 10,
          metadata: {
            translation_completed: '4',
            translation_total: 9,
          },
        }),
        false,
      ),
    ).toEqual({ completed: 4, total: 9 });
  });

  it('suppresses sentence-stage translation and media progress when batch progress is active', () => {
    const event = progressEvent({ completed: 3, total: 8 });

    expect(resolveTranslationStageProgress(event, true)).toBeNull();
    expect(resolveMediaStageProgress(event, true)).toBeNull();
  });

  it('resolves sentence-stage media progress from the event snapshot', () => {
    expect(resolveMediaStageProgress(progressEvent({ completed: 7, total: 12 }), false)).toEqual({
      completed: 7,
      total: 12,
    });
  });

  it('resolves playable progress from playable event before media batch fallback', () => {
    expect(
      resolvePlayableStageProgress({
        latestPlayableEvent: progressEvent({ completed: 5, total: 8 }),
        mediaBatchStats: {
          items_completed: 2,
          items_total: 9,
        },
      }),
    ).toEqual({ completed: 5, total: 8 });
  });

  it('falls back to media batch item counts for playable progress', () => {
    expect(
      resolvePlayableStageProgress({
        latestPlayableEvent: undefined,
        mediaBatchStats: {
          items_completed: '6',
          items_total: 10,
        },
      }),
    ).toEqual({ completed: 6, total: 10 });
    expect(
      resolvePlayableStageProgress({
        latestPlayableEvent: progressEvent({ completed: 6, total: null }),
        mediaBatchStats: null,
      }),
    ).toBeNull();
  });

  it('formats progress counts defensively', () => {
    expect(formatProgressValue({ completed: 3.6, total: 10.2 })).toBe('4 / 10');
    expect(formatProgressValue({ completed: -2, total: null })).toBe('0');
    expect(formatProgressValue({ completed: Number.POSITIVE_INFINITY, total: 4 })).toBe('0 / 4');
  });

  it('builds LLM batch stat entries with fallback zeros before backend stats arrive', () => {
    expect(buildBatchStatEntries(5, null)).toEqual([
      ['Batch size', '5'],
      ['Batches completed', '0'],
      ['Items translated', '0']
    ]);
  });

  it('builds LLM batch stat entries from backend timing stats', () => {
    expect(
      buildBatchStatEntries(5, {
        batches_completed: 2,
        items_completed: 11,
        avg_batch_seconds: 3.25,
        avg_item_seconds: 0.42,
        last_batch_seconds: 8.9,
        last_batch_items: 4
      })
    ).toEqual([
      ['Batch size', '5'],
      ['Batches completed', '2'],
      ['Items translated', '11'],
      ['Avg batch time', '3.3 s/batch'],
      ['Avg item time', '0.42 s/item'],
      ['Last batch time', '8.9 s/batch (4 sentences)']
    ]);
  });

  it('builds parallelism entries for local LLM batches and TTS workers', () => {
    expect(
      buildParallelismEntries({
        tuning: { thread_count: 4, translation_pool_workers: 2 },
        pipelineConfig: {
          ollama_model: 'ollama_local:gemma3:12b',
          selected_voice: 'Monica',
          generate_audio: true,
        },
        parameters: {
          translation_batch_size: 5,
        },
        metadata: {},
        translationProvider: 'llm',
        configuredBatchSize: 5,
      }),
    ).toEqual([
      {
        label: 'LLM (ollama_local:gemma3:12b (12B)) parallel calls',
        value: '2',
        hint:
          'Controlled by Worker threads. Model: ollama_local:gemma3:12b. Provider: ollama_local. Batch size: 5 sentences/request. Model is local (batch calls capped to 1)',
      },
      {
        label: 'LLM batch cap applies',
        value: 'Yes',
        hint: 'Local model; batching is capped to 1 parallel LLM call.',
      },
      {
        label: 'TTS parallel calls',
        value: '4',
        hint: 'Controlled by Worker threads. Voice: Monica',
      },
    ]);
  });

  it('builds parallelism entries for cloud-backed translation without local batch cap', () => {
    expect(
      buildParallelismEntries({
        tuning: { thread_count: 3, translation_pool_workers: 6 },
        pipelineConfig: {
          selected_voice: 'gTTS',
          generate_audio: false,
        },
        parameters: {
          llm_model: 'ollama_cloud:gpt-oss:20b',
        },
        metadata: {
          translation_model: 'ollama_cloud:gpt-oss:20b',
        },
        translationProvider: 'llm',
        configuredBatchSize: 8,
      }),
    ).toEqual([
      {
        label: 'LLM (ollama_cloud:gpt-oss:20b (20B)) parallel calls',
        value: '6',
        hint:
          'Controlled by Worker threads. Model: ollama_cloud:gpt-oss:20b. Provider: ollama_cloud. Batch size: 8 sentences/request. Model is cloud-backed (no local cap)',
      },
      {
        label: 'LLM batch cap applies',
        value: 'No',
        hint: 'Cloud-backed model; batching is not capped.',
      },
      {
        label: 'TTS parallel calls',
        value: '3',
        hint: 'Controlled by Worker threads. Voice: gTTS. Audio disabled for this job',
      },
    ]);
  });

  it('falls back to pipeline thread count when translation pool is not reported', () => {
    expect(
      buildParallelismEntries({
        tuning: null,
        pipelineConfig: { thread_count: '2' },
        parameters: null,
        metadata: {},
        translationProvider: 'googletrans',
        configuredBatchSize: null,
      }),
    ).toEqual([
      {
        label: 'Google Translate (googletrans) parallel calls',
        value: '2',
        hint: 'Controlled by Worker threads',
      },
      {
        label: 'TTS parallel calls',
        value: '2',
        hint: 'Controlled by Worker threads',
      },
    ]);
  });

  it('resolves completed lookup-cache progress', () => {
    expect(
      resolveLookupCacheProgress({
        word_count: '12',
        llm_calls: 3,
        skipped_stopwords: 5,
        build_time_seconds: 1.25
      })
    ).toEqual({
      wordCount: 12,
      llmCalls: 3,
      skippedStopwords: 5,
      buildTimeSeconds: 1.25
    });
    expect(resolveLookupCacheProgress({ llm_calls: 3 })).toBeNull();
  });

  it('resolves lookup-cache building progress from SSE metadata', () => {
    expect(
      resolveLookupCacheBuildingProgress({
        lookup_cache_progress: {
          batches_completed: 1,
          batches_total: 4,
          words_to_lookup: 27,
          cached_entries: 9,
          llm_calls: 2
        }
      })
    ).toEqual({
      status: 'building',
      batchesCompleted: 1,
      batchesTotal: 4,
      wordsToLookup: 27,
      cachedEntries: 9,
      llmCalls: 2
    });
    expect(resolveLookupCacheBuildingProgress({ lookup_cache_status: 'building' })).toEqual({
      status: 'building',
      batchesCompleted: null,
      batchesTotal: null,
      wordsToLookup: null,
      cachedEntries: null,
      llmCalls: null
    });
  });
});
