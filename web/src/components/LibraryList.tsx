import { useMemo } from 'react';
import type { LibraryItem, LibraryViewMode } from '../api/dtos';
import styles from './LibraryList.module.css';

type Props = {
  items: LibraryItem[];
  view: LibraryViewMode;
  onOpen: (item: LibraryItem) => void;
  onRemoveMedia: (item: LibraryItem) => void;
  onRemove: (item: LibraryItem) => void;
  onRefreshMetadata: (item: LibraryItem) => void;
  onEditMetadata: (item: LibraryItem) => void;
  selectedJobId?: string | null;
  mutating?: Record<string, boolean>;
};

type AuthorGroup = {
  author: string;
  books: Array<{
    bookTitle: string;
    languages: Array<{ language: string; items: LibraryItem[] }>;
  }>;
};

type GenreGroup = {
  genre: string;
  authors: Array<{
    author: string;
    books: Array<{ bookTitle: string; items: LibraryItem[] }>;
  }>;
};

type LanguageGroup = {
  language: string;
  authors: Array<{
    author: string;
    books: Array<{ bookTitle: string; items: LibraryItem[] }>;
  }>;
};

const UNKNOWN_AUTHOR = 'Unknown Author';
const UNTITLED_BOOK = 'Untitled Book';
const UNKNOWN_GENRE = 'Unknown Genre';

type StatusVariant = 'ready' | 'missing';

function describeStatus(item: LibraryItem): { label: string; variant?: StatusVariant } {
  const base = item.status === 'finished' ? 'Finished' : 'Paused';
  if (!item.mediaCompleted) {
    return { label: `${base} · media removed`, variant: 'missing' };
  }
  if (item.status === 'paused') {
    return { label: `${base} · media finalized`, variant: 'ready' };
  }
  return { label: base, variant: 'ready' };
}

function renderStatusBadge(item: LibraryItem) {
  const { label, variant } = describeStatus(item);
  return (
    <span className={styles.statusBadge} data-variant={variant}>
      {label}
    </span>
  );
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return '—';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function buildAuthorGroups(items: LibraryItem[]): AuthorGroup[] {
  const authorMap = new Map<string, Map<string, Map<string, LibraryItem[]>>>();
  items.forEach((item) => {
    const authorKey = item.author.trim() || UNKNOWN_AUTHOR;
    const bookKey = item.bookTitle.trim() || UNTITLED_BOOK;
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
              items: [...entries].sort((left, right) => right.updatedAt.localeCompare(left.updatedAt))
            }))
        }))
    }));
}

function buildGenreGroups(items: LibraryItem[]): GenreGroup[] {
  const genreMap = new Map<string, Map<string, Map<string, LibraryItem[]>>>();
  items.forEach((item) => {
    const genreKey = (item.genre ?? '').toString().trim() || UNKNOWN_GENRE;
    const authorKey = item.author.trim() || UNKNOWN_AUTHOR;
    const bookKey = item.bookTitle.trim() || UNTITLED_BOOK;

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
              items: [...entries].sort((left, right) => right.updatedAt.localeCompare(left.updatedAt))
            }))
        }))
    }));
}

function buildLanguageGroups(items: LibraryItem[]): LanguageGroup[] {
  const languageMap = new Map<string, Map<string, Map<string, LibraryItem[]>>>();
  items.forEach((item) => {
    const languageKey = item.language || 'unknown';
    const authorKey = item.author.trim() || UNKNOWN_AUTHOR;
    const bookKey = item.bookTitle.trim() || UNTITLED_BOOK;

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
              items: [...entries].sort((left, right) => right.updatedAt.localeCompare(left.updatedAt))
            }))
        }))
    }));
}

