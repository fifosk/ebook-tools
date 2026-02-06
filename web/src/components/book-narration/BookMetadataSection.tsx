import { useCallback, useMemo, useRef, useState } from 'react';
import type { BookOpenLibraryMetadataPreviewResponse } from '../../api/dtos';
import { appendAccessToken, uploadCoverFile } from '../../api/client';
import {
  coerceRecord,
  formatGenreValue,
  normalizeIsbnCandidate,
  normalizeTextValue,
  parseJsonField,
  resolveCoverPreviewUrlFromCoverFile
} from './bookNarrationUtils';
import { MetadataLookupRow } from '../metadata/MetadataLookupRow';
import { MetadataGrid, type MetadataRow } from '../metadata/MetadataGrid';
import { RawPayloadDetails } from '../metadata/RawPayloadDetails';

type BookMetadataSectionProps = {
  headingId: string;
  title: string;
  description: string;
  metadataSourceName: string;
  metadataLookupQuery: string;
  metadataPreview: BookOpenLibraryMetadataPreviewResponse | null;
  metadataLoading: boolean;
  metadataError: string | null;
  mediaMetadataJson: string;
  cachedCoverDataUrl: string | null;
  onMetadataLookupQueryChange: (value: string) => void;
  onLookupMetadata: (query: string, force: boolean) => void;
  onClearMetadata: () => void;
  onBookMetadataJsonChange: (value: string) => void;
};

