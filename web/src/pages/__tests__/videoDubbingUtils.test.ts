import { describe, expect, it } from 'vitest';
import type {
  AcquisitionCandidate,
  AcquisitionJobStatusResponse,
  CreationTemplateEntry,
  VoiceInventoryResponse,
  YoutubeInlineSubtitleStream,
  YoutubeNasSubtitle,
  YoutubeNasVideo
} from '../../api/dtos';
import {
  buildVideoDubbingGeneratePayload,
  buildVideoDubbingTemplatePayload,
  buildVoiceOptions,
  canExtractEmbeddedSubtitles,
  extractVideoDubbingTemplateFormState,
  filterPlayableSubtitles,
  formatSubtitleExtractionStatus,
  hasYoutubeMetadataTitle,
  findDownloadStationCompletedVideo,
  isDownloadStationHandoffCandidate,
  makeVideoDiscoveryTemplateState,
  mergeTvMetadataPreviewWithPreservedYoutubeMetadata,
  resolveDownloadStationCompletedFiles,
  resolveVideoDubPrefill,
  resolveDefaultStreamLanguages,
  resolveSelectionAfterVideoDelete,
  resolveSubtitleNotice,
  resolveVideoDubbingSelection,
  resolveVideoDubbingMetadataSourceName,
  updateVideoDubbingMediaMetadataDraft,
  updateVideoDubbingMediaMetadataSection
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

function subtitle(overrides: Partial<YoutubeNasSubtitle>): YoutubeNasSubtitle {
  return {
    path: '/subs/example.ass',
    filename: 'example.ass',
    language: 'en',
    format: 'ass',
    ...overrides
  };
}

function video(overrides: Partial<YoutubeNasVideo>): YoutubeNasVideo {
  return {
    path: '/videos/example.mkv',
    filename: 'example.mkv',
    folder: '/videos',
    size_bytes: 100,
    modified_at: '2026-06-23T00:00:00Z',
    subtitles: [],
    ...overrides
  };
}

function acquisitionJob(
  overrides: Partial<AcquisitionJobStatusResponse> = {}
): AcquisitionJobStatusResponse {
  return {
    provider: 'download_station',
    task_id: 'task-1',
    status: 'completed',
    progress: 1,
    message: null,
    external_task_id: null,
    raw_status: 'finished',
    started_at: null,
    updated_at: '2026-06-26T12:00:00Z',
    completed_files: [],
    next_actions: ['discover_manual_downloads'],
    metadata: {},
    ...overrides,
  };
}

type GenerateInput = Parameters<typeof buildVideoDubbingGeneratePayload>[0];

function generateInput(overrides: Partial<GenerateInput> = {}): GenerateInput {
  return {
    selectedVideo: video({ path: '/videos/show.mkv' }),
    selectedSubtitle: subtitle({ path: '/subs/show.es.ass' }),
    mediaMetadataDraft: null,
    subtitleLanguageLabel: '',
    subtitleLanguageCode: '',
    targetLanguageCode: '',
    voice: '',
    startOffset: '',
    endOffset: '',
    originalMixPercent: 5,
    flushSentences: 10,
    translationBatchSize: 2,
    llmModel: '',
    translationProvider: '',
    transliterationMode: '',
    transliterationModel: '',
    splitBatches: true,
    stitchBatches: true,
    includeTransliteration: true,
    targetHeight: 480,
    preserveAspectRatio: true,
    enableLookupCache: true,
    ...overrides,
  };
}

describe('videoDubbingUtils', () => {
  it('filters playable subtitle formats for video dubbing selection', () => {
    const selectedVideo = video({
      subtitles: [
        subtitle({ path: '/subs/a.ass', filename: 'a.ass', format: 'ass' }),
        subtitle({ path: '/subs/b.srt', filename: 'b.srt', format: 'SRT' }),
        subtitle({ path: '/subs/c.txt', filename: 'c.txt', format: 'txt' }),
      ]
    });

    expect(filterPlayableSubtitles(null)).toEqual([]);
    expect(filterPlayableSubtitles(selectedVideo).map((entry) => entry.path)).toEqual([
      '/subs/a.ass',
      '/subs/b.srt',
    ]);
  });

  it('resolves metadata lookup source names from subtitle before video fallbacks', () => {
    const selectedVideo = video({
      path: '/videos/show/episode.mkv',
      filename: 'episode.mkv',
    });

    expect(
      resolveVideoDubbingMetadataSourceName({
        subtitle: subtitle({ filename: 'episode.en.ass', path: '/subs/episode.en.ass' }),
        video: selectedVideo,
      }),
    ).toBe('episode.en.ass');
    expect(
      resolveVideoDubbingMetadataSourceName({
        subtitle: subtitle({ filename: '', path: '/subs/episode.de.srt' }),
        video: selectedVideo,
      }),
    ).toBe('episode.de.srt');
    expect(resolveVideoDubbingMetadataSourceName({ subtitle: null, video: selectedVideo })).toBe('episode.mkv');
    expect(resolveVideoDubbingMetadataSourceName({ subtitle: null, video: null })).toBe('');
  });

  it('detects explicit Download Station handoff candidates with legacy fallback', () => {
    expect(
      isDownloadStationHandoffCandidate({
        provider: 'newznab_torznab',
        metadata: { handoff_provider: 'download_station' },
      }),
    ).toBe(true);
    expect(
      isDownloadStationHandoffCandidate({
        provider: 'newznab_torznab',
        metadata: { handoff_provider: ' Download_Station ' },
      }),
    ).toBe(true);
    expect(
      isDownloadStationHandoffCandidate({
        provider: 'newznab_torznab',
        metadata: { has_download_url: true },
      }),
    ).toBe(true);
    expect(
      isDownloadStationHandoffCandidate({
        provider: 'newznab_torznab',
        metadata: { has_download_url: ' true ' },
      }),
    ).toBe(true);
    expect(
      isDownloadStationHandoffCandidate({
        provider: 'youtube_search',
        metadata: { handoff_provider: 'download_station' },
      }),
    ).toBe(false);
  });

  it('resolves Download Station completed files from top-level status before metadata fallbacks', () => {
    expect(resolveDownloadStationCompletedFiles(null)).toEqual([]);
    expect(
      resolveDownloadStationCompletedFiles(acquisitionJob({
        completed_files: ['/downloads/top-level.mkv'],
        metadata: { completed_files: ['/downloads/metadata.mkv'] },
      })),
    ).toEqual(['/downloads/top-level.mkv']);
    expect(
      resolveDownloadStationCompletedFiles(acquisitionJob({
        metadata: { completed_files: ['/downloads/metadata.mkv'] },
      })),
    ).toEqual(['/downloads/metadata.mkv']);
    expect(
      resolveDownloadStationCompletedFiles(acquisitionJob({
        metadata: { files: ['/downloads/files-array.mkv'] },
      })),
    ).toEqual(['/downloads/files-array.mkv']);
    expect(
      resolveDownloadStationCompletedFiles(acquisitionJob({
        metadata: { completed_file: '/downloads/single.mkv' },
      })),
    ).toEqual(['/downloads/single.mkv']);
  });

  it('matches Download Station completed file hints to refreshed NAS videos', () => {
    const videos = [
      video({
        path: '/nas/videos/Other Episode/other.mkv',
        filename: 'other.mkv',
        folder: '/nas/videos/Other Episode',
      }),
      video({
        path: '/nas/videos/Demo Episode/Demo Episode.mkv',
        filename: 'Demo Episode.mkv',
        folder: '/nas/videos/Demo Episode',
        subtitles: [subtitle({ path: '/nas/videos/Demo Episode/Demo Episode.en.srt' })],
      }),
    ];

    expect(
      findDownloadStationCompletedVideo(videos, ['/downloads/Demo Episode.mkv'])?.path,
    ).toBe('/nas/videos/Demo Episode/Demo Episode.mkv');
    expect(
      findDownloadStationCompletedVideo(videos, ['/downloads/Demo Episode'])?.path,
    ).toBe('/nas/videos/Demo Episode/Demo Episode.mkv');
    expect(findDownloadStationCompletedVideo(videos, ['/downloads/missing.mkv'])).toBeNull();
  });

  it('copies metadata drafts before applying top-level edits', () => {
    const current = {
      job_label: 'Original label',
      youtube: { title: 'Video title' }
    };

    const next = updateVideoDubbingMediaMetadataDraft(current, (draft) => {
      draft['job_label'] = 'Updated label';
    });

    expect(next).toEqual({
      job_label: 'Updated label',
      youtube: { title: 'Video title' }
    });
    expect(current).toEqual({
      job_label: 'Original label',
      youtube: { title: 'Video title' }
    });
    expect(next).not.toBe(current);
  });

  it('copies nested metadata sections before applying edits', () => {
    const episode = { season: 1, number: 2, name: 'Old title' };
    const current = {
      episode,
      show: { name: 'Example Show' }
    };

    const next = updateVideoDubbingMediaMetadataSection(current, 'episode', (section) => {
      section['number'] = 3;
      section['name'] = 'New title';
    });

    expect(next).toEqual({
      episode: { season: 1, number: 3, name: 'New title' },
      show: { name: 'Example Show' }
    });
    expect(current.episode).toBe(episode);
    expect(current.episode).toEqual({ season: 1, number: 2, name: 'Old title' });
    expect(next.episode).not.toBe(episode);
  });

  it('preserves existing YouTube metadata when TV metadata refresh has no YouTube section', () => {
    const current = {
      youtube: { title: 'Existing video', channel: 'Channel' },
      show: { name: 'Old show' }
    };

    const next = mergeTvMetadataPreviewWithPreservedYoutubeMetadata(current, {
      show: { name: 'New show' },
      episode: { season: 2, number: 4 }
    });

    expect(next).toEqual({
      show: { name: 'New show' },
      episode: { season: 2, number: 4 },
      youtube: { title: 'Existing video', channel: 'Channel' }
    });
    expect(next?.youtube).not.toBe(current.youtube);
  });

  it('lets refreshed TV metadata override YouTube metadata when the backend provides it', () => {
    expect(
      mergeTvMetadataPreviewWithPreservedYoutubeMetadata(
        { youtube: { title: 'Old video' } },
        { youtube: { title: 'Backend video' } }
      )
    ).toEqual({
      youtube: { title: 'Backend video' }
    });
  });

  it('does not create an empty TV metadata draft just to preserve YouTube metadata', () => {
    expect(
      mergeTvMetadataPreviewWithPreservedYoutubeMetadata(
        { youtube: { title: 'Existing video' } },
        null
      )
    ).toBeNull();
  });

  it('detects usable YouTube metadata titles before auto lookup', () => {
    expect(hasYoutubeMetadataTitle({ youtube: { title: ' Existing title ' } })).toBe(true);
    expect(hasYoutubeMetadataTitle({ youtube: { title: '   ' } })).toBe(false);
    expect(hasYoutubeMetadataTitle({ youtube: { title: 42 } })).toBe(false);
    expect(hasYoutubeMetadataTitle(null)).toBe(false);
  });

  it('preserves the selected playable subtitle when the selected video is still present', () => {
    const selectedVideo = video({
      path: '/videos/show/episode.mkv',
      subtitles: [
        subtitle({ path: '/subs/episode.en.ass', filename: 'episode.en.ass', language: 'en', format: 'ass' }),
        subtitle({ path: '/subs/episode.es.srt', filename: 'episode.es.srt', language: 'es', format: 'srt' }),
      ],
    });

    const selection = resolveVideoDubbingSelection({
      videos: [selectedVideo],
      preferredVideoPath: '/videos/show/episode.mkv',
      preferredSubtitlePath: '/subs/episode.es.srt',
    });

    expect(selection.videoPath).toBe('/videos/show/episode.mkv');
    expect(selection.subtitlePath).toBe('/subs/episode.es.srt');
    expect(selection.subtitle?.language).toBe('es');
  });

  it('falls back to the first video and its English subtitle when the preferred video is missing', () => {
    const selection = resolveVideoDubbingSelection({
      videos: [
        video({
          path: '/videos/next.mkv',
          subtitles: [
            subtitle({ path: '/subs/next.fr.srt', filename: 'next.fr.srt', language: 'fr', format: 'srt' }),
            subtitle({ path: '/subs/next.en.ass', filename: 'next.en.ass', language: 'en-US', format: 'ass' }),
          ],
        }),
      ],
      preferredVideoPath: '/videos/missing.mkv',
      preferredSubtitlePath: '/subs/missing.es.srt',
    });

    expect(selection.videoPath).toBe('/videos/next.mkv');
    expect(selection.subtitlePath).toBe('/subs/next.en.ass');
  });

  it('falls back to the first video with a playable subtitle when the preferred video is missing', () => {
    const selection = resolveVideoDubbingSelection({
      videos: [
        video({
          path: '/videos/no-playable.mkv',
          subtitles: [
            subtitle({ path: '/subs/no-playable.sup', filename: 'no-playable.sup', language: 'en', format: 'sup' }),
          ],
        }),
        video({
          path: '/videos/usable.mkv',
          subtitles: [
            subtitle({ path: '/subs/usable.fr.vtt', filename: 'usable.fr.vtt', language: 'fr', format: 'vtt' }),
            subtitle({ path: '/subs/usable.en.srt', filename: 'usable.en.srt', language: 'en-US', format: 'srt' }),
          ],
        }),
      ],
      preferredVideoPath: '/videos/missing.mkv',
      preferredSubtitlePath: '/subs/missing.es.srt',
    });

    expect(selection.videoPath).toBe('/videos/usable.mkv');
    expect(selection.subtitlePath).toBe('/subs/usable.en.srt');
  });

  it('returns empty selection values for an empty video library', () => {
    expect(resolveVideoDubbingSelection({ videos: [] })).toEqual({
      video: null,
      subtitle: null,
      videoPath: null,
      subtitlePath: null,
    });
  });

  it('keeps the current selection when deleting a different video', () => {
    const kept = video({
      path: '/videos/kept.mkv',
      subtitles: [subtitle({ path: '/subs/kept.es.ass', language: 'es' })],
    });
    const deleted = video({ path: '/videos/deleted.mkv' });

    expect(
      resolveSelectionAfterVideoDelete({
        videos: [kept, deleted],
        deletedVideoPath: deleted.path,
        selectedVideoPath: kept.path,
        selectedSubtitlePath: '/subs/kept.es.ass',
      }),
    ).toEqual({
      videos: [kept],
      selectedVideoPath: kept.path,
      selectedSubtitlePath: '/subs/kept.es.ass',
      fallbackLanguage: null,
    });
  });

  it('falls back to the next video and its default subtitle when deleting the selected video', () => {
    const deleted = video({ path: '/videos/deleted.mkv' });
    const fallback = video({
      path: '/videos/fallback.mkv',
      subtitles: [
        subtitle({ path: '/subs/fallback.de.srt', language: 'de', format: 'srt' }),
        subtitle({ path: '/subs/fallback.en.ass', language: 'en-US', format: 'ass' }),
      ],
    });

    expect(
      resolveSelectionAfterVideoDelete({
        videos: [deleted, fallback],
        deletedVideoPath: deleted.path,
        selectedVideoPath: deleted.path,
        selectedSubtitlePath: '/subs/deleted.en.ass',
      }),
    ).toEqual({
      videos: [fallback],
      selectedVideoPath: fallback.path,
      selectedSubtitlePath: '/subs/fallback.en.ass',
      fallbackLanguage: 'en-US',
    });
  });

  it('clears video and subtitle selection when deleting the last video', () => {
    const deleted = video({ path: '/videos/deleted.mkv' });

    expect(
      resolveSelectionAfterVideoDelete({
        videos: [deleted],
        deletedVideoPath: deleted.path,
        selectedVideoPath: deleted.path,
        selectedSubtitlePath: '/subs/deleted.en.ass',
      }),
    ).toEqual({
      videos: [],
      selectedVideoPath: null,
      selectedSubtitlePath: null,
      fallbackLanguage: null,
    });
  });

  it('detects video containers that can expose embedded subtitle streams', () => {
    expect(canExtractEmbeddedSubtitles(null)).toBe(false);
    expect(canExtractEmbeddedSubtitles(video({ path: '/videos/movie.MKV' }))).toBe(true);
    expect(canExtractEmbeddedSubtitles(video({ path: '/videos/movie.mp4' }))).toBe(true);
    expect(canExtractEmbeddedSubtitles(video({ path: '/videos/movie.webm' }))).toBe(false);
  });

  it('formats subtitle extraction status messages', () => {
    expect(formatSubtitleExtractionStatus(0, 'episode.mkv')).toBe('No subtitle streams found to extract.');
    expect(formatSubtitleExtractionStatus(1, 'episode.mkv')).toBe('Extracted 1 subtitle track from episode.mkv.');
    expect(formatSubtitleExtractionStatus(3, 'episode.mkv')).toBe('Extracted 3 subtitle tracks from episode.mkv.');
  });

  it('resolves subtitle availability notices for the source panel', () => {
    const selectedVideo = video({ subtitles: [] });
    const playable = [subtitle({ path: '/subs/episode.en.ass', format: 'ass' })];

    expect(resolveSubtitleNotice(null, [])).toBe('Select a video to see subtitles.');
    expect(resolveSubtitleNotice(selectedVideo, [])).toBe('No subtitles were found next to this video.');
    expect(resolveSubtitleNotice(selectedVideo, playable)).toBeNull();
  });

  it('builds the YouTube dub request payload with normalized optional values', () => {
    const result = buildVideoDubbingGeneratePayload(generateInput({
      mediaMetadataDraft: { tv: { title: 'Show' } },
      subtitleLanguageLabel: 'Spanish',
      subtitleLanguageCode: 'es',
      targetLanguageCode: 'en',
      voice: '  Monica  ',
      startOffset: '01:05',
      endOffset: '01:02:03',
      originalMixPercent: 11,
      flushSentences: 8,
      translationBatchSize: 3,
      llmModel: 'gpt-4.1-mini',
      translationProvider: 'llm',
      transliterationMode: 'always',
      transliterationModel: 'uroman',
      splitBatches: false,
      stitchBatches: true,
      includeTransliteration: false,
      targetHeight: 720,
      preserveAspectRatio: false,
      enableLookupCache: false,
    }));

    expect(result).toEqual({
      error: null,
      payload: {
        video_path: '/videos/show.mkv',
        subtitle_path: '/subs/show.es.ass',
        media_metadata: { tv: { title: 'Show' } },
        source_language: 'Spanish',
        target_language: 'en',
        voice: 'Monica',
        start_time_offset: '01:05',
        end_time_offset: '01:02:03',
        original_mix_percent: 11,
        flush_sentences: 8,
        llm_model: 'gpt-4.1-mini',
        translation_provider: 'llm',
        translation_batch_size: 3,
        transliteration_mode: 'always',
        transliteration_model: 'uroman',
        split_batches: false,
        stitch_batches: true,
        include_transliteration: false,
        target_height: 720,
        preserve_aspect_ratio: false,
        enable_lookup_cache: false,
      },
    });
  });

  it('uses fallback voice and omits blank optional YouTube dub payload values', () => {
    const result = buildVideoDubbingGeneratePayload(generateInput({
      voice: '   ',
    }));

    expect(result.error).toBeNull();
    if (!result.payload) {
      throw new Error('Expected YouTube dub payload');
    }
    expect(result.payload).toMatchObject({
      video_path: '/videos/show.mkv',
      subtitle_path: '/subs/show.es.ass',
      voice: 'gTTS',
      original_mix_percent: 5,
      flush_sentences: 10,
      translation_batch_size: 2,
      split_batches: true,
      stitch_batches: true,
      include_transliteration: true,
      target_height: 480,
      preserve_aspect_ratio: true,
      enable_lookup_cache: true,
    });
    expect(result.payload.source_language).toBeUndefined();
    expect(result.payload.target_language).toBeUndefined();
    expect(result.payload.media_metadata).toBeUndefined();
    expect(result.payload.start_time_offset).toBeUndefined();
    expect(result.payload.end_time_offset).toBeUndefined();
    expect(result.payload.llm_model).toBeUndefined();
    expect(result.payload.translation_provider).toBeUndefined();
    expect(result.payload.transliteration_mode).toBeUndefined();
    expect(result.payload.transliteration_model).toBeUndefined();
  });

  it('builds a reusable YouTube dub template from the generate payload', () => {
    const result = buildVideoDubbingGeneratePayload(generateInput({
      mediaMetadataDraft: {
        youtube: { title: 'Example Video', auth_token: 'do-not-store' },
        episode: { name: 'Episode One' }
      },
      subtitleLanguageLabel: 'Spanish',
      targetLanguageCode: 'en',
      voice: 'Monica',
      startOffset: '00:15',
      endOffset: '01:45',
      llmModel: 'gpt-test'
    }));

    if (!result.payload) {
      throw new Error(result.error);
    }
    const template = buildVideoDubbingTemplatePayload(result.payload);

    expect(template).toMatchObject({
      name: 'Example Video',
      mode: 'youtube_dub',
      payload: {
        kind: 'youtube_dub_form',
        source: 'web',
        version: 1,
        form_state: {
          video_path: '/videos/show.mkv',
          subtitle_path: '/subs/show.es.ass',
          source_language: 'Spanish',
          target_language: 'en',
          voice: 'Monica',
          start_time_offset: '00:15',
          end_time_offset: '01:45',
          llm_model: 'gpt-test',
          media_metadata: {
            youtube: { title: 'Example Video' },
            episode: { name: 'Episode One' }
          }
        }
      }
    });
    const formState = template.payload.form_state as Record<string, unknown>;
    const metadata = formState.media_metadata as Record<string, unknown>;
    const youtube = metadata.youtube as Record<string, unknown>;
    expect(youtube.auth_token).toBeUndefined();
  });

  it('stores token-free video discovery state in reusable YouTube dub templates', () => {
    const candidate: AcquisitionCandidate = {
      candidate_id: 'newznab_torznab:readable-history',
      provider: 'newznab_torznab',
      media_kind: 'video',
      title: 'Readable History',
      rights: 'unknown',
      capabilities: ['search', 'metadata'],
      candidate_token: 'secret-candidate-token',
      contributors: [],
      source_url: null,
      local_path: null,
      cover_url: null,
      thumbnail_url: null,
      metadata: {
        source_kind: 'newznab_torznab',
        api_token: 'do-not-store'
      },
      subtitles: [],
      requires_confirmation: true,
      policy_notes: []
    };
    const result = buildVideoDubbingGeneratePayload(generateInput());
    if (!result.payload) {
      throw new Error(result.error);
    }
    const discoveryState = makeVideoDiscoveryTemplateState(candidate, {
      selectedProvider: 'newznab_torznab',
      query: 'history',
      selectedVideoPath: '/videos/history.mkv',
      selectedSubtitlePath: '/subs/history.en.srt'
    });
    const template = buildVideoDubbingTemplatePayload(result.payload, {
      ...discoveryState,
      candidate_token: 'secret-candidate-token'
    });

    expect(template.payload.discovery_state).toMatchObject({
      media_kind: 'video',
      provider: 'newznab_torznab',
      candidate_id: 'newznab_torznab:readable-history',
      selected_provider: 'newznab_torznab',
      query: 'history',
      selected_video_path: '/videos/history.mkv',
      selected_subtitle_path: '/subs/history.en.srt',
      source_kind: 'newznab_torznab',
      requires_confirmation: true
    });
    expect(JSON.stringify(template.payload.discovery_state)).not.toContain('candidate_token');
    expect(JSON.stringify(template.payload.discovery_state)).not.toContain('secret-candidate-token');
    expect(JSON.stringify(template.payload.discovery_state)).not.toContain('api_token');
  });

  it('extracts YouTube dub template settings for deep-linked Web handoff', () => {
    const template: CreationTemplateEntry = {
      id: 'youtube-template',
      name: 'Video Defaults',
      mode: 'youtube_dub',
      created_at: 1,
      updated_at: 2,
      payload: {
        kind: 'youtube_dub_form',
        form_state: {
          video_path: '/videos/show.mkv',
          subtitle_path: '/subs/show.es.ass',
          target_language: 'German',
          voice: 'Monica',
          start_time_offset_seconds: 15,
          end_time_offset: '01:45',
          original_mix_percent: '12',
          flush_sentences: 8,
          translation_batch_size: '6',
          target_height: 720,
          preserve_aspect_ratio: false,
          split_batches: false,
          stitch_batches: true,
          llm_model: 'gpt-test',
          translation_provider: 'googletrans',
          transliteration_mode: 'python',
          transliteration_model: 'romanizer',
          include_transliteration: false,
          enable_lookup_cache: false,
          media_metadata: {
            youtube: { title: 'Example Video' },
            auth_token: 'drop-me'
          }
        },
        discovery_state: {
          media_kind: 'video',
          provider: 'newznab_torznab',
          candidate_id: 'newznab_torznab:readable-history',
          selected_video_path: '/videos/show.mkv',
          selected_subtitle_path: '/subs/show.es.ass',
          candidate_token: 'drop-me'
        }
      }
    };

    expect(extractVideoDubbingTemplateFormState(template)).toEqual({
      videoPath: '/videos/show.mkv',
      subtitlePath: '/subs/show.es.ass',
      targetLanguage: 'German',
      voice: 'Monica',
      startOffset: '00:15',
      endOffset: '01:45',
      originalMixPercent: 12,
      flushSentences: 8,
      translationBatchSize: 6,
      targetHeight: 720,
      preserveAspectRatio: false,
      splitBatches: false,
      stitchBatches: true,
      llmModel: 'gpt-test',
      translationProvider: 'googletrans',
      transliterationMode: 'python',
      transliterationModel: 'romanizer',
      includeTransliteration: false,
      enableLookupCache: false,
      mediaMetadataDraft: {
        youtube: { title: 'Example Video' }
      },
      discoveryState: {
        media_kind: 'video',
        provider: 'newznab_torznab',
        candidate_id: 'newznab_torznab:readable-history',
        selected_video_path: '/videos/show.mkv',
        selected_subtitle_path: '/subs/show.es.ass'
      }
    });
  });

  it('rejects YouTube dub generation without a selected video and subtitle', () => {
    const result = buildVideoDubbingGeneratePayload(generateInput({
      selectedVideo: null,
      selectedSubtitle: null,
    }));

    expect(result).toEqual({
      payload: null,
      error: 'Choose a video and an ASS subtitle before generating audio.',
    });
  });

  it('rejects invalid and inverted YouTube dub clip offsets', () => {
    expect(
      buildVideoDubbingGeneratePayload(generateInput({
        startOffset: 'bad',
        endOffset: '',
      })),
    ).toEqual({
      payload: null,
      error: 'Offsets must be numbers or timecodes like HH:MM:SS',
    });
    expect(
      buildVideoDubbingGeneratePayload(generateInput({
        startOffset: '02:00',
        endOffset: '01:59',
      })),
    ).toEqual({
      payload: null,
      error: 'End offset must be greater than start offset.',
    });
  });

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
        stitch_batches: false,
        llm_model: ' gpt-4.1-mini ',
        translation_provider: ' llm ',
        transliteration_mode: ' always ',
        transliteration_model: ' uroman ',
        include_transliteration: false,
        enable_lookup_cache: false
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
      stitchBatches: false,
      llmModel: 'gpt-4.1-mini',
      translationProvider: 'llm',
      transliterationMode: 'always',
      transliterationModel: 'uroman',
      includeTransliteration: false,
      enableLookupCache: false
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
        stitch_batches: null,
        include_transliteration: null,
        enable_lookup_cache: null
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
      stitchBatches: undefined,
      llmModel: undefined,
      translationProvider: undefined,
      transliterationMode: undefined,
      transliterationModel: undefined,
      includeTransliteration: true,
      enableLookupCache: undefined
    });
  });

  it('returns null when no video dub prefill snapshot is present', () => {
    expect(resolveVideoDubPrefill(null)).toBeNull();
    expect(resolveVideoDubPrefill(undefined)).toBeNull();
  });
});
