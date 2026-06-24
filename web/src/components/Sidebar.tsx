import type { SelectedView } from '../App';
import type { JobState } from './JobList';
import { SidebarAdminLinks } from './sidebar/SidebarAdminLinks';
import { SidebarCreationLinks } from './sidebar/SidebarCreationLinks';
import { SidebarPlayerButton } from './sidebar/SidebarPlayerButton';
import { SidebarJobRow } from './sidebar/SidebarJobRow';

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
        <SidebarCreationLinks
          selectedView={selectedView}
          onSelectView={onSelectView}
          createBookView={createBookView}
          subtitlesView={subtitlesView}
          youtubeSubtitlesView={youtubeSubtitlesView}
          youtubeDubView={youtubeDubView}
        />
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
        <SidebarAdminLinks
          selectedView={selectedView}
          onSelectView={onSelectView}
          adminUserManagementView={adminUserManagementView}
          adminReadingBedsView={adminReadingBedsView}
          adminSettingsView={adminSettingsView}
          adminSystemView={adminSystemView}
        />
      ) : null}
    </nav>
  );
}

export default Sidebar;
