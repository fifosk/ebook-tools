import { useEffect, useState } from 'react';
import type {
  LibraryItem,
  LibraryViewMode,
  ResumePositionEntry,
} from '../../api/dtos';
import { searchLibrary, type LibrarySearchParams } from '../../api/client';
import { fetchResumePositions } from '../../api/client/resume';
import {
  libraryResumeJobIds,
  reconcileSelectedLibraryItem,
} from './libraryPageMetadata';

type UseLibrarySearchResultsArgs = {
  effectiveQuery: string;
  page: number;
  pageSize: number;
  refreshKey: number;
  view: LibraryViewMode;
};

export function useLibrarySearchResults({
  effectiveQuery,
  page,
  pageSize,
  refreshKey,
  view,
}: UseLibrarySearchResultsArgs) {
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [selectedItem, setSelectedItem] = useState<LibraryItem | null>(null);
  const [resumeEntries, setResumeEntries] = useState<ResumePositionEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    const params: LibrarySearchParams = {
      query: effectiveQuery || undefined,
      view,
      page,
      limit: pageSize,
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
  }, [effectiveQuery, page, pageSize, refreshKey, view]);

  return {
    error,
    isLoading,
    items,
    resumeEntries,
    selectedItem,
    setItems,
    setSelectedItem,
    total,
  };
}
