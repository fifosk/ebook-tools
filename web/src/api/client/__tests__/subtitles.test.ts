import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  assistantLookup,
  deleteSubtitleSource,
  extractInlineSubtitles,
  fetchInlineSubtitleStreams,
  fetchSubtitleModels,
  fetchSubtitleSources,
  fetchSubtitleTvMetadata,
  fetchYoutubeVideoMetadata,
  fetchYoutubeLibrary,
  generateYoutubeDub,
  lookupSubtitleTvMetadataPreview,
  lookupYoutubeVideoMetadataPreview,
  submitSubtitleJob
} from '../subtitles';

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { 'Content-Type': 'application/json' }
  });
}

describe('subtitles API client', () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('uses shared subtitle, YouTube, and linguist routes with encoded queries', async () => {
    const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>();
    for (let index = 0; index < 13; index += 1) {
      fetchMock.mockResolvedValueOnce(jsonResponse({ sources: [] }));
    }
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await fetchSubtitleSources('/media/subs?season=1');
    await deleteSubtitleSource('/media/show.en.srt', '/media');
    await fetchSubtitleModels();
    await fetchSubtitleTvMetadata('job/with?parts');
    await lookupSubtitleTvMetadataPreview({ source_name: 'show s01e01', force: true });
    await fetchYoutubeVideoMetadata('job/with?parts');
    await lookupYoutubeVideoMetadataPreview({ source_name: 'clip id', force: false });
    await fetchYoutubeLibrary('/nas/videos?kind=series');
    await fetchInlineSubtitleStreams('/nas/videos/show one.mkv');
    await extractInlineSubtitles('/nas/videos/show one.mkv', ['en', 'tr']);
    await generateYoutubeDub({ video_path: '/video.mkv', subtitle_path: '/sub.srt' });
    await submitSubtitleJob(new FormData());
    await assistantLookup({
      query: 'merhaba',
      input_language: 'tr',
      lookup_language: 'en'
    });

    expect(fetchMock).toHaveBeenCalledTimes(13);

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
      '/api/subtitles/metadata/tv/lookup'
    );
    expect(new URL(String(fetchMock.mock.calls[5][0])).pathname).toBe(
      '/api/subtitles/jobs/job%2Fwith%3Fparts/metadata/youtube'
    );
    expect(new URL(String(fetchMock.mock.calls[6][0])).pathname).toBe(
      '/api/subtitles/metadata/youtube/lookup'
    );

    const youtubeLibraryUrl = new URL(String(fetchMock.mock.calls[7][0]));
    expect(youtubeLibraryUrl.pathname).toBe('/api/subtitles/youtube/library');
    expect(youtubeLibraryUrl.searchParams.get('base_dir')).toBe('/nas/videos?kind=series');

    const streamsUrl = new URL(String(fetchMock.mock.calls[8][0]));
    expect(streamsUrl.pathname).toBe('/api/subtitles/youtube/subtitle-streams');
    expect(streamsUrl.searchParams.get('video_path')).toBe('/nas/videos/show one.mkv');

    expect(new URL(String(fetchMock.mock.calls[9][0])).pathname).toBe(
      '/api/subtitles/youtube/extract-subtitles'
    );
    expect(new URL(String(fetchMock.mock.calls[10][0])).pathname).toBe(
      '/api/subtitles/youtube/dub'
    );
    expect(new URL(String(fetchMock.mock.calls[11][0])).pathname).toBe('/api/subtitles/jobs');
    expect(new URL(String(fetchMock.mock.calls[12][0])).pathname).toBe('/api/assistant/lookup');
  });
});
