import type { ReactNode } from 'react';
import type { JobState } from '../JobList';
import type { BookNarrationFormSection } from '../book-narration/BookNarrationForm';
import type {
  AccessPolicyUpdatePayload,
  JobParameterSnapshot,
  PipelineRequestPayload,
  PipelineStatusResponse,
  ProgressEventPayload
} from '../../api/dtos';
import type { PlayerContext } from '../../pages/PlayerView';
import type { LibraryOpenInput, MediaSelectionRequest } from '../../types/player';
import type { LibraryFocusRequest } from '../../stores/uiStore';
import { ErrorBoundary } from '../ErrorBoundary';
import JobProgress from '../JobProgress';
import LibraryPage from '../../pages/LibraryPage';
import CreateBookPage from '../../pages/CreateBookPage';
import PlayerView from '../../pages/PlayerView';
import NewImmersiveBookPage from '../../pages/NewImmersiveBookPage';
import SubtitleToolPage from '../../pages/SubtitleToolPage';
import YoutubeVideoPage from '../../pages/YoutubeVideoPage';
import VideoDubbingPage from '../../pages/VideoDubbingPage';
import UserManagementPanel from '../admin/UserManagementPanel';
import ReadingBedsPanel from '../admin/ReadingBedsPanel';
import {
  SelectedView,
  PipelineMenuView,
  BOOK_NARRATION_SECTION_MAP,
  ADMIN_USER_MANAGEMENT_VIEW,
  ADMIN_READING_BEDS_VIEW,
  JOB_PROGRESS_VIEW,
  JOB_MEDIA_VIEW,
  LIBRARY_VIEW,
  CREATE_BOOK_VIEW,
  SUBTITLES_VIEW,
  YOUTUBE_SUBTITLES_VIEW,
  YOUTUBE_DUB_VIEW,
  isPipelineView
} from '../../constants/appViews';

interface MainContentProps {
  selectedView: SelectedView;
  selectedJob: JobState | undefined;
  canScheduleJobs: boolean;
  sessionUsername: string;

  // Library
  libraryFocusRequest: LibraryFocusRequest | null;
  onPlayLibraryItem: (entry: LibraryOpenInput) => void;
  onConsumeLibraryFocusRequest: () => void;

  // Pipeline/Book creation
  recentPipelineJobs: PipelineStatusResponse[];
  pendingInputFile: string | null;
  copiedJobParameters: JobParameterSnapshot | null;
  isSubmitting: boolean;
  submitError: string | null;
  onSubmit: (payload: PipelineRequestPayload) => Promise<void>;
  onSectionChange: (section: BookNarrationFormSection) => void;
  onCreateBookJobSubmitted: (jobId: string) => void;

  // Subtitle tool
  subtitleJobStates: JobState[];
  subtitlePrefillParameters: JobParameterSnapshot | null;
  subtitleRefreshKey: number;
  onSubtitleJobCreated: (jobId: string) => void;
  onSubtitleJobSelected: (jobId: string) => void;

  // YouTube dub
  youtubeDubJobStates: JobState[];
  youtubeDubPrefillParameters: JobParameterSnapshot | null;
  onYoutubeDubJobCreated: (jobId: string) => void;
  onYoutubeDubJobSelected: (jobId: string) => void;
  onOpenYoutubeDubMedia: (jobId: string) => void;

  // Job progress
  onProgressEvent: (jobId: string, event: ProgressEventPayload) => void;
  onPauseJob: (jobId: string) => Promise<void>;
  onResumeJob: (jobId: string) => Promise<void>;
  onCancelJob: (jobId: string) => Promise<void>;
  onDeleteJob: (jobId: string) => Promise<void>;
  onRestartJob: (jobId: string) => Promise<void>;
  onReloadJob: (jobId: string) => Promise<void>;
  onCopyJob?: (jobId: string) => void;
  onMoveJobToLibrary: (jobId: string) => Promise<void>;
  onUpdateJobAccess: (jobId: string, payload: AccessPolicyUpdatePayload) => Promise<void>;

