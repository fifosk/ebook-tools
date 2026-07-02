import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  assistantLookup,
  deleteNasSubtitle,
  deleteSubtitleSource,
  deleteYoutubeVideo,
  downloadYoutubeSubtitle,
  downloadYoutubeVideo,
  extractInlineSubtitles,
  fetchInlineSubtitleStreams,
  fetchSubtitleModels,
  fetchSubtitleResult,
  fetchSubtitleSources,
  fetchSubtitleTvMetadata,
  fetchYoutubeSubtitleTracks,
  fetchYoutubeVideoMetadata,
  fetchYoutubeLibrary,
  generateYoutubeDub,
  lookupSubtitleTvMetadata,
  lookupSubtitleTvMetadataPreview,
  lookupYoutubeVideoMetadata,
  lookupYoutubeVideoMetadataPreview,
  submitSubtitleJob
} from '../subtitles';

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { 'Content-Type': 'application/json' }
  });
}

function subtitleSource(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    name: 'show.en.srt',
    path: '/media/show.en.srt',
    format: 'srt',
    language: 'en',
    modified_at: '2026-07-02T12:00:00Z',
    ...overrides
  };
}

function subtitleSourceListResponse(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    sources: [subtitleSource()],
    ...overrides
  };
}

function youtubeNasSubtitle(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    path: '/nas/videos/show.en.srt',
    filename: 'show.en.srt',
    language: 'en',
    format: 'srt',
    ...overrides
  };
}

function youtubeNasVideo(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    path: '/nas/videos/show one.mkv',
    filename: 'show one.mkv',
    folder: '/nas/videos',
    size_bytes: 42,
    modified_at: '2026-07-02T12:00:00Z',
    source: 'youtube',
    linked_job_ids: [],
    subtitles: [youtubeNasSubtitle()],
    ...overrides
  };
}

function youtubeLibraryResponse(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    base_dir: '/nas/videos',
    videos: [youtubeNasVideo()],
    ...overrides
  };
}

function inlineSubtitleStreamsResponse(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    video_path: '/nas/videos/show one.mkv',
    streams: [
      {
        index: 2,
        position: 0,
        language: 'en',
        codec: 'subrip',
        title: 'English',
        can_extract: true
      }
    ],
    ...overrides
  };
}

function subtitleExtractionResponse(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    video_path: '/nas/videos/show one.mkv',
    extracted: [youtubeNasSubtitle()],
    ...overrides
  };
}

