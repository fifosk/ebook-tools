import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { BookOpenLibraryMetadataPreviewResponse } from '../../api/dtos';
import { appendAccessToken, lookupBookOpenLibraryMetadataPreview } from '../../api/client';
import {
  loadCachedBookCoverDataUrl,
  loadCachedBookCoverSourceUrl,
  loadCachedBookMetadataJson,
  persistCachedBookCoverDataUrl,
  persistCachedBookMetadataJson,
} from '../../utils/bookMetadataCache';
import type { BookNarrationFormSection, FormState } from './bookNarrationFormTypes';
import {
  basenameFromPath,
  blobToDataUrl,
  coerceRecord,
  normalizeTextValue,
  parseJsonField,
  resolveCoverPreviewUrlFromCoverFile,
} from './bookNarrationUtils';

type UseBookNarrationMetadataOptions = {
  isGeneratedSource: boolean;
  activeTab: BookNarrationFormSection;
  inputFile: string;
  bookMetadataJson: string;
  normalizedInputPath: string | null;
  normalizePath: (value: string | null | undefined) => string | null;
  setFormState: React.Dispatch<React.SetStateAction<FormState>>;
  markUserEditedField: (key: keyof FormState) => void;
};

export function useBookNarrationMetadata({
  isGeneratedSource,
  activeTab,
  inputFile,
  bookMetadataJson,
  normalizedInputPath,
  normalizePath,
  setFormState,
  markUserEditedField,
}: UseBookNarrationMetadataOptions) {
  const metadataLookupIdRef = useRef<number>(0);
  const metadataAutoLookupRef = useRef<string | null>(null);
  const lastCoverCacheRequestRef = useRef<string | null>(null);
  const bookMetadataCacheHydratedRef = useRef<string | null>(null);
  const [metadataLookupQuery, setMetadataLookupQuery] = useState<string>('');
  const [metadataPreview, setMetadataPreview] = useState<BookOpenLibraryMetadataPreviewResponse | null>(null);
  const [metadataLoading, setMetadataLoading] = useState<boolean>(false);
  const [metadataError, setMetadataError] = useState<string | null>(null);
  const [cachedCoverDataUrl, setCachedCoverDataUrl] = useState<string | null>(null);

  const metadataSourceName = useMemo(() => {
    if (isGeneratedSource) {
      return '';
    }
    if (!inputFile.trim()) {
      return '';
    }
    return basenameFromPath(inputFile);
  }, [inputFile, isGeneratedSource]);

  const applyMetadataLookupToDraft = useCallback(
    (payload: BookOpenLibraryMetadataPreviewResponse) => {
      const lookup = coerceRecord(payload.book_metadata_lookup);
      const query = coerceRecord(payload.query);
      const book = lookup ? coerceRecord(lookup['book']) : null;

      const jobLabel =
        normalizeTextValue(lookup?.['job_label']) ||
        normalizeTextValue(book?.['title']) ||
        normalizeTextValue(query?.['title']) ||
        (payload.source_name ? basenameFromPath(payload.source_name) : null);
      const bookTitle = normalizeTextValue(book?.['title']) || normalizeTextValue(query?.['title']);
      const bookAuthor = normalizeTextValue(book?.['author']) || normalizeTextValue(query?.['author']);
      const bookYear = normalizeTextValue(book?.['year']);
      const isbn =
        normalizeTextValue(book?.['isbn']) ||
        normalizeTextValue(query?.['isbn']) ||
        normalizeTextValue(lookup?.['isbn']);
      const summary = normalizeTextValue(book?.['summary']);
      const coverUrl = normalizeTextValue(book?.['cover_url']);
      const coverFile = normalizeTextValue(book?.['cover_file']);
      const openlibraryWorkKey = normalizeTextValue(book?.['openlibrary_work_key']);
      const openlibraryWorkUrl = normalizeTextValue(book?.['openlibrary_work_url']);
      const openlibraryBookKey = normalizeTextValue(book?.['openlibrary_book_key']);
      const openlibraryBookUrl = normalizeTextValue(book?.['openlibrary_book_url']);

      setFormState((previous) => {
        let draft: Record<string, unknown> = {};
        try {
          const parsed = parseJsonField('book_metadata', previous.book_metadata);
          draft = { ...parsed };
        } catch {
          draft = {};
        }

        if (jobLabel) {
          draft['job_label'] = jobLabel;
        }
        if (bookTitle) {
          draft['book_title'] = bookTitle;
        }
        if (bookAuthor) {
          draft['book_author'] = bookAuthor;
        }
        if (bookYear) {
          draft['book_year'] = bookYear;
        }
        if (isbn) {
          draft['isbn'] = isbn;
          draft['book_isbn'] = isbn;
        }
        if (summary) {
          draft['book_summary'] = summary;
        }
        if (coverUrl) {
          draft['cover_url'] = coverUrl;
        }
        if (coverFile) {
          draft['book_cover_file'] = coverFile;
        }
        if (openlibraryWorkKey) {
          draft['openlibrary_work_key'] = openlibraryWorkKey;
        }
        if (openlibraryWorkUrl) {
          draft['openlibrary_work_url'] = openlibraryWorkUrl;
        }
        if (openlibraryBookKey) {
          draft['openlibrary_book_key'] = openlibraryBookKey;
        }
        if (openlibraryBookUrl) {
          draft['openlibrary_book_url'] = openlibraryBookUrl;
        }
        const queriedAt = normalizeTextValue(lookup?.['queried_at']);
        if (queriedAt) {
          draft['openlibrary_queried_at'] = queriedAt;
        }
        if (lookup) {
          draft['book_metadata_lookup'] = lookup;
        } else if ('book_metadata_lookup' in draft) {
          delete draft['book_metadata_lookup'];
        }

        const nextJson = JSON.stringify(draft, null, 2);
        if (previous.book_metadata === nextJson) {
          return previous;
        }
        return { ...previous, book_metadata: nextJson };
      });
    },
    [setFormState],
  );

  const performMetadataLookup = useCallback(
    async (query: string, force: boolean) => {
      const normalized = query.trim();
      if (!normalized) {
        setMetadataPreview(null);
        setMetadataError(null);
        setMetadataLoading(false);
        return;
      }

      const requestId = metadataLookupIdRef.current + 1;
      metadataLookupIdRef.current = requestId;
      setMetadataLoading(true);
      setMetadataError(null);
      try {
        const payload = await lookupBookOpenLibraryMetadataPreview({ query: normalized, force });
        if (metadataLookupIdRef.current !== requestId) {
          return;
        }
        setMetadataPreview(payload);
        applyMetadataLookupToDraft(payload);
      } catch (error) {
        if (metadataLookupIdRef.current !== requestId) {
          return;
        }
        const message = error instanceof Error ? error.message : 'Unable to lookup book metadata.';
        setMetadataError(message);
        setMetadataPreview(null);
      } finally {
        if (metadataLookupIdRef.current === requestId) {
          setMetadataLoading(false);
        }
      }
    },
    [applyMetadataLookupToDraft],
  );

  const handleClearMetadata = useCallback(() => {
    setMetadataPreview(null);
    setMetadataError(null);
    setMetadataLoading(false);
    markUserEditedField('book_metadata');
    setFormState((previous) => ({ ...previous, book_metadata: '{}' }));
  }, [markUserEditedField, setFormState]);

  useEffect(() => {
    const normalized = metadataSourceName.trim();
    setMetadataLookupQuery(normalized);
    setMetadataPreview(null);
    setMetadataError(null);
    setMetadataLoading(false);
    metadataAutoLookupRef.current = null;
  }, [metadataSourceName]);

  useEffect(() => {
    if (activeTab !== 'metadata') {
      return;
    }
    const normalized = metadataSourceName.trim();
    if (!normalized) {
      return;
    }
    if (metadataAutoLookupRef.current === normalized) {
      return;
    }
    metadataAutoLookupRef.current = normalized;
    void performMetadataLookup(normalized, false);
  }, [activeTab, metadataSourceName, performMetadataLookup]);

  useEffect(() => {
    if (!normalizedInputPath) {
      setCachedCoverDataUrl(null);
      return;
    }
    setCachedCoverDataUrl(loadCachedBookCoverDataUrl(normalizedInputPath));
  }, [normalizedInputPath]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    if (!normalizedInputPath) {
      lastCoverCacheRequestRef.current = null;
      return;
    }

    let parsed: Record<string, unknown> | null = null;
    try {
      parsed = parseJsonField('book_metadata', bookMetadataJson);
    } catch {
      parsed = null;
    }

    const coverAssetUrl = normalizeTextValue(parsed?.['job_cover_asset_url']);
    const coverFile = normalizeTextValue(parsed?.['book_cover_file']);
    const coverUrl = normalizeTextValue(parsed?.['cover_url']);
    const coverCandidate =
      (coverAssetUrl ? appendAccessToken(coverAssetUrl) : null) ||
      resolveCoverPreviewUrlFromCoverFile(coverFile) ||
      (coverUrl && (/^https?:\/\//i.test(coverUrl) || coverUrl.startsWith('//')) ? coverUrl : null);
    if (!coverCandidate || coverCandidate.startsWith('data:')) {
      return;
    }

    let url: URL;
    try {
      url = new URL(coverCandidate, window.location.href);
    } catch {
      return;
    }

    const isSameOrigin = url.origin === window.location.origin;
    const stableSource =
      isSameOrigin && url.pathname.startsWith('/storage/covers/')
        ? `${url.origin}${url.pathname}`
        : url.href;
    const existingSource = loadCachedBookCoverSourceUrl(normalizedInputPath);
    if (existingSource === stableSource && cachedCoverDataUrl) {
      return;
    }
    if (lastCoverCacheRequestRef.current === stableSource) {
      return;
    }
    lastCoverCacheRequestRef.current = stableSource;

    const controller = new AbortController();
    void (async () => {
      try {
        const response = await fetch(url.href, {
          credentials: isSameOrigin ? 'include' : 'omit',
          signal: controller.signal,
        });
        if (!response.ok) {
          return;
        }
        const blob = await response.blob();
        if (!blob.type.startsWith('image/')) {
          return;
        }
        if (blob.size > 250_000) {
          return;
        }
        const dataUrl = await blobToDataUrl(blob);
        if (!dataUrl) {
          return;
        }
        persistCachedBookCoverDataUrl(normalizedInputPath, stableSource, dataUrl);
        setCachedCoverDataUrl(dataUrl);
      } catch {
        // ignore
      }
    })();

    return () => controller.abort();
  }, [bookMetadataJson, cachedCoverDataUrl, normalizedInputPath]);

  useEffect(() => {
    if (!normalizedInputPath) {
      bookMetadataCacheHydratedRef.current = null;
      return;
    }
    if (bookMetadataCacheHydratedRef.current === normalizedInputPath) {
      return;
    }
    bookMetadataCacheHydratedRef.current = normalizedInputPath;

    const cached = loadCachedBookMetadataJson(normalizedInputPath);
    if (!cached) {
      return;
    }
    setFormState((previous) => {
      const previousNormalized = normalizePath(previous.input_file);
      if (previousNormalized !== normalizedInputPath) {
        return previous;
      }
      const current = previous.book_metadata.trim();
      if (current && current !== '{}' && current !== 'null') {
        return previous;
      }
      return { ...previous, book_metadata: cached };
    });
  }, [normalizePath, normalizedInputPath, setFormState]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    if (!normalizedInputPath) {
      return;
    }
    const raw = bookMetadataJson;
    const trimmed = raw.trim();
    if (!trimmed || trimmed === '{}' || trimmed === 'null') {
      return;
    }

    const handle = window.setTimeout(() => {
      persistCachedBookMetadataJson(normalizedInputPath, raw);
    }, 600);
    return () => {
      window.clearTimeout(handle);
    };
  }, [bookMetadataJson, normalizedInputPath]);

  return {
    metadataSourceName,
    metadataLookupQuery,
    setMetadataLookupQuery,
    metadataPreview,
    metadataLoading,
    metadataError,
    cachedCoverDataUrl,
    performMetadataLookup,
    handleClearMetadata,
  };
}
