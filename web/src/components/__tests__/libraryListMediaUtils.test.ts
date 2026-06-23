import { describe, expect, it, vi } from 'vitest';
import type { LibraryItem } from '../../api/dtos';
import {
  extractTvMediaMetadata,
  extractYoutubeVideoMetadata,
  resolveBookSummary,
  resolveSubtitleEpisodeParts,
  resolveSubtitleGenres,
  resolveSubtitleShowName,
  resolveSubtitleSummary,
  resolveTvImage,
  resolveVideoSourcePill,
  resolveYoutubeChannel,
  resolveYoutubeSummary,
  resolveYoutubeThumbnail,
  resolveYoutubeTitle,
  videoSourceBadgeFromLabel
} from '../library-list/libraryListMediaUtils';

vi.mock('../../api/client', () => ({
  appendAccessToken: (url: string) => `token:${url}`,
  resolveLibraryMediaUrl: (jobId: string, relativePath: string) => `library:${jobId}:${relativePath}`
}));

function item(overrides: Partial<LibraryItem> = {}): LibraryItem {
  return {
    jobId: 'job-1',
    author: '',
    bookTitle: '',
    itemType: 'narrated_subtitle',
    language: 'en',
    status: 'finished',
    mediaCompleted: true,
    createdAt: '2026-06-23T10:00:00Z',
    updatedAt: '2026-06-23T10:00:00Z',
    libraryPath: '/library/job-1',
    metadata: {},
    ...overrides
  };
}

describe('libraryListMediaUtils', () => {
  it('resolves book summaries from media metadata fallbacks', () => {
    expect(resolveBookSummary(item({ metadata: { media_metadata: { book_summary: '  Primary summary  ' } } }))).toBe(
      'Primary summary',
    );
    expect(resolveBookSummary(item({ metadata: { result: { book_metadata: { description: 'Description' } } } }))).toBe(
      'Description',
    );
    expect(resolveBookSummary(item({ metadata: { media_metadata: { summary: '   ' } } }))).toBeNull();
  });

  it('extracts TV metadata from supported library payload shapes', () => {
    expect(
      extractTvMediaMetadata(
        item({
          metadata: {
            result: {
              subtitle: {
                metadata: {
                  media_metadata: { show: { name: 'Nested Show' } }
                }
              }
            }
          }
        }),
      )?.show,
    ).toEqual({ name: 'Nested Show' });

    expect(extractTvMediaMetadata(item({ metadata: { request: { media_metadata: { show: { name: 'Request Show' } } } } }))).toEqual({
      show: { name: 'Request Show' }
    });
  });

  it('resolves subtitle display metadata with explicit values before TV fallbacks', () => {
    const tvMetadata = {
      show: {
        name: 'TV Show',
        summary: 'Show summary',
        genres: ['Drama', ' Mystery ', '', 42]
      },
      episode: {
        season: 2,
        number: 3,
        name: 'Episode Name',
        airdate: '2026-06-01',
        summary: 'Episode summary'
      }
    };
    const libraryItem = item({
      author: '',
      metadata: {
        series_title: ' Explicit Series ',
        episode_title: ' Explicit Episode ',
        series_genres: [' Sci-Fi ', 'Comedy', 'Drama', 'Extra']
      }
    });

    expect(resolveSubtitleShowName(libraryItem, tvMetadata)).toBe('Explicit Series');
    expect(resolveSubtitleEpisodeParts(libraryItem, tvMetadata)).toEqual({
      code: 'S02E03',
      title: 'Explicit Episode',
      airdate: '2026-06-01'
    });
    expect(resolveSubtitleSummary(tvMetadata)).toBe('Episode summary');
    expect(resolveSubtitleGenres(libraryItem, tvMetadata)).toEqual(['Sci-Fi', 'Comedy', 'Drama']);
  });

  it('falls back to untitled subtitle labels and TV episode genres', () => {
    const tvMetadata = {
      show: {
        name: 'Fallback Show',
        summary: 'Fallback summary',
        genres: ['One', 'Two', 'Three', 'Four']
      },
      episode: {
        season: 0,
        number: 3
      }
    };

    expect(resolveSubtitleShowName(item({ author: '' }), null)).toBe('Untitled Subtitle');
    expect(resolveSubtitleShowName(item({ author: 'Author Name' }), null)).toBe('Author Name');
    expect(resolveSubtitleGenres(item(), tvMetadata)).toEqual(['One', 'Two', 'Three']);
    expect(resolveSubtitleEpisodeParts(item(), tvMetadata)).toEqual({
      code: null,
      title: null,
      airdate: null
    });
  });

  it('resolves image and YouTube metadata assets', () => {
    const tvMetadata = {
      episode: { image: { medium: 'episode.jpg', original: 'episode-original.jpg' } },
      show: { image: '/api/library/media/job-1/file/show.jpg' },
      youtube: {
        title: ' YouTube Title ',
        uploader: 'Uploader Name',
        description: 'Video description',
        thumbnail: 'https://example.com/thumb.jpg'
      }
    };
    const youtube = extractYoutubeVideoMetadata(tvMetadata);

    expect(resolveTvImage('job-1', tvMetadata, 'episode')).toBe('library:job-1:episode.jpg');
    expect(resolveTvImage('job-1', tvMetadata, 'show')).toBe('token:/api/library/media/job-1/file/show.jpg');
    expect(resolveYoutubeTitle(youtube)).toBe('YouTube Title');
    expect(resolveYoutubeChannel(youtube)).toBe('Uploader Name');
    expect(resolveYoutubeSummary(youtube)).toBe('Video description');
    expect(resolveYoutubeThumbnail('job-1', youtube)).toBe('https://example.com/thumb.jpg');
  });

  it('normalizes video source labels and badges', () => {
    expect(resolveVideoSourcePill(item({ metadata: { request: { source_kind: 'youtube' } } }))).toBe('YouTube');
    expect(resolveVideoSourcePill(item({ metadata: { result: { youtube_dub: { source_kind: 'nas_video' } } } }))).toBe('NAS');
    expect(resolveVideoSourcePill(item({ metadata: { source_kind: ' local_file ' } }))).toBe('local_file');
    expect(videoSourceBadgeFromLabel('YouTube')).toEqual({ icon: '📺', label: 'YT', title: 'YouTube download' });
    expect(videoSourceBadgeFromLabel('NAS')).toEqual({ icon: '🗃', label: 'NAS', title: 'NAS video' });
    expect(videoSourceBadgeFromLabel('File')).toEqual({ icon: '📦', label: 'File', title: 'File' });
  });
});
