import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import type { LibraryItem, LibraryViewMode, LibraryMetadataUpdatePayload } from '../api/dtos';
import {
  applyLibraryIsbn,
  appendAccessToken,
  lookupLibraryIsbnMetadata,
  removeLibraryEntry,
  reindexLibrary,
  searchLibrary,
  updateLibraryMetadata,
  uploadLibrarySource,
  type LibrarySearchParams
} from '../api/client';
import LibraryList from '../components/LibraryList';
import LibraryToolbar from '../components/LibraryToolbar';
import styles from './LibraryPage.module.css';
import { extractLibraryBookMetadata, resolveLibraryCoverUrl } from '../utils/libraryMetadata';
import type { LibraryOpenInput, LibraryOpenRequest } from '../types/player';
import { extractJobType, getJobTypeGlyph } from '../utils/jobGlyphs';

const PAGE_SIZE = 25;

const UNKNOWN_AUTHOR = 'Unknown Author';
const UNKNOWN_CREATOR = 'Unknown Creator';
const UNKNOWN_GENRE = 'Unknown Genre';
const UNTITLED_BOOK = 'Untitled Book';
const UNTITLED_VIDEO = 'Untitled Video';
const UNTITLED_SUBTITLE = 'Untitled Subtitle';
const SUBTITLE_AUTHOR = 'Subtitles';

type LibraryPageProps = {
  onPlay?: (item: LibraryOpenInput) => void;
};

type LibraryItemType = 'book' | 'video' | 'narrated_subtitle';

function resolveItemType(item: LibraryItem | null | undefined): LibraryItemType {
  return (item?.itemType ?? 'book') as LibraryItemType;
}

function resolveTitle(item: LibraryItem | null | undefined): string {
  const candidate = item?.bookTitle?.trim() ?? '';
  if (candidate) {
    return candidate;
  }
  switch (resolveItemType(item)) {
    case 'video':
      return UNTITLED_VIDEO;
    case 'narrated_subtitle':
      return UNTITLED_SUBTITLE;
    default:
      return UNTITLED_BOOK;
  }
}

function resolveAuthor(item: LibraryItem | null | undefined): string {
  const candidate = item?.author?.trim() ?? '';
  if (candidate) {
    return candidate;
  }
  switch (resolveItemType(item)) {
    case 'video':
      return UNKNOWN_CREATOR;
    case 'narrated_subtitle':
      return SUBTITLE_AUTHOR;
    default:
      return UNKNOWN_AUTHOR;
  }
}

function resolveGenre(item: LibraryItem | null | undefined): string {
  const candidate = item?.genre?.toString().trim() ?? '';
  if (candidate) {
    return candidate;
  }
  switch (resolveItemType(item)) {
    case 'video':
      return 'Video';
    case 'narrated_subtitle':
      return 'Subtitles';
    default:
      return UNKNOWN_GENRE;
  }
}

