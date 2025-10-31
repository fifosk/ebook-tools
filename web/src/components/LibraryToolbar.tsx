import type { LibraryViewMode } from '../api/dtos';
import styles from './LibraryToolbar.module.css';

const VIEW_OPTIONS: Array<{ value: LibraryViewMode; label: string }> = [
  { value: 'flat', label: 'All' },
  { value: 'by_author', label: 'By Author' },
  { value: 'by_genre', label: 'By Genre' },
  { value: 'by_language', label: 'By Language' }
];

type Props = {
  query: string;
  onQueryChange: (value: string) => void;
  view: LibraryViewMode;
  onViewChange: (view: LibraryViewMode) => void;
  isLoading: boolean;
  onReindex?: () => void;
  onRefresh?: () => void;
  isReindexing?: boolean;
};

function LibraryToolbar({
  query,
  onQueryChange,
  view,
  onViewChange,
  isLoading,
  onReindex,
  onRefresh,
  isReindexing = false
}: Props) {
  return (
    <div className={styles.toolbar}>
      <div className={styles.searchGroup}>
        <input
          type="search"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Search library by author, title, genre, or language"
          className={styles.searchInput}
          aria-label="Search library"
        />
        {isLoading ? <span aria-live="polite">Loading…</span> : null}
      </div>
      <div className={styles.views} role="group" aria-label="Library view modes">
        {VIEW_OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            className={`${styles.viewButton} ${view === option.value ? styles.viewButtonActive : ''}`}
            onClick={() => onViewChange(option.value)}
            aria-pressed={view === option.value}
          >
            {option.label}
          </button>
        ))}
      </div>
      <div className={styles.actions}>
        {onRefresh ? (
          <button type="button" className={styles.actionButton} onClick={onRefresh}>
            Refresh
          </button>
        ) : null}
        {onReindex ? (
          <button
            type="button"
            className={styles.actionButton}
            onClick={onReindex}
            disabled={isReindexing}
          >
            {isReindexing ? 'Reindexing…' : 'Reindex library'}
          </button>
        ) : null}
      </div>
    </div>
  );
}

export default LibraryToolbar;
