import type { SelectedView } from '../App';
import type { JobState } from './JobList';
import { SidebarAdminLinks } from './sidebar/SidebarAdminLinks';
import { SidebarCreationLinks } from './sidebar/SidebarCreationLinks';
import { SidebarJobOverview } from './sidebar/SidebarJobOverview';
import { SidebarPlayerButton } from './sidebar/SidebarPlayerButton';

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
      <SidebarJobOverview
        sidebarJobs={sidebarJobs}
        activeJobId={activeJobId}
        onSelectJob={onSelectJob}
        onOpenPlayer={onOpenPlayer}
      />
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
