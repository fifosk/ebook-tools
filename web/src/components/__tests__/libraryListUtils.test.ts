import { describe, expect, it } from 'vitest';
import type { LibraryItem } from '../../api/dtos';
import {
  buildAuthorGroups,
  buildGenreGroups,
  buildLanguageGroups,
  isBookItem,
  isSubtitleItem,
  isVideoItem,
  resolveAuthor,
  resolveGenre,
  resolveTitle
} from '../library-list/libraryListUtils';

function item(overrides: Partial<LibraryItem> = {}): LibraryItem {
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

describe('libraryListUtils', () => {
  it('resolves layout type and metadata fallbacks by item type', () => {
    const book = item();
    const video = item({ itemType: 'video' });
    const subtitle = item({ itemType: 'narrated_subtitle' });

    expect(isBookItem(book)).toBe(true);
    expect(isVideoItem(video)).toBe(true);
    expect(isSubtitleItem(subtitle)).toBe(true);
    expect(resolveTitle(book)).toBe('Untitled Book');
    expect(resolveTitle(video)).toBe('Untitled Video');
    expect(resolveTitle(subtitle)).toBe('Untitled Subtitle');
    expect(resolveAuthor(book)).toBe('Unknown Author');
    expect(resolveAuthor(video)).toBe('Unknown Creator');
    expect(resolveAuthor(subtitle)).toBe('Subtitles');
    expect(resolveGenre(book)).toBe('Unknown Genre');
    expect(resolveGenre(video)).toBe('Video');
    expect(resolveGenre(subtitle)).toBe('Subtitles');
  });

  it('trims explicit title, author, and genre metadata', () => {
    const explicit = item({
      bookTitle: '  Example Book  ',
      author: '  Example Author  ',
      genre: '  Mystery  '
    });

    expect(resolveTitle(explicit)).toBe('Example Book');
    expect(resolveAuthor(explicit)).toBe('Example Author');
    expect(resolveGenre(explicit)).toBe('Mystery');
  });

  it('groups by author, title, language, and newest item first', () => {
    const groups = buildAuthorGroups([
      item({
        jobId: 'older',
        author: 'Author B',
        bookTitle: 'Book B',
        language: 'es',
        updatedAt: '2026-06-20T10:00:00Z'
      }),
      item({
        jobId: 'newer',
        author: 'Author B',
        bookTitle: 'Book B',
        language: 'es',
        updatedAt: '2026-06-22T10:00:00Z'
      }),
      item({
        jobId: 'first-author',
        author: 'Author A',
        bookTitle: 'Book A',
        language: 'en',
        updatedAt: '2026-06-21T10:00:00Z'
      })
    ]);

    expect(groups.map((group) => group.author)).toEqual(['Author A', 'Author B']);
    expect(groups[1].books[0].languages[0].items.map((entry) => entry.jobId)).toEqual(['newer', 'older']);
  });

  it('groups by genre and language with stable sorted headings', () => {
    const items = [
      item({ jobId: 'fantasy', genre: 'Fantasy', author: 'Zed', bookTitle: 'B', language: 'fr' }),
      item({ jobId: 'mystery', genre: 'Mystery', author: 'Ann', bookTitle: 'A', language: 'en' }),
      item({ jobId: 'unknown-language', genre: 'Fantasy', author: 'Ann', bookTitle: 'A', language: undefined })
    ];

    expect(buildGenreGroups(items).map((group) => group.genre)).toEqual(['Fantasy', 'Mystery']);
    expect(buildGenreGroups(items)[0].authors.map((author) => author.author)).toEqual(['Ann', 'Zed']);
    expect(buildLanguageGroups(items).map((group) => group.language)).toEqual(['en', 'fr', 'unknown']);
  });
});
