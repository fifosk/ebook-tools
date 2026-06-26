import type { SelectedView } from '../../App';
import type { JobState } from '../JobList';
import EmojiIcon from '../EmojiIcon';
import JobStatusBadge from '../JobStatusBadge';
import JobTypeGlyphBadge from '../JobTypeGlyphBadge';
import {
  resolveImageWaitStatus,
  resolveJobGlyph,
  resolveSidebarLabel,
  resolveSidebarLanguage,
  resolveSidebarStage,
  resolveSidebarStatus,
} from './sidebarUtils';

interface SidebarPlayerButtonProps {
  selectedView: SelectedView;
  jobMediaView: SelectedView;
  activeJob: JobState | null;
  onOpenPlayer: (jobId?: string, options?: { autoPlay?: boolean }) => void;
}

export function SidebarPlayerButton({
  selectedView,
  jobMediaView,
  activeJob,
  onOpenPlayer
}: SidebarPlayerButtonProps) {
  const activeJobLabel = activeJob ? resolveSidebarLabel(activeJob) : null;
  const activeJobGlyph = activeJob ? resolveJobGlyph(activeJob) : null;
  const activeJobLanguage = activeJob ? resolveSidebarLanguage(activeJob) : null;
  const activeJobImageWait = activeJob ? resolveImageWaitStatus(activeJob) : null;
  const activeJobStatus = activeJob
    ? activeJobImageWait
      ? { icon: activeJobImageWait.icon, tooltip: activeJobImageWait.tooltip }
      : resolveSidebarStatus(activeJob.status.status ?? 'pending')
    : null;
  const activeJobStage = activeJob ? resolveSidebarStage(activeJob) : null;

  return (
    <button
      type="button"
      className={`sidebar__link sidebar__link--player ${selectedView === jobMediaView ? 'is-active' : ''}`}
      onClick={() => onOpenPlayer()}
      disabled={!activeJob}
    >
      <span className="sidebar__player-label">
        {activeJob ? (
          <span className="sidebar__player-label-text" title={activeJobLabel?.tooltip ?? `Job ${activeJob.jobId}`}>
            {activeJobGlyph ? (
              <JobTypeGlyphBadge glyph={activeJobGlyph} className="sidebar__job-type" />
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
            <JobStatusBadge
              status={activeJob.status.status ?? 'pending'}
              glyph={{ icon: activeJobStatus.icon, label: activeJobStatus.tooltip }}
            />
          ) : null}
        </span>
      ) : (
        <span className="sidebar__player-meta">Select a job</span>
      )}
    </button>
  );
}
