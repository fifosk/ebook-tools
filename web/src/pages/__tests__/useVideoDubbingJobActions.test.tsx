import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  generateYoutubeDub,
  saveCreationTemplate
} from '../../api/client';
import type {
  CreationTemplateEntry,
  YoutubeNasSubtitle,
  YoutubeNasVideo
} from '../../api/dtos';
import { useVideoDubbingJobActions } from '../video-dubbing/useVideoDubbingJobActions';
import type { VideoDubbingGeneratePayloadInput } from '../video-dubbing/videoDubbingUtils';

vi.mock('../../api/client', () => ({
  generateYoutubeDub: vi.fn(),
  saveCreationTemplate: vi.fn()
}));

const mockGenerateYoutubeDub = vi.mocked(generateYoutubeDub);
const mockSaveCreationTemplate = vi.mocked(saveCreationTemplate);

const subtitle: YoutubeNasSubtitle = {
  path: '/media/episode.en.ass',
  filename: 'episode.en.ass',
  language: 'en',
  format: 'ass'
};

const video: YoutubeNasVideo = {
  path: '/media/episode.mkv',
  filename: 'episode.mkv',
  folder: '/media',
  size_bytes: 1234,
  modified_at: '2026-06-26T12:00:00Z',
  subtitles: [subtitle]
};

function basePayloadInput(
  overrides: Partial<VideoDubbingGeneratePayloadInput> = {}
): VideoDubbingGeneratePayloadInput {
  return {
    selectedVideo: video,
    selectedSubtitle: subtitle,
    mediaMetadataDraft: { title: 'Episode Title' },
    subtitleLanguageLabel: 'English',
    subtitleLanguageCode: 'en',
    targetLanguageCode: 'tr',
    voice: 'gTTS',
    startOffset: '',
    endOffset: '',
    originalMixPercent: 20,
    flushSentences: 4,
    translationBatchSize: 12,
    llmModel: 'ollama_local/mistral',
    translationProvider: 'ollama_local',
    transliterationMode: 'none',
    transliterationModel: '',
    splitBatches: true,
    stitchBatches: true,
    includeTransliteration: false,
    targetHeight: 720,
    preserveAspectRatio: true,
    enableLookupCache: true,
    ...overrides
  };
}

function savedTemplate(overrides: Partial<CreationTemplateEntry> = {}): CreationTemplateEntry {
  return {
    id: 'template-1',
    name: 'Episode Template',
    mode: 'youtube_dub',
    created_at: 1782475200,
    updated_at: 1782475200,
    payload: {},
    ...overrides
  };
}

function renderJobActions(overrides: Partial<Parameters<typeof useVideoDubbingJobActions>[0]> = {}) {
  const onJobCreated = vi.fn();
  const onActiveTabChange = vi.fn();
  const onStatusMessageChange = vi.fn();
  const refreshIntakeStatus = vi.fn().mockResolvedValue(undefined);
  const result = renderHook((props: Parameters<typeof useVideoDubbingJobActions>[0]) =>
    useVideoDubbingJobActions(props),
    {
      initialProps: {
        ...basePayloadInput(),
        selectedVideoDiscoveryTemplateState: null,
        isIntakeAtCapacity: false,
        onJobCreated,
        onActiveTabChange,
        onStatusMessageChange,
        refreshIntakeStatus,
        ...overrides
      }
    }
  );

  return {
    ...result,
    onJobCreated,
    onActiveTabChange,
    onStatusMessageChange,
    refreshIntakeStatus
  };
}

describe('useVideoDubbingJobActions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('blocks generation while the intake queue is at capacity', async () => {
    const { result } = renderJobActions({ isIntakeAtCapacity: true });

    await act(async () => {
      await result.current.handleGenerate();
    });

    expect(result.current.generateError).toBe(
      'Job queue is at capacity. Wait for pending jobs to clear before creating a dubbed video.'
    );
    expect(mockGenerateYoutubeDub).not.toHaveBeenCalled();
    expect(result.current.canGenerate).toBe(false);
  });

  it('submits a valid dubbed video job and switches to the jobs tab', async () => {
    mockGenerateYoutubeDub.mockResolvedValueOnce({
      job_id: 'youtube_dub_1',
      status: 'pending',
      created_at: '2026-06-26T12:00:00Z',
      job_type: 'youtube_dub'
    });
    const {
      result,
      onJobCreated,
      onActiveTabChange,
      onStatusMessageChange,
      refreshIntakeStatus
    } = renderJobActions();

    await act(async () => {
      await result.current.handleGenerate();
    });

    expect(mockGenerateYoutubeDub).toHaveBeenCalledWith(expect.objectContaining({
      video_path: video.path,
      subtitle_path: subtitle.path,
      target_language: 'tr'
    }));
    expect(onStatusMessageChange).toHaveBeenLastCalledWith(
      'Dub job submitted as youtube_dub_1. Track progress below.'
    );
    expect(onJobCreated).toHaveBeenCalledWith('youtube_dub_1');
    expect(onActiveTabChange).toHaveBeenCalledWith('jobs');
    expect(refreshIntakeStatus).toHaveBeenCalledTimes(1);
    expect(result.current.isGenerating).toBe(false);
  });

  it('surfaces payload validation errors when saving a template', async () => {
    const { result } = renderJobActions({ selectedSubtitle: null });

    await act(async () => {
      await result.current.handleSaveTemplate();
    });

    expect(result.current.templateError).toBe('Choose a video and an ASS subtitle before generating audio.');
    expect(mockSaveCreationTemplate).not.toHaveBeenCalled();
  });

  it('saves templates with sanitized discovery state for Apple Create reuse', async () => {
    mockSaveCreationTemplate.mockResolvedValueOnce(savedTemplate({ name: 'Saved Discovery Template' }));
    const { result } = renderJobActions({
      selectedVideoDiscoveryTemplateState: {
        selected_provider: 'newznab_torznab',
        query: 'episode',
        selected_video_path: '/media/episode.mkv'
      }
    });

    await act(async () => {
      await result.current.handleSaveTemplate();
    });

    expect(mockSaveCreationTemplate).toHaveBeenCalledWith(expect.objectContaining({
      mode: 'youtube_dub',
      payload: expect.objectContaining({
        kind: 'youtube_dub_form',
        discovery_state: expect.objectContaining({
          selected_provider: 'newznab_torznab',
          query: 'episode'
        })
      })
    }));
    expect(result.current.templateStatus).toBe(
      'Saved template "Saved Discovery Template". Apple Create can apply it from YouTube Dub.'
    );
    expect(result.current.isSavingTemplate).toBe(false);
  });
});
