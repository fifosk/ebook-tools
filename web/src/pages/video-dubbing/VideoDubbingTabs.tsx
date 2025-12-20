import type { VideoDubbingTab } from './videoDubbingTypes';
import styles from '../VideoDubbingPage.module.css';

type VideoDubbingTabsProps = {
  activeTab: VideoDubbingTab;
  videoCount: number;
  jobCount: number;
  isGenerating: boolean;
  canGenerate: boolean;
  onTabChange: (tab: VideoDubbingTab) => void;
  onGenerate: () => void;
};

export default function VideoDubbingTabs({
  activeTab,
  videoCount,
  jobCount,
  isGenerating,
  canGenerate,
  onTabChange,
  onGenerate
}: VideoDubbingTabsProps) {
  return (
    <div className={styles.tabsRow}>
      <div className={styles.tabs} role="tablist" aria-label="Dubbed video tabs">
        <button
          type="button"
          role="tab"
          className={`${styles.tabButton} ${activeTab === 'videos' ? styles.tabButtonActive : ''}`}
          aria-selected={activeTab === 'videos'}
          onClick={() => onTabChange('videos')}
        >
          Source <span className={styles.sectionCount}>{videoCount}</span>
        </button>
        <button
          type="button"
          role="tab"
          className={`${styles.tabButton} ${activeTab === 'metadata' ? styles.tabButtonActive : ''}`}
          aria-selected={activeTab === 'metadata'}
          onClick={() => onTabChange('metadata')}
        >
          Metadata
        </button>
        <button
          type="button"
          role="tab"
          className={`${styles.tabButton} ${activeTab === 'options' ? styles.tabButtonActive : ''}`}
          aria-selected={activeTab === 'options'}
          onClick={() => onTabChange('options')}
        >
          Options
        </button>
        <button
          type="button"
          role="tab"
          className={`${styles.tabButton} ${activeTab === 'jobs' ? styles.tabButtonActive : ''}`}
          aria-selected={activeTab === 'jobs'}
          onClick={() => onTabChange('jobs')}
        >
          Jobs <span className={styles.sectionCount}>{jobCount}</span>
        </button>
      </div>
      <div className={styles.tabsActions}>
        <button className={styles.primaryButton} type="button" onClick={onGenerate} disabled={!canGenerate}>
          {isGenerating ? 'Rendering…' : 'Generate dubbed video'}
        </button>
      </div>
    </div>
  );
}