  // Player
  playerContext: PlayerContext | null;
  playerJobMetadata: Record<string, unknown> | null;
  playerSelection: MediaSelectionRequest | null;
  onVideoPlaybackStateChange: (isPlaying: boolean) => void;
  onPlayerFullscreenChange: (isFullscreen: boolean) => void;
  onBackToLibraryFromPlayer: (payload: {
    jobId: string;
    itemType: 'book' | 'video' | 'narrated_subtitle' | null;
  }) => void;
}

/**
 * Main content area of the dashboard.
 * Renders the appropriate view based on selectedView.
 */
export function MainContent({
  selectedView,
  selectedJob,
  canScheduleJobs,
  sessionUsername,
  libraryFocusRequest,
  onPlayLibraryItem,
  onConsumeLibraryFocusRequest,
  recentPipelineJobs,
  pendingInputFile,
  copiedJobParameters,
  isSubmitting,
  submitError,
  onSubmit,
  onSectionChange,
  onCreateBookJobSubmitted,
  subtitleJobStates,
  subtitlePrefillParameters,
  subtitleRefreshKey,
  onSubtitleJobCreated,
  onSubtitleJobSelected,
  youtubeDubJobStates,
  youtubeDubPrefillParameters,
  onYoutubeDubJobCreated,
  onYoutubeDubJobSelected,
  onOpenYoutubeDubMedia,
  onProgressEvent,
  onPauseJob,
  onResumeJob,
  onCancelJob,
  onDeleteJob,
  onRestartJob,
  onReloadJob,
  onCopyJob,
  onMoveJobToLibrary,
  onUpdateJobAccess,
  playerContext,
  playerJobMetadata,
  playerSelection,
  onVideoPlaybackStateChange,
  onPlayerFullscreenChange,
  onBackToLibraryFromPlayer
}: MainContentProps) {
  const isAdminUsersView = selectedView === ADMIN_USER_MANAGEMENT_VIEW;
  const isAdminReadingBedsView = selectedView === ADMIN_READING_BEDS_VIEW;
  const isLibraryView = selectedView === LIBRARY_VIEW;
  const isCreateBookView = selectedView === CREATE_BOOK_VIEW;
  const isSubtitlesView = selectedView === SUBTITLES_VIEW;
  const isYoutubeSubtitlesView = selectedView === YOUTUBE_SUBTITLES_VIEW;
  const isYoutubeDubView = selectedView === YOUTUBE_DUB_VIEW;
  const isAddBookView = isPipelineView(selectedView);

  const activePipelineSection = isAddBookView
    ? BOOK_NARRATION_SECTION_MAP[selectedView as PipelineMenuView]
    : null;

  return (
    <main className="dashboard__main">
      {/* Admin header */}
      {isAdminUsersView ? (
        <header className="dashboard__header">
          <h1>User management</h1>
          <p>Administer dashboard accounts, reset passwords, and control access for operators.</p>
        </header>
      ) : isAdminReadingBedsView ? (
        <header className="dashboard__header">
          <h1>Reading music</h1>
          <p>Manage background music tracks shown in the interactive player.</p>
        </header>
      ) : null}

      {/* Admin views */}
      {isAdminUsersView ? (
        <section>
          <UserManagementPanel currentUser={sessionUsername} />
        </section>
      ) : isAdminReadingBedsView ? (
        <section>
          <ReadingBedsPanel />
        </section>
      ) : isLibraryView ? (
        <LibraryPage
          onPlay={onPlayLibraryItem}
          focusRequest={libraryFocusRequest}
          onConsumeFocusRequest={onConsumeLibraryFocusRequest}
        />
      ) : isCreateBookView && canScheduleJobs ? (
        <section>
          <CreateBookPage onJobSubmitted={onCreateBookJobSubmitted} recentJobs={recentPipelineJobs} />
        </section>
      ) : (
        <>
          {isAddBookView && canScheduleJobs ? (
            <section>
              <NewImmersiveBookPage
                activeSection={activePipelineSection ?? 'source'}
                onSectionChange={onSectionChange}
                onSubmit={onSubmit}
                isSubmitting={isSubmitting}
                prefillInputFile={pendingInputFile}
                prefillParameters={copiedJobParameters}
                submitError={submitError}
                recentJobs={recentPipelineJobs}
              />
            </section>
          ) : null}
          {isSubtitlesView && canScheduleJobs ? (
            <section>
              <SubtitleToolPage
                subtitleJobs={subtitleJobStates}
                onJobCreated={onSubtitleJobCreated}
                onSelectJob={onSubtitleJobSelected}
                onMoveToLibrary={onMoveJobToLibrary}
                prefillParameters={subtitlePrefillParameters}
                refreshSignal={subtitleRefreshKey}
              />
            </section>
          ) : null}
          {isYoutubeSubtitlesView && canScheduleJobs ? (
            <section>
              <YoutubeVideoPage />
            </section>
          ) : null}
          {isYoutubeDubView && canScheduleJobs ? (
            <section>
              <VideoDubbingPage
                jobs={youtubeDubJobStates}
                onJobCreated={onYoutubeDubJobCreated}
                onSelectJob={onYoutubeDubJobSelected}
                onOpenJobMedia={onOpenYoutubeDubMedia}
                prefillParameters={youtubeDubPrefillParameters}
              />
            </section>
          ) : null}
          {selectedView === JOB_PROGRESS_VIEW ? (
            <section className="job-progress-section">
              {selectedJob ? (
                <ErrorBoundary
                  resetKeys={[selectedJob.jobId]}
                  onError={(error, errorInfo) => {
                    console.error('JobProgress error:', error, errorInfo);
                  }}
                >
                  <JobProgress
                    jobId={selectedJob.jobId}
                    status={selectedJob.status}
                    latestEvent={selectedJob.latestEvent}
                    latestTranslationEvent={selectedJob.latestTranslationEvent}
                    latestMediaEvent={selectedJob.latestMediaEvent}
                    latestPlayableEvent={selectedJob.latestPlayableEvent}
                    onEvent={(event) => onProgressEvent(selectedJob.jobId, event)}
                    onPause={() => onPauseJob(selectedJob.jobId)}
                    onResume={() => onResumeJob(selectedJob.jobId)}
                    onCancel={() => onCancelJob(selectedJob.jobId)}
                    onDelete={() => onDeleteJob(selectedJob.jobId)}
                    onRestart={() => onRestartJob(selectedJob.jobId)}
                    onReload={() => onReloadJob(selectedJob.jobId)}
                    onCopy={canScheduleJobs && onCopyJob ? () => onCopyJob(selectedJob.jobId) : undefined}
                    onMoveToLibrary={() => onMoveJobToLibrary(selectedJob.jobId)}
                    onUpdateAccess={(payload) => onUpdateJobAccess(selectedJob.jobId, payload)}
                    isReloading={selectedJob.isReloading}
                    isMutating={selectedJob.isMutating}
                    canManage={selectedJob.canManage}
                  />
                </ErrorBoundary>
              ) : (
                <div className="job-card job-card--placeholder" aria-live="polite">
                  <h3 style={{ marginTop: 0 }}>No job selected</h3>
                  <p>Select an active job to monitor its pipeline progress and live status updates.</p>
                </div>
              )}
            </section>
          ) : null}
          {selectedView === JOB_MEDIA_VIEW ? (
            <div className="job-media-section">
              <PlayerView
                context={playerContext}
                jobBookMetadata={playerJobMetadata}
                onVideoPlaybackStateChange={onVideoPlaybackStateChange}
                onFullscreenChange={onPlayerFullscreenChange}
                onOpenLibraryItem={onPlayLibraryItem}
                onBackToLibrary={onBackToLibraryFromPlayer}
                selectionRequest={playerSelection}
              />
            </div>
          ) : null}
        </>
      )}
    </main>
  );
}

export default MainContent;
