import { useEffect, useRef } from 'react';
import Sidebar from './components/Sidebar';
import MyLinguistAssistant from './components/MyLinguistAssistant';
import MyPainterAssistant from './components/MyPainterAssistant';
import { AuthScreen, AccountPanel, MainContent } from './components/app';
import { useAppAuth } from './hooks/useAppAuth';
import { useAppJobs } from './hooks/useAppJobs';
import { useAppNavigation } from './hooks/useAppNavigation';
import { useJobsStore } from './stores/jobsStore';
import { useUIStore } from './stores/uiStore';
import { fetchPipelineStatus } from './api/client';
import { normalizeRole } from './utils/accessControl';
import {
  APP_BRANCH,
  JOB_PROGRESS_VIEW,
  JOB_MEDIA_VIEW,
  LIBRARY_VIEW,
  CREATE_BOOK_VIEW,
  SUBTITLES_VIEW,
  YOUTUBE_SUBTITLES_VIEW,
  YOUTUBE_DUB_VIEW,
  ADMIN_USER_MANAGEMENT_VIEW,
  ADMIN_READING_BEDS_VIEW,
  ADMIN_SETTINGS_VIEW,
  ADMIN_SYSTEM_VIEW,
  isJobCreationView
} from './constants/appViews';

// Re-export types for backward compatibility
export type { PipelineMenuView, SelectedView } from './constants/appViews';

