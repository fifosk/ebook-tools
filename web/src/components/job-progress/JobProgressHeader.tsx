import type { StatusGlyph } from '../../utils/status';

type JobProgressHeaderProps = {
  jobId: string;
  jobLabel: string | null;
  jobType: string;
  statusValue: string;
  statusGlyph: StatusGlyph;
  canPause: boolean;
  canResume: boolean;
  canCancel: boolean;
  canRestart: boolean;
  canCopy: boolean;
  shouldRenderLibraryButton: boolean;
  canMoveToLibrary: boolean;
  canDelete: boolean;
  isMutating: boolean;
  libraryButtonTitle?: string;
  onPause: () => void;
  onResume: () => void;
  onCancel: () => void;
  onRestart: () => void;
  onDelete: () => void;
  onCopy?: () => void;
  onMoveToLibrary?: () => void;
};

export function JobProgressHeader({
  jobId,
  jobLabel,
  jobType,
  statusValue,
  statusGlyph,
  canPause,
  canResume,
  canCancel,
  canRestart,
  canCopy,
  shouldRenderLibraryButton,
  canMoveToLibrary,
  canDelete,
  isMutating,
  libraryButtonTitle,
  onPause,
  onResume,
  onCancel,
  onRestart,
  onDelete,
  onCopy,
  onMoveToLibrary,
}: JobProgressHeaderProps) {
  return (
    <div className="job-card__header">
      <div className="job-card__header-title">
        <h3>
          Job {jobId}
          {jobLabel ? (
            <>
              {' '}
              &mdash; {jobLabel}
            </>
          ) : null}
        </h3>
        <span className="job-card__badge">{jobType}</span>
      </div>
      <div className="job-card__header-actions">
        <span
          className="job-status"
          data-state={statusValue}
          title={statusGlyph.label}
          aria-label={statusGlyph.label}
        >
          {statusGlyph.icon}
        </span>
        <div className="job-actions" aria-label={`Actions for job ${jobId}`} aria-busy={isMutating}>
          {canPause ? (
            <button type="button" className="link-button" onClick={onPause} disabled={isMutating}>
              Pause
            </button>
          ) : null}
          {canResume ? (
            <button type="button" className="link-button" onClick={onResume} disabled={isMutating}>
              Resume
            </button>
          ) : null}
          {canCancel ? (
            <button type="button" className="link-button" onClick={onCancel} disabled={isMutating}>
              Cancel
            </button>
          ) : null}
          {canRestart ? (
            <button type="button" className="link-button" onClick={onRestart} disabled={isMutating}>
              Restart
            </button>
          ) : null}
          {canCopy ? (
            <button type="button" className="link-button" onClick={() => onCopy?.()} disabled={isMutating}>
              Copy
            </button>
          ) : null}
          {shouldRenderLibraryButton ? (
            <button
              type="button"
              className="link-button"
              onClick={() => onMoveToLibrary?.()}
              disabled={isMutating || !canMoveToLibrary}
              title={libraryButtonTitle}
            >
              Move to library
            </button>
          ) : null}
          {canDelete ? (
            <button type="button" className="link-button" onClick={onDelete} disabled={isMutating}>
              Delete
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
