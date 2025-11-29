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
  youtubeSubtitlesView: SelectedView;
  adminView: SelectedView;
}

function isPipelineView(view: SelectedView): boolean {
  return typeof view === 'string' && view.startsWith('pipeline:');
}

function resolveSubtitleTargetLanguage(status: JobState['status']): string | null {
  if (status.job_type !== 'subtitle') {
    return null;
  }
  const rawResult = status.result as Record<string, unknown> | null;
  if (!rawResult) {
    return null;
  }
  const subtitleSection = rawResult['subtitle'];
  if (!subtitleSection || typeof subtitleSection !== 'object') {
    return null;
  }
  const metadata = (subtitleSection as Record<string, unknown>)['metadata'];
  if (!metadata || typeof metadata !== 'object') {
    return null;
  }
  const target = (metadata as Record<string, unknown>)['target_language'];
  return typeof target === 'string' && target.trim() ? target.trim() : null;
}

function resolveSidebarLanguage(job: JobState): { label: string; tooltip?: string } {
  const rawLanguages = job.status.parameters?.target_languages;
  const normalized =
    Array.isArray(rawLanguages) && rawLanguages.length > 0
      ? rawLanguages
          .map((value) => (typeof value === 'string' ? value.trim() : ''))
          .filter((value) => value.length > 0)
      : [];

  if (normalized.length > 0) {
    return {
      label: normalized.length > 1 ? `${normalized[0]} +${normalized.length - 1}` : normalized[0],
      tooltip: normalized.join(', ')
    };
  }

  const fallback = resolveSubtitleTargetLanguage(job.status);
  if (fallback) {
    return { label: fallback };
  }

  return { label: `Job ${job.jobId}` };
}

const STATUS_SHORTHANDS: Record<string, string> = {
  completed: 'C',
  running: 'R',
  pending: 'P',
  pausing: 'Pg',
  paused: 'Pd',
  failed: 'F',
  cancelled: 'X'
};

function resolveSidebarStatus(value: string): { label: string; tooltip: string } {
  const normalized = value.toLowerCase();
  const label = STATUS_SHORTHANDS[normalized] ?? normalized.charAt(0).toUpperCase();
  const tooltip = `${normalized.charAt(0).toUpperCase()}${normalized.slice(1)}`;
  return { label, tooltip };
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
  youtubeSubtitlesView,
  jobMediaView,
  adminView
}: SidebarProps) {
  const isAddBookActive = isPipelineView(selectedView);
  const canOpenPlayer = Boolean(activeJobId);
  const bookJobs = sidebarJobs.filter((job) => job.status.job_type !== 'subtitle');
  const subtitleJobs = sidebarJobs.filter((job) => job.status.job_type === 'subtitle');

  return (
    <nav className="sidebar__nav" aria-label="Dashboard menu">
      <details className="sidebar__section" open>
        <summary>Books</summary>
        <ul className="sidebar__list">
          <li>
            <button
              type="button"
              className={`sidebar__link ${isAddBookActive ? 'is-active' : ''}`}
              onClick={() => onSelectView('pipeline:source')}
            >
              Add book
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
              className={`sidebar__link ${selectedView === youtubeSubtitlesView ? 'is-active' : ''}`}
              onClick={() => onSelectView(youtubeSubtitlesView)}
            >
              YouTube subtitles
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
        <div>
          <details className="sidebar__section" open>
            <summary>Books</summary>
            {bookJobs.length > 0 ? (
              <ul className="sidebar__list">
                {bookJobs.map((job) => {
                  const statusValue = job.status?.status ?? 'pending';
                  const statusLabel = resolveSidebarStatus(statusValue);
                  const isActiveJob = activeJobId === job.jobId;
                  const languageLabel = resolveSidebarLanguage(job);
                  return (
                    <li key={job.jobId}>
                      <button
                        type="button"
                        className={`sidebar__link sidebar__link--job ${isActiveJob ? 'is-active' : ''}`}
                        onClick={() => onSelectJob(job.jobId)}
                        title={`Job ${job.jobId}`}
                      >
                        <span
                          className="sidebar__job-label"
                          title={languageLabel.tooltip ?? `Job ${job.jobId}`}
                        >
                          {languageLabel.label}
                        </span>
                        <span
                          className="job-status"
                          data-state={statusValue}
                          title={statusLabel.tooltip}
                          aria-label={statusLabel.tooltip}
                        >
                          {statusLabel.label}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="sidebar__empty">No book jobs yet.</p>
            )}
          </details>
          <details className="sidebar__section" open>
            <summary>Subtitles</summary>
            {subtitleJobs.length > 0 ? (
              <ul className="sidebar__list">
                {subtitleJobs.map((job) => {
                  const statusValue = job.status?.status ?? 'pending';
                  const statusLabel = resolveSidebarStatus(statusValue);
                  const isActiveJob = activeJobId === job.jobId;
                  const languageLabel = resolveSidebarLanguage(job);
                  return (
                    <li key={job.jobId}>
                      <button
                        type="button"
                        className={`sidebar__link sidebar__link--job ${isActiveJob ? 'is-active' : ''}`}
                        onClick={() => onSelectJob(job.jobId)}
                        title={`Job ${job.jobId}`}
                      >
                        <span
                          className="sidebar__job-label"
                          title={languageLabel.tooltip ?? `Job ${job.jobId}`}
                        >
                          {languageLabel.label}
                        </span>
                        <span
                          className="job-status"
                          data-state={statusValue}
                          title={statusLabel.tooltip}
                          aria-label={statusLabel.tooltip}
                        >
                          {statusLabel.label}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="sidebar__empty">No subtitle jobs yet.</p>
            )}
          </details>
        </div>
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
