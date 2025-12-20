import type { SubtitleToolTab } from './subtitleToolTypes';
import styles from '../SubtitleToolPage.module.css';

type SubtitleToolTabsProps = {
  activeTab: SubtitleToolTab;
  sourceCount: number;
  jobCount: number;
  isSubmitting: boolean;
  isAssSelection: boolean;
  onTabChange: (tab: SubtitleToolTab) => void;
};

export default function SubtitleToolTabs({
  activeTab,
  sourceCount,
  jobCount,
  isSubmitting,
  isAssSelection,
  onTabChange
}: SubtitleToolTabsProps) {
  return (
    <div className={styles.tabsRow}>
      <div className={styles.tabs} role="tablist" aria-label="Subtitle job tabs">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'subtitles'}
          className={`${styles.tabButton} ${activeTab === 'subtitles' ? styles.tabButtonActive : ''}`}
          onClick={() => onTabChange('subtitles')}
        >
          <span>Source</span>
          <span className={styles.sectionCount}>{sourceCount}</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'metadata'}
          className={`${styles.tabButton} ${activeTab === 'metadata' ? styles.tabButtonActive : ''}`}
          onClick={() => onTabChange('metadata')}
        >
          Metadata
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'options'}
          className={`${styles.tabButton} ${activeTab === 'options' ? styles.tabButtonActive : ''}`}
          onClick={() => onTabChange('options')}
        >
          Options
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'jobs'}
          className={`${styles.tabButton} ${activeTab === 'jobs' ? styles.tabButtonActive : ''}`}
          onClick={() => onTabChange('jobs')}
        >
          <span>Jobs</span>
          <span className={styles.sectionCount}>{jobCount}</span>
        </button>
      </div>
      <div className={styles.tabsActions}>
        <button
          type="submit"
          form="subtitle-submit-form"
          className={styles.primaryButton}
          disabled={isSubmitting || isAssSelection}
        >
          {isSubmitting ? 'Submitting…' : 'Create subtitle job'}
        </button>
      </div>
    </div>
  );
}
