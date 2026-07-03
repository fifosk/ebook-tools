import { describe, expect, it } from 'vitest';
import {
  resolveJobProgressActionState,
  resolveJobProgressKindFlags
} from '../job-progress/jobProgressActions';

describe('jobProgressActions', () => {
  it('resolves job kind flags used by Web job action and metadata chrome', () => {
    expect(resolveJobProgressKindFlags('pipeline', false)).toMatchObject({
      isBookJob: true,
      isPipelineLikeJob: true,
      isSubtitleJob: false,
      isVideoDubJob: false,
      supportsTvMetadata: false,
      supportsYoutubeMetadata: false,
      isLibraryMovableJob: true,
    });
    expect(resolveJobProgressKindFlags('youtube_dub', false)).toMatchObject({
      isBookJob: false,
      isVideoDubJob: true,
      supportsTvMetadata: true,
      supportsYoutubeMetadata: true,
      isLibraryMovableJob: true,
    });
    expect(resolveJobProgressKindFlags('subtitle', true)).toMatchObject({
      isSubtitleJob: true,
      supportsTvMetadata: true,
      supportsYoutubeMetadata: false,
      isLibraryMovableJob: true,
    });
  });

  it('keeps running book controls manageable and library move disabled until media is ready', () => {
    expect(
      resolveJobProgressActionState({
        statusValue: 'running',
        canManage: true,
        isTerminal: false,
        isBookJob: true,
        isLibraryMovableJob: true,
        mediaCompleted: false,
        hasCopyAction: true,
        hasMoveToLibraryAction: true,
      })
    ).toEqual({
      canPause: true,
      canResume: false,
      canCancel: true,
      canDelete: false,
      canRestart: false,
      canCopy: true,
      isLibraryCandidate: false,
      shouldRenderLibraryButton: true,
      canMoveToLibrary: false,
      libraryButtonTitle: 'Media generation is still finalizing.',
      showLibraryReadyNotice: false,
    });
  });

  it('allows paused completed-media jobs to move to Library and resume', () => {
    expect(
      resolveJobProgressActionState({
        statusValue: 'paused',
        canManage: true,
        isTerminal: false,
        isBookJob: true,
        isLibraryMovableJob: true,
        mediaCompleted: true,
        hasCopyAction: false,
        hasMoveToLibraryAction: true,
      })
    ).toMatchObject({
      canPause: false,
      canResume: true,
      canCancel: true,
      canDelete: false,
      canRestart: true,
      canMoveToLibrary: true,
      libraryButtonTitle: undefined,
      showLibraryReadyNotice: true,
    });
  });

  it('hides mutation actions for read-only sessions', () => {
    expect(
      resolveJobProgressActionState({
        statusValue: 'completed',
        canManage: false,
        isTerminal: true,
        isBookJob: true,
        isLibraryMovableJob: true,
        mediaCompleted: true,
        hasCopyAction: true,
        hasMoveToLibraryAction: true,
      })
    ).toMatchObject({
      canPause: false,
      canResume: false,
      canCancel: false,
      canDelete: false,
      canRestart: false,
      canCopy: true,
      shouldRenderLibraryButton: false,
      canMoveToLibrary: false,
      showLibraryReadyNotice: false,
    });
  });
});
