import type { SelectedView } from '../App';
import type { JobState } from './JobList';
import { SidebarPlayerButton } from './sidebar/SidebarPlayerButton';
import { SidebarJobRow } from './sidebar/SidebarJobRow';
import { isPipelineView } from './sidebar/sidebarUtils';

interface SidebarProps {
  selectedView: SelectedView;
  onSelectView: (view: SelectedView) => void;
  sidebarJobs: JobState[];
  activeJobId: string | null;
  onSelectJob: (jobId: string) => void;
  onOpenPlayer: (jobId?: string, options?: { autoPlay?: boolean }) => void;
  isAdmin: boolean;
  canScheduleJobs: boolean;
  createBookView: SelectedView;
  libraryView: SelectedView;
  jobMediaView: SelectedView;
  subtitlesView: SelectedView;
  youtubeSubtitlesView: SelectedView;
  youtubeDubView: SelectedView;
  adminUserManagementView: SelectedView;
  adminReadingBedsView: SelectedView;
  adminSettingsView: SelectedView;
  adminSystemView: SelectedView;
}

export function Sidebar({
  selectedView,
  onSelectView,
  sidebarJobs,
  activeJobId,
  onSelectJob,
  onOpenPlayer,
  isAdmin,
  canScheduleJobs,
  createBookView,
  libraryView,
  subtitlesView,
  youtubeSubtitlesView,
  youtubeDubView,
  jobMediaView,
  adminUserManagementView,
  adminReadingBedsView,
  adminSettingsView,
  adminSystemView
}: SidebarProps) {
  const isAddBookActive = isPipelineView(selectedView);
  const activeJob = activeJobId
    ? sidebarJobs.find((job) => job.jobId === activeJobId) ?? null
    : null;
  const bookJobs = sidebarJobs.filter((job) =>
    job.status.job_type === 'pipeline' || job.status.job_type === 'book'
  );
  const subtitleJobs = sidebarJobs.filter((job) => job.status.job_type === 'subtitle');
  const youtubeDubJobs = sidebarJobs.filter((job) => job.status.job_type === 'youtube_dub');
  const hasJobOverview = bookJobs.length > 0 || subtitleJobs.length > 0 || youtubeDubJobs.length > 0;

  return (
    <nav className="sidebar__nav" aria-label="Dashboard menu">
      <div className="sidebar__player">
        <SidebarPlayerButton
          selectedView={selectedView}
          jobMediaView={jobMediaView}
          activeJob={activeJob}
          onOpenPlayer={onOpenPlayer}
        />
        <button
          type="button"
          className={`sidebar__link ${selectedView === libraryView ? 'is-active' : ''}`}
          onClick={() => onSelectView(libraryView)}
        >
          🗂️ Browse library
        </button>
      </div>
      {canScheduleJobs ? (
        <>
          <details className="sidebar__section" open>
            <summary>🎧 Audiobooks</summary>
            <ul className="sidebar__list">
              <li>
                <button
                  type="button"
                  className={`sidebar__link ${isAddBookActive ? 'is-active' : ''}`}
                  onClick={() => onSelectView('pipeline:source')}
                >
                  📚 Book Page
                </button>
              </li>
              <li>
                <button
                  type="button"
                  className={`sidebar__link ${selectedView === createBookView ? 'is-active' : ''}`}
                  onClick={() => onSelectView(createBookView)}
                >
                  📝 Create Audiobook
                </button>
              </li>
            </ul>
          </details>
          <details className="sidebar__section" open>
            <summary>📺 Videos</summary>
            <ul className="sidebar__list">
              <li>
                <button
                  type="button"
                  className={`sidebar__link ${selectedView === subtitlesView ? 'is-active' : ''}`}
                  onClick={() => onSelectView(subtitlesView)}
                >
                  🎞️ Subtitles
                </button>
              </li>
              <li>
                <button
                  type="button"
                  className={`sidebar__link ${selectedView === youtubeSubtitlesView ? 'is-active' : ''}`}
                  onClick={() => onSelectView(youtubeSubtitlesView)}
                >
                  📺 YouTube Video
                </button>
              </li>
              <li>
                <button
                  type="button"
                  className={`sidebar__link ${selectedView === youtubeDubView ? 'is-active' : ''}`}
                  onClick={() => onSelectView(youtubeDubView)}
                >
                  🎙️ Dub Video
                </button>
              </li>
            </ul>
          </details>
        </>
      ) : null}
      <details className="sidebar__section" open>
        <summary>📊 Job Overview</summary>
        <div>
          {!hasJobOverview ? <p className="sidebar__empty">No jobs yet.</p> : null}
          {bookJobs.length > 0 ? (
            <details className="sidebar__section" open>
              <summary>🎧 Audiobooks</summary>
              <ul className="sidebar__list">
                {bookJobs.map((job) => (
                  <SidebarJobRow
                    key={job.jobId}
                    job={job}
                    activeJobId={activeJobId}
                    onSelectJob={onSelectJob}
                    onOpenPlayer={onOpenPlayer}
                  />
                ))}
              </ul>
            </details>
          ) : null}
          {subtitleJobs.length > 0 ? (
            <details className="sidebar__section" open>
              <summary>🎞️ Subtitles</summary>
              <ul className="sidebar__list">
                {subtitleJobs.map((job) => (
                  <SidebarJobRow
                    key={job.jobId}
                    job={job}
                    activeJobId={activeJobId}
                    onSelectJob={onSelectJob}
                    onOpenPlayer={onOpenPlayer}
                  />
                ))}
              </ul>
            </details>
          ) : null}
          {youtubeDubJobs.length > 0 ? (
            <details className="sidebar__section" open>
              <summary>📺 Videos</summary>
              <ul className="sidebar__list">
                {youtubeDubJobs.map((job) => (
                  <SidebarJobRow
                    key={job.jobId}
                    job={job}
                    activeJobId={activeJobId}
                    onSelectJob={onSelectJob}
                    onOpenPlayer={onOpenPlayer}
                  />
                ))}
              </ul>
            </details>
          ) : null}
        </div>
      </details>
      {isAdmin ? (
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
      ) : null}
    </nav>
  );
}

export default Sidebar;
