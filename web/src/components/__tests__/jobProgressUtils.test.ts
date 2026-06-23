import { describe, expect, it } from 'vitest';
import {
  buildBatchProgress,
  buildBatchStatEntries,
  formatProgressValue,
  resolveGeneratedFileRecord,
  resolveLookupCacheBuildingProgress,
  resolveLookupCacheProgress
} from '../job-progress/jobProgressUtils';

describe('jobProgressUtils progress helpers', () => {
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
