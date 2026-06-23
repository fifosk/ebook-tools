import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import type {
  AccessPolicyUpdatePayload,
  LibraryItem,
  LibraryViewMode
} from '../api/dtos';
import {
  applyLibraryIsbn,
  appendAccessToken,
  createExport,
  enrichLibraryMetadata,
  lookupLibraryIsbnMetadata,
  removeLibraryEntry,
  reindexLibrary,
  resolveLibraryMediaUrl,
  searchLibrary,
  updateLibraryAccess,
  updateLibraryMetadata,
  uploadLibrarySource,
  withBase,
  type LibrarySearchParams
} from '../api/client';
import {
  buildLibraryItemBuckets,
  buildLibraryMetadataUpdatePlan,
  extractTvMediaMetadata,
  extractYoutubeVideoMetadata,
  formatCount,
  formatLibraryRangeLabel,
  formatYoutubeUploadDate,
  mergeIsbnMetadataIntoEditValues,
  resolveAuthor,
  resolveGenre,
  resolveIsbnPreviewCoverCandidate,
  resolveItemType,
  resolveLibraryTotalPages,
  resolveTitle,
  resolveTvImage,
  resolveYoutubeThumbnail,
  selectActiveLibraryItems,
  type LibraryEditValues,
  type LibraryItemType
} from './library/libraryPageMetadata';
import LibraryList from '../components/LibraryList';
import LibraryToolbar from '../components/LibraryToolbar';
import AccessPolicyEditor from '../components/access/AccessPolicyEditor';
import styles from './LibraryPage.module.css';
import { extractLibraryBookMetadata, resolveLibraryCoverUrl } from '../utils/libraryMetadata';
import { downloadWithSaveAs } from '../utils/downloads';
import { canAccessPolicy, normalizeRole } from '../utils/accessControl';
import type { LibraryOpenInput, LibraryOpenRequest } from '../types/player';
import { extractJobType, getJobTypeGlyph, isTvSeriesMetadata } from '../utils/jobGlyphs';
import JobTypeGlyphBadge from '../components/JobTypeGlyphBadge';
import { useAuth } from '../components/AuthProvider';

const PAGE_SIZE = 25;

type LibraryPageProps = {
  onPlay?: (item: LibraryOpenInput) => void;
  focusRequest?: { jobId: string; itemType: LibraryItemType; token: number } | null;
  onConsumeFocusRequest?: () => void;
};

