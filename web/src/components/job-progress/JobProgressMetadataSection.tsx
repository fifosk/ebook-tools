import { MetadataLookupRow } from '../metadata/MetadataLookupRow';
import { MetadataGrid, type MetadataRow } from '../metadata/MetadataGrid';
import {
  formatMetadataLabel,
  formatMetadataValue,
} from './jobProgressUtils';
import type { JobProgressMetadataLookupResult } from './useJobProgressMetadataLookup';

type JobProgressMetadataSectionProps = {
  isSubtitleJob: boolean;
  isBookJob: boolean;
  shouldShowCoverPreview: boolean;
  coverUrl: string | null;
  coverFailed: boolean;
  coverAltText: string;
  openlibraryLink: string | null;
  metadataEntries: Array<[string, unknown]>;
  technicalMetadataEntries: Array<[string, unknown]>;
  isbnLookupQuery: string;
  existingIsbn: string | null;
  isLookingUp: boolean;
  lookupError: string | null;
  lookupResult: JobProgressMetadataLookupResult | null;
  canManage: boolean;
  isReloading: boolean;
  isMutating: boolean;
  onCoverError: () => void;
  onIsbnLookupQueryChange: (value: string) => void;
  onLookupMetadata: (force: boolean) => void;
  onClearMetadata: () => void;
  onReload: () => void;
};

export function JobProgressMetadataSection({
  isSubtitleJob,
  isBookJob,
  shouldShowCoverPreview,
  coverUrl,
  coverFailed,
  coverAltText,
  openlibraryLink,
  metadataEntries,
  technicalMetadataEntries,
  isbnLookupQuery,
  existingIsbn,
  isLookingUp,
  lookupError,
  lookupResult,
  canManage,
  isReloading,
  isMutating,
  onCoverError,
  onIsbnLookupQueryChange,
  onLookupMetadata,
  onClearMetadata,
  onReload,
}: JobProgressMetadataSectionProps) {
  const metadataRows: MetadataRow[] = metadataEntries.map(([key, value]) => ({
    id: key,
    label: formatMetadataLabel(key),
    value: formatMetadataValue(key, value),
  }));
  const technicalMetadataRows: MetadataRow[] = technicalMetadataEntries.map(([key, value]) => ({
    id: key,
    label: formatMetadataLabel(key),
    value: formatMetadataValue(key, value),
  }));

  return (
    <div className="job-card__section">
      <h4>{isSubtitleJob ? 'Subtitle metadata' : 'Book metadata'}</h4>
      {shouldShowCoverPreview && coverUrl && !coverFailed ? (
        <div className="book-metadata-cover" aria-label="Book cover">
          {openlibraryLink ? (
            <a href={openlibraryLink} target="_blank" rel="noopener noreferrer">
              <img
                src={coverUrl}
                alt={coverAltText}
                loading="lazy"
                decoding="async"
                onError={onCoverError}
              />
            </a>
          ) : (
            <img
              src={coverUrl}
              alt={coverAltText}
              loading="lazy"
              decoding="async"
              onError={onCoverError}
            />
          )}
        </div>
      ) : null}
      {metadataEntries.length > 0 ? (
        <MetadataGrid rows={metadataRows} />
      ) : (
        <p className="job-card__metadata-empty">Metadata is not available yet.</p>
      )}
      {isBookJob ? (
        <MetadataLookupRow
          query={isbnLookupQuery}
          onQueryChange={onIsbnLookupQueryChange}
          onLookup={onLookupMetadata}
          onClear={onClearMetadata}
          isLoading={isLookingUp}
          placeholder={existingIsbn ? existingIsbn : 'Title, author, or ISBN'}
          inputLabel="Lookup query"
          hasResult={!!lookupResult}
          disabled={!canManage || isReloading || isMutating}
        />
      ) : null}
      {lookupError ? (
        <div className="notice notice--warning" role="alert" style={{ marginBottom: '0.75rem' }}>
          {lookupError}
        </div>
      ) : null}
      {lookupResult?.success ? (
        <div className="notice notice--success" role="status" style={{ marginBottom: '0.75rem' }}>
          {`Metadata found from ${lookupResult.source ?? 'external source'}${lookupResult.confidence ? ` (confidence: ${lookupResult.confidence})` : ''}`}
        </div>
      ) : null}
      {technicalMetadataEntries.length > 0 ? (
        <details className="job-card__details">
          <summary>Technical parameters</summary>
          <MetadataGrid rows={technicalMetadataRows} />
        </details>
      ) : null}
      <div className="job-card__tab-actions">
        <button
          type="button"
          className="link-button"
          onClick={onReload}
          disabled={!canManage || isReloading || isMutating || isLookingUp}
          aria-busy={isReloading || isMutating}
          data-variant="metadata-action"
        >
          {isReloading ? (
            <>
              Reloading&hellip;
            </>
          ) : (
            'Reload job'
          )}
        </button>
      </div>
    </div>
  );
}
