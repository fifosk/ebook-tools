import type { JobState } from '../JobList';
import EmojiIcon from '../EmojiIcon';
import JobStatusBadge from '../JobStatusBadge';
import JobTypeGlyphBadge from '../JobTypeGlyphBadge';
import {
  resolveImageWaitStatus,
  resolveJobGlyph,
  resolveSidebarLabel,
  resolveSidebarLanguage,
  resolveSidebarProgress,
  resolveSidebarStage,
  resolveSidebarStatus,
} from './sidebarUtils';

interface SidebarJobRowProps {
  job: JobState;
  activeJobId: string | null;
  onSelectJob: (jobId: string) => void;
  onOpenPlayer: (jobId?: string, options?: { autoPlay?: boolean }) => void;
}

export function SidebarJobRow({ job, activeJobId, onSelectJob, onOpenPlayer }: SidebarJobRowProps) {
  const statusValue = job.status?.status ?? 'pending';
  const imageWait = resolveImageWaitStatus(job);
  const statusLabel = imageWait ?? resolveSidebarStatus(statusValue);
  const isActiveJob = activeJobId === job.jobId;
  const languageMeta = resolveSidebarLanguage(job);
  const nameMeta = resolveSidebarLabel(job);
  const progressPercent = resolveSidebarProgress(job);
  const glyph = resolveJobGlyph(job);
  const stageGlyph = resolveSidebarStage(job);

  return (
    <li className="sidebar__job-row">
      <button
        type="button"
        className={`sidebar__link sidebar__link--job sidebar__job-main ${isActiveJob ? 'is-active' : ''}`}
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
          <JobTypeGlyphBadge glyph={glyph} className="sidebar__job-type" />
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
          <JobStatusBadge
            status={statusValue}
            glyph={{ icon: statusLabel.icon, label: statusLabel.tooltip }}
          />
        </span>
      </button>
      <button
        type="button"
        className="sidebar__job-play"
        onClick={(event) => {
          event.stopPropagation();
          onOpenPlayer(job.jobId, { autoPlay: true });
        }}
        title={`Play ${nameMeta.tooltip}`}
        aria-label={`Play ${nameMeta.label}`}
      >
        <span className="sidebar__job-play-icon" aria-hidden="true">
          ▶
        </span>
      </button>
    </li>
  );
}
