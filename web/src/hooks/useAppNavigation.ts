import { useCallback, useEffect, useMemo } from 'react';
import type { BookNarrationFormSection } from '../components/book-narration/BookNarrationForm';
import type { LibraryItem, JobParameterSnapshot } from '../api/dtos';
import type { PlayerContext } from '../pages/PlayerView';
import type { LibraryOpenInput, MediaSelectionRequest } from '../types/player';
import { isLibraryOpenRequest } from '../types/player';
import { useJobsStore } from '../stores/jobsStore';
import { useUIStore } from '../stores/uiStore';
import { buildLibraryBookMetadata } from '../utils/libraryMetadata';
import {
  SelectedView,
  BOOK_NARRATION_SECTION_TO_VIEW,
  JOB_PROGRESS_VIEW,
  JOB_MEDIA_VIEW,
  LIBRARY_VIEW,
  ADMIN_USER_MANAGEMENT_VIEW,
  ADMIN_READING_BEDS_VIEW,
  ADMIN_SETTINGS_VIEW,
  ADMIN_SYSTEM_VIEW,
  SUBTITLES_VIEW,
  isJobCreationView
} from '../constants/appViews';
import type { JobRegistryEntry } from './useAppJobs';

interface UseAppNavigationOptions {
  jobs: Record<string, JobRegistryEntry>;
  canScheduleJobs: boolean;
  isAdmin: boolean;
  pipelineJobTypes: Set<string>;
}

/**
 * Hook for navigation and view-related handlers in the App component.
 * Encapsulates view selection, player context, and library navigation.
 */
