import { describe, expect, it } from 'vitest';
import type { PipelineStatusResponse } from '../../api/dtos';
import {
  countGeneratedImages,
  resolveGeneratedChunks,
  resolveGeneratedFileRecord,
  resolveGeneratedFiles,
  resolveImagePromptPlanSummary,
  resolveSentenceRange,
  sumRetryCounts,
} from '../job-progress/jobProgressGeneratedFiles';

const baseStatus: PipelineStatusResponse = {
  job_id: 'book-job',
  job_type: 'book',
  status: 'running',
  created_at: '2026-07-04T00:00:00Z',
  started_at: null,
  completed_at: null,
  result: null,
  error: null,
  latest_event: null,
  tuning: null,
};

describe('jobProgressGeneratedFiles', () => {
  it('resolves named generated-file records only when the value is an object', () => {
    const generated = {
      translation_batch_stats: {
        batches_completed: 3,
        batches_total: 8,
      },
      plain_value: 'ignored',
    };

    expect(resolveGeneratedFileRecord(generated, 'translation_batch_stats')).toEqual({
      batches_completed: 3,
      batches_total: 8,
    });
    expect(resolveGeneratedFileRecord(generated, 'plain_value')).toBeNull();
    expect(resolveGeneratedFileRecord(null, 'translation_batch_stats')).toBeNull();
  });

  it('deduplicates chunk records by chunk id across generated-file fallbacks', () => {
    const chunks = resolveGeneratedChunks({
      ...baseStatus,
      generated_files: {
        chunks: [
          { chunk_id: 'chunk-1', start_sentence: 1, end_sentence: 3 },
          { chunkId: 'chunk-2', startSentence: 4, endSentence: 6 },
        ],
      },
      result: {
        generated_files: {
          chunks: [
            { chunk_id: 'chunk-1', start_sentence: 1, end_sentence: 3 },
            { chunk_id: 'chunk-3', start_sentence: 7, end_sentence: 9 },
          ],
        },
      },
    });

    expect(chunks.map((chunk) => chunk.chunk_id ?? chunk.chunkId)).toEqual([
      'chunk-1',
      'chunk-2',
      'chunk-3',
    ]);
  });

  it('deduplicates generated files by type and path while preserving unkeyed records', () => {
    const files = resolveGeneratedFiles({
      ...baseStatus,
      generated_files: {
        files: [
          { type: 'audio', path: 'media/a.mp3' },
          { type: 'audio', path: 'media/a.mp3', duplicate: true },
          { type: '', path: '', note: 'unkeyed' },
        ],
      },
      result: {
        generated_files: {
          files: [
            { type: 'image', path: 'media/images/sentence_0001.png' },
          ],
        },
      },
    });

    expect(files).toEqual([
      { type: 'audio', path: 'media/a.mp3' },
      { type: '', path: '', note: 'unkeyed' },
      { type: 'image', path: 'media/images/sentence_0001.png' },
    ]);
  });

  it('extracts prompt-plan summaries and sentence ranges from current or result payloads', () => {
    const status: PipelineStatusResponse = {
      ...baseStatus,
      generated_files: {
        chunks: [{ chunk_id: 'chunk-2', start_sentence: 4, end_sentence: 8 }],
      },
      result: {
        generated_files: {
          chunks: [{ chunk_id: 'chunk-1', startSentence: 1, endSentence: 3 }],
          image_prompt_plan_summary: {
            scenes: 2,
          },
        },
      },
    };

    expect(resolveSentenceRange(status)).toEqual({ start: 1, end: 8 });
    expect(resolveImagePromptPlanSummary(status)).toEqual({ scenes: 2 });
  });

  it('counts generated image files and retry totals defensively', () => {
    expect(countGeneratedImages({
      ...baseStatus,
      generated_files: {
        files: [
          { type: 'image', path: 'media/not-in-image-folder.txt' },
          { type: 'audio', path: 'media/images/sentence_0001.jpg' },
          { type: 'text', path: 'media/images/notes.txt' },
        ],
      },
    })).toBe(2);
    expect(sumRetryCounts({ timeout: 2, invalid: -4, bad: Number.NaN })).toBe(2);
    expect(sumRetryCounts(null)).toBe(0);
  });
});
