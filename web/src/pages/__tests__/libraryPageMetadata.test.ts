import { describe, expect, it } from 'vitest';
import type { LibraryItem } from '../../api/dtos';
import {
  buildLibraryMetadataUpdatePlan,
  buildLibraryItemBuckets,
  extractTvMediaMetadata,
  extractYoutubeVideoMetadata,
  formatCount,
  formatLibraryRangeLabel,
  formatYoutubeUploadDate,
  mergeIsbnMetadataIntoEditValues,
  readNestedValue,
  resolveAuthor,
  resolveGenre,
  resolveIsbnPreviewCoverCandidate,
  resolveItemType,
  resolveLibraryAssetUrl,
  resolveLibraryTotalPages,
  selectActiveLibraryItems,
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

  it('buckets library items by active surface type while preserving order', () => {
    const book = makeItem({ jobId: 'book-1', itemType: 'book' });
    const video = makeItem({ jobId: 'video-1', itemType: 'video' });
    const subtitle = makeItem({ jobId: 'subtitle-1', itemType: 'narrated_subtitle' });
    const unknown = makeItem({ jobId: 'legacy-book', itemType: undefined });

    const buckets = buildLibraryItemBuckets([video, book, subtitle, unknown]);

    expect(buckets.videoItems.map((item) => item.jobId)).toEqual(['video-1']);
    expect(buckets.bookItems.map((item) => item.jobId)).toEqual(['book-1', 'legacy-book']);
    expect(buckets.subtitleItems.map((item) => item.jobId)).toEqual(['subtitle-1']);
    expect(selectActiveLibraryItems(buckets, 'video')).toBe(buckets.videoItems);
    expect(selectActiveLibraryItems(buckets, 'narrated_subtitle')).toBe(buckets.subtitleItems);
    expect(selectActiveLibraryItems(buckets, 'book')).toBe(buckets.bookItems);
  });

  it('formats library pagination totals and range labels', () => {
    expect(resolveLibraryTotalPages(0, 25)).toBe(1);
    expect(resolveLibraryTotalPages(51, 25)).toBe(3);
    expect(resolveLibraryTotalPages(10, 0)).toBe(1);

    expect(formatLibraryRangeLabel({ total: 0, page: 1, pageSize: 25, itemCount: 0 })).toBe('No results');
    expect(formatLibraryRangeLabel({ total: 51, page: 1, pageSize: 25, itemCount: 25 })).toBe(
      'Showing 1–25 of 51',
    );
    expect(formatLibraryRangeLabel({ total: 51, page: 3, pageSize: 25, itemCount: 1 })).toBe(
      'Showing 51–51 of 51',
    );
    expect(formatLibraryRangeLabel({ total: 3, page: -2, pageSize: 25, itemCount: 3 })).toBe(
      'Showing 1–3 of 3',
    );
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

  it('merges ISBN preview metadata into edit fields without erasing existing values', () => {
    expect(
      mergeIsbnMetadataIntoEditValues(
        {
          title: 'Existing title',
          author: 'Existing author',
          genre: 'Existing genre',
          language: 'en',
          isbn: '',
        },
        {
          book_title: '  Lookup title  ',
          book_author: '',
          book_genre: ' Mystery ',
          book_language: ' de ',
        },
        '9781234567890',
      ),
    ).toEqual({
      title: 'Lookup title',
      author: 'Existing author',
      genre: 'Mystery',
      language: 'de',
      isbn: '9781234567890',
    });

    expect(
      mergeIsbnMetadataIntoEditValues(
        {
          title: 'Existing title',
          author: 'Existing author',
          genre: 'Existing genre',
          language: 'en',
          isbn: 'kept-isbn',
        },
        {
          book_title: null,
          book_author: 'Lookup author',
        },
        'fallback-isbn',
      ).isbn,
    ).toBe('kept-isbn');
  });

  it('resolves ISBN preview cover candidates by preferring local cover files', () => {
    expect(
      resolveIsbnPreviewCoverCandidate({
        book_cover_file: ' covers/book.jpg ',
        cover_url: 'https://example.test/cover.jpg',
      }),
    ).toBe('covers/book.jpg');
    expect(resolveIsbnPreviewCoverCandidate({ cover_url: ' https://example.test/cover.jpg ' })).toBe(
      'https://example.test/cover.jpg',
    );
    expect(resolveIsbnPreviewCoverCandidate({ book_cover_file: ' ', cover_url: null })).toBeNull();
  });

  it('builds trimmed metadata update payloads without an ISBN side effect when unchanged', () => {
    const plan = buildLibraryMetadataUpdatePlan(
      makeItem({ isbn: '9781234567890' }),
      {
        title: '  Updated title  ',
        author: '  Updated author  ',
        genre: '   ',
        language: ' en ',
        isbn: ' 9781234567890 ',
      },
    );

    expect(plan).toEqual({
      payload: {
        title: 'Updated title',
        author: 'Updated author',
        genre: null,
        language: 'en',
        isbn: '9781234567890',
      },
      isbnToApply: null,
    });
  });

  it('separates changed ISBN apply from the regular metadata update payload', () => {
    const plan = buildLibraryMetadataUpdatePlan(
      makeItem({ isbn: '9781234567890' }),
      {
        title: 'Title',
        author: 'Author',
        genre: 'Fiction',
        language: 'de',
        isbn: ' 9780987654321 ',
      },
    );

    expect(plan.payload.isbn).toBe('9780987654321');
    expect(plan.isbnToApply).toBe('9780987654321');
  });

  it('keeps explicit ISBN clears in the metadata payload', () => {
    const plan = buildLibraryMetadataUpdatePlan(
      makeItem({ isbn: '9781234567890' }),
      {
        title: 'Title',
        author: 'Author',
        genre: 'History',
        language: 'fr',
        isbn: '   ',
      },
    );

    expect(plan.payload.isbn).toBe('');
    expect(plan.isbnToApply).toBeNull();
  });
});
