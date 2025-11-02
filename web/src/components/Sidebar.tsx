import type { JobState } from './JobList';
import type { SelectedView } from '../App';

interface SidebarProps {
  selectedView: SelectedView;
  onSelectView: (view: SelectedView) => void;
  sidebarJobs: JobState[];
  activeJobId: string | null;
  onSelectJob: (jobId: string) => void;
  onOpenPlayer: () => void;
  isAdmin: boolean;
  createBookView: SelectedView;
  libraryView: SelectedView;
  jobMediaView: SelectedView;
  subtitlesView: SelectedView;
  adminView: SelectedView;
}

function isPipelineView(view: SelectedView): boolean {
  return typeof view === 'string' && view.startsWith('pipeline:');
}

export function Sidebar({
  selectedView,
  onSelectView,
  sidebarJobs,
  activeJobId,
  onSelectJob,
  onOpenPlayer,
  isAdmin,
  createBookView,
  libraryView,
  subtitlesView,
  jobMediaView,
  adminView
}: SidebarProps) {
  const isNewImmersiveBookActive = isPipelineView(selectedView);
  const canOpenPlayer = Boolean(activeJobId);

  return (
    <nav className="sidebar__nav" aria-label="Dashboard menu">
      <details className="sidebar__section" open>
        <summary>Books</summary>
        <ul className="sidebar__list">
          <li>
            <button
              type="button"
              className={`sidebar__link ${isNewImmersiveBookActive ? 'is-active' : ''}`}
              onClick={() => onSelectView('pipeline:source')}
            >
              New immersive book
            </button>
          </li>
          <li>
            <button
              type="button"
              className={`sidebar__link ${selectedView === subtitlesView ? 'is-active' : ''}`}
              onClick={() => onSelectView(subtitlesView)}
            >
              Subtitles
            </button>
          </li>
          <li>
            <button
              type="button"
              className={`sidebar__link ${selectedView === createBookView ? 'is-active' : ''}`}
              onClick={() => onSelectView(createBookView)}
            >
              Create book
            </button>
          </li>
        </ul>
      </details>
      <details className="sidebar__section">
        <summary>Library</summary>
        <button
          type="button"
          className={`sidebar__link ${selectedView === libraryView ? 'is-active' : ''}`}
          onClick={() => onSelectView(libraryView)}
        >
          Browse library
        </button>
      </details>
      <details className="sidebar__section">
        <summary>Player</summary>
        <button
          type="button"
          className={`sidebar__link ${selectedView === jobMediaView ? 'is-active' : ''}`}
          onClick={onOpenPlayer}
          disabled={!canOpenPlayer}
        >
          {canOpenPlayer
            ? `Open player for job ${activeJobId}`
            : 'Select a job to open the player'}
        </button>
      </details>
      <details className="sidebar__section" open>
        <summary>Active jobs</summary>
        {sidebarJobs.length > 0 ? (
          <ul className="sidebar__list">
            {sidebarJobs.map((job) => {
              const statusValue = job.status?.status ?? 'pending';
              const isActiveJob = activeJobId === job.jobId;
              return (
                <li key={job.jobId}>
                  <button
                    type="button"
                    className={`sidebar__link sidebar__link--job ${isActiveJob ? 'is-active' : ''}`}
                    onClick={() => onSelectJob(job.jobId)}
                  >
                    <span className="sidebar__job-label">Job {job.jobId}</span>
                    <span className="job-status" data-state={statusValue}>
                      {statusValue}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="sidebar__empty">No active jobs yet.</p>
        )}
      </details>
      {isAdmin ? (
        <details className="sidebar__section">
          <summary>Administration</summary>
          <button
            type="button"
            className={`sidebar__link ${selectedView === adminView ? 'is-active' : ''}`}
            onClick={() => onSelectView(adminView)}
          >
            User management
          </button>
        </details>
      ) : null}
    </nav>
  );
}

export default Sidebar;