export function useAppNavigation(options: UseAppNavigationOptions) {
  const { jobs, canScheduleJobs, isAdmin, pipelineJobTypes } = options;

  const { activeJobId, setActiveJob } = useJobsStore();

  const {
    selectedView,
    setSelectedView,
    playerContext,
    playerSelection,
    setPlayerContext,
    setPlayerSelection,
    libraryFocusRequest,
    setLibraryFocusRequest,
    isSidebarOpen,
    setSidebarOpen,
    isImmersiveMode,
    setImmersiveMode,
    isPlayerFullscreen,
    setPlayerFullscreen,
    incrementSubtitleRefreshKey
  } = useUIStore();

  // Computed job metadata
  const activeJobMetadata = useMemo<Record<string, unknown> | null>(() => {
    if (!activeJobId) {
      return null;
    }
    const jobEntry = jobs[activeJobId];
    if (!jobEntry || !pipelineJobTypes.has(jobEntry.status.job_type)) {
      return null;
    }
    const rawResult = jobEntry.status.result;
    const metadata =
      rawResult && typeof rawResult === 'object' && ('media_metadata' in rawResult || 'book_metadata' in rawResult)
        ? (rawResult as Record<string, unknown>).media_metadata ?? (rawResult as Record<string, unknown>).book_metadata
        : null;
    return metadata && typeof metadata === 'object' ? (metadata as Record<string, unknown>) : null;
  }, [activeJobId, jobs, pipelineJobTypes]);

  const playerJobMetadata = useMemo<Record<string, unknown> | null>(() => {
    if (playerContext?.type !== 'job') {
      return null;
    }
    if (playerContext.jobId === activeJobId) {
      return activeJobMetadata;
    }
    const entry = jobs[playerContext.jobId];
    if (!entry || !pipelineJobTypes.has(entry.status.job_type)) {
      return null;
    }
    const rawResult = entry.status.result;
    const metadata =
      rawResult && typeof rawResult === 'object' && ('media_metadata' in rawResult || 'book_metadata' in rawResult)
        ? (rawResult as Record<string, unknown>).media_metadata ?? (rawResult as Record<string, unknown>).book_metadata
        : null;
    return metadata && typeof metadata === 'object' ? (metadata as Record<string, unknown>) : null;
  }, [activeJobId, activeJobMetadata, jobs, pipelineJobTypes, playerContext]);

  // Handlers
  const handleVideoPlaybackStateChange = useCallback(
    (_isPlaying: boolean) => {
      if (!isPlayerFullscreen) {
        setImmersiveMode(false);
      }
    },
    [isPlayerFullscreen, setImmersiveMode]
  );

  const handleSidebarToggle = useCallback(() => {
    if (isPlayerFullscreen) {
      return;
    }
    setSidebarOpen(!isSidebarOpen);
  }, [isPlayerFullscreen, isSidebarOpen, setSidebarOpen]);

  const handlePlayerFullscreenChange = useCallback(
    (isFullscreen: boolean) => {
      setPlayerFullscreen(isFullscreen);
      setImmersiveMode(isFullscreen);
    },
    [setImmersiveMode, setPlayerFullscreen]
  );

  const handleOpenPlayerForJob = useCallback(
    (jobId?: string, options?: { autoPlay?: boolean }) => {
      const resolvedJobId = jobId ?? activeJobId;
      if (!resolvedJobId) {
        return;
      }
      if (resolvedJobId !== activeJobId) {
        setActiveJob(resolvedJobId);
      }
      const entry = jobs[resolvedJobId];
      const jobType = entry?.status?.job_type ?? null;
      setPlayerContext({ type: 'job', jobId: resolvedJobId, jobType });
      if (options?.autoPlay && jobType !== 'youtube_dub') {
        setPlayerSelection({
          baseId: null,
          preferredType: 'audio',
          autoPlay: true,
          token: Date.now()
        });
      } else {
        setPlayerSelection(null);
      }
      setSelectedView(JOB_MEDIA_VIEW);
      setImmersiveMode(false);
    },
    [activeJobId, jobs, setActiveJob, setImmersiveMode, setPlayerContext, setPlayerSelection, setSelectedView]
  );

  const handlePlayLibraryItem = useCallback(
    (entry: LibraryOpenInput) => {
      let jobId: string | null = null;
      let itemType: 'book' | 'video' | 'narrated_subtitle' | null = null;
      let metadata: Record<string, unknown> | null = null;
      let libraryItem: LibraryItem | null = null;
      let selection: MediaSelectionRequest | null = null;

      if (typeof entry === 'string') {
        jobId = entry;
      } else if (isLibraryOpenRequest(entry)) {
        jobId = entry.jobId;
        selection = entry.selection ?? null;
        if (entry.item) {
          libraryItem = entry.item;
          metadata = buildLibraryBookMetadata(entry.item);
          itemType = entry.item.itemType ?? null;
        }
      } else {
        const resolvedItem = entry as LibraryItem;
        libraryItem = resolvedItem;
        jobId = resolvedItem.jobId;
        itemType = resolvedItem.itemType ?? null;
        metadata = buildLibraryBookMetadata(resolvedItem);
      }

      if (!jobId) {
        return;
      }

      setPlayerContext({
        type: 'library',
        jobId,
        itemType,
        mediaMetadata: metadata,
        item: libraryItem
      });
      setPlayerSelection(
        selection
          ? {
              baseId: selection.baseId,
              preferredType: selection.preferredType ?? null,
              offsetRatio: selection.offsetRatio ?? null,
              approximateTime: selection.approximateTime ?? null,
              autoPlay: selection.autoPlay ?? undefined,
              token: selection.token ?? Date.now()
            }
          : null
      );
      setActiveJob(null);
      setSelectedView(JOB_MEDIA_VIEW);
      setImmersiveMode(false);
    },
    [setActiveJob, setImmersiveMode, setPlayerContext, setPlayerSelection, setSelectedView]
  );

  const handleBackToLibraryFromPlayer = useCallback(
    (payload: { jobId: string; itemType: 'book' | 'video' | 'narrated_subtitle' | null }) => {
      const jobId = payload.jobId;
      if (!jobId) {
        return;
      }
      const itemType = payload.itemType ?? 'book';
      setLibraryFocusRequest({ jobId, itemType, token: Date.now() });
      setSelectedView(LIBRARY_VIEW);
      setImmersiveMode(false);
    },
    [setImmersiveMode, setLibraryFocusRequest, setSelectedView]
  );

  const handleConsumeLibraryFocusRequest = useCallback(() => {
    setLibraryFocusRequest(null);
  }, [setLibraryFocusRequest]);

  const handleSelectSidebarJob = useCallback(
    (jobId: string) => {
      setActiveJob(jobId);
      setSelectedView(JOB_PROGRESS_VIEW);
    },
    [setActiveJob, setSelectedView]
  );

  const handleImmersiveSectionChange = useCallback(
    (section: BookNarrationFormSection) => {
      const nextView = BOOK_NARRATION_SECTION_TO_VIEW[section];
      setSelectedView(nextView);
    },
    [setSelectedView]
  );

  const handleSidebarSelectView = useCallback(
    (view: SelectedView) => {
      if (!canScheduleJobs && isJobCreationView(view)) {
        window.alert('You need editor access to submit jobs.');
        return;
      }
      if (!isAdmin && (view === ADMIN_USER_MANAGEMENT_VIEW || view === ADMIN_READING_BEDS_VIEW || view === ADMIN_SETTINGS_VIEW || view === ADMIN_SYSTEM_VIEW)) {
        window.alert('Administrator access required.');
        return;
      }
      if (view === SUBTITLES_VIEW) {
        incrementSubtitleRefreshKey();
      }
      setSelectedView(view);
    },
    [canScheduleJobs, isAdmin, setSelectedView, incrementSubtitleRefreshKey]
  );

  const handleSubtitleJobCreated = useCallback(
    (jobId: string) => {
      setActiveJob(jobId);
      void useJobsStore.getState().refreshJobs();
    },
    [setActiveJob]
  );

  const handleSubtitleJobSelected = useCallback(
    (jobId: string) => {
      setActiveJob(jobId);
      setSelectedView(JOB_PROGRESS_VIEW);
    },
    [setActiveJob, setSelectedView]
  );

  const handleYoutubeDubJobCreated = useCallback(
    (jobId: string) => {
      setActiveJob(jobId);
      void useJobsStore.getState().refreshJobs();
    },
    [setActiveJob]
  );

  const handleYoutubeDubJobSelected = useCallback(
    (jobId: string) => {
      setActiveJob(jobId);
      setSelectedView(JOB_PROGRESS_VIEW);
    },
    [setActiveJob, setSelectedView]
  );

  const handleOpenYoutubeDubMedia = useCallback(
    (jobId: string) => {
      setActiveJob(jobId);
      const entry = jobs[jobId];
      const jobType = entry?.status?.job_type ?? 'youtube_dub';
      setPlayerContext({ type: 'job', jobId, jobType });
      setPlayerSelection(null);
      setSelectedView(JOB_MEDIA_VIEW);
      setImmersiveMode(false);
    },
    [jobs, setActiveJob, setImmersiveMode, setPlayerContext, setPlayerSelection, setSelectedView]
  );

  return {
    // State
    selectedView,
    playerContext,
    playerSelection,
    libraryFocusRequest,
    isSidebarOpen,
    isImmersiveMode,
    isPlayerFullscreen,
    activeJobMetadata,
    playerJobMetadata,

    // Actions
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
  };
}
