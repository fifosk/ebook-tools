import {
  DEFAULT_LANGUAGE_FLAG,
  resolveLanguageFlag,
  resolveLanguageName
} from '../constants/languageCodes';
import type { SelectedView } from '../App';
import type { JobState } from './JobList';
import EmojiIcon from './EmojiIcon';
import { getStatusGlyph } from '../utils/status';
import { getJobTypeGlyph } from '../utils/jobGlyphs';

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
  adminUserManagementView: SelectedView;
  adminReadingBedsView: SelectedView;
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
  const status = job.status as JobState['status'] & { job_label?: string | null; jobLabel?: string | null };
  const explicit = normalizeLabel(status.job_label ?? (status as unknown as Record<string, unknown>)['jobLabel']);
  if (explicit) {
    return explicit;
  }
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
  return getJobTypeGlyph(jobType);
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

function resolveImageWaitStatus(job: JobState): { icon: string; tooltip: string; percent: number | null } | null {
  const stats = job.status.image_generation ?? null;
  if (!stats || !stats.enabled) {
    return null;
  }
  if (job.status.status !== 'running') {
    return null;
  }
  const expected = stats.expected;
  const generated = stats.generated;
  const sentenceTotal = stats.sentence_total;
  if (
    typeof expected !== 'number' ||
    !Number.isFinite(expected) ||
    expected <= 0 ||
    typeof generated !== 'number' ||
    !Number.isFinite(generated) ||
    typeof sentenceTotal !== 'number' ||
    !Number.isFinite(sentenceTotal)
  ) {
    return null;
  }
  const event = job.latestEvent ?? job.status.latest_event ?? null;
  const completed = event?.snapshot?.completed;
  if (typeof completed !== 'number' || !Number.isFinite(completed)) {
    return null;
  }
  if (completed < sentenceTotal) {
    return null;
  }
  if (generated >= expected) {
    return null;
  }
  const percent =
    typeof stats.percent === 'number' && Number.isFinite(stats.percent)
      ? stats.percent
      : Math.round((generated / expected) * 100);
  return {
    icon: '🖼️',
    tooltip: `Waiting for images (${generated}/${expected})`,
    percent,
  };
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
  adminUserManagementView,
  adminReadingBedsView
}: SidebarProps) {
  const isAddBookActive = isPipelineView(selectedView);
  const canOpenPlayer = Boolean(activeJobId);
  const activeJob = activeJobId
    ? sidebarJobs.find((job) => job.jobId === activeJobId) ?? null
    : null;
  const activeJobLabel = activeJob ? resolveSidebarLabel(activeJob) : null;
  const activeJobGlyph = activeJob ? resolveJobGlyph(activeJob.status.job_type) : null;
  const activeJobLanguage = activeJob ? resolveSidebarLanguage(activeJob) : null;
  const activeJobImageWait = activeJob ? resolveImageWaitStatus(activeJob) : null;
  const activeJobStatus = activeJob
    ? activeJobImageWait
      ? { icon: activeJobImageWait.icon, tooltip: activeJobImageWait.tooltip }
      : resolveSidebarStatus(activeJob.status.status ?? 'pending')
    : null;
  const activeJobStage = activeJob ? resolveSidebarStage(activeJob) : null;
  const bookJobs = sidebarJobs.filter((job) =>
    job.status.job_type === 'pipeline' || job.status.job_type === 'book'
  );
  const subtitleJobs = sidebarJobs.filter((job) => job.status.job_type === 'subtitle');
  const youtubeDubJobs = sidebarJobs.filter((job) => job.status.job_type === 'youtube_dub');
  const hasJobOverview = bookJobs.length > 0 || subtitleJobs.length > 0 || youtubeDubJobs.length > 0;

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
		                <EmojiIcon
		                  className="sidebar__job-flag"
		                  emoji={activeJobLanguage.flag}
		                  title={activeJobLanguage.tooltip ?? activeJobLanguage.label}
		                  ariaLabel={activeJobLanguage.tooltip ?? activeJobLanguage.label}
		                />
		              ) : null}
              {activeJobStage ? (
                <span className="job-stage" title={activeJobStage.tooltip} aria-label={activeJobStage.tooltip}>
                  {activeJobStage.icon}
                </span>
              ) : null}
              {activeJobImageWait && activeJobImageWait.percent !== null ? (
                <span
                  className="job-progress"
                  data-state="image"
                  title={activeJobImageWait.tooltip}
                  aria-label={activeJobImageWait.tooltip}
                >
                  {activeJobImageWait.percent}%
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
            </span>
          ) : (
            <span className="sidebar__player-meta">Select a job</span>
          )}
        </button>
        <button
          type="button"
          className={`sidebar__link ${selectedView === libraryView ? 'is-active' : ''}`}
          onClick={() => onSelectView(libraryView)}
        >
          🗂️ Browse library
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
      <details className="sidebar__section" open>
        <summary>📊 Job Overview</summary>
        <div>
          {!hasJobOverview ? <p className="sidebar__empty">No jobs yet.</p> : null}
          {bookJobs.length > 0 ? (
            <details className="sidebar__section" open>
              <summary>🎧 Audiobooks</summary>
              <ul className="sidebar__list">
	                {bookJobs.map((job) => {
	                  const statusValue = job.status?.status ?? 'pending';
	                  const imageWait = resolveImageWaitStatus(job);
	                  const statusLabel = imageWait ?? resolveSidebarStatus(statusValue);
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
                          {imageWait && imageWait.percent !== null ? (
                            <span
                              className="job-progress"
                              data-state="image"
                              title={imageWait.tooltip}
                              aria-label={imageWait.tooltip}
                            >
                              {imageWait.percent}%
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
		                            <EmojiIcon
		                              className="sidebar__job-flag"
		                              emoji={languageMeta.flag}
		                              title={languageMeta.tooltip ?? languageMeta.label}
		                              ariaLabel={languageMeta.tooltip ?? languageMeta.label}
		                            />
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
            </details>
          ) : null}
          {subtitleJobs.length > 0 ? (
            <details className="sidebar__section" open>
              <summary>🎞️ Subtitles</summary>
              <ul className="sidebar__list">
	                {subtitleJobs.map((job) => {
	                  const statusValue = job.status?.status ?? 'pending';
	                  const imageWait = resolveImageWaitStatus(job);
	                  const statusLabel = imageWait ?? resolveSidebarStatus(statusValue);
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
                          {imageWait && imageWait.percent !== null ? (
                            <span
                              className="job-progress"
                              data-state="image"
                              title={imageWait.tooltip}
                              aria-label={imageWait.tooltip}
                            >
                              {imageWait.percent}%
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
		                            <EmojiIcon
		                              className="sidebar__job-flag"
		                              emoji={languageMeta.flag}
		                              title={languageMeta.tooltip ?? languageMeta.label}
		                              ariaLabel={languageMeta.tooltip ?? languageMeta.label}
		                            />
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
            </details>
          ) : null}
          {youtubeDubJobs.length > 0 ? (
            <details className="sidebar__section" open>
              <summary>📺 Videos</summary>
              <ul className="sidebar__list">
	                {youtubeDubJobs.map((job) => {
	                  const statusValue = job.status?.status ?? 'pending';
	                  const imageWait = resolveImageWaitStatus(job);
	                  const statusLabel = imageWait ?? resolveSidebarStatus(statusValue);
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
                          {imageWait && imageWait.percent !== null ? (
                            <span
                              className="job-progress"
                              data-state="image"
                              title={imageWait.tooltip}
                              aria-label={imageWait.tooltip}
                            >
                              {imageWait.percent}%
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
		                            <EmojiIcon
		                              className="sidebar__job-flag"
		                              emoji={languageMeta.flag}
		                              title={languageMeta.tooltip ?? languageMeta.label}
		                              ariaLabel={languageMeta.tooltip ?? languageMeta.label}
		                            />
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
        </details>
      ) : null}
    </nav>
  );
}

export default Sidebar;
