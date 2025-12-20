import { useCallback, useMemo, useRef, useState } from 'react';
import type { BookOpenLibraryMetadataPreviewResponse } from '../../api/dtos';
import { appendAccessToken, uploadCoverFile } from '../../api/client';
import {
  coerceRecord,
  normalizeIsbnCandidate,
  normalizeTextValue,
  parseJsonField,
  resolveCoverPreviewUrlFromCoverFile
} from './bookNarrationUtils';

type BookMetadataSectionProps = {
  headingId: string;
  title: string;
  description: string;
  metadataSourceName: string;
  metadataLookupQuery: string;
  metadataPreview: BookOpenLibraryMetadataPreviewResponse | null;
  metadataLoading: boolean;
  metadataError: string | null;
  bookMetadataJson: string;
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
  bookMetadataJson,
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
      const parsed = parseJsonField('book_metadata', bookMetadataJson);
      return { parsedMetadata: parsed, parsedError: null };
    } catch (error) {
      return {
        parsedMetadata: null,
        parsedError: error instanceof Error ? error.message : String(error)
      };
    }
  }, [bookMetadataJson]);

  const updateBookMetadata = useCallback(
    (updater: (draft: Record<string, unknown>) => void) => {
      let draft: Record<string, unknown> = {};
      try {
        draft = parseJsonField('book_metadata', bookMetadataJson);
      } catch {
        draft = {};
      }
      const next = { ...draft };
      updater(next);
      const nextJson = JSON.stringify(next, null, 2);
      if (nextJson === bookMetadataJson) {
        return;
      }
      onBookMetadataJsonChange(nextJson);
    },
    [bookMetadataJson, onBookMetadataJsonChange]
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
  const summary = normalizeTextValue(parsedMetadata?.['book_summary']);
  const coverAssetUrl = normalizeTextValue(parsedMetadata?.['job_cover_asset_url']);
  const coverUrl = normalizeTextValue(parsedMetadata?.['cover_url']);
  const coverFile = normalizeTextValue(parsedMetadata?.['book_cover_file']);
  const openlibraryWorkUrl = normalizeTextValue(parsedMetadata?.['openlibrary_work_url']);
  const openlibraryBookUrl = normalizeTextValue(parsedMetadata?.['openlibrary_book_url']);
  const openlibraryLink = openlibraryBookUrl || openlibraryWorkUrl;
  const isbnQuery = normalizeIsbnCandidate(isbn);
  const resolvedLookupQuery = (isbnQuery ?? metadataLookupQuery).trim();

  const lookup = metadataPreview ? coerceRecord(metadataPreview.book_metadata_lookup) : null;
  const storedLookup = parsedMetadata ? coerceRecord(parsedMetadata['book_metadata_lookup']) : null;
  const rawPayload = lookup ?? storedLookup;
  const lookupBook = lookup ? coerceRecord(lookup['book']) : null;
  const lookupError = normalizeTextValue(lookup?.['error']);
  const lookupCoverUrl =
    normalizeTextValue(lookupBook?.['cover_url']) || normalizeTextValue(lookup?.['cover_url']);
  const lookupCoverFile =
    normalizeTextValue(lookupBook?.['cover_file']) || normalizeTextValue(lookup?.['cover_file']);
  const coverPreviewUrl =
    (coverAssetUrl ? appendAccessToken(coverAssetUrl) : null) ||
    resolveCoverPreviewUrlFromCoverFile(coverFile) ||
    resolveCoverPreviewUrlFromCoverFile(lookupCoverFile) ||
    lookupCoverUrl ||
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

      <div className="metadata-loader-row">
        <label style={{ marginBottom: 0 }}>
          Lookup query
          <input
            type="text"
            value={metadataLookupQuery}
            onChange={(event) => onMetadataLookupQueryChange(event.target.value)}
            placeholder={
              metadataSourceName ? metadataSourceName : 'Title, ISBN, or filename (ISBN field preferred)'
            }
          />
        </label>
        <div className="metadata-loader-actions">
          <button
            type="button"
            className="link-button"
            onClick={() => void onLookupMetadata(resolvedLookupQuery, false)}
            disabled={!resolvedLookupQuery || metadataLoading}
            aria-busy={metadataLoading}
          >
            {metadataLoading ? 'Looking up…' : 'Lookup'}
          </button>
          <button
            type="button"
            className="link-button"
            onClick={() => void onLookupMetadata(resolvedLookupQuery, true)}
            disabled={!resolvedLookupQuery || metadataLoading}
            aria-busy={metadataLoading}
          >
            Refresh
          </button>
          <button
            type="button"
            className="link-button"
            onClick={onClearMetadata}
            disabled={metadataLoading}
          >
            Clear
          </button>
        </div>
      </div>

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

      {bookTitle || bookAuthor || bookYear || isbn || openlibraryLink || coverUrl || coverFile ? (
        <dl className="metadata-grid">
          {jobLabel ? (
            <div className="metadata-grid__row">
              <dt>Label</dt>
              <dd>{jobLabel}</dd>
            </div>
          ) : null}
          {bookTitle ? (
            <div className="metadata-grid__row">
              <dt>Title</dt>
              <dd>{bookTitle}</dd>
            </div>
          ) : null}
          {bookAuthor ? (
            <div className="metadata-grid__row">
              <dt>Author</dt>
              <dd>{bookAuthor}</dd>
            </div>
          ) : null}
          {bookYear ? (
            <div className="metadata-grid__row">
              <dt>Year</dt>
              <dd>{bookYear}</dd>
            </div>
          ) : null}
          {isbn ? (
            <div className="metadata-grid__row">
              <dt>ISBN</dt>
              <dd>{isbn}</dd>
            </div>
          ) : null}
          {openlibraryLink ? (
            <div className="metadata-grid__row">
              <dt>Open Library</dt>
              <dd>
                <a href={openlibraryLink} target="_blank" rel="noopener noreferrer">
                  {openlibraryLink}
                </a>
              </dd>
            </div>
          ) : null}
          {coverUrl ? (
            <div className="metadata-grid__row">
              <dt>Cover URL</dt>
              <dd>{coverUrl}</dd>
            </div>
          ) : null}
          {coverFile ? (
            <div className="metadata-grid__row">
              <dt>Cover file</dt>
              <dd>{coverFile}</dd>
            </div>
          ) : null}
        </dl>
      ) : null}

      {metadataPreview ? (
        <dl className="metadata-grid">
          {metadataPreview.source_name ? (
            <div className="metadata-grid__row">
              <dt>Source</dt>
              <dd>{metadataPreview.source_name}</dd>
            </div>
          ) : null}
          {metadataPreview.query?.title ? (
            <div className="metadata-grid__row">
              <dt>Query</dt>
              <dd>
                {[metadataPreview.query.title, metadataPreview.query.author, metadataPreview.query.isbn]
                  .filter(Boolean)
                  .join(' · ')}
              </dd>
            </div>
          ) : metadataPreview.query?.isbn ? (
            <div className="metadata-grid__row">
              <dt>Query</dt>
              <dd>{metadataPreview.query.isbn}</dd>
            </div>
          ) : null}
          {lookupError ? (
            <div className="metadata-grid__row">
              <dt>Status</dt>
              <dd>{lookupError}</dd>
            </div>
          ) : null}
        </dl>
      ) : null}

      {rawPayload ? (
        <details>
          <summary>Raw payload</summary>
          <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(rawPayload, null, 2)}</pre>
        </details>
      ) : null}

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
          <label style={{ gridColumn: '1 / -1' }}>
            Cover URL
            <input
              type="text"
              value={coverUrl ?? ''}
              onChange={(event) => {
                const value = event.target.value;
                updateBookMetadata((draft) => {
                  const trimmed = value.trim();
                  if (trimmed) {
                    draft['cover_url'] = trimmed;
                  } else {
                    delete draft['cover_url'];
                  }
                });
              }}
            />
          </label>
          <label style={{ gridColumn: '1 / -1' }}>
            Cover file (local)
            <input
              type="text"
              value={coverFile ?? ''}
              onChange={(event) => {
                const value = event.target.value;
                updateBookMetadata((draft) => {
                  const trimmed = value.trim();
                  if (trimmed) {
                    draft['book_cover_file'] = trimmed;
                  } else {
                    delete draft['book_cover_file'];
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
