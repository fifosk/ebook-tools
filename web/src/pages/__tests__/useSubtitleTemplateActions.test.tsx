import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { saveCreationTemplate } from '../../api/client';
import type { CreationTemplateEntry } from '../../api/dtos';
import { useSubtitleTemplateActions } from '../subtitle-tool/useSubtitleTemplateActions';

vi.mock('../../api/client', () => ({
  saveCreationTemplate: vi.fn()
}));

const mockSaveCreationTemplate = vi.mocked(saveCreationTemplate);

function savedTemplate(name = 'Subtitle Defaults'): CreationTemplateEntry {
  return {
    id: 'template-1',
    name,
    mode: 'subtitle_job',
    created_at: 1782475200,
    updated_at: 1782475200,
    payload: {}
  };
}

function baseOptions(overrides: Partial<Parameters<typeof useSubtitleTemplateActions>[0]> = {}) {
  return {
    inputLanguage: 'English',
    targetLanguage: 'French',
    isAssSelection: false,
    sourceMode: 'existing' as const,
    selectedSource: '/media/source.srt',
    startTime: '1:02',
    endTime: '+5',
    outputFormat: 'ass' as const,
    assFontSize: 999,
    assEmphasis: 0.05,
    selectedModel: 'gpt-test',
    translationProvider: 'llm',
    transliterationMode: 'default',
    transliterationModel: 'romanizer',
    workerCount: 4,
    batchSize: 20,
    translationBatchSize: 8,
    enableTransliteration: true,
    enableHighlight: false,
    showOriginal: true,
    generateAudioBook: false,
    mirrorToSourceDir: true,
    uploadFile: null,
    mediaMetadataDraft: {
      show: { name: 'Example Show' },
      episode: { name: 'A Soft Launch' },
      api_token: 'do-not-store'
    },
    ...overrides
  };
}

describe('useSubtitleTemplateActions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('surfaces validation errors before saving a template', async () => {
    const { result } = renderHook(() => useSubtitleTemplateActions(baseOptions({ inputLanguage: '' })));

    await act(async () => {
      await result.current.handleSaveTemplate();
    });

    expect(result.current.templateError).toBe('Choose an original language.');
    expect(result.current.templateStatus).toBeNull();
    expect(mockSaveCreationTemplate).not.toHaveBeenCalled();
  });

  it('saves sanitized subtitle templates for Apple Create reuse', async () => {
    mockSaveCreationTemplate.mockResolvedValueOnce(savedTemplate('Reusable Subtitle Template'));
    const { result } = renderHook(() => useSubtitleTemplateActions(baseOptions()));

    await act(async () => {
      await result.current.handleSaveTemplate();
    });

    expect(mockSaveCreationTemplate).toHaveBeenCalledWith(expect.objectContaining({
      mode: 'subtitle_job',
      payload: expect.objectContaining({
        kind: 'subtitle_job_form',
        form_state: expect.objectContaining({
          source_path: '/media/source.srt',
          start_time: '01:02',
          end_time: '+05:00',
          ass_font_size: 120,
          ass_emphasis_scale: 1,
          media_metadata: {
            show: { name: 'Example Show' },
            episode: { name: 'A Soft Launch' }
          }
        })
      })
    }));
    expect(JSON.stringify(mockSaveCreationTemplate.mock.calls[0][0])).not.toContain('api_token');
    expect(result.current.templateStatus).toBe(
      'Saved template "Reusable Subtitle Template". Apple Create can apply it from Subtitles.'
    );
    expect(result.current.templateError).toBeNull();
    expect(result.current.isSavingTemplate).toBe(false);
  });

  it('surfaces save failures and clears the saving flag', async () => {
    mockSaveCreationTemplate.mockRejectedValueOnce(new Error('template service unavailable'));
    const { result } = renderHook(() => useSubtitleTemplateActions(baseOptions()));

    await act(async () => {
      await result.current.handleSaveTemplate();
    });

    expect(result.current.templateError).toBe('template service unavailable');
    expect(result.current.templateStatus).toBeNull();
    expect(result.current.isSavingTemplate).toBe(false);
  });
});
