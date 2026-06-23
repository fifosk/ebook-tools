import { describe, expect, it } from 'vitest';
import type { LibraryItem } from '../../api/dtos';
import {
  extractTvMediaMetadata,
  extractYoutubeVideoMetadata,
  formatCount,
  formatYoutubeUploadDate,
  readNestedValue,
  resolveAuthor,
  resolveGenre,
  resolveItemType,
  resolveLibraryAssetUrl,
  resolveTitle,
  resolveTvImage,
  resolveYoutubeThumbnail
} from '../library/libraryPageMetadata';

function makeItem(overrides: Partial<LibraryItem> = {}): LibraryItem {
  return {
    jobId: 'job-1',
    author: '',
    bookTitle: '',
    itemType: 'book',
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

describe('libraryPageMetadata', () => {
  it('resolves item type, title, author, and genre fallbacks by surface type', () => {
    const video = makeItem({ itemType: 'video' });
    const subtitle = makeItem({ itemType: 'narrated_subtitle' });
    const titled = makeItem({
      itemType: 'book',
      bookTitle: '  The Book  ',
      author: '  A. Writer  ',
      genre: '  Fantasy  '
    });

    expect(resolveItemType(null)).toBe('book');
    expect(resolveTitle(video)).toBe('Untitled Video');
    expect(resolveAuthor(video)).toBe('Unknown Creator');
    expect(resolveGenre(video)).toBe('Video');
    expect(resolveTitle(subtitle)).toBe('Untitled Subtitle');
    expect(resolveAuthor(subtitle)).toBe('Subtitles');
    expect(resolveGenre(subtitle)).toBe('Subtitles');
    expect(resolveTitle(titled)).toBe('The Book');
    expect(resolveAuthor(titled)).toBe('A. Writer');
    expect(resolveGenre(titled)).toBe('Fantasy');
  });

  it('extracts TV and YouTube metadata from nested backend payloads', () => {
    const item = makeItem({
      metadata: {
        result: {
          youtube_dub: {
            media_metadata: {
              show: { name: 'Example Show' },
              youtube: { channel: 'Example Channel' }
            }
          }
        }
      }
    });

    const tvMetadata = extractTvMediaMetadata(item);

    expect(readNestedValue(item.metadata, ['result', 'youtube_dub', 'media_metadata', 'show', 'name'])).toBe('Example Show');
    expect(tvMetadata?.show).toEqual({ name: 'Example Show' });
    expect(extractYoutubeVideoMetadata(tvMetadata)?.channel).toBe('Example Channel');
  });

  it('resolves library image and thumbnail candidates without losing links', () => {
    expect(resolveLibraryAssetUrl('job-1', '/api/library/items')).toBe('/api/library/items');
    expect(resolveLibraryAssetUrl('job-1', '/covers/poster.jpg')).toBe('/covers/poster.jpg');
    expect(resolveLibraryAssetUrl('job-1', 'https://example.test/poster.jpg')).toBe('https://example.test/poster.jpg');
    expect(resolveLibraryAssetUrl('job-1', 'media/poster one.jpg')).toContain('/api/library/media/job-1/file/media/poster%20one.jpg');

    const tvImage = resolveTvImage(
      'job-1',
      {
        show: {
          image: {
            medium: '/api/library/media/job-1/poster-medium.jpg',
            original: 'https://example.test/poster-original.jpg'
          }
        }
      },
      'show'
    );
    expect(tvImage).toEqual({
      src: '/api/library/media/job-1/poster-medium.jpg',
      link: 'https://example.test/poster-original.jpg'
    });

    expect(
      resolveYoutubeThumbnail('job-1', {
        thumbnail: 'thumb.jpg',
        webpage_url: 'https://youtube.test/watch?v=abc'
      })
    ).toMatchObject({
      link: 'https://youtube.test/watch?v=abc'
    });
  });

  it('formats YouTube numeric and date metadata for the details panel', () => {
    expect(formatCount(12345.9)).toBe('12,345');
    expect(formatCount('123')).toBeNull();
    expect(formatYoutubeUploadDate('20260623')).toBe('2026-06-23');
    expect(formatYoutubeUploadDate('  live soon  ')).toBe('live soon');
  });
});
