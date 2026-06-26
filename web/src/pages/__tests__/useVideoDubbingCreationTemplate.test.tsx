import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { BookCreationOptionsResponse } from '../../api/createBook';
import type {
  CreationTemplateEntry,
  JobParameterSnapshot
} from '../../api/dtos';
import { useVideoDubbingCreationTemplate } from '../video-dubbing/useVideoDubbingCreationTemplate';

function template(overrides: Partial<CreationTemplateEntry> = {}): CreationTemplateEntry {
  return {
    id: 'template-1',
    name: 'Episode Template',
    mode: 'youtube_dub',
    created_at: 1782475200,
    updated_at: 1782475200,
    payload: {
      kind: 'youtube_dub_form',
      form_state: {
        video_path: '/media/episode.mkv',
        subtitle_path: '/media/episode.en.ass',
        target_language: 'tr',
        voice: 'gTTS',
        start_time_offset: '00:10',
        end_time_offset: '01:20',
        original_mix_percent: 15,
        flush_sentences: 5,
        translation_batch_size: 9,
        target_height: 720,
        preserve_aspect_ratio: false,
        split_batches: false,
        stitch_batches: true,
        llm_model: 'ollama_local/mistral',
        translation_provider: 'ollama_local',
        transliteration_mode: 'none',
        transliteration_model: 'latin',
        include_transliteration: false,
        enable_lookup_cache: true,
        media_metadata: { title: 'Episode Title', private_key: 'removed' }
      },
      discovery_state: {
        selected_provider: 'youtube_search',
        query: 'episode'
      }
    },
    ...overrides
  };
}

function options(overrides: Partial<Parameters<typeof useVideoDubbingCreationTemplate>[0]> = {}) {
  const draft: Record<string, unknown> = { stale: true };
  const updateMediaMetadataDraft = vi.fn((updater: (draft: Record<string, unknown>) => void) => {
    updater(draft);
  });
  return {
    creationTemplate: null,
    prefillParameters: null,
    pipelineDefaults: null,
    metadataSourceName: 'episode.mkv',
    applyPipelineDefaults: vi.fn(),
    updateMediaMetadataDraft,
    setSelectedVideoDiscoveryTemplateState: vi.fn(),
    setSelectedVideoPath: vi.fn(),
    setSelectedSubtitlePath: vi.fn(),
    applyTargetLanguage: vi.fn(),
    setVoice: vi.fn(),
    setStartOffset: vi.fn(),
    setEndOffset: vi.fn(),
    setOriginalMixPercent: vi.fn(),
    setFlushSentences: vi.fn(),
    setTranslationBatchSize: vi.fn(),
    setTargetHeight: vi.fn(),
    setPreserveAspectRatio: vi.fn(),
    setSplitBatches: vi.fn(),
    setStitchBatches: vi.fn(),
    setLlmModel: vi.fn(),
    setTranslationProvider: vi.fn(),
    setTransliterationMode: vi.fn(),
    setTransliterationModel: vi.fn(),
    setIncludeTransliteration: vi.fn(),
    setEnableLookupCache: vi.fn(),
    setTemplateStatus: vi.fn(),
    setTemplateError: vi.fn(),
    ...overrides,
    draft
  };
}

describe('useVideoDubbingCreationTemplate', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('applies a saved YouTube Dub creation template to form state', async () => {
    const props = options({ creationTemplate: template() });

    renderHook(() => useVideoDubbingCreationTemplate(props));

    await waitFor(() => expect(props.setSelectedVideoPath).toHaveBeenCalledWith('/media/episode.mkv'));
    expect(props.setSelectedSubtitlePath).toHaveBeenCalledWith('/media/episode.en.ass');
    expect(props.applyTargetLanguage).toHaveBeenCalledWith('tr');
    expect(props.setVoice).toHaveBeenCalledWith('gTTS');
    expect(props.setStartOffset).toHaveBeenCalledWith('00:10');
    expect(props.setOriginalMixPercent).toHaveBeenCalledWith(15);
    expect(props.setTargetHeight).toHaveBeenCalledWith(720);
    expect(props.setPreserveAspectRatio).toHaveBeenCalledWith(false);
    expect(props.setSelectedVideoDiscoveryTemplateState).toHaveBeenCalledWith(expect.objectContaining({
      selected_provider: 'youtube_search',
      query: 'episode'
    }));
    expect(props.setTemplateError).toHaveBeenCalledWith(null);
    expect(props.setTemplateStatus).toHaveBeenCalledWith('Applied template "Episode Template".');
  });

  it('applies template metadata after the metadata draft has reset for the source name', async () => {
    const props = options({ creationTemplate: template() });

    renderHook(() => useVideoDubbingCreationTemplate(props));

    await waitFor(() => expect(props.updateMediaMetadataDraft).toHaveBeenCalled());
    expect(props.draft).toEqual({
      title: 'Episode Title',
      private_key: 'removed'
    });
  });

  it('reports incompatible templates without applying form state', async () => {
    const props = options({
      creationTemplate: template({
        name: 'Narrate Template',
        mode: 'narrate_ebook'
      })
    });

    renderHook(() => useVideoDubbingCreationTemplate(props));

    await waitFor(() =>
      expect(props.setTemplateError).toHaveBeenCalledWith(
        'Template "Narrate Template" is not compatible with Video Dubbing.'
      )
    );
    expect(props.setTemplateStatus).toHaveBeenCalledWith(null);
    expect(props.setSelectedVideoPath).not.toHaveBeenCalled();
  });

  it('applies rerun prefill selection and model state', async () => {
    const prefill: JobParameterSnapshot = {
      input_file: '/media/rerun.mkv',
      subtitle_path: '/media/rerun.en.ass',
      target_languages: ['de'],
      selected_voice: 'Anna',
      llm_model: 'ollama_local/llama3',
      translation_provider: 'ollama_local',
      transliteration_mode: 'none',
      transliteration_model: 'latin'
    };
    const props = options({ prefillParameters: prefill });

    renderHook(() => useVideoDubbingCreationTemplate(props));

    await waitFor(() => expect(props.setSelectedVideoPath).toHaveBeenCalledWith('/media/rerun.mkv'));
    expect(props.setSelectedSubtitlePath).toHaveBeenCalledWith('/media/rerun.en.ass');
    expect(props.applyTargetLanguage).toHaveBeenCalledWith('de');
    expect(props.setVoice).toHaveBeenCalledWith('Anna');
    expect(props.setLlmModel).toHaveBeenCalledWith('ollama_local/llama3');
    expect(props.setTranslationProvider).toHaveBeenCalledWith('ollama_local');
    expect(props.applyPipelineDefaults).not.toHaveBeenCalled();
  });

  it('applies pipeline defaults when no prefill or saved template is active', async () => {
    const pipelineDefaults: BookCreationOptionsResponse['pipeline_defaults'] = {
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
      translation_provider: 'ollama_local',
      translation_batch_size: 8,
      transliteration_mode: 'none',
      enable_lookup_cache: true,
      lookup_cache_batch_size: 24,
      tempo: 1
    };
    const props = options({ pipelineDefaults });

    renderHook(() => useVideoDubbingCreationTemplate(props));

    await waitFor(() => expect(props.applyPipelineDefaults).toHaveBeenCalledWith(pipelineDefaults));
  });
});
