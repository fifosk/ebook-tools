export type JobProgressKindFlags = {
  isBookJob: boolean;
  isPipelineLikeJob: boolean;
  isSubtitleJob: boolean;
  isVideoDubJob: boolean;
  supportsTvMetadata: boolean;
  supportsYoutubeMetadata: boolean;
  isLibraryMovableJob: boolean;
};

export type JobProgressActionState = {
  canPause: boolean;
  canResume: boolean;
  canCancel: boolean;
  canDelete: boolean;
  canRestart: boolean;
  canCopy: boolean;
  isLibraryCandidate: boolean;
  shouldRenderLibraryButton: boolean;
  canMoveToLibrary: boolean;
  libraryButtonTitle?: string;
  showLibraryReadyNotice: boolean;
};

export function resolveJobProgressKindFlags(
  jobType: string,
  isNarratedSubtitleJob: boolean
): JobProgressKindFlags {
  const isBookJob = jobType === 'pipeline' || jobType === 'book';
  const isPipelineLikeJob = isBookJob;
  const isSubtitleJob = jobType === 'subtitle';
  const isVideoDubJob = jobType === 'youtube_dub';
  const supportsTvMetadata = isSubtitleJob || isVideoDubJob;
  const supportsYoutubeMetadata = isVideoDubJob;
  const isLibraryMovableJob = isPipelineLikeJob || isVideoDubJob || isNarratedSubtitleJob;

  return {
    isBookJob,
    isPipelineLikeJob,
    isSubtitleJob,
    isVideoDubJob,
    supportsTvMetadata,
    supportsYoutubeMetadata,
    isLibraryMovableJob,
  };
}

export function resolveJobProgressActionState({
  statusValue,
  canManage,
  isTerminal,
  isBookJob,
  isLibraryMovableJob,
  mediaCompleted,
  hasCopyAction,
  hasMoveToLibraryAction,
}: {
  statusValue: string;
  canManage: boolean;
  isTerminal: boolean;
  isBookJob: boolean;
  isLibraryMovableJob: boolean;
  mediaCompleted: boolean | null | undefined;
  hasCopyAction: boolean;
  hasMoveToLibraryAction: boolean;
}): JobProgressActionState {
  const canPause =
    isBookJob && canManage && !isTerminal && statusValue !== 'paused' && statusValue !== 'pausing';
  const canResume = isBookJob && canManage && statusValue === 'paused';
  const canCancel = canManage && !isTerminal;
  const canDelete = canManage && isTerminal;
  const canRestart =
    isBookJob &&
    canManage &&
    statusValue !== 'running' &&
    statusValue !== 'pending' &&
    statusValue !== 'pausing';
  const isLibraryCandidate =
    isLibraryMovableJob && (statusValue === 'completed' || (statusValue === 'paused' && mediaCompleted === true));
  const shouldRenderLibraryButton = hasMoveToLibraryAction && canManage && isLibraryMovableJob;
  const canMoveToLibrary = shouldRenderLibraryButton && isLibraryCandidate;

  return {
    canPause,
    canResume,
    canCancel,
    canDelete,
    canRestart,
    canCopy: hasCopyAction,
    isLibraryCandidate,
    shouldRenderLibraryButton,
    canMoveToLibrary,
    libraryButtonTitle:
      shouldRenderLibraryButton && !isLibraryCandidate
        ? 'Media generation is still finalizing.'
        : undefined,
    showLibraryReadyNotice: canManage && isLibraryCandidate,
  };
}
