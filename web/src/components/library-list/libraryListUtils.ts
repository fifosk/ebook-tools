import type { LibraryItem } from '../../api/dtos';

export type LibraryItemKind = 'book' | 'video' | 'narrated_subtitle';

export type AuthorGroup = {
  author: string;
  books: Array<{
    bookTitle: string;
    languages: Array<{ language: string; items: LibraryItem[] }>;
  }>;
};

export type GenreGroup = {
  genre: string;
  authors: Array<{
    author: string;
    books: Array<{ bookTitle: string; items: LibraryItem[] }>;
  }>;
};

export type LanguageGroup = {
  language: string;
  authors: Array<{
    author: string;
    books: Array<{ bookTitle: string; items: LibraryItem[] }>;
  }>;
};

export const SUBTITLE_AUTHOR = 'Subtitles';
export const UNTITLED_SUBTITLE = 'Untitled Subtitle';

const UNKNOWN_AUTHOR = 'Unknown Author';
const UNKNOWN_CREATOR = 'Unknown Creator';
const UNTITLED_BOOK = 'Untitled Book';
const UNTITLED_VIDEO = 'Untitled Video';
const UNKNOWN_GENRE = 'Unknown Genre';

export function normalizeItemType(item: LibraryItem): LibraryItemKind {
  return (item.itemType ?? 'book') as LibraryItemKind;
}

export function isBookItem(item: LibraryItem): boolean {
  return normalizeItemType(item) === 'book';
}

export function isSubtitleItem(item: LibraryItem): boolean {
  return normalizeItemType(item) === 'narrated_subtitle';
}

export function isVideoItem(item: LibraryItem): boolean {
  return normalizeItemType(item) === 'video';
}

export function resolveTitle(item: LibraryItem): string {
  const base = (item.bookTitle ?? '').trim();
  if (base) {
    return base;
  }
  switch (normalizeItemType(item)) {
    case 'video':
      return UNTITLED_VIDEO;
    case 'narrated_subtitle':
      return UNTITLED_SUBTITLE;
    default:
      return UNTITLED_BOOK;
  }
}

export function resolveAuthor(item: LibraryItem): string {
  const base = (item.author ?? '').trim();
  if (base) {
    return base;
  }
  switch (normalizeItemType(item)) {
    case 'video':
      return UNKNOWN_CREATOR;
    case 'narrated_subtitle':
      return SUBTITLE_AUTHOR;
    default:
      return UNKNOWN_AUTHOR;
  }
}

export function resolveGenre(item: LibraryItem): string {
  const base = (item.genre ?? '').toString().trim();
  if (base) {
    return base;
  }
  switch (normalizeItemType(item)) {
    case 'video':
      return 'Video';
    case 'narrated_subtitle':
      return 'Subtitles';
    default:
      return UNKNOWN_GENRE;
  }
}

function sortItemsByUpdatedAt(items: LibraryItem[]): LibraryItem[] {
  return [...items].sort((left, right) => right.updatedAt.localeCompare(left.updatedAt));
}

export function buildAuthorGroups(items: LibraryItem[]): AuthorGroup[] {
  const authorMap = new Map<string, Map<string, Map<string, LibraryItem[]>>>();
  items.forEach((item) => {
    const authorKey = resolveAuthor(item);
    const bookKey = resolveTitle(item);
    const languageKey = item.language || 'unknown';

    if (!authorMap.has(authorKey)) {
      authorMap.set(authorKey, new Map());
    }
    const booksMap = authorMap.get(authorKey)!;
    if (!booksMap.has(bookKey)) {
      booksMap.set(bookKey, new Map());
    }
    const languageMap = booksMap.get(bookKey)!;
    if (!languageMap.has(languageKey)) {
      languageMap.set(languageKey, []);
    }
    languageMap.get(languageKey)!.push(item);
  });

  return Array.from(authorMap.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([author, booksMap]) => ({
      author,
      books: Array.from(booksMap.entries())
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([bookTitle, languageMap]) => ({
          bookTitle,
          languages: Array.from(languageMap.entries())
            .sort((a, b) => a[0].localeCompare(b[0]))
            .map(([language, entries]) => ({
              language,
              items: sortItemsByUpdatedAt(entries)
            }))
        }))
    }));
}

export function buildGenreGroups(items: LibraryItem[]): GenreGroup[] {
  const genreMap = new Map<string, Map<string, Map<string, LibraryItem[]>>>();
  items.forEach((item) => {
    const genreKey = resolveGenre(item);
    const authorKey = resolveAuthor(item);
    const bookKey = resolveTitle(item);

    if (!genreMap.has(genreKey)) {
      genreMap.set(genreKey, new Map());
    }
    const authorMap = genreMap.get(genreKey)!;
    if (!authorMap.has(authorKey)) {
      authorMap.set(authorKey, new Map());
    }
    const bookMap = authorMap.get(authorKey)!;
    if (!bookMap.has(bookKey)) {
      bookMap.set(bookKey, []);
    }
    bookMap.get(bookKey)!.push(item);
  });

  return Array.from(genreMap.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([genre, authorMap]) => ({
      genre,
      authors: Array.from(authorMap.entries())
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([author, bookMap]) => ({
          author,
          books: Array.from(bookMap.entries())
            .sort((a, b) => a[0].localeCompare(b[0]))
            .map(([bookTitle, entries]) => ({
              bookTitle,
              items: sortItemsByUpdatedAt(entries)
            }))
        }))
    }));
}

export function buildLanguageGroups(items: LibraryItem[]): LanguageGroup[] {
  const languageMap = new Map<string, Map<string, Map<string, LibraryItem[]>>>();
  items.forEach((item) => {
    const languageKey = item.language || 'unknown';
    const authorKey = resolveAuthor(item);
    const bookKey = resolveTitle(item);

    if (!languageMap.has(languageKey)) {
      languageMap.set(languageKey, new Map());
    }
    const authorMap = languageMap.get(languageKey)!;
    if (!authorMap.has(authorKey)) {
      authorMap.set(authorKey, new Map());
    }
    const bookMap = authorMap.get(authorKey)!;
    if (!bookMap.has(bookKey)) {
      bookMap.set(bookKey, []);
    }
    bookMap.get(bookKey)!.push(item);
  });

  return Array.from(languageMap.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([language, authorMap]) => ({
      language,
      authors: Array.from(authorMap.entries())
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([author, bookMap]) => ({
          author,
          books: Array.from(bookMap.entries())
            .sort((a, b) => a[0].localeCompare(b[0]))
            .map(([bookTitle, entries]) => ({
              bookTitle,
              items: sortItemsByUpdatedAt(entries)
            }))
        }))
    }));
}
