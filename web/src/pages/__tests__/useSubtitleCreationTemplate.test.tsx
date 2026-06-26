import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { CreationTemplateEntry } from '../../api/dtos';
import { useSubtitleCreationTemplate } from '../subtitle-tool/useSubtitleCreationTemplate';

function template(overrides: Partial<CreationTemplateEntry> = {}): CreationTemplateEntry {
  return {
    id: 'subtitle-template',
    name: 'Subtitle Defaults',
    mode: 'subtitle_job',
    created_at: 1782475200,
    updated_at: 1782475200,
    payload: {
      kind: 'subtitle_job_form',
      form_state: {
        source_mode: 'existing',
        source_path: '/subs/current.srt',
        input_language: 'Spanish',
        target_language: 'German',
        enable_transliteration: false,
        highlight: true,
        show_original: false,
        generate_audio_book: true,
        output_format: 'srt',
        mirror_batches_to_source_dir: false,
        start_time: '00:10',
        end_time: '+02:00',
        llm_model: 'gpt-test',
        translation_provider: 'googletrans',
        transliteration_mode: 'python',
        transliteration_model: 'romanizer',
        worker_count: '3',
        batch_size: 16,
        translation_batch_size: 7,
        ass_font_size: '64',
        ass_emphasis_scale: 1.4,
        media_metadata: {
          show: { name: 'Example Show' },
          token: 'drop-me'
        }
      }
    },
    ...overrides
  };
}

function options(overrides: Partial<Parameters<typeof useSubtitleCreationTemplate>[0]> = {}) {
  const draft: Record<string, unknown> = { stale: true };
  const updateMediaMetadataDraft = vi.fn((updater: (draft: Record<string, unknown>) => void) => {
    updater(draft);
  });
  return {
    creationTemplate: null,
    metadataSourceName: 'current.srt',
    updateMediaMetadataDraft,
    handleSourceModeChange: vi.fn(),
    setSelectedSource: vi.fn(),
    setInputLanguage: vi.fn(),
    setTargetLanguage: vi.fn(),
    setPrimaryTargetLanguage: vi.fn(),
    setEnableTransliteration: vi.fn(),
    setEnableHighlight: vi.fn(),
    setShowOriginal: vi.fn(),
    setGenerateAudioBook: vi.fn(),
    setOutputFormat: vi.fn(),
    setMirrorToSourceDir: vi.fn(),
    setStartTime: vi.fn(),
    setEndTime: vi.fn(),
    setSelectedModel: vi.fn(),
    setTranslationProvider: vi.fn(),
    setTransliterationMode: vi.fn(),
    setTransliterationModel: vi.fn(),
    setWorkerCount: vi.fn(),
    setBatchSize: vi.fn(),
    setTranslationBatchSize: vi.fn(),
    setAssFontSize: vi.fn(),
    setAssEmphasis: vi.fn(),
    setTemplateStatus: vi.fn(),
    setTemplateError: vi.fn(),
    ...overrides,
    draft
  };
}

describe('useSubtitleCreationTemplate', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('applies a saved Subtitle Tool creation template to form state', async () => {
    const props = options({ creationTemplate: template() });

    renderHook(() => useSubtitleCreationTemplate(props));

    await waitFor(() => expect(props.setSelectedSource).toHaveBeenCalledWith('/subs/current.srt'));
    expect(props.handleSourceModeChange).toHaveBeenCalledWith('existing');
    expect(props.setInputLanguage).toHaveBeenCalledWith('Spanish');
    expect(props.setTargetLanguage).toHaveBeenCalledWith('German');
    expect(props.setPrimaryTargetLanguage).toHaveBeenCalledWith('German');
    expect(props.setEnableTransliteration).toHaveBeenCalledWith(false);
    expect(props.setEnableHighlight).toHaveBeenCalledWith(true);
    expect(props.setShowOriginal).toHaveBeenCalledWith(false);
    expect(props.setGenerateAudioBook).toHaveBeenCalledWith(true);
    expect(props.setOutputFormat).toHaveBeenCalledWith('srt');
    expect(props.setTranslationProvider).toHaveBeenCalledWith('googletrans');
    expect(props.setWorkerCount).toHaveBeenCalledWith(3);
    expect(props.setAssFontSize).toHaveBeenCalledWith(64);
    expect(props.setAssEmphasis).toHaveBeenCalledWith(1.4);
    expect(props.setTemplateError).toHaveBeenCalledWith(null);
    expect(props.setTemplateStatus).toHaveBeenCalledWith('Applied template "Subtitle Defaults".');
  });

  it('applies template metadata after the metadata draft has reset for the source name', async () => {
    const props = options({ creationTemplate: template() });

    renderHook(() => useSubtitleCreationTemplate(props));

    await waitFor(() => expect(props.updateMediaMetadataDraft).toHaveBeenCalled());
    expect(props.draft).toEqual({
      show: { name: 'Example Show' }
    });
  });

  it('reports incompatible templates without applying form state', async () => {
    const props = options({
      creationTemplate: template({
        name: 'Narrate Template',
        mode: 'narrate_ebook'
      })
    });

    renderHook(() => useSubtitleCreationTemplate(props));

    await waitFor(() =>
      expect(props.setTemplateError).toHaveBeenCalledWith(
        'Template "Narrate Template" is not compatible with Subtitle Tool.'
      )
    );
    expect(props.setTemplateStatus).toHaveBeenCalledWith(null);
    expect(props.setSelectedSource).not.toHaveBeenCalled();
  });
});
