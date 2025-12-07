import {
  DEFAULT_LANGUAGE_FLAG,
  resolveLanguageFlag,
  resolveLanguageName
} from '../constants/languageCodes';
import type { SelectedView } from '../App';
import type { JobState } from './JobList';

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
  youtubeDubView: SelectedView;
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

function resolveSidebarLanguage(job: JobState): { label: string; tooltip?: string; flag?: string } {
  const parameters = job.status.parameters;
  const rawLanguages = parameters?.target_languages;
  const firstLanguage =
    Array.isArray(rawLanguages) && rawLanguages.length > 0
      ? rawLanguages.find((value) => typeof value === 'string' && value.trim().length > 0)
      : null;
  const singleLanguage = (() => {
    const raw =
      parameters && typeof parameters === 'object'
        ? (parameters as Record<string, unknown>)['target_language']
        : null;
    return typeof raw === 'string' ? raw.trim() : null;
  })();
  const normalized =
    Array.isArray(rawLanguages) && rawLanguages.length > 0
      ? rawLanguages
          .map((value) => (typeof value === 'string' ? value.trim() : ''))
          .filter((value) => value.length > 0)
      : [];
  if (singleLanguage) {
    normalized.push(singleLanguage);
  }
  const resolvedLanguages = normalized.map((language) => resolveLanguageName(language) ?? language);

  if (resolvedLanguages.length > 0) {
    return {
      label:
        resolvedLanguages.length > 1
          ? `${resolvedLanguages[0]} +${resolvedLanguages.length - 1}`
          : resolvedLanguages[0],
      tooltip: resolvedLanguages.join(', '),
      flag: resolveLanguageFlag(firstLanguage ?? singleLanguage ?? resolvedLanguages[0]) ?? DEFAULT_LANGUAGE_FLAG
    };
  }

  const fallback = resolveSubtitleTargetLanguage(job.status);
  if (fallback) {
    const resolved = resolveLanguageName(fallback) ?? fallback;
    return { label: resolved, flag: resolveLanguageFlag(fallback) ?? DEFAULT_LANGUAGE_FLAG };
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

function resolveJobGlyph(jobType: string): { icon: string; label: string } {
  switch (jobType) {
    case 'pipeline':
      return { icon: '🎙️', label: 'Narration job' };
    case 'book':
      return { icon: '📝', label: 'Create audiobook job' };
    case 'subtitle':
      return { icon: '🎞️', label: 'Subtitle job' };
    case 'youtube_dub':
      return { icon: '🎙️', label: 'Dub video job' };
    default:
      return { icon: '📦', label: `${jobType} job` };
  }
}

function resolveSidebarProgress(job: JobState): number | null {
  if (!job.status || job.status.status !== 'running') {
    return null;
  }
  const event = job.latestEvent ?? job.status.latest_event ?? null;
  const snapshot = event?.snapshot;
  if (!snapshot) {
    return null;
  }
  const { completed, total } = snapshot;
  if (
    typeof completed !== 'number' ||
    typeof total !== 'number' ||
    !Number.isFinite(completed) ||
    !Number.isFinite(total) ||
    total <= 0
  ) {
    return null;
  }
  const ratio = completed / total;
  if (!Number.isFinite(ratio) || ratio < 0) {
    return null;
  }
  return Math.min(100, Math.max(0, Math.round(ratio * 100)));
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
  youtubeDubView,
  jobMediaView,
  adminView
}: SidebarProps) {
  const isAddBookActive = isPipelineView(selectedView);
  const canOpenPlayer = Boolean(activeJobId);
  const bookJobs = sidebarJobs.filter((job) =>
    job.status.job_type === 'pipeline' || job.status.job_type === 'book'
  );
  const subtitleJobs = sidebarJobs.filter((job) => job.status.job_type === 'subtitle');
  const youtubeDubJobs = sidebarJobs.filter((job) => job.status.job_type === 'youtube_dub');

  return (
    <nav className="sidebar__nav" aria-label="Dashboard menu">
      <details className="sidebar__section" open>
        <summary>🎧 Audiobooks</summary>
        <ul className="sidebar__list">
          <li>
            <button
              type="button"
              className={`sidebar__link ${isAddBookActive ? 'is-active' : ''}`}
              onClick={() => onSelectView('pipeline:source')}
            >
              🎙️ Narrate Ebook
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
        <summary>🎬 Media</summary>
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
        </ul>
      </details>
      <details className="sidebar__section" open>
        <summary>📺 Videos</summary>
        <ul className="sidebar__list">
          <li>
            <button
              type="button"
              className={`sidebar__link ${selectedView === youtubeSubtitlesView ? 'is-active' : ''}`}
              onClick={() => onSelectView(youtubeSubtitlesView)}
            >
              📺 YT Download
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
      <details className="sidebar__section">
        <summary>🗃️ Library</summary>
        <ul className="sidebar__list">
          <li>
            <button
              type="button"
              className={`sidebar__link ${selectedView === libraryView ? 'is-active' : ''}`}
              onClick={() => onSelectView(libraryView)}
            >
              🗂️ Browse library
            </button>
          </li>
          <li>
            <button
              type="button"
              className={`sidebar__link ${selectedView === jobMediaView ? 'is-active' : ''}`}
              onClick={onOpenPlayer}
              disabled={!canOpenPlayer}
            >
              {canOpenPlayer ? `🎬 Open player for job ${activeJobId}` : '🎬 Select a job to open the player'}
            </button>
          </li>
        </ul>
      </details>
      <details className="sidebar__section" open>
        <summary>📊 Job Overview</summary>
        <div>
          <details className="sidebar__section" open>
            <summary>🎧 Audiobooks</summary>
            {bookJobs.length > 0 ? (
              <ul className="sidebar__list">
                {bookJobs.map((job) => {
                  const statusValue = job.status?.status ?? 'pending';
                  const statusLabel = resolveSidebarStatus(statusValue);
                  const isActiveJob = activeJobId === job.jobId;
                  const languageMeta = resolveSidebarLanguage(job);
                  const progressPercent = resolveSidebarProgress(job);
                  const glyph = resolveJobGlyph(job.status.job_type);
                  return (
                    <li key={job.jobId}>
                      <button
                        type="button"
                        className={`sidebar__link sidebar__link--job ${isActiveJob ? 'is-active' : ''}`}
                        onClick={() => onSelectJob(job.jobId)}
                        title={`Job ${job.jobId}`}
                      >
                        <span className="sidebar__job-label" title={languageMeta.tooltip ?? `Job ${job.jobId}`}>
                          {languageMeta.label}
                        </span>
                        <span className="sidebar__job-meta">
                          {progressPercent !== null ? (
                            <span
                              className="job-progress"
                              data-state={statusValue}
                              title={`${progressPercent}% complete`}
                              aria-label={`${progressPercent}% complete`}
                            >
                              {progressPercent}%
                            </span>
                          ) : null}
                          <span
                            className="sidebar__job-type"
                            title={glyph.label}
                            aria-label={glyph.label}
                          >
                            {glyph.icon}
                          </span>
                          {languageMeta.flag ? (
                            <span
                              className="sidebar__job-flag"
                              title={languageMeta.tooltip ?? languageMeta.label}
                              aria-label={languageMeta.tooltip ?? languageMeta.label}
                            >
                              {languageMeta.flag}
                            </span>
                          ) : null}
                          <span
                            className="job-status"
                            data-state={statusValue}
                            title={statusLabel.tooltip}
                            aria-label={statusLabel.tooltip}
                          >
                            {statusLabel.label}
                          </span>
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="sidebar__empty">No audiobook jobs yet.</p>
            )}
          </details>
          <details className="sidebar__section" open>
            <summary>🎞️ Subtitles</summary>
            {subtitleJobs.length > 0 ? (
              <ul className="sidebar__list">
                {subtitleJobs.map((job) => {
                  const statusValue = job.status?.status ?? 'pending';
                  const statusLabel = resolveSidebarStatus(statusValue);
                  const isActiveJob = activeJobId === job.jobId;
                  const languageMeta = resolveSidebarLanguage(job);
                  const progressPercent = resolveSidebarProgress(job);
                  const glyph = resolveJobGlyph(job.status.job_type);
                  return (
                    <li key={job.jobId}>
                      <button
                        type="button"
                        className={`sidebar__link sidebar__link--job ${isActiveJob ? 'is-active' : ''}`}
                        onClick={() => onSelectJob(job.jobId)}
                        title={`Job ${job.jobId}`}
                      >
                        <span className="sidebar__job-label" title={languageMeta.tooltip ?? `Job ${job.jobId}`}>
                          {languageMeta.label}
                        </span>
                        <span className="sidebar__job-meta">
                          {progressPercent !== null ? (
                            <span
                              className="job-progress"
                              data-state={statusValue}
                              title={`${progressPercent}% complete`}
                              aria-label={`${progressPercent}% complete`}
                            >
                              {progressPercent}%
                            </span>
                          ) : null}
                          <span
                            className="sidebar__job-type"
                            title={glyph.label}
                            aria-label={glyph.label}
                          >
                            {glyph.icon}
                          </span>
                          {languageMeta.flag ? (
                            <span
                              className="sidebar__job-flag"
                              title={languageMeta.tooltip ?? languageMeta.label}
                              aria-label={languageMeta.tooltip ?? languageMeta.label}
                            >
                              {languageMeta.flag}
                            </span>
                          ) : null}
                          <span
                            className="job-status"
                            data-state={statusValue}
                            title={statusLabel.tooltip}
                            aria-label={statusLabel.tooltip}
                          >
                            {statusLabel.label}
                          </span>
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
          <details className="sidebar__section" open>
            <summary>📺 Videos</summary>
            {youtubeDubJobs.length > 0 ? (
              <ul className="sidebar__list">
                {youtubeDubJobs.map((job) => {
                  const statusValue = job.status?.status ?? 'pending';
                  const statusLabel = resolveSidebarStatus(statusValue);
                  const isActiveJob = activeJobId === job.jobId;
                  const languageMeta = resolveSidebarLanguage(job);
                  const progressPercent = resolveSidebarProgress(job);
                  const glyph = resolveJobGlyph(job.status.job_type);
                  return (
                    <li key={job.jobId}>
                      <button
                        type="button"
                        className={`sidebar__link sidebar__link--job ${isActiveJob ? 'is-active' : ''}`}
                        onClick={() => onSelectJob(job.jobId)}
                        title={`Job ${job.jobId}`}
                      >
                        <span className="sidebar__job-label" title={languageMeta.tooltip ?? `Job ${job.jobId}`}>
                          {languageMeta.label}
                        </span>
                        <span className="sidebar__job-meta">
                          {progressPercent !== null ? (
                            <span
                              className="job-progress"
                              data-state={statusValue}
                              title={`${progressPercent}% complete`}
                              aria-label={`${progressPercent}% complete`}
                            >
                              {progressPercent}%
                            </span>
                          ) : null}
                          <span
                            className="sidebar__job-type"
                            title={glyph.label}
                            aria-label={glyph.label}
                          >
                            {glyph.icon}
                          </span>
                          {languageMeta.flag ? (
                            <span
                              className="sidebar__job-flag"
                              title={languageMeta.tooltip ?? languageMeta.label}
                              aria-label={languageMeta.tooltip ?? languageMeta.label}
                            >
                              {languageMeta.flag}
                            </span>
                          ) : null}
                          <span
                            className="job-status"
                            data-state={statusValue}
                            title={statusLabel.tooltip}
                            aria-label={statusLabel.tooltip}
                          >
                            {statusLabel.label}
                          </span>
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="sidebar__empty">No dubbing jobs yet.</p>
            )}
          </details>
        </div>
      </details>
      {isAdmin ? (
        <details className="sidebar__section">
          <summary>🛠️ Administration</summary>
          <button
            type="button"
            className={`sidebar__link ${selectedView === adminView ? 'is-active' : ''}`}
            onClick={() => onSelectView(adminView)}
          >
            🛠️ User management
          </button>
        </details>
      ) : null}
    </nav>
  );
}

export default Sidebar;
