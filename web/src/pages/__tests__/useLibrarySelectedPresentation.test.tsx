import { renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { LibraryItem } from '../../api/dtos';
import { useLibrarySelectedPresentation } from '../library/useLibrarySelectedPresentation';

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
    ...overrides,
  };
}

describe('useLibrarySelectedPresentation', () => {
  it('builds book presentation values and prefers edit preview cover while editing', () => {
    const selectedItem = makeItem({
      bookTitle: '  The Selected Book  ',
      author: '  Author Name  ',
      genre: '  Mystery  ',
      metadata: {
        job_type: 'book',
        media_metadata: {
          book_cover_file: 'covers/book.jpg',
        },
      },
    });

    const { result, rerender } = renderHook(
      ({ isEditing, previewCoverUrl }) =>
        useLibrarySelectedPresentation({ selectedItem, isEditing, previewCoverUrl }),
      {
        initialProps: {
          isEditing: false,
          previewCoverUrl: null as string | null,
        },
      },
    );

    expect(result.current.itemType).toBe('book');
    expect(result.current.title).toBe('The Selected Book');
    expect(result.current.author).toBe('Author Name');
    expect(result.current.genre).toBe('Mystery');
    expect(result.current.jobType).toBe('book');
    expect(result.current.jobGlyph.label).toBe('Book job');
    expect(result.current.coverUrl).toContain('/api/library/media/job-1/file/covers/book.jpg');
    expect(result.current.displayedCoverUrl).toBe(result.current.coverUrl);

    rerender({ isEditing: true, previewCoverUrl: '/preview/cover.jpg' });

    expect(result.current.displayedCoverUrl).toBe('/preview/cover.jpg');
  });

  it('builds video presentation with TV and YouTube artwork metadata', () => {
    const selectedItem = makeItem({
      jobId: 'video-1',
      itemType: 'video',
      metadata: {
        type: 'youtube_dub',
        result: {
          youtube_dub: {
            media_metadata: {
              kind: 'tv_episode',
              show: {
                name: 'Example Show',
                image: {
                  medium: 'show-medium.jpg',
                  original: 'https://example.test/show-original.jpg',
                },
              },
              episode: {
                image: 'episode-still.jpg',
              },
              youtube: {
                title: 'Episode Clip',
                thumbnail: 'thumb.jpg',
                webpage_url: 'https://youtube.test/watch?v=abc',
              },
            },
          },
        },
      },
    });

    const { result } = renderHook(() =>
      useLibrarySelectedPresentation({
        selectedItem,
        isEditing: false,
        previewCoverUrl: null,
      }),
    );

    expect(result.current.itemType).toBe('video');
    expect(result.current.title).toBe('Untitled Video');
    expect(result.current.author).toBe('Unknown Creator');
    expect(result.current.genre).toBe('Video');
    expect(result.current.jobType).toBe('youtube_dub');
    expect(result.current.jobGlyph.variant).toBe('tv');
    expect(result.current.tvMetadata?.show).toMatchObject({ name: 'Example Show' });
    expect(result.current.youtubeMetadata?.title).toBe('Episode Clip');
    expect(result.current.tvPoster).toEqual({
      src: expect.stringContaining('/api/library/media/video-1/file/show-medium.jpg'),
      link: 'https://example.test/show-original.jpg',
    });
    expect(result.current.tvStill?.src).toContain('/api/library/media/video-1/file/episode-still.jpg');
    expect(result.current.youtubeThumbnail).toMatchObject({
      src: expect.stringContaining('/api/library/media/video-1/file/thumb.jpg'),
      link: 'https://youtube.test/watch?v=abc',
    });
  });
});
