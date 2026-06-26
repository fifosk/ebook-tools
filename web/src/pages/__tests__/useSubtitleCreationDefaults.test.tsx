import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchBookCreationOptions, type BookCreationOptionsResponse } from '../../api/createBook';
import { useSubtitleCreationDefaults } from '../subtitle-tool/useSubtitleCreationDefaults';

vi.mock('../../api/createBook', () => ({
  fetchBookCreationOptions: vi.fn()
}));

const mockFetchBookCreationOptions = vi.mocked(fetchBookCreationOptions);

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((nextResolve, nextReject) => {
    resolve = nextResolve;
    reject = nextReject;
  });
  return { promise, resolve, reject };
}

function creationOptions(): BookCreationOptionsResponse {
  return {
    sentence_bounds: {
      min: 1,
      max: 500,
      default: 30
    },
    defaults: {
      topic: 'Demo topic',
      book_name: 'Demo Book',
      genre: 'Mystery',
      author: 'Demo Author',
      input_language: 'English',
      output_language: 'French',
      voice: 'gTTS'
    },
    pipeline_defaults: {
      sentences_per_output_file: 10,
      stitch_full: true,
      audio_mode: 'edge',
      audio_bitrate_kbps: null,
      written_mode: 'markdown',
      selected_voice: 'gTTS',
      generate_audio: true,
      output_html: true,
      output_pdf: false,
      include_transliteration: true,
      translation_provider: 'googletrans',
      translation_batch_size: 8,
      transliteration_mode: 'python',
      enable_lookup_cache: true,
      lookup_cache_batch_size: 24,
      tempo: 1
    },
    subtitle_defaults: {
      worker_count: 12,
      batch_size: 22,
      translation_batch_size: 8,
      ass_font_size: 64,
      ass_emphasis_scale: 1.6
    },
    generated_source_defaults: {
      add_images: false,
      image_prompt_pipeline: 'prompt_plan',
      image_style_template: 'wireframe',
      image_prompt_context_sentences: 2,
      image_width: '1024',
      image_height: '1024'
    },
    supported_input_languages: ['English'],
    supported_output_languages: ['French'],
    supported_voices: ['gTTS']
  };
}

describe('useSubtitleCreationDefaults', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.spyOn(console, 'warn').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('loads backend creation defaults when no prefill or template is active', async () => {
    const applySubtitleDefaults = vi.fn();
    const options = creationOptions();
    mockFetchBookCreationOptions.mockResolvedValue(options);

    renderHook(() =>
      useSubtitleCreationDefaults({
        shouldSkipDefaults: false,
        applySubtitleDefaults
      })
    );

    await waitFor(() =>
      expect(applySubtitleDefaults).toHaveBeenCalledWith(
        options.subtitle_defaults,
        options.pipeline_defaults
      )
    );
  });

  it('skips backend defaults while prefill or template state is active', () => {
    const applySubtitleDefaults = vi.fn();

    renderHook(() =>
      useSubtitleCreationDefaults({
        shouldSkipDefaults: true,
        applySubtitleDefaults
      })
    );

    expect(mockFetchBookCreationOptions).not.toHaveBeenCalled();
    expect(applySubtitleDefaults).not.toHaveBeenCalled();
  });

  it('logs creation default failures without applying defaults', async () => {
    const applySubtitleDefaults = vi.fn();
    const failure = new Error('defaults unavailable');
    mockFetchBookCreationOptions.mockRejectedValue(failure);

    renderHook(() =>
      useSubtitleCreationDefaults({
        shouldSkipDefaults: false,
        applySubtitleDefaults
      })
    );

    await waitFor(() =>
      expect(console.warn).toHaveBeenCalledWith(
        'Unable to load subtitle creation defaults',
        failure
      )
    );
    expect(applySubtitleDefaults).not.toHaveBeenCalled();
  });

  it('ignores late default responses after unmount', async () => {
    const applySubtitleDefaults = vi.fn();
    const pending = deferred<Awaited<ReturnType<typeof fetchBookCreationOptions>>>();
    mockFetchBookCreationOptions.mockReturnValue(pending.promise);

    const { unmount } = renderHook(() =>
      useSubtitleCreationDefaults({
        shouldSkipDefaults: false,
        applySubtitleDefaults
      })
    );

    unmount();
    await act(async () => {
      pending.resolve(creationOptions());
    });

    expect(applySubtitleDefaults).not.toHaveBeenCalled();
  });
});