function LibraryList({
  items,
  view,
  onOpen,
  onRemoveMedia,
  onRemove,
  onRefreshMetadata,
  onEditMetadata,
  selectedJobId,
  mutating = {}
}: Props) {
  const authorGroups = useMemo(() => buildAuthorGroups(items), [items]);
  const genreGroups = useMemo(() => buildGenreGroups(items), [items]);
  const languageGroups = useMemo(() => buildLanguageGroups(items), [items]);

  const renderActions = (item: LibraryItem) => (
    <div className={styles.actions}>
      <button
        type="button"
        className={styles.actionButton}
        onClick={() => onOpen(item)}
        disabled={Boolean(mutating[item.jobId])}
      >
        Open
      </button>
      <button
        type="button"
        className={styles.actionButton}
        onClick={() => onRemoveMedia(item)}
        disabled={Boolean(mutating[item.jobId])}
      >
        Remove media
      </button>
      <button
        type="button"
        className={styles.actionButton}
        onClick={() => onRefreshMetadata(item)}
        disabled={Boolean(mutating[item.jobId])}
      >
        Refetch cover
      </button>
      <button
        type="button"
        className={styles.actionButton}
        onClick={() => onEditMetadata(item)}
        disabled={Boolean(mutating[item.jobId])}
      >
        Update metadata
      </button>
      <button
        type="button"
        className={styles.actionButton}
        onClick={() => onRemove(item)}
        disabled={Boolean(mutating[item.jobId])}
      >
        Remove entry
      </button>
    </div>
  );

  if (items.length === 0) {
    return (
      <div className={styles.listContainer}>
        <p className={styles.emptyState}>No library entries match the current filters.</p>
      </div>
    );
  }

  if (view === 'flat') {
    return (
      <div className={styles.listContainer}>
        <div className={styles.tableWrapper}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Title</th>
                <th>Author</th>
                <th>Language</th>
                <th>Status</th>
                <th>Updated</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr
                  key={item.jobId}
                  className={selectedJobId === item.jobId ? styles.tableRowActive : undefined}
                >
                  <td>{item.bookTitle || UNTITLED_BOOK}</td>
                  <td>{item.author || UNKNOWN_AUTHOR}</td>
                  <td>{item.language}</td>
                  <td>
                    {renderStatusBadge(item)}
                  </td>
                  <td>{formatTimestamp(item.updatedAt)}</td>
                  <td>{renderActions(item)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  if (view === 'by_author') {
    return (
      <div className={styles.listContainer}>
        {authorGroups.map((group) => (
          <details key={group.author} className={styles.group} open>
            <summary>{group.author}</summary>
            {group.books.map((book) => (
              <details key={book.bookTitle} className={styles.subGroup} open>
                <summary>{book.bookTitle}</summary>
                {book.languages.map((entry) => (
                  <div key={entry.language}>
                    <h4 className={styles.languageHeader}>{entry.language}</h4>
                    <ul className={styles.itemList}>
                      {entry.items.map((item) => (
                        <li key={item.jobId} className={styles.itemCard}>
                          <div className={styles.itemHeader}>
                            <span>Job {item.jobId}</span>
                            {renderStatusBadge(item)}
                          </div>
                          <div className={styles.itemMeta}>
                            Updated {formatTimestamp(item.updatedAt)} · Library path {item.libraryPath}
                          </div>
                          {renderActions(item)}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </details>
            ))}
          </details>
        ))}
      </div>
    );
  }

  if (view === 'by_genre') {
    return (
      <div className={styles.listContainer}>
        {genreGroups.map((group) => (
          <details key={group.genre} className={styles.group} open>
            <summary>{group.genre}</summary>
            {group.authors.map((author) => (
              <details key={author.author} className={styles.subGroup} open>
                <summary>{author.author}</summary>
                {author.books.map((book) => (
                  <div key={book.bookTitle}>
                    <h4 className={styles.languageHeader}>{book.bookTitle}</h4>
                    <ul className={styles.itemList}>
                      {book.items.map((item) => (
                        <li key={item.jobId} className={styles.itemCard}>
                          <div className={styles.itemHeader}>
                            <span>Job {item.jobId}</span>
                            {renderStatusBadge(item)}
                          </div>
                          <div className={styles.itemMeta}>
                            Language {item.language} · Updated {formatTimestamp(item.updatedAt)}
                          </div>
                          {renderActions(item)}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </details>
            ))}
          </details>
        ))}
      </div>
    );
  }

  return (
    <div className={styles.listContainer}>
      {languageGroups.map((group) => (
        <details key={group.language} className={styles.group} open>
          <summary>{group.language}</summary>
          {group.authors.map((author) => (
            <details key={author.author} className={styles.subGroup} open>
              <summary>{author.author}</summary>
              {author.books.map((book) => (
                <div key={book.bookTitle}>
                  <h4 className={styles.languageHeader}>{book.bookTitle}</h4>
                  <ul className={styles.itemList}>
                    {book.items.map((item) => (
                      <li key={item.jobId} className={styles.itemCard}>
                        <div className={styles.itemHeader}>
                          <span>Job {item.jobId}</span>
                          {renderStatusBadge(item)}
                        </div>
                        <div className={styles.itemMeta}>
                          Updated {formatTimestamp(item.updatedAt)} · Library path {item.libraryPath}
                        </div>
                        {renderActions(item)}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </details>
          ))}
        </details>
      ))}
    </div>
  );
}

export default LibraryList;
