import type { SelectedView } from '../../App';

interface SidebarAdminLinksProps {
  selectedView: SelectedView;
  onSelectView: (view: SelectedView) => void;
  adminUserManagementView: SelectedView;
  adminReadingBedsView: SelectedView;
  adminSettingsView: SelectedView;
  adminSystemView: SelectedView;
}

export function SidebarAdminLinks({
  selectedView,
  onSelectView,
  adminUserManagementView,
  adminReadingBedsView,
  adminSettingsView,
  adminSystemView
}: SidebarAdminLinksProps) {
  return (
    <details className="sidebar__section">
      <summary>🛠️ Administration</summary>
      <button
        type="button"
        className={`sidebar__link ${selectedView === adminUserManagementView ? 'is-active' : ''}`}
        onClick={() => onSelectView(adminUserManagementView)}
      >
        🛠️ User management
      </button>
      <button
        type="button"
        className={`sidebar__link ${selectedView === adminReadingBedsView ? 'is-active' : ''}`}
        onClick={() => onSelectView(adminReadingBedsView)}
      >
        🎶 Reading music
      </button>
      <button
        type="button"
        className={`sidebar__link ${selectedView === adminSettingsView ? 'is-active' : ''}`}
        onClick={() => onSelectView(adminSettingsView)}
      >
        ⚙️ Settings
      </button>
      <button
        type="button"
        className={`sidebar__link ${selectedView === adminSystemView ? 'is-active' : ''}`}
        onClick={() => onSelectView(adminSystemView)}
      >
        🖥️ System
      </button>
      <div className="sidebar__section-divider" />
      <a
        className="sidebar__link sidebar__link--external"
        href="https://grafana.langtools.fifosk.synology.me/d/ebook-tools-overview/ebook-tools-e28094-overview?orgId=1&refresh=30s"
        target="_blank"
        rel="noopener noreferrer"
      >
        <svg className="sidebar__link-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <polyline points="7 17 12 9 17 17" />
          <line x1="7" y1="13" x2="17" y2="13" />
        </svg>
        Grafana
        <svg className="sidebar__external-arrow" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3.5 8.5L8.5 3.5M8.5 3.5H4.5M8.5 3.5V7.5" />
        </svg>
      </a>
      <a
        className="sidebar__link sidebar__link--external"
        href="https://prometheus.langtools.fifosk.synology.me/"
        target="_blank"
        rel="noopener noreferrer"
      >
        <svg className="sidebar__link-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="9" />
          <path d="M12 3v18" />
          <path d="M3.5 8.5h17" />
          <path d="M3.5 15.5h17" />
        </svg>
        Prometheus
        <svg className="sidebar__external-arrow" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3.5 8.5L8.5 3.5M8.5 3.5H4.5M8.5 3.5V7.5" />
        </svg>
      </a>
    </details>
  );
}