function LibraryPage({ onPlay, focusRequest = null, onConsumeFocusRequest }: LibraryPageProps) {
  const { session } = useAuth();
  const sessionUser = session?.user ?? null;
  const userId = sessionUser?.username ?? null;
  const normalizedRole = normalizeRole(sessionUser?.role ?? null);
  const isAdmin = normalizedRole === 'admin';
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
  const [editValues, setEditValues] = useState<LibraryEditValues>(
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
  const [pendingFocus, setPendingFocus] = useState<{ jobId: string; itemType: LibraryItemType; token: number } | null>(null);
  const [isEnriching, setIsEnriching] = useState(false);
  const [enrichmentError, setEnrichmentError] = useState<string | null>(null);
  const [enrichmentResult, setEnrichmentResult] = useState<{
    enriched: boolean;
    source?: string | null;
    confidence?: string | null;
  } | null>(null);
  const [detailTab, setDetailTab] = useState<'overview' | 'metadata' | 'permissions'>('overview');

  const resolveItemPermissions = useCallback(
    (item: LibraryItem) => {
      const ownerId = item.ownerId ?? null;
      const defaultVisibility = 'public';
      const canView = canAccessPolicy(item.access ?? null, {
        ownerId,
        userId,
        userRole: normalizedRole,
        permission: 'view',
        defaultVisibility
      });
      const canEdit = canAccessPolicy(item.access ?? null, {
        ownerId,
        userId,
        userRole: normalizedRole,
        permission: 'edit',
        defaultVisibility
      });
      return { canView, canEdit, canExport: canView };
    },
    [normalizedRole, userId]
  );

  const handleQueryChange = useCallback(
    (value: string) => {
      setQuery(value);
      if (pendingFocus && value.trim() !== pendingFocus.jobId) {
        setPendingFocus(null);
      }
    },
    [pendingFocus]
  );

  useEffect(() => {
    const handle = window.setTimeout(() => setEffectiveQuery(query), 250);
    return () => window.clearTimeout(handle);
  }, [query]);

  useEffect(() => {
    if (!focusRequest) {
      return;
    }
    setPendingFocus((current) => {
      if (current && current.token === focusRequest.token) {
        return current;
      }
      return focusRequest;
    });
    onConsumeFocusRequest?.();
  }, [focusRequest, onConsumeFocusRequest]);

  useEffect(() => {
    if (!pendingFocus) {
      return;
    }
    setQuery(pendingFocus.jobId);
    setEffectiveQuery(pendingFocus.jobId);
    setView('flat');
    setPage(1);
    setActiveTab(pendingFocus.itemType);
  }, [pendingFocus]);

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
      setEnrichmentError(null);
      setEnrichmentResult(null);
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

  useEffect(() => {
    if (!pendingFocus) {
      return;
    }
    const match = items.find((item) => item.jobId === pendingFocus.jobId) ?? null;
    if (match) {
      selectLibraryItem(match);
      setPendingFocus(null);
    }
  }, [pendingFocus, items, selectLibraryItem]);

  const openLibraryItem = useCallback(
    (item: LibraryItem) => {
      const permissions = resolveItemPermissions(item);
      if (!permissions.canView) {
        window.alert('You are not authorized to play this entry.');
        return;
      }
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
    [onPlay, resolveItemPermissions, selectLibraryItem]
  );

  const handleOpen = useCallback((item: LibraryItem) => {
    openLibraryItem(item);
  }, [openLibraryItem]);

  const handleRemoveEntry = useCallback(
    async (item: LibraryItem) => {
      const permissions = resolveItemPermissions(item);
      if (!permissions.canEdit) {
        window.alert('You are not authorized to remove this library entry.');
        return;
      }
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
    [items.length, page, resolveItemPermissions]
  );

  const handleExportEntry = useCallback(
    async (item: LibraryItem) => {
      const permissions = resolveItemPermissions(item);
      if (!permissions.canExport) {
        window.alert('You are not authorized to export this entry.');
        return;
      }
      if (mutating[item.jobId]) {
        return;
      }
      if (!item.mediaCompleted) {
        window.alert('Export is available once the entry has finished processing.');
        return;
      }
      setMutating((previous) => ({ ...previous, [item.jobId]: true }));
      try {
        const result = await createExport({
          source_kind: 'library',
          source_id: item.jobId,
          player_type: 'interactive-text'
        });
        const resolved =
          result.download_url.startsWith('http://') || result.download_url.startsWith('https://')
            ? result.download_url
            : withBase(result.download_url);
        const downloadUrl = appendAccessToken(resolved);
        await downloadWithSaveAs(downloadUrl, result.filename ?? null);
      } catch (actionError) {
        const message =
          actionError instanceof Error ? actionError.message : 'Unable to export offline player.';
        window.alert(message);
      } finally {
        setMutating((previous) => {
          const next = { ...previous };
          delete next[item.jobId];
          return next;
        });
      }
    },
    [appendAccessToken, createExport, downloadWithSaveAs, mutating, resolveItemPermissions, withBase]
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
      const permissions = resolveItemPermissions(item);
      if (!permissions.canEdit) {
        window.alert('You are not authorized to edit this entry.');
        return;
      }
      startEditingItem(item);
    },
    [resolveItemPermissions, startEditingItem]
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

      setEditValues((previous) => mergeIsbnMetadataIntoEditValues(previous, metadata, trimmedIsbn));

      const coverCandidate = resolveIsbnPreviewCoverCandidate(metadata);

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

  const handleEnrichMetadata = useCallback(
    async (force: boolean) => {
      if (!selectedItem) {
        return;
      }
      const permissions = resolveItemPermissions(selectedItem);
      if (!permissions.canEdit) {
        setEnrichmentError('You are not authorized to enrich this entry.');
        return;
      }
      setIsEnriching(true);
      setEnrichmentError(null);
      setEnrichmentResult(null);
      try {
        const result = await enrichLibraryMetadata(selectedItem.jobId, { force });
        setEnrichmentResult({
          enriched: result.enriched,
          source: result.source,
          confidence: result.confidence,
        });
        if (result.enriched) {
          // Update local state with enriched item
          setItems((previous) =>
            previous.map((entry) => (entry.jobId === result.item.jobId ? result.item : entry))
          );
          setSelectedItem(result.item);
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Failed to enrich metadata';
        setEnrichmentError(message);
      } finally {
        setIsEnriching(false);
      }
    },
    [resolveItemPermissions, selectedItem]
  );

  const handleEditSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (!selectedItem) {
        return;
      }
      const permissions = resolveItemPermissions(selectedItem);
      if (!permissions.canEdit) {
        setEditError('You are not authorized to edit this entry.');
        return;
      }
      setIsSaving(true);
      setEditError(null);

      const updatePlan = buildLibraryMetadataUpdatePlan(selectedItem, editValues);

      try {
        if (selectedFile) {
          await uploadLibrarySource(selectedItem.jobId, selectedFile);
        }

        if (updatePlan.isbnToApply) {
          await applyLibraryIsbn(selectedItem.jobId, updatePlan.isbnToApply);
        }

        const updated = await updateLibraryMetadata(selectedItem.jobId, updatePlan.payload);
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
    [editValues, resolveItemPermissions, selectedItem]
  );

  const handleUpdateAccess = useCallback(
    async (payload: AccessPolicyUpdatePayload) => {
      if (!selectedItem) {
        throw new Error('Select a library entry to update access.');
      }
      const permissions = resolveItemPermissions(selectedItem);
      if (!permissions.canEdit) {
        throw new Error('You are not authorized to update access for this entry.');
      }
      const jobId = selectedItem.jobId;
      setMutating((previous) => ({ ...previous, [jobId]: true }));
      try {
        const updated = await updateLibraryAccess(jobId, payload);
        setItems((previous) =>
          previous.map((entry) => (entry.jobId === updated.jobId ? updated : entry))
        );
        setSelectedItem(updated);
      } finally {
        setMutating((previous) => {
          if (!previous[jobId]) {
            return previous;
          }
          const next = { ...previous };
          delete next[jobId];
          return next;
        });
      }
    },
    [resolveItemPermissions, selectedItem]
  );

  const totalPages = useMemo(() => {
    return resolveLibraryTotalPages(total, PAGE_SIZE);
  }, [total]);

  const rangeLabel = useMemo(() => {
    return formatLibraryRangeLabel({
      total,
      page,
      pageSize: PAGE_SIZE,
      itemCount: items.length,
    });
  }, [items.length, page, total]);

  const selectedItemType = useMemo(() => resolveItemType(selectedItem), [selectedItem]);
  const selectedTitle = useMemo(() => resolveTitle(selectedItem), [selectedItem]);
  const selectedAuthor = useMemo(() => resolveAuthor(selectedItem), [selectedItem]);
  const selectedGenre = useMemo(() => resolveGenre(selectedItem), [selectedItem]);
  const selectedJobType = useMemo(() => extractJobType(selectedItem?.metadata) ?? null, [selectedItem]);
  const tvMetadata = useMemo(() => extractTvMediaMetadata(selectedItem), [selectedItem]);
  const youtubeMetadata = useMemo(() => extractYoutubeVideoMetadata(tvMetadata), [tvMetadata]);
  const selectedJobGlyph = useMemo(
    () => getJobTypeGlyph(selectedJobType, { isTvSeries: isTvSeriesMetadata(tvMetadata) }),
    [selectedJobType, tvMetadata]
  );
  const selectedPermissions = useMemo(
    () => (selectedItem ? resolveItemPermissions(selectedItem) : null),
    [resolveItemPermissions, selectedItem]
  );

  const itemBuckets = useMemo(() => buildLibraryItemBuckets(items), [items]);
  const { bookItems, videoItems, subtitleItems } = itemBuckets;
  const activeItems = useMemo(
    () => selectActiveLibraryItems(itemBuckets, activeTab),
    [activeTab, itemBuckets]
  );

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

  const tvPoster = useMemo(() => {
    if (!selectedItem) {
      return null;
    }
    return resolveTvImage(selectedItem.jobId, tvMetadata, 'show');
  }, [selectedItem, tvMetadata]);
  const tvStill = useMemo(() => {
    if (!selectedItem) {
      return null;
    }
    return resolveTvImage(selectedItem.jobId, tvMetadata, 'episode');
  }, [selectedItem, tvMetadata]);
  const youtubeThumbnail = useMemo(() => {
    if (!selectedItem) {
      return null;
    }
    return resolveYoutubeThumbnail(selectedItem.jobId, youtubeMetadata);
  }, [selectedItem, youtubeMetadata]);

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
        onQueryChange={handleQueryChange}
        view={view}
        onViewChange={(nextView) => setView(nextView)}
        isLoading={isLoading}
        onReindex={isAdmin ? handleReindex : undefined}
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
              onExport={handleExportEntry}
              onRemove={handleRemoveEntry}
              onEditMetadata={handleEditMetadata}
              resolvePermissions={resolveItemPermissions}
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
                <JobTypeGlyphBadge glyph={selectedJobGlyph} className={styles.detailsJobGlyph} />
                {selectedTitle}
              </h2>
              <div className={styles.detailTabs} role="tablist" aria-label="Detail tabs">
                <button
                  type="button"
                  role="tab"
                  aria-selected={detailTab === 'overview'}
                  className={`${styles.detailTab} ${detailTab === 'overview' ? styles.detailTabActive : ''}`}
                  onClick={() => setDetailTab('overview')}
                >
                  Overview
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={detailTab === 'metadata'}
                  className={`${styles.detailTab} ${detailTab === 'metadata' ? styles.detailTabActive : ''}`}
                  onClick={() => setDetailTab('metadata')}
                >
                  Metadata
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={detailTab === 'permissions'}
                  className={`${styles.detailTab} ${detailTab === 'permissions' ? styles.detailTabActive : ''}`}
                  onClick={() => setDetailTab('permissions')}
                >
                  Permissions
                </button>
              </div>

              {/* Overview Tab */}
              {detailTab === 'overview' ? (
                <div className={styles.tabContent}>
                  {selectedItemType !== 'book' && (tvPoster || tvStill) ? (
                    <div className="tv-metadata-media" aria-label="TV images">
                      {tvPoster ? (
                        <a
                          href={tvPoster.link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="tv-metadata-media__poster"
                        >
                          <img
                            src={tvPoster.src}
                            alt="Show poster"
                            loading="lazy"
                            decoding="async"
                          />
                        </a>
                      ) : null}
                      {tvStill ? (
                        <a
                          href={tvStill.link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="tv-metadata-media__still"
                        >
                          <img
                            src={tvStill.src}
                            alt="Episode still"
                            loading="lazy"
                            decoding="async"
                          />
                        </a>
                      ) : null}
                    </div>
                  ) : null}
                  {selectedItemType === 'video' && !(tvPoster || tvStill) && youtubeThumbnail ? (
                    <div className="tv-metadata-media" aria-label="YouTube thumbnail">
                      <a
                        href={youtubeThumbnail.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="tv-metadata-media__still"
                      >
                        <img
                          src={youtubeThumbnail.src}
                          alt="YouTube thumbnail"
                          loading="lazy"
                          decoding="async"
                        />
                      </a>
                    </div>
                  ) : null}
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
                      disabled={!selectedPermissions?.canView}
                    >
                      Play
                    </button>
                    <button
                      type="button"
                      className={styles.secondaryButton}
                      onClick={() => startEditingItem(selectedItem)}
                      disabled={isSaving || Boolean(mutating[selectedItem.jobId]) || !selectedPermissions?.canEdit}
                    >
                      Edit
                    </button>
                    {selectedItemType === 'book' ? (
                      <button
                        type="button"
                        className={styles.secondaryButton}
                        onClick={(e) => handleEnrichMetadata(e.shiftKey)}
                        disabled={
                          isEnriching ||
                          isSaving ||
                          Boolean(mutating[selectedItem.jobId]) ||
                          !selectedPermissions?.canEdit
                        }
                        title="Fetch metadata from OpenLibrary, Google Books, etc. Hold Shift to force refresh."
                      >
                        {isEnriching ? 'Refreshing…' : 'Refresh metadata'}
                      </button>
                    ) : null}
                    {!selectedItem.mediaCompleted ? (
                      <span className={styles.actionHint}>
                        Media is still finalizing or was previously removed for this entry.
                      </span>
                    ) : null}
                  </div>
                  {enrichmentError ? (
                    <div className={styles.editError} role="alert" style={{ marginTop: '0.75rem' }}>
                      {enrichmentError}
                    </div>
                  ) : null}
                  {enrichmentResult ? (
                    <div
                      className={enrichmentResult.enriched ? styles.successNotice : styles.infoNotice}
                      role="status"
                      style={{ marginTop: '0.75rem', padding: '0.5rem', borderRadius: '4px', backgroundColor: enrichmentResult.enriched ? '#d4edda' : '#e7f3ff' }}
                    >
                      {enrichmentResult.enriched
                        ? `Enriched from ${enrichmentResult.source ?? 'external source'} (confidence: ${enrichmentResult.confidence ?? 'unknown'})`
                        : 'No additional metadata found from external sources'}
                    </div>
                  ) : null}
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
                  </ul>
                </div>
              ) : null}

              {/* Metadata Tab */}
              {detailTab === 'metadata' ? (
                <div className={styles.tabContent}>
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
                      <strong>Job:</strong>{' '}
                      <JobTypeGlyphBadge glyph={selectedJobGlyph} className={styles.detailsJobGlyphInline} />{' '}
                      {selectedJobType ?? '—'}
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
                    {selectedItemType === 'video' && youtubeMetadata ? (
                      <>
                        <li className={styles.detailItem}>
                          <strong>YouTube channel:</strong>{' '}
                          {typeof youtubeMetadata.channel === 'string' && youtubeMetadata.channel.trim()
                            ? youtubeMetadata.channel.trim()
                            : typeof youtubeMetadata.uploader === 'string' && youtubeMetadata.uploader.trim()
                              ? youtubeMetadata.uploader.trim()
                              : '—'}
                        </li>
                        <li className={styles.detailItem}>
                          <strong>YouTube views:</strong> {formatCount(youtubeMetadata.view_count) ?? '—'}
                          {formatCount(youtubeMetadata.like_count) ? ` · 👍 ${formatCount(youtubeMetadata.like_count)}` : ''}
                        </li>
                        <li className={styles.detailItem}>
                          <strong>YouTube uploaded:</strong> {formatYoutubeUploadDate(youtubeMetadata.upload_date) ?? '—'}
                        </li>
                        <li className={styles.detailItem}>
                          <strong>YouTube duration:</strong>{' '}
                          {typeof youtubeMetadata.duration_seconds === 'number'
                            ? `${Math.trunc(youtubeMetadata.duration_seconds)}s`
                            : '—'}
                        </li>
                        <li className={styles.detailItem}>
                          <strong>YouTube link:</strong>{' '}
                          {typeof youtubeMetadata.webpage_url === 'string' && youtubeMetadata.webpage_url.trim() ? (
                            <a href={youtubeMetadata.webpage_url.trim()} target="_blank" rel="noopener noreferrer">
                              Open
                            </a>
                          ) : (
                            '—'
                          )}
                        </li>
                      </>
                    ) : null}
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
                    <h3>Raw Metadata</h3>
                    <pre className={styles.metadataBlock}>
                      {JSON.stringify(selectedItem.metadata, null, 2)}
                    </pre>
                  </div>
                </div>
              ) : null}

              {/* Permissions Tab */}
              {detailTab === 'permissions' ? (
                <div className={styles.tabContent}>
                  <AccessPolicyEditor
                    policy={selectedItem.access ?? null}
                    ownerId={selectedItem.ownerId ?? null}
                    defaultVisibility="public"
                    canEdit={Boolean(selectedPermissions?.canEdit)}
                    onSave={handleUpdateAccess}
                    title="Sharing"
                  />
                </div>
              ) : null}
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
