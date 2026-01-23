import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { JobParameterSnapshot } from '../api/dtos';
import type { MediaSelectionRequest } from '../types/player';
import type { PlayerContext } from '../pages/PlayerView';

export type PipelineMenuView =
  | 'pipeline:source'
  | 'pipeline:metadata'
  | 'pipeline:language'
  | 'pipeline:output'
  | 'pipeline:images'
  | 'pipeline:performance'
  | 'pipeline:submit';

export type SelectedView =
  | PipelineMenuView
  | 'admin:users'
  | 'admin:reading-beds'
  | 'job:progress'
  | 'job:media'
  | 'library:list'
  | 'books:create'
  | 'subtitles:home'
  | 'subtitles:youtube'
  | 'subtitles:youtube-dub';

export interface LibraryFocusRequest {
  jobId: string;
  itemType: 'book' | 'video' | 'narrated_subtitle';
  token: number;
}

/**
 * UI Store - Manages all UI-related state with Zustand + localStorage persistence
 *
 * Features:
 * - Pure UI state (no business logic)
 * - Persists user preferences (selectedView, isSidebarOpen, isAccountExpanded)
 * - Transient state for forms and auth (not persisted)
 * - Simple setters for all state
 */
interface UIState {
  // View navigation
  /** Currently selected view/page in the application */
  selectedView: SelectedView;
  /** Navigate to a different view */
  setSelectedView: (view: SelectedView) => void;

  // Sidebar state
  /** Whether the sidebar is open or collapsed */
  isSidebarOpen: boolean;
  /** Toggle sidebar open/closed */
  toggleSidebar: () => void;
  /** Set sidebar state directly */
  setSidebarOpen: (open: boolean) => void;

  // Player state
  /** Context for the media player (job or library item) */
  playerContext: PlayerContext | null;
  /** Current media selection request */
  playerSelection: MediaSelectionRequest | null;
  /** Whether player is in immersive (fullscreen-like) mode */
  isImmersiveMode: boolean;
  /** Whether player is in actual fullscreen */
  isPlayerFullscreen: boolean;
  setPlayerContext: (context: PlayerContext | null) => void;
  setPlayerSelection: (selection: MediaSelectionRequest | null) => void;
  setImmersiveMode: (immersive: boolean) => void;
  setPlayerFullscreen: (fullscreen: boolean) => void;

  // Library focus
  libraryFocusRequest: LibraryFocusRequest | null;
  setLibraryFocusRequest: (request: LibraryFocusRequest | null) => void;

  // Form prefill state (transient, not persisted)
  pendingInputFile: string | null;
  copiedJobParameters: JobParameterSnapshot | null;
  subtitlePrefillParameters: JobParameterSnapshot | null;
  youtubeDubPrefillParameters: JobParameterSnapshot | null;
  setPendingInputFile: (file: string | null) => void;
  setCopiedJobParameters: (params: JobParameterSnapshot | null) => void;
  setSubtitlePrefillParameters: (params: JobParameterSnapshot | null) => void;
  setYoutubeDubPrefillParameters: (params: JobParameterSnapshot | null) => void;

  // Subtitle page refresh key
  subtitleRefreshKey: number;
  incrementSubtitleRefreshKey: () => void;

  // Account UI
  isAccountExpanded: boolean;
  setAccountExpanded: (expanded: boolean) => void;

  // Auth UI state (transient)
  authError: string | null;
  isLoggingIn: boolean;
  showChangePassword: boolean;
  passwordError: string | null;
  passwordMessage: string | null;
  isUpdatingPassword: boolean;
  setAuthError: (error: string | null) => void;
  setIsLoggingIn: (loading: boolean) => void;
  setShowChangePassword: (show: boolean) => void;
  setPasswordError: (error: string | null) => void;
  setPasswordMessage: (message: string | null) => void;
  setIsUpdatingPassword: (updating: boolean) => void;

  // Form submission state (transient)
  isSubmitting: boolean;
  submitError: string | null;
  setIsSubmitting: (submitting: boolean) => void;
  setSubmitError: (error: string | null) => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      // Initial state
      selectedView: 'pipeline:source',
      isSidebarOpen: true,
      playerContext: null,
      playerSelection: null,
      isImmersiveMode: false,
      isPlayerFullscreen: false,
      libraryFocusRequest: null,
      pendingInputFile: null,
      copiedJobParameters: null,
      subtitlePrefillParameters: null,
      youtubeDubPrefillParameters: null,
      subtitleRefreshKey: 0,
      isAccountExpanded: false,
      authError: null,
      isLoggingIn: false,
      showChangePassword: false,
      passwordError: null,
      passwordMessage: null,
      isUpdatingPassword: false,
      isSubmitting: false,
      submitError: null,

      // View navigation
      setSelectedView: (selectedView: SelectedView) => set({ selectedView }),

      // Sidebar
      toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
      setSidebarOpen: (isSidebarOpen: boolean) => set({ isSidebarOpen }),

      // Player
      setPlayerContext: (playerContext: PlayerContext | null) => set({ playerContext }),
      setPlayerSelection: (playerSelection: MediaSelectionRequest | null) =>
        set({ playerSelection }),
      setImmersiveMode: (isImmersiveMode: boolean) => set({ isImmersiveMode }),
      setPlayerFullscreen: (isPlayerFullscreen: boolean) => set({ isPlayerFullscreen }),

      // Library focus
      setLibraryFocusRequest: (libraryFocusRequest: LibraryFocusRequest | null) =>
        set({ libraryFocusRequest }),

      // Form prefills
      setPendingInputFile: (pendingInputFile: string | null) => set({ pendingInputFile }),
      setCopiedJobParameters: (copiedJobParameters: JobParameterSnapshot | null) =>
        set({ copiedJobParameters }),
      setSubtitlePrefillParameters: (subtitlePrefillParameters: JobParameterSnapshot | null) =>
        set({ subtitlePrefillParameters }),
      setYoutubeDubPrefillParameters: (
        youtubeDubPrefillParameters: JobParameterSnapshot | null
      ) => set({ youtubeDubPrefillParameters }),

      // Subtitle refresh
      incrementSubtitleRefreshKey: () =>
        set((state) => ({ subtitleRefreshKey: state.subtitleRefreshKey + 1 })),

      // Account UI
      setAccountExpanded: (isAccountExpanded: boolean) => set({ isAccountExpanded }),

      // Auth UI
      setAuthError: (authError: string | null) => set({ authError }),
      setIsLoggingIn: (isLoggingIn: boolean) => set({ isLoggingIn }),
      setShowChangePassword: (showChangePassword: boolean) => set({ showChangePassword }),
      setPasswordError: (passwordError: string | null) => set({ passwordError }),
      setPasswordMessage: (passwordMessage: string | null) => set({ passwordMessage }),
      setIsUpdatingPassword: (isUpdatingPassword: boolean) => set({ isUpdatingPassword }),

      // Form submission
      setIsSubmitting: (isSubmitting: boolean) => set({ isSubmitting }),
      setSubmitError: (submitError: string | null) => set({ submitError }),
    }),
    {
      name: 'ui-storage',
      // Only persist user preferences, not transient state
      partialize: (state) => ({
        selectedView: state.selectedView,
        isSidebarOpen: state.isSidebarOpen,
        isAccountExpanded: state.isAccountExpanded,
      }),
    }
  )
);