export function App() {
  // Auth state and handlers
  const auth = useAppAuth();
  const {
    session,
    sessionUser,
    sessionUsername,
    isAuthenticated,
    isAuthLoading,
    logoutReason,
    authError,
    isLoggingIn,
    showChangePassword,
    passwordError,
    passwordMessage,
    isUpdatingPassword,
    isAccountExpanded,
    handleLogin,
    handleOAuthLogin,
    handleLogout,
    handlePasswordChange,
    toggleChangePassword,
    handlePasswordCancel,
    setAccountExpanded,
    setAuthError,
    isRegistering,
    registrationError,
    registrationSuccess,
    handleRegister
  } = auth;

  // Derived auth state
  const normalizedRole = normalizeRole(sessionUser?.role ?? null);
  const isAdmin = normalizedRole === 'admin';
  const canScheduleJobs = normalizedRole === 'admin' || normalizedRole === 'editor';

  // Jobs state and handlers
  const jobsHook = useAppJobs({
    sessionUsername,
    normalizedRole,
    canScheduleJobs,
    session
  });
  const {
    jobs,
    sidebarJobs,
    subtitleJobStates,
    youtubeDubJobStates,
    selectedJob,
    recentPipelineJobs,
    activeJobId,
    isSubmitting,
    submitError,
    pipelineJobTypes,
    setActiveJob,
    handleProgressEvent,
    refreshJobsIfAuthenticated,
    handleSubmit,
    handleReloadJob,
    handleUpdateJobAccess,
    handlePauseJob,
    handleResumeJob,
    handleCancelJob,
    handleDeleteJob,
    handleCopyJob,
    handleRestartJob,
    handleMoveJobToLibrary
  } = jobsHook;

  // Navigation state and handlers
  const navigation = useAppNavigation({
    jobs,
    canScheduleJobs,
    isAdmin,
    pipelineJobTypes
  });
  const {
    selectedView,
    playerContext,
    playerSelection,
    libraryFocusRequest,
    isSidebarOpen,
    isImmersiveMode,
    activeJobMetadata,
    playerJobMetadata,
    setSelectedView,
    setPlayerContext,
    setPlayerSelection,
    setImmersiveMode,
    handleVideoPlaybackStateChange,
    handleSidebarToggle,
    handlePlayerFullscreenChange,
    handleOpenPlayerForJob,
    handlePlayLibraryItem,
    handleBackToLibraryFromPlayer,
    handleConsumeLibraryFocusRequest,
    handleSelectSidebarJob,
    handleImmersiveSectionChange,
    handleSidebarSelectView,
    handleSubtitleJobCreated,
    handleSubtitleJobSelected,
    handleYoutubeDubJobCreated,
    handleYoutubeDubJobSelected,
    handleOpenYoutubeDubMedia
  } = navigation;

  // UI store for form prefills
  const {
    pendingInputFile,
    copiedJobParameters,
    subtitlePrefillParameters,
    youtubeDubPrefillParameters,
    subtitleRefreshKey
  } = useUIStore();

  // Enforce role-based view access
  useEffect(() => {
    if (!sessionUser) {
      return;
    }
    if (!canScheduleJobs && isJobCreationView(selectedView)) {
      setSelectedView(LIBRARY_VIEW);
    }
    if (
      !isAdmin &&
      (selectedView === ADMIN_USER_MANAGEMENT_VIEW || selectedView === ADMIN_READING_BEDS_VIEW)
    ) {
      setSelectedView(LIBRARY_VIEW);
    }
  }, [canScheduleJobs, isAdmin, selectedView, sessionUser, setSelectedView]);

  // Clear jobs on logout, refresh on login
  useEffect(() => {
    if (!session) {
      useJobsStore.getState().setJobs([]);
      setActiveJob(null);
      setPlayerContext(null);
      setPlayerSelection(null);
      setSelectedView('pipeline:source');
      return;
    }

    refreshJobsIfAuthenticated();
    const interval = window.setInterval(() => {
      void refreshJobsIfAuthenticated();
    }, 5000);
    return () => {
      window.clearInterval(interval);
    };
  }, [refreshJobsIfAuthenticated, session, setActiveJob, setPlayerContext, setPlayerSelection, setSelectedView]);

  // Validate view when job/player state changes
  useEffect(() => {
    if (typeof selectedView === 'string' && selectedView.startsWith('pipeline:')) {
      return;
    }
    if (selectedView === ADMIN_USER_MANAGEMENT_VIEW || selectedView === ADMIN_READING_BEDS_VIEW) {
      return;
    }
    if (selectedView === JOB_PROGRESS_VIEW) {
      if (!activeJobId || !jobs[activeJobId]) {
        setActiveJob(null);
        setSelectedView('pipeline:source');
      }
      return;
    }
    if (selectedView === JOB_MEDIA_VIEW) {
      if (!playerContext) {
        setSelectedView('pipeline:source');
        return;
      }
      if (playerContext.type === 'job' && !jobs[playerContext.jobId]) {
        setPlayerContext(null);
        setPlayerSelection(null);
        setSelectedView('pipeline:source');
      }
    }
  }, [activeJobId, jobs, playerContext, selectedView, setActiveJob, setPlayerContext, setPlayerSelection, setSelectedView]);

  // Sync player context with active job in media view
  useEffect(() => {
    if (selectedView !== JOB_MEDIA_VIEW) {
      return;
    }
    if (playerContext?.type !== 'job') {
      return;
    }
    if (activeJobId && playerContext.jobId !== activeJobId) {
      const entry = jobs[activeJobId];
      const jobType = entry?.status?.job_type ?? null;
      setPlayerContext({ type: 'job', jobId: activeJobId, jobType });
      setPlayerSelection(null);
    }
  }, [activeJobId, jobs, playerContext, selectedView, setPlayerContext, setPlayerSelection]);

  // Exit immersive mode when leaving media view
  useEffect(() => {
    if (selectedView !== JOB_MEDIA_VIEW) {
      setImmersiveMode(false);
    }
  }, [selectedView, setImmersiveMode]);

  // Clear auth error on successful login
  useEffect(() => {
    if (session) {
      setAuthError(null);
    }
  }, [session, setAuthError]);

  // Fetch job metadata when viewing job details
  const lastFetchedJobRef = useRef<string | null>(null);
  const lastFetchedAtRef = useRef<number>(0);

  useEffect(() => {
    if (!activeJobId) {
      return;
    }
    if (selectedView !== JOB_MEDIA_VIEW && selectedView !== JOB_PROGRESS_VIEW) {
      return;
    }

    const metadataEmpty = !activeJobMetadata || Object.keys(activeJobMetadata).length === 0;
    const jobChanged = lastFetchedJobRef.current !== activeJobId;
    const now = Date.now();
    const elapsed = now - lastFetchedAtRef.current;
    if (!jobChanged && (!metadataEmpty || elapsed < 5000)) {
      return;
    }

    let cancelled = false;

    const fetchSelectedJobStatus = async () => {
      try {
        const status = await fetchPipelineStatus(activeJobId);
        if (cancelled) {
          return;
        }
        const current = useJobsStore.getState().getJob(activeJobId);
        if (current) {
          useJobsStore.getState().updateJob(activeJobId, {
            status,
            latestEvent: status.latest_event ?? current.latestEvent
          });
        }
      } catch (error) {
        if (!cancelled) {
          console.warn('Unable to refresh job metadata for job detail view', activeJobId, error);
        }
      } finally {
        if (!cancelled) {
          lastFetchedJobRef.current = activeJobId;
          lastFetchedAtRef.current = Date.now();
        }
      }
    };

    void fetchSelectedJobStatus();

    return () => {
      cancelled = true;
    };
  }, [activeJobId, selectedView, activeJobMetadata]);

  // Exit immersive mode when no job is selected
  useEffect(() => {
    if (!selectedJob) {
      setImmersiveMode(false);
    }
  }, [selectedJob, setImmersiveMode]);

  // Render loading state
  if (isAuthLoading) {
    return (
      <AuthScreen
        isLoading
        isSubmitting={false}
        error={null}
        onSubmit={handleLogin}
        onOAuthSubmit={handleOAuthLogin}
        onRegister={handleRegister}
      />
    );
  }

  // Render login screen
  if (!isAuthenticated) {
    return (
      <AuthScreen
        isSubmitting={isLoggingIn}
        error={authError}
        notice={logoutReason}
        onSubmit={handleLogin}
        onOAuthSubmit={handleOAuthLogin}
        onRegister={handleRegister}
        isRegistering={isRegistering}
        registrationError={registrationError}
        registrationSuccess={registrationSuccess}
      />
    );
  }

  // Dashboard layout classes
  const dashboardClassNames = ['dashboard'];
  if (!isSidebarOpen) {
    dashboardClassNames.push('dashboard--collapsed');
  }
  if (isImmersiveMode) {
    dashboardClassNames.push('dashboard--immersive');
  }

  return (
    <div className={dashboardClassNames.join(' ')}>
      <aside
        id="dashboard-sidebar"
        className={`dashboard__sidebar ${isSidebarOpen ? '' : 'dashboard__sidebar--collapsed'}`}
      >
        <div className="sidebar__header">
          <div className="sidebar__brand">
            <button
              type="button"
              className="sidebar__logo-mark"
              onClick={handleSidebarToggle}
              aria-expanded={isSidebarOpen}
              aria-controls="dashboard-sidebar"
              aria-label={isSidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
              title={isSidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
            >
              <span aria-hidden="true">🌐</span>
            </button>
            <span className="sidebar__title" aria-label="Language Tools">
              Language Tools
            </span>
            <span className="sidebar__version app-version" aria-label={`Version ${APP_BRANCH}`}>
              v{APP_BRANCH}
            </span>
          </div>
        </div>
        <Sidebar
          selectedView={selectedView}
          onSelectView={handleSidebarSelectView}
          sidebarJobs={sidebarJobs}
          activeJobId={activeJobId}
          onSelectJob={handleSelectSidebarJob}
          onOpenPlayer={handleOpenPlayerForJob}
          isAdmin={isAdmin}
          canScheduleJobs={canScheduleJobs}
          createBookView={CREATE_BOOK_VIEW}
          libraryView={LIBRARY_VIEW}
          subtitlesView={SUBTITLES_VIEW}
          youtubeSubtitlesView={YOUTUBE_SUBTITLES_VIEW}
          youtubeDubView={YOUTUBE_DUB_VIEW}
          jobMediaView={JOB_MEDIA_VIEW}
          adminUserManagementView={ADMIN_USER_MANAGEMENT_VIEW}
          adminReadingBedsView={ADMIN_READING_BEDS_VIEW}
          adminSettingsView={ADMIN_SETTINGS_VIEW}
          adminSystemView={ADMIN_SYSTEM_VIEW}
        />
        <AccountPanel
          sessionUser={sessionUser}
          isExpanded={isAccountExpanded}
          showChangePassword={showChangePassword}
          passwordError={passwordError}
          passwordMessage={passwordMessage}
          isUpdatingPassword={isUpdatingPassword}
          onToggleExpand={() => setAccountExpanded(!isAccountExpanded)}
          onToggleChangePassword={toggleChangePassword}
          onPasswordChange={handlePasswordChange}
          onPasswordCancel={handlePasswordCancel}
          onLogout={() => void handleLogout()}
        />
      </aside>
      <div className="dashboard__content">
        <MainContent
          selectedView={selectedView}
          selectedJob={selectedJob}
          canScheduleJobs={canScheduleJobs}
          sessionUsername={sessionUsername ?? ''}
          libraryFocusRequest={libraryFocusRequest}
          onPlayLibraryItem={handlePlayLibraryItem}
          onConsumeLibraryFocusRequest={handleConsumeLibraryFocusRequest}
          recentPipelineJobs={recentPipelineJobs}
          pendingInputFile={pendingInputFile}
          copiedJobParameters={copiedJobParameters}
          isSubmitting={isSubmitting}
          submitError={submitError}
          onSubmit={handleSubmit}
          onSectionChange={handleImmersiveSectionChange}
          onCreateBookJobSubmitted={(jobId) => {
            if (jobId) {
              setActiveJob(jobId);
              setSelectedView(JOB_PROGRESS_VIEW);
              setImmersiveMode(false);
            }
          }}
          subtitleJobStates={subtitleJobStates}
          subtitlePrefillParameters={subtitlePrefillParameters}
          subtitleRefreshKey={subtitleRefreshKey}
          onSubtitleJobCreated={handleSubtitleJobCreated}
          onSubtitleJobSelected={handleSubtitleJobSelected}
          youtubeDubJobStates={youtubeDubJobStates}
          youtubeDubPrefillParameters={youtubeDubPrefillParameters}
          onYoutubeDubJobCreated={handleYoutubeDubJobCreated}
          onYoutubeDubJobSelected={handleYoutubeDubJobSelected}
          onOpenYoutubeDubMedia={handleOpenYoutubeDubMedia}
          onProgressEvent={handleProgressEvent}
          onPauseJob={handlePauseJob}
          onResumeJob={handleResumeJob}
          onCancelJob={handleCancelJob}
          onDeleteJob={handleDeleteJob}
          onRestartJob={handleRestartJob}
          onReloadJob={handleReloadJob}
          onCopyJob={canScheduleJobs ? handleCopyJob : undefined}
          onMoveJobToLibrary={handleMoveJobToLibrary}
          onUpdateJobAccess={handleUpdateJobAccess}
          playerContext={playerContext}
          playerJobMetadata={playerJobMetadata}
          playerSelection={playerSelection}
          onVideoPlaybackStateChange={handleVideoPlaybackStateChange}
          onPlayerFullscreenChange={handlePlayerFullscreenChange}
          onBackToLibraryFromPlayer={handleBackToLibraryFromPlayer}
        />
      </div>
      <MyLinguistAssistant />
      <MyPainterAssistant />
    </div>
  );
}

export default App;
