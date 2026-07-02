import { useCallback, useEffect, useState } from 'react';
import type { LibraryItemType } from './libraryPageMetadata';

export type LibraryFocusRequest = {
  jobId: string;
  itemType: LibraryItemType;
  token: number;
};

export type UseLibraryFocusQueryInput = {
  focusRequest: LibraryFocusRequest | null;
  onConsumeFocusRequest?: () => void;
  onApplyFocusRequest: (request: LibraryFocusRequest) => void;
};

export type UseLibraryFocusQueryResult = {
  query: string;
  effectiveQuery: string;
  pendingFocus: LibraryFocusRequest | null;
  handleQueryChange: (value: string) => void;
  clearPendingFocus: () => void;
};

export function useLibraryFocusQuery({
  focusRequest,
  onConsumeFocusRequest,
  onApplyFocusRequest,
}: UseLibraryFocusQueryInput): UseLibraryFocusQueryResult {
  const [query, setQuery] = useState('');
  const [effectiveQuery, setEffectiveQuery] = useState('');
  const [pendingFocus, setPendingFocus] = useState<LibraryFocusRequest | null>(null);

  const handleQueryChange = useCallback(
    (value: string) => {
      setQuery(value);
      if (pendingFocus && value.trim() !== pendingFocus.jobId) {
        setPendingFocus(null);
      }
    },
    [pendingFocus],
  );

  const clearPendingFocus = useCallback(() => {
    setPendingFocus(null);
  }, []);

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
    onApplyFocusRequest(pendingFocus);
  }, [onApplyFocusRequest, pendingFocus]);

  return {
    query,
    effectiveQuery,
    pendingFocus,
    handleQueryChange,
    clearPendingFocus,
  };
}
