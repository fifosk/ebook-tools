import { useCallback, useMemo, useState } from 'react';
import {
  clearMediaMetadataCache,
  lookupBookOpenLibraryMetadata
} from '../../api/client';
import {
  normalizeIsbnCandidate,
  normalizeTextValue
} from './jobProgressUtils';

export type JobProgressMetadataLookupResult = {
  success: boolean;
  source?: string | null;
  confidence?: string | null;
};

type JobProgressMetadataLookupOptions = {
  jobId: string;
  metadata: Record<string, unknown>;
  onReload: () => void;
};

export function useJobProgressMetadataLookup({
  jobId,
  metadata,
  onReload
}: JobProgressMetadataLookupOptions) {
  const [isbnLookupQuery, setIsbnLookupQuery] = useState('');
  const [isLookingUp, setIsLookingUp] = useState(false);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [lookupResult, setLookupResult] = useState<JobProgressMetadataLookupResult | null>(null);

  const existingIsbn = useMemo(() => {
    return normalizeTextValue(metadata['book_isbn']) ?? normalizeTextValue(metadata['isbn']) ?? null;
  }, [metadata]);

  const resolvedLookupQuery = useMemo(() => {
    const inputIsbn = normalizeIsbnCandidate(isbnLookupQuery);
    if (inputIsbn) {
      return inputIsbn;
    }
    const metadataIsbn = normalizeIsbnCandidate(existingIsbn);
    if (metadataIsbn) {
      return metadataIsbn;
    }
    return isbnLookupQuery.trim();
  }, [existingIsbn, isbnLookupQuery]);

  const handleLookupMetadata = useCallback(async (force: boolean) => {
    setIsLookingUp(true);
    setLookupError(null);
    setLookupResult(null);
    try {
      const result = await lookupBookOpenLibraryMetadata(jobId, { force });
      const mediaMetadata = result.media_metadata_lookup;
      const lookupBook = mediaMetadata && typeof mediaMetadata === 'object'
        ? (mediaMetadata as Record<string, unknown>)['book']
        : null;
      const hasTitle = lookupBook && typeof lookupBook === 'object'
        ? Boolean((lookupBook as Record<string, unknown>)['title'])
        : false;
      const lookupErr = mediaMetadata && typeof mediaMetadata === 'object'
        ? (mediaMetadata as Record<string, unknown>)['error']
        : null;
      const provider = mediaMetadata && typeof mediaMetadata === 'object'
        ? (mediaMetadata as Record<string, unknown>)['provider']
        : null;
      const confidence = mediaMetadata && typeof mediaMetadata === 'object'
        ? (mediaMetadata as Record<string, unknown>)['confidence']
        : null;

      if (lookupErr && typeof lookupErr === 'string') {
        setLookupError(lookupErr);
        setLookupResult({ success: false });
      } else if (hasTitle) {
        setLookupResult({
          success: true,
          source: typeof provider === 'string' ? provider : null,
          confidence: typeof confidence === 'string' ? confidence : null,
        });
        onReload();
      } else {
        setLookupError('No book metadata found.');
        setLookupResult({ success: false });
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to lookup metadata';
      setLookupError(message);
      setLookupResult(null);
    } finally {
      setIsLookingUp(false);
    }
  }, [jobId, onReload]);

  const handleClearMetadata = useCallback(async () => {
    setLookupResult(null);
    setLookupError(null);
    setIsbnLookupQuery('');

    const query = resolvedLookupQuery.trim();
    if (query) {
      try {
        await clearMediaMetadataCache(query);
      } catch {
        // Frontend lookup state is already cleared; cache clearing is best-effort.
      }
    }

    onReload();
  }, [onReload, resolvedLookupQuery]);

  return {
    isbnLookupQuery,
    setIsbnLookupQuery,
    isLookingUp,
    lookupError,
    lookupResult,
    existingIsbn,
    handleLookupMetadata,
    handleClearMetadata
  };
}
