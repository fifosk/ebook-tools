import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import type { LibraryItem, LibraryViewMode } from '../api/dtos';
import {
  removeLibraryEntry,
  removeLibraryMedia,
  reindexLibrary,
  refreshLibraryMetadata,
  searchLibrary,
  updateLibraryMetadata,
  type LibraryMetadataUpdatePayload,
  type LibrarySearchParams
} from '../api/client';
import LibraryList from '../components/LibraryList';
import LibraryToolbar from '../components/LibraryToolbar';
import styles from './LibraryPage.module.css';
import { extractLibraryBookMetadata, resolveLibraryCoverUrl } from '../utils/libraryMetadata';

const PAGE_SIZE = 25;

type LibraryPageProps = {
  onPlay?: (item: LibraryItem) => void;
};

function LibraryPage({ onPlay }: LibraryPageProps) {
  const [query, setQuery] = useState('');
  const [effectiveQuery, setEffectiveQuery] = useState('');
  const [view, setView] = useState<LibraryViewMode>('flat');
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [selectedItem, setSelectedItem] = useState<LibraryItem | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mutating, setMutating] = useState<Record<string, boolean>>({});
  const [refreshKey, setRefreshKey] = useState(0);
  const [isReindexing, setIsReindexing] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editValues, setEditValues] = useState<{ title: string; author: string; genre: string; language: string }>({
    title: '',
    author: '',
    genre: '',
    language: ''
  });
  const [isSaving, setIsSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

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
    }
  }, [selectedItem]);

  const handleOpen = useCallback((item: LibraryItem) => {
    setIsEditing(false);
    setEditError(null);
    setSelectedItem(item);
  }, []);

  const handleRemoveMedia = useCallback(async (item: LibraryItem) => {
    setMutating((previous) => ({ ...previous, [item.jobId]: true }));
    try {
      const response = await removeLibraryMedia(item.jobId);
      if (response.item) {
        setItems((previous) =>
          previous.map((entry) => (entry.jobId === response.item!.jobId ? response.item! : entry))
        );
        setSelectedItem((current) =>
          current && response.item && current.jobId === response.item.jobId
            ? response.item
            : current
        );
      }
    } catch (actionError) {
      const message =
        actionError instanceof Error ? actionError.message : 'Unable to remove generated media.';
      window.alert(message);
    } finally {
      setMutating((previous) => {
        const next = { ...previous };
        delete next[item.jobId];
        return next;
      });
      setRefreshKey((key) => key + 1);
    }
  }, []);

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

  const handleRefreshMetadata = useCallback(async (item: LibraryItem) => {
    setMutating((previous) => ({ ...previous, [item.jobId]: true }));
    try {
      const updated = await refreshLibraryMetadata(item.jobId);
      setItems((previous) =>
        previous.map((entry) => (entry.jobId === updated.jobId ? updated : entry))
      );
      setSelectedItem((current) => (current && current.jobId === updated.jobId ? updated : current));
    } catch (actionError) {
      const message =
        actionError instanceof Error ? actionError.message : 'Unable to refresh metadata.';
      window.alert(message);
    } finally {
      setMutating((previous) => {
        const next = { ...previous };
        delete next[item.jobId];
        return next;
      });
    }
  }, []);

  const startEditingItem = useCallback(
    (item: LibraryItem) => {
      handleOpen(item);
      setEditError(null);
      setEditValues({
        title: item.bookTitle ?? '',
        author: item.author ?? '',
        genre: item.genre ?? '',
        language: item.language ?? ''
      });
      setIsEditing(true);
    },
    [handleOpen]
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
  }, []);

  const handleEditValueChange = useCallback(
    (field: 'title' | 'author' | 'genre' | 'language') => (event: ChangeEvent<HTMLInputElement>) => {
      const { value } = event.target;
      setEditValues((previous) => ({ ...previous, [field]: value }));
    },
    []
  );

  const handleEditSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (!selectedItem) {
        return;
      }
      setIsSaving(true);
      setEditError(null);

      const payload: LibraryMetadataUpdatePayload = {
        title: editValues.title.trim(),
        author: editValues.author.trim(),
        genre: editValues.genre.trim() ? editValues.genre.trim() : null,
        language: editValues.language.trim(),
      };

      try {
        const updated = await updateLibraryMetadata(selectedItem.jobId, payload);
        setItems((previous) =>
          previous.map((entry) => (entry.jobId === updated.jobId ? updated : entry))
        );
        setSelectedItem(updated);
        setIsEditing(false);
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

  const handlePlay = useCallback(() => {
    if (!selectedItem || !onPlay) {
      return;
    }
    onPlay(selectedItem);
  }, [onPlay, selectedItem]);

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
        <div>
          <LibraryList
            items={items}
            view={view}
            onOpen={handleOpen}
            onRemoveMedia={handleRemoveMedia}
            onRemove={handleRemoveEntry}
            onRefreshMetadata={handleRefreshMetadata}
            onEditMetadata={handleEditMetadata}
            selectedJobId={selectedItem?.jobId}
            mutating={mutating}
          />
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
        </div>
        <aside className={styles.detailsCard} aria-live="polite">
          {selectedItem ? (
            <>
              <h2>{selectedItem.bookTitle || 'Untitled Book'}</h2>
              {coverUrl ? (
                <div className={styles.coverWrapper}>
                  <img
                    src={coverUrl}
                    alt={`Cover art for ${selectedItem.bookTitle || 'selected book'}`}
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
                  Open in Player
                </button>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={() => handleRefreshMetadata(selectedItem)}
                  disabled={Boolean(mutating[selectedItem.jobId]) || isSaving}
                >
                  Refetch Cover
                </button>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={() => startEditingItem(selectedItem)}
                  disabled={isSaving || Boolean(mutating[selectedItem.jobId])}
                >
                  Edit Metadata
                </button>
                {!selectedItem.mediaCompleted ? (
                  <span className={styles.actionHint}>
                    Media is still finalizing or was previously removed for this entry.
                  </span>
                ) : null}
              </div>
              {isEditing ? (
                <form className={styles.editForm} onSubmit={handleEditSubmit}>
                  {editError ? <div className={styles.editError}>{editError}</div> : null}
                  <div className={styles.fieldGroup}>
                    <label className={styles.fieldLabel} htmlFor="library-edit-title">Book Name</label>
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
                    <label className={styles.fieldLabel} htmlFor="library-edit-author">Author</label>
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
              ) : null}
              <ul className={styles.detailList}>
                <li className={styles.detailItem}>
                  <strong>Job ID:</strong> {selectedItem.jobId}
                </li>
                <li className={styles.detailItem}>
                  <strong>Author:</strong> {selectedItem.author || 'Unknown Author'}
                </li>
                <li className={styles.detailItem}>
                  <strong>Genre:</strong> {selectedItem.genre ?? 'Unknown Genre'}
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