function LibraryPage({ onPlay }: LibraryPageProps) {
  const [query, setQuery] = useState('');
  const [effectiveQuery, setEffectiveQuery] = useState('');
  const [view, setView] = useState<LibraryViewMode>('flat');
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [selectedItem, setSelectedItem] = useState<LibraryItem | null>(null);
  const [activeTab, setActiveTab] = useState<LibraryItemType>('book');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mutating, setMutating] = useState<Record<string, boolean>>({});
  const [refreshKey, setRefreshKey] = useState(0);
  const [isReindexing, setIsReindexing] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editValues, setEditValues] = useState<{ title: string; author: string; genre: string; language: string; isbn: string }>(
    {
      title: '',
      author: '',
      genre: '',
      language: '',
      isbn: ''
    }
  );
  const [isSaving, setIsSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isbnPreview, setIsbnPreview] = useState<Record<string, unknown> | null>(null);
  const [previewCoverUrl, setPreviewCoverUrl] = useState<string | null>(null);
  const [isbnFetchError, setIsbnFetchError] = useState<string | null>(null);
  const [isFetchingIsbn, setIsFetchingIsbn] = useState(false);

  useEffect(() => {
    const handle = window.setTimeout(() => setEffectiveQuery(query), 250);
    return () => window.clearTimeout(handle);
  }, [query]);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    const params: LibrarySearchParams = {
      query: effectiveQuery || undefined,
      view,
      page,
      limit: PAGE_SIZE
    };

    searchLibrary(params)
      .then((response) => {
        if (cancelled) {
          return;
        }
        setItems(response.items);
        setTotal(response.total);
        setSelectedItem((current) => {
          if (!current) {
            return null;
          }
          return response.items.find((item) => item.jobId === current.jobId) ?? null;
        });
      })
      .catch((loadError) => {
        if (cancelled) {
          return;
        }
        const message =
          loadError instanceof Error ? loadError.message : 'Unable to load library inventory.';
        setError(message);
        setItems([]);
        setTotal(0);
        setSelectedItem(null);
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [effectiveQuery, page, view, refreshKey]);

  useEffect(() => {
    setPage(1);
  }, [effectiveQuery, view]);

  useEffect(() => {
    if (!selectedItem) {
      setIsEditing(false);
      setEditError(null);
      setSelectedFile(null);
      setIsbnPreview(null);
      setPreviewCoverUrl(null);
      setIsbnFetchError(null);
      setIsFetchingIsbn(false);
    }
  }, [selectedItem]);

  useEffect(() => {
    setSelectedItem((current) => {
      if (!current) {
        return null;
      }
      return resolveItemType(current) === activeTab ? current : null;
    });
  }, [activeTab]);

  const selectLibraryItem = useCallback((item: LibraryItem) => {
    setIsEditing(false);
    setEditError(null);
    setActiveTab(resolveItemType(item));
    setSelectedItem(item);
  }, []);

  const openLibraryItem = useCallback(
    (item: LibraryItem) => {
      selectLibraryItem(item);
      if (onPlay) {
        const itemType = resolveItemType(item);
        const payload: LibraryOpenRequest = {
          kind: 'library-open',
          jobId: item.jobId,
          item,
          selection: {
            baseId: null,
            preferredType: itemType === 'video' ? 'video' : 'text',
            offsetRatio: null,
            approximateTime: null,
            token: Date.now()
          }
        };
        onPlay(payload);
      }
    },
    [onPlay, selectLibraryItem]
  );

  const handleOpen = useCallback((item: LibraryItem) => {
    openLibraryItem(item);
  }, [openLibraryItem]);

  const handleRemoveEntry = useCallback(
    async (item: LibraryItem) => {
      if (!window.confirm(`Remove job ${item.jobId} from the library? This cannot be undone.`)) {
        return;
      }
      setMutating((previous) => ({ ...previous, [item.jobId]: true }));
      try {
        await removeLibraryEntry(item.jobId);
        if (items.length === 1 && page > 1) {
          setPage((previousPage) => Math.max(1, previousPage - 1));
        } else {
          setRefreshKey((key) => key + 1);
        }
        setSelectedItem((current) => (current?.jobId === item.jobId ? null : current));
      } catch (actionError) {
        const message =
          actionError instanceof Error ? actionError.message : 'Unable to remove library entry.';
        window.alert(message);
        setRefreshKey((key) => key + 1);
      } finally {
        setMutating((previous) => {
          const next = { ...previous };
          delete next[item.jobId];
          return next;
        });
      }
    },
    [items.length, page]
  );

  const handleReindex = useCallback(async () => {
    setIsReindexing(true);
    try {
      const result = await reindexLibrary();
      window.alert(`Reindexed ${result.indexed} library entries.`);
      setRefreshKey((key) => key + 1);
    } catch (actionError) {
      const message = actionError instanceof Error ? actionError.message : 'Unable to reindex library.';
      window.alert(message);
    } finally {
      setIsReindexing(false);
    }
  }, []);

  const startEditingItem = useCallback(
    (item: LibraryItem) => {
      selectLibraryItem(item);
      setEditValues({
        title: item.bookTitle ?? '',
        author: item.author ?? '',
        genre: item.genre ?? '',
        language: item.language ?? '',
        isbn: item.isbn ?? ''
      });
      setSelectedFile(null);
      setIsbnPreview(null);
      setPreviewCoverUrl(null);
      setIsbnFetchError(null);
      setIsEditing(true);
    },
    [selectLibraryItem]
  );

  const handleEditMetadata = useCallback(
    (item: LibraryItem) => {
      startEditingItem(item);
    },
    [startEditingItem]
  );

  const handleEditCancel = useCallback(() => {
    setIsEditing(false);
    setEditError(null);
    setSelectedFile(null);
    setIsbnPreview(null);
    setPreviewCoverUrl(null);
    setIsbnFetchError(null);
    setIsFetchingIsbn(false);
  }, []);

  const handleEditValueChange = useCallback(
    (field: 'title' | 'author' | 'genre' | 'language' | 'isbn') => (event: ChangeEvent<HTMLInputElement>) => {
      const { value } = event.target;
      setEditValues((previous) => ({ ...previous, [field]: value }));
    },
    []
  );

  const handleSourceFileChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files && event.target.files.length > 0 ? event.target.files[0] : null;
    setSelectedFile(file ?? null);
  }, []);

  const handleFetchIsbnMetadata = useCallback(async () => {
    const trimmedIsbn = editValues.isbn.trim();
    if (!trimmedIsbn) {
      setIsbnFetchError('Enter an ISBN to fetch metadata.');
      return;
    }
    setIsbnFetchError(null);
    setIsFetchingIsbn(true);
    try {
      const response = await lookupLibraryIsbnMetadata(trimmedIsbn);
      const metadata = (response?.metadata ?? {}) as Record<string, unknown>;
      setIsbnPreview(metadata);

      setEditValues((previous) => ({
        ...previous,
        title: typeof metadata['book_title'] === 'string' && metadata['book_title'].trim() ? (metadata['book_title'] as string) : previous.title,
        author: typeof metadata['book_author'] === 'string' && metadata['book_author'].trim() ? (metadata['book_author'] as string) : previous.author,
        genre: typeof metadata['book_genre'] === 'string' && metadata['book_genre'].trim() ? (metadata['book_genre'] as string) : previous.genre,
        language:
          typeof metadata['book_language'] === 'string' && metadata['book_language'].trim()
            ? (metadata['book_language'] as string)
            : previous.language,
        isbn: previous.isbn || trimmedIsbn
      }));

      const coverCandidate = ((): string | null => {
        const coverFile = metadata['book_cover_file'];
        if (typeof coverFile === 'string' && coverFile.trim()) {
          return coverFile.trim();
        }
        const coverUrl = metadata['cover_url'];
        if (typeof coverUrl === 'string' && coverUrl.trim()) {
          return coverUrl.trim();
        }
        return null;
      })();

      setPreviewCoverUrl(coverCandidate ? appendAccessToken(coverCandidate) : null);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to fetch metadata from ISBN.';
      setIsbnFetchError(message);
      setIsbnPreview(null);
      setPreviewCoverUrl(null);
    } finally {
      setIsFetchingIsbn(false);
    }
  }, [editValues.isbn]);

  const handleEditSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (!selectedItem) {
        return;
      }
      setIsSaving(true);
      setEditError(null);

      const trimmedTitle = editValues.title.trim();
      const trimmedAuthor = editValues.author.trim();
      const trimmedGenre = editValues.genre.trim();
      const trimmedLanguage = editValues.language.trim();
      const trimmedIsbn = editValues.isbn.trim();

      const payload: LibraryMetadataUpdatePayload = {
        title: trimmedTitle,
        author: trimmedAuthor,
        genre: trimmedGenre ? trimmedGenre : null,
        language: trimmedLanguage,
        isbn: trimmedIsbn
      };

      try {
        if (selectedFile) {
          await uploadLibrarySource(selectedItem.jobId, selectedFile);
        }

        const originalIsbn = selectedItem.isbn ?? '';
        if (trimmedIsbn && trimmedIsbn !== originalIsbn) {
          await applyLibraryIsbn(selectedItem.jobId, trimmedIsbn);
        } else if (!trimmedIsbn && originalIsbn) {
          payload.isbn = '';
        }

        const updated = await updateLibraryMetadata(selectedItem.jobId, payload);
        setItems((previous) =>
          previous.map((entry) => (entry.jobId === updated.jobId ? updated : entry))
        );
        setSelectedItem(updated);
        setIsEditing(false);
        setSelectedFile(null);
        setIsbnPreview(null);
        setPreviewCoverUrl(null);
        setIsbnFetchError(null);
      } catch (actionError) {
        const message =
          actionError instanceof Error ? actionError.message : 'Unable to update metadata.';
        setEditError(message);
      } finally {
        setIsSaving(false);
      }
    },
    [editValues, selectedItem]
  );

  const totalPages = useMemo(() => {
    if (total === 0) {
      return 1;
    }
    return Math.max(1, Math.ceil(total / PAGE_SIZE));
  }, [total]);

  const rangeLabel = useMemo(() => {
    if (total === 0) {
      return 'No results';
    }
    const start = (page - 1) * PAGE_SIZE + 1;
    const end = Math.min(total, start + items.length - 1);
    return `Showing ${start}–${end} of ${total}`;
  }, [items.length, page, total]);

  const selectedItemType = useMemo(() => resolveItemType(selectedItem), [selectedItem]);
  const selectedTitle = useMemo(() => resolveTitle(selectedItem), [selectedItem]);
  const selectedAuthor = useMemo(() => resolveAuthor(selectedItem), [selectedItem]);
  const selectedGenre = useMemo(() => resolveGenre(selectedItem), [selectedItem]);
  const selectedJobType = useMemo(() => extractJobType(selectedItem?.metadata) ?? null, [selectedItem]);
  const selectedJobGlyph = useMemo(() => getJobTypeGlyph(selectedJobType), [selectedJobType]);

  const bookItems = useMemo(() => items.filter((item) => resolveItemType(item) === 'book'), [items]);
  const videoItems = useMemo(() => items.filter((item) => resolveItemType(item) === 'video'), [items]);
  const subtitleItems = useMemo(
    () => items.filter((item) => resolveItemType(item) === 'narrated_subtitle'),
    [items]
  );
  const activeItems = useMemo(() => {
    switch (activeTab) {
      case 'video':
        return videoItems;
      case 'narrated_subtitle':
        return subtitleItems;
      default:
        return bookItems;
    }
  }, [activeTab, bookItems, subtitleItems, videoItems]);

  const selectedBookMetadata = useMemo(
    () => extractLibraryBookMetadata(selectedItem),
    [selectedItem]
  );

  const coverUrl = useMemo(() => {
    if (!selectedItem) {
      return null;
    }
    return resolveLibraryCoverUrl(selectedItem, selectedBookMetadata);
  }, [selectedBookMetadata, selectedItem]);

  const displayedCoverUrl = useMemo(() => {
    if (isEditing && previewCoverUrl) {
      return previewCoverUrl;
    }
    return coverUrl;
  }, [coverUrl, isEditing, previewCoverUrl]);

  const handlePlay = useCallback(() => {
    if (!selectedItem || !onPlay) {
      return;
    }
    openLibraryItem(selectedItem);
  }, [onPlay, openLibraryItem, selectedItem]);

  return (
    <div className={styles.page}>
      {error ? <div className={styles.errorBanner}>{error}</div> : null}
      <LibraryToolbar
        query={query}
        onQueryChange={setQuery}
        view={view}
        onViewChange={(nextView) => setView(nextView)}
        isLoading={isLoading}
        onReindex={handleReindex}
        onRefresh={() => setRefreshKey((key) => key + 1)}
        isReindexing={isReindexing}
      />
      <div className={styles.content}>
        <section aria-label="Library entries">
          <div className={styles.listCard}>
            <div className={styles.sectionHeader}>
              <div className={styles.tabs} role="tablist" aria-label="Library tabs">
                <button
                  type="button"
                  role="tab"
                  className={`${styles.tabButton} ${activeTab === 'book' ? styles.tabButtonActive : ''}`}
                  aria-selected={activeTab === 'book'}
                  onClick={() => setActiveTab('book')}
                >
                  Books <span className={styles.sectionCount}>{bookItems.length}</span>
                </button>
                <button
                  type="button"
                  role="tab"
                  className={`${styles.tabButton} ${activeTab === 'narrated_subtitle' ? styles.tabButtonActive : ''}`}
                  aria-selected={activeTab === 'narrated_subtitle'}
                  onClick={() => setActiveTab('narrated_subtitle')}
                >
                  Subtitles <span className={styles.sectionCount}>{subtitleItems.length}</span>
                </button>
                <button
                  type="button"
                  role="tab"
                  className={`${styles.tabButton} ${activeTab === 'video' ? styles.tabButtonActive : ''}`}
                  aria-selected={activeTab === 'video'}
                  onClick={() => setActiveTab('video')}
                >
                  Videos <span className={styles.sectionCount}>{videoItems.length}</span>
                </button>
              </div>
            </div>
            <LibraryList
              items={activeItems}
              view={view}
              variant="embedded"
              onSelect={selectLibraryItem}
              onOpen={handleOpen}
              onRemove={handleRemoveEntry}
              onEditMetadata={handleEditMetadata}
              selectedJobId={selectedItem?.jobId}
              mutating={mutating}
            />
          </div>
        </section>
        <div className={styles.pagination}>
          <button type="button" onClick={() => setPage((previous) => Math.max(1, previous - 1))} disabled={page <= 1}>
            Previous
          </button>
          <span>{rangeLabel}</span>
          <button
            type="button"
            onClick={() => setPage((previous) => Math.min(totalPages, previous + 1))}
            disabled={page >= totalPages}
          >
            Next
          </button>
        </div>
        <aside className={styles.detailsCard} aria-live="polite">
          {selectedItem ? (
            <>
              <h2 className={styles.detailsTitle}>
                <span className={styles.detailsJobGlyph} title={selectedJobGlyph.label} aria-label={selectedJobGlyph.label}>
                  {selectedJobGlyph.icon}
                </span>
                {selectedTitle}
              </h2>
              {displayedCoverUrl ? (
                <div className={styles.coverWrapper}>
                  <img
                    src={displayedCoverUrl}
                    alt={`Cover art for ${selectedTitle}`}
                    className={styles.coverImage}
                  />
                </div>
              ) : null}
              <div className={styles.actionBar}>
                <button
                  type="button"
                  className={styles.primaryButton}
                  onClick={handlePlay}
                >
                  Play
                </button>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={() => startEditingItem(selectedItem)}
                  disabled={isSaving || Boolean(mutating[selectedItem.jobId])}
                >
                  Edit
                </button>
                {!selectedItem.mediaCompleted ? (
                  <span className={styles.actionHint}>
                    Media is still finalizing or was previously removed for this entry.
                  </span>
                ) : null}
              </div>
              {isEditing ? (
                <>
                  <form className={styles.editForm} onSubmit={handleEditSubmit}>
                  {editError ? <div className={styles.editError}>{editError}</div> : null}
                  <div className={styles.fieldGroup}>
                    <label className={styles.fieldLabel} htmlFor="library-edit-title">Title</label>
                    <input
                      id="library-edit-title"
                      type="text"
                      className={styles.fieldInput}
                      value={editValues.title}
                      onChange={handleEditValueChange('title')}
                      disabled={isSaving}
                    />
                  </div>
                  <div className={styles.fieldGroup}>
                    <label className={styles.fieldLabel} htmlFor="library-edit-author">Author / Creator</label>
                    <input
                      id="library-edit-author"
                      type="text"
                      className={styles.fieldInput}
                      value={editValues.author}
                      onChange={handleEditValueChange('author')}
                      disabled={isSaving}
                    />
                  </div>
                  <div className={styles.fieldGroup}>
                    <label className={styles.fieldLabel} htmlFor="library-edit-genre">Genre</label>
                    <input
                      id="library-edit-genre"
                      type="text"
                      className={styles.fieldInput}
                      value={editValues.genre}
                      onChange={handleEditValueChange('genre')}
                      disabled={isSaving}
                    />
                  </div>
                  <div className={styles.fieldGroup}>
                    <label className={styles.fieldLabel} htmlFor="library-edit-language">Language</label>
                    <input
                      id="library-edit-language"
                      type="text"
                      className={styles.fieldInput}
                      value={editValues.language}
                      onChange={handleEditValueChange('language')}
                      disabled={isSaving}
                    />
                  </div>
                  <div className={styles.fieldGroup}>
                    <label className={styles.fieldLabel} htmlFor="library-edit-isbn">ISBN</label>
                    <div className={styles.inlineFieldRow}>
                      <input
                        id="library-edit-isbn"
                        type="text"
                        className={styles.fieldInput}
                        value={editValues.isbn}
                        onChange={handleEditValueChange('isbn')}
                        disabled={isSaving || isFetchingIsbn}
                      />
                      <button
                        type="button"
                        className={styles.secondaryButton}
                        onClick={handleFetchIsbnMetadata}
                        disabled={isSaving || isFetchingIsbn || !editValues.isbn.trim()}
                      >
                        {isFetchingIsbn ? 'Fetching…' : 'Fetch from ISBN'}
                      </button>
                    </div>
                    {isbnFetchError ? <div className={styles.editError}>{isbnFetchError}</div> : null}
                  </div>
                  <div className={styles.fieldGroup}>
                    <label className={styles.fieldLabel} htmlFor="library-edit-source">Replace Source File</label>
                    <input
                      id="library-edit-source"
                      type="file"
                      accept=".epub,.pdf,.mp4,.mkv,.mov,.webm"
                      onChange={handleSourceFileChange}
                      disabled={isSaving}
                    />
                    <span className={styles.fileHint}>
                      {selectedFile
                        ? `Selected: ${selectedFile.name}`
                        : selectedItem.sourcePath
                        ? `Current: ${selectedItem.sourcePath}`
                        : 'No source file stored yet.'}
                    </span>
                  </div>
                  <div className={styles.editActions}>
                    <button type="submit" className={styles.primaryButton} disabled={isSaving}>
                      Save changes
                    </button>
                    <button
                      type="button"
                      className={styles.secondaryButton}
                      onClick={handleEditCancel}
                      disabled={isSaving}
                    >
                      Cancel
                    </button>
                  </div>
                </form>
                  {isbnPreview ? (
                    <div className={styles.previewBlock}>
                      <h3>Fetched Metadata Preview</h3>
                      <pre className={styles.metadataBlock}>
                        {JSON.stringify(isbnPreview, null, 2)}
                      </pre>
                    </div>
                  ) : null}
                </>
              ) : null}
              <ul className={styles.detailList}>
                <li className={styles.detailItem}>
                  <strong>Job ID:</strong> {selectedItem.jobId}
                </li>
                <li className={styles.detailItem}>
                  <strong>Type:</strong>{' '}
                  {selectedItemType === 'video'
                    ? 'Video'
                    : selectedItemType === 'narrated_subtitle'
                      ? 'Narrated Subtitle'
                      : 'Book'}
                </li>
                <li className={styles.detailItem}>
                  <strong>Job:</strong> {selectedJobGlyph.icon} {selectedJobType ?? '—'}
                </li>
                <li className={styles.detailItem}>
                  <strong>ISBN:</strong> {selectedItem.isbn && selectedItem.isbn.trim() ? selectedItem.isbn : '—'}
                </li>
                <li className={styles.detailItem}>
                  <strong>
                    {selectedItemType === 'video'
                      ? 'Source video:'
                      : selectedItemType === 'narrated_subtitle'
                        ? 'Source subtitle:'
                        : 'Source file:'}
                  </strong>{' '}
                  {selectedItem.sourcePath ? selectedItem.sourcePath : '—'}
                </li>
                <li className={styles.detailItem}>
                  <strong>{selectedItemType === 'video' ? 'Creator:' : 'Author:'}</strong> {selectedAuthor}
                </li>
                <li className={styles.detailItem}>
                  <strong>Genre:</strong> {selectedGenre}
                </li>
                <li className={styles.detailItem}>
                  <strong>Language:</strong> {selectedItem.language}
                </li>
                <li className={styles.detailItem}>
                  <strong>Status:</strong> {selectedItem.status}
                </li>
                <li className={styles.detailItem}>
                  <strong>Media finalized:</strong> {selectedItem.mediaCompleted ? 'Yes' : 'No'}
                </li>
                <li className={styles.detailItem}>
                  <strong>Created:</strong> {formatTimestamp(selectedItem.createdAt)}
                </li>
                <li className={styles.detailItem}>
                  <strong>Updated:</strong> {formatTimestamp(selectedItem.updatedAt)}
                </li>
                <li className={styles.detailItem}>
                  <strong>Library path:</strong> {selectedItem.libraryPath}
                </li>
              </ul>
              <div>
                <h3>Metadata</h3>
                <pre className={styles.metadataBlock}>
                  {JSON.stringify(selectedItem.metadata, null, 2)}
                </pre>
              </div>
            </>
          ) : (
            <p>Select an entry to inspect its metadata snapshot.</p>
          )}
        </aside>
      </div>
    </div>
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

export default LibraryPage;
