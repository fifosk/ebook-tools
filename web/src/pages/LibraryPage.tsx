import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import type {
  AccessPolicyUpdatePayload,
  LibraryItem,
  LibraryViewMode,
  ResumePositionEntry
} from '../api/dtos';
import {
  applyLibraryIsbn,
  appendAccessToken,
  createExport,
  enrichLibraryMetadata,
  lookupLibraryIsbnMetadata,
  removeLibraryEntry,
  reindexLibrary,
  searchLibrary,
  updateLibraryAccess,
  updateLibraryMetadata,
  uploadLibrarySource,
  resolveExportDownloadUrl,
  type LibrarySearchParams
} from '../api/client';
import { fetchResumePositions } from '../api/client/resume';
import {
  buildLibraryItemBuckets,
  buildLibraryMetadataUpdatePlan,
  clearLibraryItemMutating,
  clearSelectedLibraryItem,
  extractTvMediaMetadata,
  extractYoutubeVideoMetadata,
  formatLibraryRangeLabel,
  libraryResumeJobIds,
  markLibraryItemMutating,
  mergeIsbnMetadataIntoEditValues,
  reconcileSelectedLibraryItem,
  replaceLibraryItem,
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
import LibraryToolbar from '../components/LibraryToolbar';
import LibraryDetailTabs, { type LibraryDetailTab } from './library/LibraryDetailTabs';
import LibraryEntriesPanel from './library/LibraryEntriesPanel';
import LibraryMetadataTab from './library/LibraryMetadataTab';
import LibraryOverviewTab from './library/LibraryOverviewTab';
import LibraryPermissionsTab from './library/LibraryPermissionsTab';
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
  const [detailTab, setDetailTab] = useState<LibraryDetailTab>('overview');
  const [resumeEntries, setResumeEntries] = useState<ResumePositionEntry[]>([]);

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
        setSelectedItem((current) => reconcileSelectedLibraryItem(current, response.items));
        const jobIds = libraryResumeJobIds(response.items);
        if (jobIds.length === 0) {
          setResumeEntries([]);
          return;
        }
        fetchResumePositions(jobIds)
          .then((resumeResponse) => {
            if (!cancelled) {
              setResumeEntries(resumeResponse.entries);
            }
          })
          .catch(() => {
            if (!cancelled) {
              setResumeEntries([]);
            }
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
        setResumeEntries([]);
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
      setMutating((previous) => markLibraryItemMutating(previous, item.jobId));
      try {
        await removeLibraryEntry(item.jobId);
        if (items.length === 1 && page > 1) {
          setPage((previousPage) => Math.max(1, previousPage - 1));
        } else {
          setRefreshKey((key) => key + 1);
        }
        setSelectedItem((current) => clearSelectedLibraryItem(current, item.jobId));
      } catch (actionError) {
        const message =
          actionError instanceof Error ? actionError.message : 'Unable to remove library entry.';
        window.alert(message);
        setRefreshKey((key) => key + 1);
      } finally {
        setMutating((previous) => clearLibraryItemMutating(previous, item.jobId));
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
      setMutating((previous) => markLibraryItemMutating(previous, item.jobId));
      try {
        const result = await createExport({
          source_kind: 'library',
          source_id: item.jobId,
          player_type: 'interactive-text'
        });
        const resolved = resolveExportDownloadUrl(result);
        const downloadUrl = appendAccessToken(resolved);
        await downloadWithSaveAs(downloadUrl, result.filename ?? null);
      } catch (actionError) {
        const message =
          actionError instanceof Error ? actionError.message : 'Unable to export offline player.';
        window.alert(message);
      } finally {
        setMutating((previous) => clearLibraryItemMutating(previous, item.jobId));
      }
    },
    [appendAccessToken, createExport, downloadWithSaveAs, mutating, resolveItemPermissions]
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
          setItems((previous) => replaceLibraryItem(previous, result.item));
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
        setItems((previous) => replaceLibraryItem(previous, updated));
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
      setMutating((previous) => markLibraryItemMutating(previous, jobId));
      try {
        const updated = await updateLibraryAccess(jobId, payload);
        setItems((previous) => replaceLibraryItem(previous, updated));
        setSelectedItem(updated);
      } finally {
        setMutating((previous) => clearLibraryItemMutating(previous, jobId));
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
        <LibraryEntriesPanel
          activeTab={activeTab}
          onActiveTabChange={setActiveTab}
          bookCount={bookItems.length}
          subtitleCount={subtitleItems.length}
          videoCount={videoItems.length}
          items={activeItems}
          view={view}
          onSelect={selectLibraryItem}
          onOpen={handleOpen}
          onExport={handleExportEntry}
          onRemove={handleRemoveEntry}
          onEditMetadata={handleEditMetadata}
          resolvePermissions={resolveItemPermissions}
          selectedJobId={selectedItem?.jobId}
          mutating={mutating}
          resumeEntries={resumeEntries}
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
        <aside className={styles.detailsCard} aria-live="polite">
          {selectedItem ? (
            <>
              <h2 className={styles.detailsTitle}>
                <JobTypeGlyphBadge glyph={selectedJobGlyph} className={styles.detailsJobGlyph} />
                {selectedTitle}
              </h2>
              <LibraryDetailTabs activeTab={detailTab} onChange={setDetailTab} />

              {/* Overview Tab */}
              {detailTab === 'overview' ? (
                <LibraryOverviewTab
                  item={selectedItem}
                  itemType={selectedItemType}
                  title={selectedTitle}
                  author={selectedAuthor}
                  genre={selectedGenre}
                  displayedCoverUrl={displayedCoverUrl}
                  tvPoster={tvPoster}
                  tvStill={tvStill}
                  youtubeThumbnail={youtubeThumbnail}
                  permissions={selectedPermissions}
                  mutating={Boolean(mutating[selectedItem.jobId])}
                  isSaving={isSaving}
                  isEditing={isEditing}
                  isEnriching={isEnriching}
                  enrichmentError={enrichmentError}
                  enrichmentResult={enrichmentResult}
                  editValues={editValues}
                  editError={editError}
                  selectedFile={selectedFile}
                  isbnPreview={isbnPreview}
                  isbnFetchError={isbnFetchError}
                  isFetchingIsbn={isFetchingIsbn}
                  onPlay={handlePlay}
                  onStartEditing={startEditingItem}
                  onEnrichMetadata={handleEnrichMetadata}
                  onEditSubmit={handleEditSubmit}
                  onEditCancel={handleEditCancel}
                  onEditValueChange={handleEditValueChange}
                  onFetchIsbnMetadata={handleFetchIsbnMetadata}
                  onSourceFileChange={handleSourceFileChange}
                />
              ) : null}

              {/* Metadata Tab */}
              {detailTab === 'metadata' ? (
                <LibraryMetadataTab
                  item={selectedItem}
                  itemType={selectedItemType}
                  jobGlyph={selectedJobGlyph}
                  jobType={selectedJobType}
                  youtubeMetadata={youtubeMetadata}
                />
              ) : null}

              {/* Permissions Tab */}
              {detailTab === 'permissions' ? (
                <LibraryPermissionsTab
                  policy={selectedItem.access ?? null}
                  ownerId={selectedItem.ownerId ?? null}
                  canEdit={Boolean(selectedPermissions?.canEdit)}
                  onSave={handleUpdateAccess}
                />
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

export default LibraryPage;