export default function BookMetadataSection({
  headingId,
  title,
  description,
  metadataSourceName,
  metadataLookupQuery,
  metadataPreview,
  metadataLoading,
  metadataError,
  mediaMetadataJson,
  cachedCoverDataUrl,
  onMetadataLookupQueryChange,
  onLookupMetadata,
  onClearMetadata,
  onBookMetadataJsonChange
}: BookMetadataSectionProps) {
  const coverUploadInputRef = useRef<HTMLInputElement | null>(null);
  const [coverUploadCandidate, setCoverUploadCandidate] = useState<File | null>(null);
  const [isUploadingCover, setIsUploadingCover] = useState(false);
  const [coverUploadError, setCoverUploadError] = useState<string | null>(null);
  const [isCoverDragActive, setIsCoverDragActive] = useState(false);
  const [coverPreviewRefreshKey, setCoverPreviewRefreshKey] = useState(0);

  const { parsedMetadata, parsedError } = useMemo(() => {
    try {
      const parsed = parseJsonField('book_metadata', mediaMetadataJson);
      return { parsedMetadata: parsed, parsedError: null };
    } catch (error) {
      return {
        parsedMetadata: null,
        parsedError: error instanceof Error ? error.message : String(error)
      };
    }
  }, [mediaMetadataJson]);

  const updateBookMetadata = useCallback(
    (updater: (draft: Record<string, unknown>) => void) => {
      let draft: Record<string, unknown> = {};
      try {
        draft = parseJsonField('book_metadata', mediaMetadataJson);
      } catch {
        draft = {};
      }
      const next = { ...draft };
      updater(next);
      const nextJson = JSON.stringify(next, null, 2);
      if (nextJson === mediaMetadataJson) {
        return;
      }
      onBookMetadataJsonChange(nextJson);
    },
    [mediaMetadataJson, onBookMetadataJsonChange]
  );

  const performCoverUpload = useCallback(
    async (candidate: File | null) => {
      if (!candidate || isUploadingCover) {
        return;
      }
      setCoverUploadCandidate(candidate);
      setIsUploadingCover(true);
      setCoverUploadError(null);
      try {
        const entry = await uploadCoverFile(candidate);
        updateBookMetadata((draft) => {
          draft['book_cover_file'] = entry.path;
        });
        setCoverPreviewRefreshKey((previous) => previous + 1);
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Unable to upload cover image.';
        setCoverUploadError(message);
      } finally {
        setIsUploadingCover(false);
        setCoverUploadCandidate(null);
        setIsCoverDragActive(false);
        if (coverUploadInputRef.current) {
          coverUploadInputRef.current.value = '';
        }
      }
    },
    [isUploadingCover, updateBookMetadata]
  );

  const jobLabel = normalizeTextValue(parsedMetadata?.['job_label']);
  const bookTitle = normalizeTextValue(parsedMetadata?.['book_title']);
  const bookAuthor = normalizeTextValue(parsedMetadata?.['book_author']);
  const bookYear = normalizeTextValue(parsedMetadata?.['book_year']);
  const isbn =
    normalizeTextValue(parsedMetadata?.['isbn']) || normalizeTextValue(parsedMetadata?.['book_isbn']);
  const genre =
    formatGenreValue(parsedMetadata?.['book_genre']) ||
    formatGenreValue(parsedMetadata?.['book_genres']) ||
    formatGenreValue(parsedMetadata?.['genre']);
  const summary = normalizeTextValue(parsedMetadata?.['book_summary']);
  const coverAssetUrl = normalizeTextValue(parsedMetadata?.['job_cover_asset_url']);
  const coverUrl = normalizeTextValue(parsedMetadata?.['cover_url']);
  const bookCoverUrl = normalizeTextValue(parsedMetadata?.['book_cover_url']);
  const coverFile = normalizeTextValue(parsedMetadata?.['book_cover_file']);
  const openlibraryWorkUrl = normalizeTextValue(parsedMetadata?.['openlibrary_work_url']);
  const openlibraryBookUrl = normalizeTextValue(parsedMetadata?.['openlibrary_book_url']);
  const openlibraryLink = openlibraryBookUrl || openlibraryWorkUrl;
  const isbnQuery = normalizeIsbnCandidate(isbn);
  const resolvedLookupQuery = (isbnQuery ?? metadataLookupQuery).trim();

  const lookup = metadataPreview ? coerceRecord(metadataPreview.media_metadata_lookup) : null;
  const storedLookup = parsedMetadata
    ? coerceRecord(parsedMetadata['media_metadata_lookup'] ?? parsedMetadata['book_metadata_lookup'])
    : null;
  const rawPayload = lookup ?? storedLookup;
  const lookupBook = lookup ? coerceRecord(lookup['book']) : null;
  const lookupError = normalizeTextValue(lookup?.['error']);
  const lookupCoverUrl =
    normalizeTextValue(lookupBook?.['cover_url']) || normalizeTextValue(lookup?.['cover_url']);
  const lookupCoverFile =
    normalizeTextValue(lookupBook?.['cover_file']) || normalizeTextValue(lookup?.['cover_file']);
  // Genre from lookup preview (new job form) or stored metadata (existing job)
  const lookupGenre = formatGenreValue(lookupBook?.['genre']);
  // Resolved genre: prefer stored metadata, fall back to lookup preview
  const resolvedGenre = genre || lookupGenre;
  // Resolve local cover file path to URL (may fail if server doesn't serve /storage/covers/)
  const resolvedCoverFile = resolveCoverPreviewUrlFromCoverFile(coverFile);
  const resolvedLookupCoverFile = resolveCoverPreviewUrlFromCoverFile(lookupCoverFile);

  // Check if we have external URLs (https://...) which are more reliable than local API endpoints
  const hasExternalLookupCover = lookupCoverUrl?.startsWith('https://');
  const hasExternalBookCover = bookCoverUrl?.startsWith('https://');

  // Cover priority:
  // 1. External lookup cover URL (https:// from OpenLibrary etc - most reliable)
  // 2. External book cover URL from enrichment (https:// from OpenLibrary etc)
  // 3. Job cover asset URL (API-served, may fail if cover not mirrored to job directory)
  // 4. Local cover file path (requires backend to serve /storage/covers/)
  // 5. Legacy cover_url field
  const coverPreviewUrl =
    (hasExternalLookupCover ? lookupCoverUrl : null) ||
    (hasExternalBookCover ? bookCoverUrl : null) ||
    (coverAssetUrl ? appendAccessToken(coverAssetUrl) : null) ||
    lookupCoverUrl ||
    bookCoverUrl ||
    resolvedCoverFile ||
    resolvedLookupCoverFile ||
    coverUrl;
  const coverPreviewUrlWithRefresh =
    coverPreviewUrl && coverPreviewUrl.includes('/storage/covers/')
      ? `${coverPreviewUrl}${coverPreviewUrl.includes('?') ? '&' : '?'}v=${coverPreviewRefreshKey}`
      : coverPreviewUrl;
  const resolvedCoverPreviewUrl = cachedCoverDataUrl ?? coverPreviewUrlWithRefresh;
  const coverDropzoneClassName = [
    'file-dropzone',
    'cover-dropzone',
    isCoverDragActive ? 'file-dropzone--dragging' : '',
    isUploadingCover ? 'file-dropzone--uploading' : ''
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <section className="pipeline-card" aria-labelledby={headingId}>
      <header className="pipeline-card__header">
        <h3 id={headingId}>{title}</h3>
        <p>{description}</p>
      </header>

      {metadataError ? (
        <div className="alert" role="alert">
          {metadataError}
        </div>
      ) : null}

      <MetadataLookupRow
        query={metadataLookupQuery}
        onQueryChange={onMetadataLookupQueryChange}
        onLookup={(force) => void onLookupMetadata(resolvedLookupQuery, force)}
        onClear={onClearMetadata}
        isLoading={metadataLoading}
        placeholder={
          metadataSourceName ? metadataSourceName : 'Title, ISBN, or filename (ISBN field preferred)'
        }
        inputLabel="Lookup query"
        hasResult={!!metadataPreview || !!rawPayload}
        disabled={!resolvedLookupQuery}
      />

      {!metadataSourceName && !metadataLookupQuery.trim() ? (
        <p className="form-help-text" role="status">
          Select an EPUB file in the Source tab to load metadata.
        </p>
      ) : null}

      {metadataLoading ? (
        <p className="form-help-text" role="status">
          Loading metadata…
        </p>
      ) : null}

      <div className="book-metadata-cover" aria-label="Book cover">
        {resolvedCoverPreviewUrl ? (
          openlibraryLink ? (
            <a href={openlibraryLink} target="_blank" rel="noopener noreferrer">
              <img
                src={resolvedCoverPreviewUrl ?? undefined}
                alt={bookTitle ? `Cover for ${bookTitle}` : 'Book cover'}
                loading="lazy"
                decoding="async"
              />
            </a>
          ) : (
            <img
              src={resolvedCoverPreviewUrl ?? undefined}
              alt={bookTitle ? `Cover for ${bookTitle}` : 'Book cover'}
              loading="lazy"
              decoding="async"
            />
          )
        ) : (
          <div className="book-metadata-cover__placeholder" aria-hidden="true">
            No cover
          </div>
        )}
        <div
          className={coverDropzoneClassName}
          onDragOver={(event) => {
            if (isUploadingCover) {
              return;
            }
            event.preventDefault();
            setIsCoverDragActive(true);
          }}
          onDragLeave={() => setIsCoverDragActive(false)}
          onDrop={(event) => {
            if (isUploadingCover) {
              return;
            }
            event.preventDefault();
            setIsCoverDragActive(false);
            const file = event.dataTransfer.files?.[0] ?? null;
            void performCoverUpload(file);
          }}
          aria-busy={isUploadingCover}
        >
          <label>
            <strong>Upload cover</strong>
            <span>
              {isUploadingCover
                ? 'Uploading…'
                : coverUploadCandidate
                  ? coverUploadCandidate.name
                  : 'Drop image here or click to browse (saved as 600×900 JPG)'}
            </span>
          </label>
          <input
            ref={coverUploadInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={(event) => {
              const file = event.target.files?.[0] ?? null;
              setCoverUploadError(null);
              void performCoverUpload(file);
            }}
            disabled={isUploadingCover}
          />
        </div>
      </div>

      {coverUploadError ? (
        <p className="form-help-text form-help-text--error" role="alert">
          Cover upload failed: {coverUploadError}
        </p>
      ) : null}

      <MetadataGrid
        rows={[
          { label: 'Label', value: jobLabel },
          { label: 'Title', value: bookTitle },
          { label: 'Author', value: bookAuthor },
          { label: 'Year', value: bookYear },
          { label: 'ISBN', value: isbn },
          { label: 'Genre', value: resolvedGenre },
          { label: 'Open Library', value: openlibraryLink, href: openlibraryLink ?? undefined },
        ]}
      />

      {metadataPreview ? (
        <MetadataGrid
          rows={[
            { label: 'Source', value: metadataPreview.source_name },
            {
              label: 'Query',
              value: metadataPreview.query?.title
                ? [metadataPreview.query.title, metadataPreview.query.author, metadataPreview.query.isbn]
                    .filter(Boolean)
                    .join(' · ')
                : metadataPreview.query?.isbn,
            },
            { label: 'Status', value: lookupError },
          ]}
        />
      ) : null}

      <RawPayloadDetails payload={rawPayload} />

      <fieldset>
        <legend>Edit metadata</legend>
        {parsedError ? (
          <div className="notice notice--warning" role="alert">
            Book metadata JSON is invalid: {parsedError}
          </div>
        ) : null}
        <div className="field-grid">
          <label>
            Job label
            <input
              type="text"
              value={jobLabel ?? ''}
              onChange={(event) => {
                const value = event.target.value;
                updateBookMetadata((draft) => {
                  const trimmed = value.trim();
                  if (trimmed) {
                    draft['job_label'] = trimmed;
                  } else {
                    delete draft['job_label'];
                  }
                });
              }}
            />
          </label>
          <label>
            Title
            <input
              type="text"
              value={bookTitle ?? ''}
              onChange={(event) => {
                const value = event.target.value;
                updateBookMetadata((draft) => {
                  const trimmed = value.trim();
                  if (trimmed) {
                    draft['book_title'] = trimmed;
                  } else {
                    delete draft['book_title'];
                  }
                });
              }}
            />
          </label>
          <label>
            Author
            <input
              type="text"
              value={bookAuthor ?? ''}
              onChange={(event) => {
                const value = event.target.value;
                updateBookMetadata((draft) => {
                  const trimmed = value.trim();
                  if (trimmed) {
                    draft['book_author'] = trimmed;
                  } else {
                    delete draft['book_author'];
                  }
                });
              }}
            />
          </label>
          <label>
            Year
            <input
              type="text"
              inputMode="numeric"
              value={bookYear ?? ''}
              onChange={(event) => {
                const value = event.target.value;
                updateBookMetadata((draft) => {
                  const trimmed = value.trim();
                  if (trimmed) {
                    draft['book_year'] = trimmed;
                  } else {
                    delete draft['book_year'];
                  }
                });
              }}
            />
          </label>
          <label>
            ISBN
            <input
              type="text"
              value={isbn ?? ''}
              onChange={(event) => {
                const value = event.target.value;
                updateBookMetadata((draft) => {
                  const trimmed = value.trim();
                  if (trimmed) {
                    draft['isbn'] = trimmed;
                    draft['book_isbn'] = trimmed;
                  } else {
                    delete draft['isbn'];
                    delete draft['book_isbn'];
                  }
                });
              }}
            />
          </label>
          <label>
            Genre
            <input
              type="text"
              value={resolvedGenre ?? ''}
              onChange={(event) => {
                const value = event.target.value;
                updateBookMetadata((draft) => {
                  const trimmed = value.trim();
                  if (trimmed) {
                    draft['book_genre'] = trimmed;
                  } else {
                    delete draft['book_genre'];
                  }
                });
              }}
            />
          </label>
          <label style={{ gridColumn: '1 / -1' }}>
            Summary
            <textarea
              rows={4}
              value={summary ?? ''}
              onChange={(event) => {
                const value = event.target.value;
                updateBookMetadata((draft) => {
                  const trimmed = value.trim();
                  if (trimmed) {
                    draft['book_summary'] = trimmed;
                  } else {
                    delete draft['book_summary'];
                  }
                });
              }}
            />
          </label>
        </div>
      </fieldset>
    </section>
  );
}
