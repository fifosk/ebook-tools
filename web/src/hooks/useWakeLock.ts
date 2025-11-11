import { useEffect } from 'react';

type WakeLockType = 'screen';
type WakeLockSentinel = {
  released: boolean;
  release: () => Promise<void>;
  addEventListener: (type: 'release', listener: () => void) => void;
  removeEventListener: (type: 'release', listener: () => void) => void;
};

type WakeLockNavigator = Navigator & {
  wakeLock?: {
    request: (type: WakeLockType) => Promise<WakeLockSentinel>;
  };
};

const isWakeLockSupported = (nav: Navigator | undefined): nav is WakeLockNavigator =>
  Boolean(nav && 'wakeLock' in nav);

/**
 * Requests a screen wake lock while `enabled` is true, releasing it on cleanup.
 * Automatically re-requests the lock when the tab regains visibility.
 */
export function useWakeLock(enabled: boolean) {
  useEffect(() => {
    if (!enabled || typeof document === 'undefined') {
      return;
    }

    const globalNavigator: Navigator | undefined =
      typeof navigator === 'undefined' ? undefined : navigator;
    if (!isWakeLockSupported(globalNavigator)) {
      return;
    }

    let sentinel: WakeLockSentinel | null = null;
    let cancelled = false;

    const request = async () => {
      if (!enabled || cancelled) {
        return;
      }
      try {
        sentinel = await globalNavigator.wakeLock?.request('screen');
        sentinel?.addEventListener('release', handleRelease);
      } catch {
        sentinel = null;
      }
    };

    const handleRelease = () => {
      sentinel?.removeEventListener?.('release', handleRelease);
      sentinel = null;
      if (!cancelled && document.visibilityState === 'visible') {
        request();
      }
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        request();
      } else if (sentinel) {
        sentinel.release().catch(() => undefined);
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    request();

    return () => {
      cancelled = true;
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      sentinel?.removeEventListener?.('release', handleRelease);
      sentinel?.release().catch(() => undefined);
      sentinel = null;
    };
  }, [enabled]);
}
