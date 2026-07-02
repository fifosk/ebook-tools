import type { ChangeEvent, FormEvent } from 'react';
import type { AccessPolicyUpdatePayload, LibraryItem } from '../../api/dtos';
import JobTypeGlyphBadge from '../../components/JobTypeGlyphBadge';
import type { LibraryItemPermissions } from '../../components/library-list/libraryListActions';
import type { JobTypeGlyph } from '../../utils/jobGlyphs';
import styles from '../LibraryPage.module.css';
import LibraryDetailTabs, { type LibraryDetailTab } from './LibraryDetailTabs';
import LibraryMetadataTab from './LibraryMetadataTab';
import LibraryOverviewTab from './LibraryOverviewTab';
import LibraryPermissionsTab from './LibraryPermissionsTab';
import type { LibraryEditValues, LibraryItemType } from './libraryPageMetadata';

type LibraryImageLink = {
  src: string;
  link: string;
};

type LibraryDetailsPanelProps = {
  item: LibraryItem | null;
  itemType: LibraryItemType;
  title: string;
  author: string;
  genre: string;
  jobGlyph: JobTypeGlyph;
  jobType: string | null;
  detailTab: LibraryDetailTab;
  onDetailTabChange: (tab: LibraryDetailTab) => void;
  displayedCoverUrl: string | null;
  tvPoster: LibraryImageLink | null;
  tvStill: LibraryImageLink | null;
  youtubeThumbnail: LibraryImageLink | null;
  youtubeMetadata: Record<string, unknown> | null;
  permissions: LibraryItemPermissions | null;
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
  onSavePermissions: (payload: AccessPolicyUpdatePayload) => Promise<void>;
};

export default function LibraryDetailsPanel({
  item,
  itemType,
  title,
  author,
  genre,
  jobGlyph,
  jobType,
  detailTab,
  onDetailTabChange,
  displayedCoverUrl,
  tvPoster,
  tvStill,
  youtubeThumbnail,
  youtubeMetadata,
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
  onSavePermissions,
}: LibraryDetailsPanelProps) {
  return (
    <aside className={styles.detailsCard} aria-live="polite">
      {item ? (
        <>
          <h2 className={styles.detailsTitle}>
            <JobTypeGlyphBadge glyph={jobGlyph} className={styles.detailsJobGlyph} />
            {title}
          </h2>
          <LibraryDetailTabs activeTab={detailTab} onChange={onDetailTabChange} />

          {detailTab === 'overview' ? (
            <LibraryOverviewTab
              item={item}
              itemType={itemType}
              title={title}
              author={author}
              genre={genre}
              displayedCoverUrl={displayedCoverUrl}
              tvPoster={tvPoster}
              tvStill={tvStill}
              youtubeThumbnail={youtubeThumbnail}
              permissions={permissions}
              mutating={mutating}
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
              onPlay={onPlay}
              onStartEditing={onStartEditing}
              onEnrichMetadata={onEnrichMetadata}
              onEditSubmit={onEditSubmit}
              onEditCancel={onEditCancel}
              onEditValueChange={onEditValueChange}
              onFetchIsbnMetadata={onFetchIsbnMetadata}
              onSourceFileChange={onSourceFileChange}
            />
          ) : null}

          {detailTab === 'metadata' ? (
            <LibraryMetadataTab
              item={item}
              itemType={itemType}
              jobGlyph={jobGlyph}
              jobType={jobType}
              youtubeMetadata={youtubeMetadata}
            />
          ) : null}

          {detailTab === 'permissions' ? (
            <LibraryPermissionsTab
              policy={item.access ?? null}
              ownerId={item.ownerId ?? null}
              canEdit={Boolean(permissions?.canEdit)}
              onSave={onSavePermissions}
            />
          ) : null}
        </>
      ) : (
        <p>Select an entry to inspect its metadata snapshot.</p>
      )}
    </aside>
  );
}
