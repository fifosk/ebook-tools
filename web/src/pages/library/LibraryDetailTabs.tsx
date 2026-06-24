import styles from '../LibraryPage.module.css';

export type LibraryDetailTab = 'overview' | 'metadata' | 'permissions';

type LibraryDetailTabsProps = {
  activeTab: LibraryDetailTab;
  onChange: (tab: LibraryDetailTab) => void;
};

const DETAIL_TABS: Array<{ id: LibraryDetailTab; label: string }> = [
  { id: 'overview', label: 'Overview' },
  { id: 'metadata', label: 'Metadata' },
  { id: 'permissions', label: 'Permissions' },
];

export default function LibraryDetailTabs({ activeTab, onChange }: LibraryDetailTabsProps) {
  return (
    <div className={styles.detailTabs} role="tablist" aria-label="Detail tabs">
      {DETAIL_TABS.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={activeTab === tab.id}
          className={`${styles.detailTab} ${activeTab === tab.id ? styles.detailTabActive : ''}`}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
