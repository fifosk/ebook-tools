import { useCallback, useEffect, useMemo, useState } from 'react';
import type { LibraryItem, LibraryViewMode } from '../api/dtos';
import {
  removeLibraryEntry,
  removeLibraryMedia,
  reindexLibrary,
  searchLibrary,
  type LibrarySearchParams
} from '../api/client';
import LibraryList from '../components/LibraryList';
import LibraryToolbar from '../components/LibraryToolbar';
import PlayerPanel from '../components/PlayerPanel';
import { useLibraryMedia } from '../hooks/useLibraryMedia';
import styles from './LibraryPage.module.css';

const PAGE_SIZE = 25;

function LibraryPage() {
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
  const { media, chunks, isComplete: mediaComplete, isLoading: isMediaLoading, error: mediaError } =
    useLibraryMedia(selectedItem?.jobId ?? null);
  const handleVideoPlaybackStateChange = useCallback((_: boolean) => {
    // Library playback does not affect global UI state yet.
  }, []);

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

  const handleOpen = useCallback((item: LibraryItem) => {
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
              <div className={styles.playerSection}>
                <PlayerPanel
                  jobId={selectedItem.jobId}
                  media={media}
                  chunks={chunks}
                  mediaComplete={mediaComplete}
                  isLoading={isMediaLoading}
                  error={mediaError}
                  bookMetadata={selectedItem.metadata ?? null}
                  onVideoPlaybackStateChange={handleVideoPlaybackStateChange}
                />
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