describe('subtitles API client', () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('uses shared subtitle, YouTube, and linguist routes with encoded queries', async () => {
    const responses = [
      subtitleSourceListResponse(),
      { subtitle_path: '/media/show.en.srt', base_dir: '/media', removed: [], missing: [] },
      { models: ['model-a'] },
      { job_id: 'job-id', source_name: null, parsed: null, media_metadata: null },
      { job_id: 'job-id', source_name: null, parsed: null, media_metadata: null },
      { source_name: null, parsed: null, media_metadata: null },
      { job_id: 'job-id', source_name: null, parsed: null, youtube_metadata: null },
      { job_id: 'job-id', source_name: null, parsed: null, youtube_metadata: null },
      { source_name: null, parsed: null, youtube_metadata: null },
      { video_id: 'clip', title: null, tracks: [], video_formats: [] },
      { output_path: '/out/sub.srt', filename: 'sub.srt' },
      { output_path: '/out/video.mp4', filename: 'video.mp4', folder: '/out' },
      youtubeLibraryResponse(),
      inlineSubtitleStreamsResponse(),
      subtitleExtractionResponse(),
      { video_path: '/nas/videos/show one.mkv', subtitle_path: '/nas/videos/show one.en.srt', removed: [], missing: [] },
      { video_path: '/nas/videos/show one.mkv', removed: [], missing: [] },
      { job_id: 'dub-job', status: 'queued' },
      { job_id: 'subtitle-job', status: 'queued' },
      { job_id: 'job-id', status: 'completed' },
      { response: 'hello' }
    ];
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>();
    for (const payload of responses) {
      fetchMock.mockResolvedValueOnce(jsonResponse(payload));
    }
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await fetchSubtitleSources('/media/subs?season=1');
    await deleteSubtitleSource('/media/show.en.srt', '/media');
    await fetchSubtitleModels();
    await fetchSubtitleTvMetadata('job/with?parts');
    await lookupSubtitleTvMetadata('job/with?parts', { force: true });
    await lookupSubtitleTvMetadataPreview({ source_name: 'show s01e01', force: true });
    await fetchYoutubeVideoMetadata('job/with?parts');
    await lookupYoutubeVideoMetadata('job/with?parts', { force: true });
    await lookupYoutubeVideoMetadataPreview({ source_name: 'clip id', force: false });
    await fetchYoutubeSubtitleTracks('https://youtube.example/watch?v=clip one');
    await downloadYoutubeSubtitle({
      url: 'https://youtube.example/watch?v=clip one',
      language: 'en',
      kind: 'manual'
    });
    await downloadYoutubeVideo({ url: 'https://youtube.example/watch?v=clip one' });
    await fetchYoutubeLibrary('/nas/videos?kind=series');
    await fetchInlineSubtitleStreams('/nas/videos/show one.mkv');
    await extractInlineSubtitles('/nas/videos/show one.mkv', ['en', 'tr']);
    await deleteNasSubtitle('/nas/videos/show one.mkv', '/nas/videos/show one.en.srt');
    await deleteYoutubeVideo({ video_path: '/nas/videos/show one.mkv' });
    await generateYoutubeDub({ video_path: '/video.mkv', subtitle_path: '/sub.srt' });
    await submitSubtitleJob(new FormData());
    await fetchSubtitleResult('job/with?parts');
    await assistantLookup({
      query: 'merhaba',
      input_language: 'tr',
      lookup_language: 'en'
    });

    expect(fetchMock).toHaveBeenCalledTimes(21);

    const subtitleSourcesUrl = new URL(String(fetchMock.mock.calls[0][0]));
    expect(subtitleSourcesUrl.pathname).toBe('/api/subtitles/sources');
    expect(subtitleSourcesUrl.searchParams.get('directory')).toBe('/media/subs?season=1');

    expect(new URL(String(fetchMock.mock.calls[1][0])).pathname).toBe(
      '/api/subtitles/delete-source'
    );
    expect(new URL(String(fetchMock.mock.calls[2][0])).pathname).toBe('/api/subtitles/models');
    expect(new URL(String(fetchMock.mock.calls[3][0])).pathname).toBe(
      '/api/subtitles/jobs/job%2Fwith%3Fparts/metadata/tv'
    );
    expect(new URL(String(fetchMock.mock.calls[4][0])).pathname).toBe(
      '/api/subtitles/jobs/job%2Fwith%3Fparts/metadata/tv/lookup'
    );
    expect(new URL(String(fetchMock.mock.calls[5][0])).pathname).toBe(
      '/api/subtitles/metadata/tv/lookup'
    );
    expect(new URL(String(fetchMock.mock.calls[6][0])).pathname).toBe(
      '/api/subtitles/jobs/job%2Fwith%3Fparts/metadata/youtube'
    );
    expect(new URL(String(fetchMock.mock.calls[7][0])).pathname).toBe(
      '/api/subtitles/jobs/job%2Fwith%3Fparts/metadata/youtube/lookup'
    );
    expect(new URL(String(fetchMock.mock.calls[8][0])).pathname).toBe(
      '/api/subtitles/metadata/youtube/lookup'
    );

    const tracksUrl = new URL(String(fetchMock.mock.calls[9][0]));
    expect(tracksUrl.pathname).toBe('/api/subtitles/youtube/subtitles');
    expect(tracksUrl.searchParams.get('url')).toBe('https://youtube.example/watch?v=clip one');

    expect(new URL(String(fetchMock.mock.calls[10][0])).pathname).toBe(
      '/api/subtitles/youtube/download'
    );
    expect(new URL(String(fetchMock.mock.calls[11][0])).pathname).toBe(
      '/api/subtitles/youtube/video'
    );

    const youtubeLibraryUrl = new URL(String(fetchMock.mock.calls[12][0]));
    expect(youtubeLibraryUrl.pathname).toBe('/api/subtitles/youtube/library');
    expect(youtubeLibraryUrl.searchParams.get('base_dir')).toBe('/nas/videos?kind=series');

    const streamsUrl = new URL(String(fetchMock.mock.calls[13][0]));
    expect(streamsUrl.pathname).toBe('/api/subtitles/youtube/subtitle-streams');
    expect(streamsUrl.searchParams.get('video_path')).toBe('/nas/videos/show one.mkv');

    expect(new URL(String(fetchMock.mock.calls[14][0])).pathname).toBe(
      '/api/subtitles/youtube/extract-subtitles'
    );
    expect(new URL(String(fetchMock.mock.calls[15][0])).pathname).toBe(
      '/api/subtitles/youtube/delete-subtitle'
    );
    expect(new URL(String(fetchMock.mock.calls[16][0])).pathname).toBe(
      '/api/subtitles/youtube/delete-video'
    );
    expect(new URL(String(fetchMock.mock.calls[17][0])).pathname).toBe(
      '/api/subtitles/youtube/dub'
    );
    expect(new URL(String(fetchMock.mock.calls[18][0])).pathname).toBe('/api/subtitles/jobs');
    expect(new URL(String(fetchMock.mock.calls[19][0])).pathname).toBe(
      '/api/subtitles/jobs/job%2Fwith%3Fparts/result'
    );
    expect(new URL(String(fetchMock.mock.calls[20][0])).pathname).toBe('/api/assistant/lookup');
  });

  it('rejects malformed subtitle and YouTube source picker payloads', async () => {
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>()
      .mockResolvedValueOnce(jsonResponse(subtitleSourceListResponse({ sources: undefined })))
      .mockResolvedValueOnce(jsonResponse(subtitleSourceListResponse({
        sources: [subtitleSource({ path: undefined })]
      })))
      .mockResolvedValueOnce(jsonResponse(youtubeLibraryResponse({ videos: undefined })))
      .mockResolvedValueOnce(jsonResponse(youtubeLibraryResponse({
        videos: [youtubeNasVideo({ linked_job_ids: [42] })]
      })))
      .mockResolvedValueOnce(jsonResponse(youtubeLibraryResponse({
        videos: [youtubeNasVideo({ subtitles: [youtubeNasSubtitle({ format: undefined })] })]
      })))
      .mockResolvedValueOnce(jsonResponse(inlineSubtitleStreamsResponse({ streams: undefined })))
      .mockResolvedValueOnce(jsonResponse(inlineSubtitleStreamsResponse({
        streams: [{ index: 2, position: 0, can_extract: 'yes' }]
      })))
      .mockResolvedValueOnce(jsonResponse(subtitleExtractionResponse({ extracted: undefined })))
      .mockResolvedValueOnce(jsonResponse(subtitleExtractionResponse({
        extracted: [youtubeNasSubtitle({ filename: undefined })]
      })));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await expect(fetchSubtitleSources()).rejects.toThrow(
      'Invalid subtitle source list response: missing sources.'
    );
    await expect(fetchSubtitleSources()).rejects.toThrow(
      'Invalid subtitle source list response: missing path.'
    );
    await expect(fetchYoutubeLibrary()).rejects.toThrow(
      'Invalid YouTube NAS library response: missing videos.'
    );
    await expect(fetchYoutubeLibrary()).rejects.toThrow(
      'Invalid YouTube NAS library response: missing linked_job_ids.'
    );
    await expect(fetchYoutubeLibrary()).rejects.toThrow(
      'Invalid YouTube NAS library response: missing format.'
    );
    await expect(fetchInlineSubtitleStreams('/video.mkv')).rejects.toThrow(
      'Invalid YouTube subtitle stream list response: missing streams.'
    );
    await expect(fetchInlineSubtitleStreams('/video.mkv')).rejects.toThrow(
      'Invalid YouTube subtitle stream list response: missing can_extract.'
    );
    await expect(extractInlineSubtitles('/video.mkv')).rejects.toThrow(
      'Invalid YouTube subtitle extraction response: missing extracted.'
    );
    await expect(extractInlineSubtitles('/video.mkv')).rejects.toThrow(
      'Invalid YouTube subtitle extraction response: missing filename.'
    );
  });
});
