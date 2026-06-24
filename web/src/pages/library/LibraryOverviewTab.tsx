import type { ChangeEvent, FormEvent } from 'react';
import type { LibraryItem } from '../../api/dtos';
import styles from '../LibraryPage.module.css';
import type { LibraryEditValues, LibraryItemType } from './libraryPageMetadata';

type LibraryImageLink = {
  src: string;
  link: string;
};

type LibraryOverviewTabProps = {
  item: LibraryItem;
  itemType: LibraryItemType;
  title: string;
  author: string;
  genre: string;
  displayedCoverUrl: string | null;
  tvPoster: LibraryImageLink | null;
  tvStill: LibraryImageLink | null;
  youtubeThumbnail: LibraryImageLink | null;
  permissions: { canView: boolean; canEdit: boolean } | null;
  mutating: boolean;
  isSaving: boolean;
  isEditing: boolean;
  isEnriching: boolean;
  enrichmentError: string | null;
  enrichmentResult: {
    enriched: boolean;
    source?: string | null;
    confidence?: string | null;
  } | null;
  editValues: LibraryEditValues;
  editError: string | null;
  selectedFile: File | null;
  isbnPreview: Record<string, unknown> | null;
  isbnFetchError: string | null;
  isFetchingIsbn: boolean;
  onPlay: () => void;
  onStartEditing: (item: LibraryItem) => void;
  onEnrichMetadata: (force: boolean) => void;
  onEditSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onEditCancel: () => void;
  onEditValueChange: (field: keyof LibraryEditValues) => (event: ChangeEvent<HTMLInputElement>) => void;
  onFetchIsbnMetadata: () => void;
  onSourceFileChange: (event: ChangeEvent<HTMLInputElement>) => void;
};

export default function LibraryOverviewTab({
  item,
  itemType,
  title,
  author,
  genre,
  displayedCoverUrl,
  tvPoster,
  tvStill,
  youtubeThumbnail,
  permissions,
  mutating,
  isSaving,
  isEditing,
  isEnriching,
  enrichmentError,
  enrichmentResult,
  editValues,
  editError,
  selectedFile,
  isbnPreview,
  isbnFetchError,
  isFetchingIsbn,
  onPlay,
  onStartEditing,
  onEnrichMetadata,
  onEditSubmit,
  onEditCancel,
  onEditValueChange,
  onFetchIsbnMetadata,
  onSourceFileChange,
}: LibraryOverviewTabProps) {
  return (
    <div className={styles.tabContent}>
      {itemType !== 'book' && (tvPoster || tvStill) ? (
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
      {itemType === 'video' && !(tvPoster || tvStill) && youtubeThumbnail ? (
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
            alt={`Cover art for ${title}`}
            className={styles.coverImage}
          />
        </div>
      ) : null}
      <div className={styles.actionBar}>
        <button
          type="button"
          className={styles.primaryButton}
          onClick={onPlay}
          disabled={!permissions?.canView}
        >
          Play
        </button>
        <button
          type="button"
          className={styles.secondaryButton}
          onClick={() => onStartEditing(item)}
          disabled={isSaving || mutating || !permissions?.canEdit}
        >
          Edit
        </button>
        {itemType === 'book' ? (
          <button
            type="button"
            className={styles.secondaryButton}
            onClick={(event) => onEnrichMetadata(event.shiftKey)}
            disabled={isEnriching || isSaving || mutating || !permissions?.canEdit}
            title="Fetch metadata from OpenLibrary, Google Books, etc. Hold Shift to force refresh."
          >
            {isEnriching ? 'Refreshing…' : 'Refresh metadata'}
          </button>
        ) : null}
        {!item.mediaCompleted ? (
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
          style={{
            marginTop: '0.75rem',
            padding: '0.5rem',
            borderRadius: '4px',
            backgroundColor: enrichmentResult.enriched ? '#d4edda' : '#e7f3ff',
          }}
        >
          {enrichmentResult.enriched
            ? `Enriched from ${enrichmentResult.source ?? 'external source'} (confidence: ${enrichmentResult.confidence ?? 'unknown'})`
            : 'No additional metadata found from external sources'}
        </div>
      ) : null}
      {isEditing ? (
        <>
          <form className={styles.editForm} onSubmit={onEditSubmit}>
            {editError ? <div className={styles.editError}>{editError}</div> : null}
            <div className={styles.fieldGroup}>
              <label className={styles.fieldLabel} htmlFor="library-edit-title">Title</label>
              <input
                id="library-edit-title"
                type="text"
                className={styles.fieldInput}
                value={editValues.title}
                onChange={onEditValueChange('title')}
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
                onChange={onEditValueChange('author')}
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
                onChange={onEditValueChange('genre')}
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
                onChange={onEditValueChange('language')}
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
                  onChange={onEditValueChange('isbn')}
                  disabled={isSaving || isFetchingIsbn}
                />
                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={onFetchIsbnMetadata}
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
                onChange={onSourceFileChange}
                disabled={isSaving}
              />
              <span className={styles.fileHint}>
                {selectedFile
                  ? `Selected: ${selectedFile.name}`
                  : item.sourcePath
                    ? `Current: ${item.sourcePath}`
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
                onClick={onEditCancel}
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
          <strong>{itemType === 'video' ? 'Creator:' : 'Author:'}</strong> {author}
        </li>
        <li className={styles.detailItem}>
          <strong>Genre:</strong> {genre}
        </li>
        <li className={styles.detailItem}>
          <strong>Language:</strong> {item.language}
        </li>
        <li className={styles.detailItem}>
          <strong>Status:</strong> {item.status}
        </li>
        <li className={styles.detailItem}>
          <strong>Media finalized:</strong> {item.mediaCompleted ? 'Yes' : 'No'}
        </li>
      </ul>
    </div>
  );
}
