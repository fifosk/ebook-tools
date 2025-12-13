import {
  DEFAULT_LANGUAGE_FLAG,
  resolveLanguageFlag,
  resolveLanguageName
} from '../constants/languageCodes';
import type { SelectedView } from '../App';
import type { JobState } from './JobList';
import { getStatusGlyph } from '../utils/status';

const SIDEBAR_STAGE_GLYPHS: Record<string, { icon: string; tooltip: string }> = {
  'stitching.start': { icon: '🧵', tooltip: 'Stitching batches' },
  'stitching.done': { icon: '🧵', tooltip: 'Stitching complete' },
  'nas.mirror.start': { icon: '🗄️', tooltip: 'Copying stitched output to NAS' },
  'nas.mirror.done': { icon: '🗄️', tooltip: 'NAS copy complete' }
};

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

function resolveSubtitleMetadata(status: JobState['status']): Record<string, unknown> | null {
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
  return metadata && typeof metadata === 'object' ? (metadata as Record<string, unknown>) : null;
}

function resolveSubtitleTargetLanguage(status: JobState['status']): string | null {
  if (status.job_type !== 'subtitle') {
    return null;
  }
  const metadata = resolveSubtitleMetadata(status);
  if (!metadata) {
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

function normalizeLabel(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function filenameStem(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  const normalized = value.trim();
  if (!normalized) {
    return null;
  }
  const basename = normalized.split(/[/\\]/).pop() ?? normalized;
  const parts = basename.split('.');
  if (parts.length > 1) {
    parts.pop();
  }
  const stem = parts.join('.');
  return stem || basename;
}

function truncateLabel(label: string, maxLength = 28): string {
  if (label.length <= maxLength) {
    return label;
  }
  return `${label.slice(0, Math.max(1, maxLength - 1))}…`;
}

function resolveMetadataTitle(metadata: Record<string, unknown> | null | undefined): string | null {
  if (!metadata) {
    return null;
  }
  return (
    normalizeLabel(metadata['job_label']) ||
    normalizeLabel(metadata['jobLabel']) ||
    normalizeLabel(metadata['book_title']) ||
    normalizeLabel(metadata['title']) ||
    normalizeLabel(metadata['book_name']) ||
    normalizeLabel(metadata['name']) ||
    normalizeLabel(metadata['book_topic']) ||
    normalizeLabel(metadata['topic'])
  );
}

function resolveBookLabel(job: JobState): string | null {
  const status = job.status as JobState['status'] & { job_label?: string | null };
  const explicit = normalizeLabel(
    status.job_label ?? (status as unknown as Record<string, unknown>)['jobLabel']
  );
  const parameters = status.parameters as Record<string, unknown> | null | undefined;
  const paramMetadata =
    parameters && typeof parameters === 'object' && typeof parameters['book_metadata'] === 'object'
      ? (parameters['book_metadata'] as Record<string, unknown>)
      : null;
  const baseOutput =
    parameters && typeof parameters === 'object' ? (parameters['base_output_file'] as string | null | undefined) : null;
  const inputFile =
    parameters && typeof parameters === 'object' ? (parameters['input_file'] as string | null | undefined) : null;
  const result = status.result as Record<string, unknown> | null;
  const resultMetadata =
    result && typeof result === 'object'
      ? (typeof result['book_metadata'] === 'object'
          ? (result['book_metadata'] as Record<string, unknown>)
          : typeof result['metadata'] === 'object'
            ? (result['metadata'] as Record<string, unknown>)
            : null)
      : null;
  const pipelineConfig =
    result && typeof result === 'object' && typeof result['pipeline_config'] === 'object'
      ? (result['pipeline_config'] as Record<string, unknown>)
      : null;

  return (
    explicit ||
    resolveMetadataTitle(paramMetadata) ||
    resolveMetadataTitle(pipelineConfig) ||
    resolveMetadataTitle(resultMetadata) ||
    filenameStem(baseOutput ?? undefined) ||
    filenameStem(inputFile ?? undefined)
  );
}

function resolveSubtitleLabel(job: JobState): string | null {
  const metadata = resolveSubtitleMetadata(job.status);
  const metaName =
    normalizeLabel(metadata?.['input_file']) ||
    normalizeLabel(metadata?.['source']) ||
    normalizeLabel(metadata?.['subtitle_name']);
  if (metaName) {
    return filenameStem(metaName);
  }
  const parameters = job.status.parameters as Record<string, unknown> | null | undefined;
  const subtitlePath =
    parameters && typeof parameters === 'object' ? (parameters['subtitle_path'] as string | null | undefined) : null;
  if (subtitlePath) {
    return filenameStem(subtitlePath);
  }
  return null;
}

function resolveVideoLabel(job: JobState): string | null {
  const result = job.status.result as Record<string, unknown> | null;
  if (result && typeof result === 'object') {
    const dub = result['youtube_dub'];
    if (dub && typeof dub === 'object') {
      const dubMetadata = dub as Record<string, unknown>;
      const videoPath =
        normalizeLabel(dubMetadata['video_path']) ||
        normalizeLabel(dubMetadata['source_subtitle_path']) ||
        normalizeLabel(dubMetadata['subtitle_path']);
      if (videoPath) {
        return filenameStem(videoPath);
      }
    }
  }
  const parameters = job.status.parameters as Record<string, unknown> | null | undefined;
  const videoPath =
    parameters && typeof parameters === 'object' ? (parameters['video_path'] as string | null | undefined) : null;
  const subtitlePath =
    parameters && typeof parameters === 'object' ? (parameters['subtitle_path'] as string | null | undefined) : null;
  return filenameStem(videoPath ?? undefined) ?? filenameStem(subtitlePath ?? undefined);
}

function resolveSidebarLabel(job: JobState): { label: string; tooltip: string } {
  let candidate: string | null = null;
  switch (job.status.job_type) {
    case 'pipeline':
    case 'book':
      candidate = resolveBookLabel(job);
      break;
    case 'subtitle':
      candidate = resolveSubtitleLabel(job);
      break;
    case 'youtube_dub':
      candidate = resolveVideoLabel(job);
      break;
    default:
      candidate = resolveBookLabel(job) ?? resolveSubtitleLabel(job) ?? resolveVideoLabel(job);
      break;
  }
  if (!candidate) {
    const fallbackLanguage = resolveSidebarLanguage(job);
    candidate = fallbackLanguage.label ?? `Job ${job.jobId}`;
  }
  const normalized = candidate.trim();
  const truncated = truncateLabel(normalized);
  return { label: truncated, tooltip: normalized };
}

function resolveSidebarStatus(value: string): { icon: string; tooltip: string } {
  const glyph = getStatusGlyph(value);
  return { icon: glyph.icon, tooltip: glyph.label };
}

function resolveSidebarStage(job: JobState): { icon: string; tooltip: string } | null {
  const event = job.latestEvent ?? job.status.latest_event ?? null;
  const metadata = event?.metadata;
  if (!metadata || typeof metadata !== 'object') {
    return null;
  }
  const stageRaw = (metadata as Record<string, unknown>)['stage'];
  const stage = typeof stageRaw === 'string' ? stageRaw.trim() : '';
  if (!stage) {
    return null;
  }
  return SIDEBAR_STAGE_GLYPHS[stage] ?? null;
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
  const activeJob = activeJobId
    ? sidebarJobs.find((job) => job.jobId === activeJobId) ?? null
    : null;
  const activeJobLabel = activeJob ? resolveSidebarLabel(activeJob) : null;
  const activeJobGlyph = activeJob ? resolveJobGlyph(activeJob.status.job_type) : null;
  const activeJobLanguage = activeJob ? resolveSidebarLanguage(activeJob) : null;
  const activeJobStatus = activeJob ? resolveSidebarStatus(activeJob.status.status ?? 'pending') : null;
  const activeJobStage = activeJob ? resolveSidebarStage(activeJob) : null;
  const bookJobs = sidebarJobs.filter((job) =>
    job.status.job_type === 'pipeline' || job.status.job_type === 'book'
  );
  const subtitleJobs = sidebarJobs.filter((job) => job.status.job_type === 'subtitle');
  const youtubeDubJobs = sidebarJobs.filter((job) => job.status.job_type === 'youtube_dub');

  return (
    <nav className="sidebar__nav" aria-label="Dashboard menu">
      <div className="sidebar__player">
        <button
          type="button"
          className={`sidebar__link sidebar__link--player ${selectedView === jobMediaView ? 'is-active' : ''}`}
          onClick={onOpenPlayer}
          disabled={!canOpenPlayer}
        >
          <span className="sidebar__player-label">
            {activeJob ? (
              <span className="sidebar__player-label-text" title={activeJobLabel?.tooltip ?? `Job ${activeJob.jobId}`}>
                {activeJobGlyph ? (
                  <span className="sidebar__job-type" title={activeJobGlyph.label} aria-label={activeJobGlyph.label}>
                    {activeJobGlyph.icon}
                  </span>
                ) : null}
                <span className="sidebar__player-label-text-inner">
                  {activeJobLabel?.label ?? `Job ${activeJob.jobId}`}
                </span>
              </span>
            ) : (
              '🎬 Player'
            )}
          </span>
          {activeJob ? (
	            <span className="sidebar__player-meta">
	              {activeJobLanguage?.flag ? (
	                <span
	                  className="sidebar__job-flag"
	                  title={activeJobLanguage.tooltip ?? activeJobLanguage.label}
	                  aria-label={activeJobLanguage.tooltip ?? activeJobLanguage.label}
	                >
	                  {activeJobLanguage.flag}
	                </span>
	              ) : null}
	              {activeJobStage ? (
	                <span className="job-stage" title={activeJobStage.tooltip} aria-label={activeJobStage.tooltip}>
	                  {activeJobStage.icon}
	                </span>
	              ) : null}
	              {activeJobStatus ? (
	                <span
	                  className="job-status"
	                  data-state={activeJob.status.status ?? 'pending'}
                  title={activeJobStatus.tooltip}
                  aria-label={activeJobStatus.tooltip}
                >
                  {activeJobStatus.icon}
                </span>
              ) : null}
              {activeJobLanguage?.label ? (
                <span className="sidebar__player-language" title={activeJobLanguage.tooltip ?? activeJobLanguage.label}>
                  {activeJobLanguage.label}
                </span>
              ) : null}
            </span>
          ) : (
            <span className="sidebar__player-meta">Select a job</span>
          )}
        </button>
      </div>
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
	                  const nameMeta = resolveSidebarLabel(job);
	                  const progressPercent = resolveSidebarProgress(job);
	                  const glyph = resolveJobGlyph(job.status.job_type);
	                  const stageGlyph = resolveSidebarStage(job);
	                  return (
	                    <li key={job.jobId}>
	                      <button
	                        type="button"
                        className={`sidebar__link sidebar__link--job ${isActiveJob ? 'is-active' : ''}`}
                        onClick={() => onSelectJob(job.jobId)}
                        title={`${nameMeta.tooltip} (${job.jobId})`}
                      >
                        <span className="sidebar__job-label" title={nameMeta.tooltip}>
                          {nameMeta.label}
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
	                          {stageGlyph ? (
	                            <span className="job-stage" title={stageGlyph.tooltip} aria-label={stageGlyph.tooltip}>
	                              {stageGlyph.icon}
	                            </span>
	                          ) : null}
	                          <span
	                            className="job-status"
	                            data-state={statusValue}
	                            title={statusLabel.tooltip}
                            aria-label={statusLabel.tooltip}
                          >
                            {statusLabel.icon}
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
	                  const nameMeta = resolveSidebarLabel(job);
	                  const progressPercent = resolveSidebarProgress(job);
	                  const glyph = resolveJobGlyph(job.status.job_type);
	                  const stageGlyph = resolveSidebarStage(job);
	                  return (
	                    <li key={job.jobId}>
	                      <button
	                        type="button"
                        className={`sidebar__link sidebar__link--job ${isActiveJob ? 'is-active' : ''}`}
                        onClick={() => onSelectJob(job.jobId)}
                        title={`${nameMeta.tooltip} (${job.jobId})`}
                      >
                        <span className="sidebar__job-label" title={nameMeta.tooltip}>
                          {nameMeta.label}
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
	                          {stageGlyph ? (
	                            <span className="job-stage" title={stageGlyph.tooltip} aria-label={stageGlyph.tooltip}>
	                              {stageGlyph.icon}
	                            </span>
	                          ) : null}
	                          <span
	                            className="job-status"
	                            data-state={statusValue}
	                            title={statusLabel.tooltip}
                            aria-label={statusLabel.tooltip}
                          >
                            {statusLabel.icon}
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
	                  const nameMeta = resolveSidebarLabel(job);
	                  const progressPercent = resolveSidebarProgress(job);
	                  const glyph = resolveJobGlyph(job.status.job_type);
	                  const stageGlyph = resolveSidebarStage(job);
	                  return (
	                    <li key={job.jobId}>
	                      <button
	                        type="button"
                        className={`sidebar__link sidebar__link--job ${isActiveJob ? 'is-active' : ''}`}
                        onClick={() => onSelectJob(job.jobId)}
                        title={`${nameMeta.tooltip} (${job.jobId})`}
                      >
                        <span className="sidebar__job-label" title={nameMeta.tooltip}>
                          {nameMeta.label}
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
	                          {stageGlyph ? (
	                            <span className="job-stage" title={stageGlyph.tooltip} aria-label={stageGlyph.tooltip}>
	                              {stageGlyph.icon}
	                            </span>
	                          ) : null}
	                          <span
	                            className="job-status"
	                            data-state={statusValue}
	                            title={statusLabel.tooltip}
                            aria-label={statusLabel.tooltip}
                          >
                            {statusLabel.icon}
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
        </ul>
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
