import type { LibraryItem, LibraryViewMode, ResumePositionEntry } from '../../api/dtos';
import LibraryList from '../../components/LibraryList';
import type { LibraryItemPermissionResolver } from '../../components/library-list/libraryListActions';
import type { LibraryItemType } from './libraryPageMetadata';
import styles from '../LibraryPage.module.css';

type LibraryEntriesPanelProps = {
  activeTab: LibraryItemType;
  onActiveTabChange: (tab: LibraryItemType) => void;
  bookCount: number;
  subtitleCount: number;
  videoCount: number;
  items: LibraryItem[];
  view: LibraryViewMode;
  onSelect: (item: LibraryItem) => void;
  onOpen: (item: LibraryItem) => void;
  onExport: (item: LibraryItem) => void;
  onRemove: (item: LibraryItem) => void;
  onEditMetadata: (item: LibraryItem) => void;
  resolvePermissions: LibraryItemPermissionResolver;
  selectedJobId?: string | null;
  mutating: Record<string, boolean>;
  resumeEntries: ResumePositionEntry[];
};

export default function LibraryEntriesPanel({
  activeTab,
  onActiveTabChange,
  bookCount,
  subtitleCount,
  videoCount,
  items,
  view,
  onSelect,
  onOpen,
  onExport,
  onRemove,
  onEditMetadata,
  resolvePermissions,
  selectedJobId,
  mutating,
  resumeEntries,
}: LibraryEntriesPanelProps) {
  return (
    <section aria-label="Library entries">
      <div className={styles.listCard}>
        <div className={styles.sectionHeader}>
          <div className={styles.tabs} role="tablist" aria-label="Library tabs">
            <button
              type="button"
              role="tab"
              className={`${styles.tabButton} ${activeTab === 'book' ? styles.tabButtonActive : ''}`}
              aria-selected={activeTab === 'book'}
              onClick={() => onActiveTabChange('book')}
            >
              Books <span className={styles.sectionCount}>{bookCount}</span>
            </button>
            <button
              type="button"
              role="tab"
              className={`${styles.tabButton} ${activeTab === 'narrated_subtitle' ? styles.tabButtonActive : ''}`}
              aria-selected={activeTab === 'narrated_subtitle'}
              onClick={() => onActiveTabChange('narrated_subtitle')}
            >
              Subtitles <span className={styles.sectionCount}>{subtitleCount}</span>
            </button>
            <button
              type="button"
              role="tab"
              className={`${styles.tabButton} ${activeTab === 'video' ? styles.tabButtonActive : ''}`}
              aria-selected={activeTab === 'video'}
              onClick={() => onActiveTabChange('video')}
            >
              Videos <span className={styles.sectionCount}>{videoCount}</span>
            </button>
          </div>
        </div>
        <LibraryList
          items={items}
          view={view}
          variant="embedded"
          onSelect={onSelect}
          onOpen={onOpen}
          onExport={onExport}
          onRemove={onRemove}
          onEditMetadata={onEditMetadata}
          resolvePermissions={resolvePermissions}
          selectedJobId={selectedJobId}
          mutating={mutating}
          resumeEntries={resumeEntries}
        />
      </div>
    </section>
  );
}
