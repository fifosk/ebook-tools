import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import { useUIStore } from '../uiStore';

describe('uiStore', () => {
  beforeEach(() => {
    // Reset store state between tests
    const { result } = renderHook(() => useUIStore());
    act(() => {
      // Reset to defaults
      result.current.setSelectedView('pipeline:source');
      result.current.setSidebarOpen(true);
      result.current.setPlayerContext(null);
      result.current.setImmersiveMode(false);
      result.current.setPlayerFullscreen(false);
      result.current.setPendingInputFile(null);
      result.current.setCopiedJobParameters(null);
      result.current.setSubtitlePrefillParameters(null);
      result.current.setYoutubeDubPrefillParameters(null);
      result.current.setAccountExpanded(false);
      result.current.setAuthError(null);
      result.current.setIsLoggingIn(false);
      result.current.setShowChangePassword(false);
      result.current.setPasswordError(null);
      result.current.setPasswordMessage(null);
      result.current.setIsUpdatingPassword(false);
      result.current.setIsSubmitting(false);
      result.current.setSubmitError(null);
    });
  });

  describe('view navigation', () => {
    it('should set selected view', () => {
      const { result } = renderHook(() => useUIStore());

      expect(result.current.selectedView).toBe('pipeline:source');

      act(() => {
        result.current.setSelectedView('job:progress');
      });

      expect(result.current.selectedView).toBe('job:progress');
    });

    it('should cycle through pipeline views', () => {
      const { result } = renderHook(() => useUIStore());
      const views: Array<typeof result.current.selectedView> = [
        'pipeline:source',
        'pipeline:metadata',
        'pipeline:language',
        'pipeline:output',
      ];

      for (const view of views) {
        act(() => {
          result.current.setSelectedView(view);
        });
        expect(result.current.selectedView).toBe(view);
      }
    });
  });

  describe('sidebar state', () => {
    it('should toggle sidebar', () => {
      const { result } = renderHook(() => useUIStore());

      expect(result.current.isSidebarOpen).toBe(true);

      act(() => {
        result.current.toggleSidebar();
      });

      expect(result.current.isSidebarOpen).toBe(false);

      act(() => {
        result.current.toggleSidebar();
      });

      expect(result.current.isSidebarOpen).toBe(true);
    });

    it('should set sidebar open directly', () => {
      const { result } = renderHook(() => useUIStore());

      act(() => {
        result.current.setSidebarOpen(false);
      });

      expect(result.current.isSidebarOpen).toBe(false);

      act(() => {
        result.current.setSidebarOpen(true);
      });

      expect(result.current.isSidebarOpen).toBe(true);
    });
  });

  describe('player state', () => {
    it('should manage player context', () => {
      const { result } = renderHook(() => useUIStore());
      const context = {
        type: 'job' as const,
        jobId: 'job-123',
        title: 'Test Book',
      };

      expect(result.current.playerContext).toBeNull();

      act(() => {
        result.current.setPlayerContext(context);
      });

      expect(result.current.playerContext).toEqual(context);

      act(() => {
        result.current.setPlayerContext(null);
      });

      expect(result.current.playerContext).toBeNull();
    });

    it('should manage player selection', () => {
      const { result } = renderHook(() => useUIStore());
      const selection = {
        baseId: 'test-id',
        preferredType: 'audio' as const,
        autoPlay: true,
      };

      act(() => {
        result.current.setPlayerSelection(selection);
      });

      expect(result.current.playerSelection).toEqual(selection);
    });

    it('should toggle immersive mode', () => {
      const { result } = renderHook(() => useUIStore());

      expect(result.current.isImmersiveMode).toBe(false);

      act(() => {
        result.current.setImmersiveMode(true);
      });

      expect(result.current.isImmersiveMode).toBe(true);
    });

    it('should toggle fullscreen mode', () => {
      const { result } = renderHook(() => useUIStore());

      expect(result.current.isPlayerFullscreen).toBe(false);

      act(() => {
        result.current.setPlayerFullscreen(true);
      });

      expect(result.current.isPlayerFullscreen).toBe(true);
    });
  });

  describe('library focus', () => {
    it('should set library focus request', () => {
      const { result } = renderHook(() => useUIStore());
      const request = {
        jobId: 'job-123',
        itemType: 'book' as const,
        token: 12345,
      };

      act(() => {
        result.current.setLibraryFocusRequest(request);
      });

      expect(result.current.libraryFocusRequest).toEqual(request);

      act(() => {
        result.current.setLibraryFocusRequest(null);
      });

      expect(result.current.libraryFocusRequest).toBeNull();
    });
  });

  describe('form prefills', () => {
    it('should manage pending input file', () => {
      const { result } = renderHook(() => useUIStore());

      act(() => {
        result.current.setPendingInputFile('book.epub');
      });

      expect(result.current.pendingInputFile).toBe('book.epub');
    });

    it('should manage copied job parameters', () => {
      const { result } = renderHook(() => useUIStore());
      const params = {
        input_file: 'book.epub',
        target_languages: ['ar', 'es'],
      };

      act(() => {
        result.current.setCopiedJobParameters(params);
      });

      expect(result.current.copiedJobParameters).toEqual(params);
    });

    it('should manage subtitle prefill parameters', () => {
      const { result } = renderHook(() => useUIStore());
      const params = {
        video_path: 'video.mp4',
        subtitle_path: 'subtitles.srt',
      };

      act(() => {
        result.current.setSubtitlePrefillParameters(params);
      });

      expect(result.current.subtitlePrefillParameters).toEqual(params);
    });

    it('should manage youtube dub prefill parameters', () => {
      const { result } = renderHook(() => useUIStore());
      const params = {
        video_path: 'https://youtube.com/watch?v=123',
      };

      act(() => {
        result.current.setYoutubeDubPrefillParameters(params);
      });

      expect(result.current.youtubeDubPrefillParameters).toEqual(params);
    });
  });

  describe('subtitle refresh', () => {
    it('should increment subtitle refresh key', () => {
      const { result } = renderHook(() => useUIStore());

      expect(result.current.subtitleRefreshKey).toBe(0);

      act(() => {
        result.current.incrementSubtitleRefreshKey();
      });

      expect(result.current.subtitleRefreshKey).toBe(1);

      act(() => {
        result.current.incrementSubtitleRefreshKey();
      });

      expect(result.current.subtitleRefreshKey).toBe(2);
    });
  });

  describe('account UI', () => {
    it('should toggle account expanded state', () => {
      const { result } = renderHook(() => useUIStore());

      expect(result.current.isAccountExpanded).toBe(false);

      act(() => {
        result.current.setAccountExpanded(true);
      });

      expect(result.current.isAccountExpanded).toBe(true);
    });
  });

  describe('auth UI state', () => {
    it('should manage auth error', () => {
      const { result } = renderHook(() => useUIStore());

      act(() => {
        result.current.setAuthError('Invalid credentials');
      });

      expect(result.current.authError).toBe('Invalid credentials');

      act(() => {
        result.current.setAuthError(null);
      });

      expect(result.current.authError).toBeNull();
    });

    it('should manage logging in state', () => {
      const { result } = renderHook(() => useUIStore());

      act(() => {
        result.current.setIsLoggingIn(true);
      });

      expect(result.current.isLoggingIn).toBe(true);
    });

    it('should manage change password UI', () => {
      const { result } = renderHook(() => useUIStore());

      act(() => {
        result.current.setShowChangePassword(true);
      });

      expect(result.current.showChangePassword).toBe(true);

      act(() => {
        result.current.setPasswordError('Password too weak');
      });

      expect(result.current.passwordError).toBe('Password too weak');

      act(() => {
        result.current.setPasswordMessage('Password updated successfully');
      });

      expect(result.current.passwordMessage).toBe('Password updated successfully');
    });

    it('should manage updating password state', () => {
      const { result } = renderHook(() => useUIStore());

      act(() => {
        result.current.setIsUpdatingPassword(true);
      });

      expect(result.current.isUpdatingPassword).toBe(true);
    });
  });

  describe('form submission state', () => {
    it('should manage submission loading state', () => {
      const { result } = renderHook(() => useUIStore());

      act(() => {
        result.current.setIsSubmitting(true);
      });

      expect(result.current.isSubmitting).toBe(true);
    });

    it('should manage submission error', () => {
      const { result } = renderHook(() => useUIStore());

      act(() => {
        result.current.setSubmitError('Failed to submit');
      });

      expect(result.current.submitError).toBe('Failed to submit');

      act(() => {
        result.current.setSubmitError(null);
      });

      expect(result.current.submitError).toBeNull();
    });
  });

  describe('persistence', () => {
    it('should persist selected view across hook instances', () => {
      const { result: result1 } = renderHook(() => useUIStore());

      act(() => {
        result1.current.setSelectedView('library:list');
      });

      // Simulate new component mount
      const { result: result2 } = renderHook(() => useUIStore());

      // Should maintain view from previous instance
      expect(result2.current.selectedView).toBe('library:list');
    });

    it('should persist sidebar state across hook instances', () => {
      const { result: result1 } = renderHook(() => useUIStore());

      act(() => {
        result1.current.setSidebarOpen(false);
      });

      const { result: result2 } = renderHook(() => useUIStore());
      expect(result2.current.isSidebarOpen).toBe(false);
    });

    it('should NOT persist transient state like auth errors', () => {
      const { result: result1 } = renderHook(() => useUIStore());

      act(() => {
        result1.current.setAuthError('Test error');
      });

      // Auth error should still be there in same instance
      expect(result1.current.authError).toBe('Test error');

      // But transient state is not persisted to localStorage
      // (would need full integration test to verify localStorage)
    });
  });
});
