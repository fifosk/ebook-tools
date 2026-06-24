export type JobProgressTab = 'overview' | 'metadata' | 'permissions';

type JobProgressTabsProps = {
  activeTab: JobProgressTab;
  onChange: (tab: JobProgressTab) => void;
};

const JOB_PROGRESS_TABS: Array<{ id: JobProgressTab; label: string }> = [
  { id: 'overview', label: 'Overview' },
  { id: 'metadata', label: 'Metadata' },
  { id: 'permissions', label: 'Permissions' },
];

export function JobProgressTabs({ activeTab, onChange }: JobProgressTabsProps) {
  return (
    <div className="job-card__tabs" role="tablist" aria-label="Job tabs">
      {JOB_PROGRESS_TABS.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={activeTab === tab.id}
          className={`job-card__tab ${activeTab === tab.id ? 'is-active' : ''}`}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
