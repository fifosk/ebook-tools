import { useEffect, useState } from 'react';

type SequenceDebugState = {
  enabled?: boolean;
};

declare global {
  interface Window {
    __SEQ_DEBUG__?: SequenceDebugState;
  }
}

const SEQUENCE_DEBUG_EMPTY: SequenceDebugState = { enabled: false };

export function useSequenceDebug(): boolean {
  const [enabled, setEnabled] = useState(() => {
    if (typeof window === 'undefined') {
      return false;
    }
    const params = new URLSearchParams(window.location.search);
    const paramEnabled = params.get('seqdebug');
    if (paramEnabled === '1' || paramEnabled === 'true') {
      return true;
    }
    return Boolean(window.__SEQ_DEBUG__?.enabled);
  });

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    const handle = () => {
      const params = new URLSearchParams(window.location.search);
      const paramEnabled = params.get('seqdebug');
      const next =
        paramEnabled === '1' ||
        paramEnabled === 'true' ||
        Boolean((window.__SEQ_DEBUG__ ?? SEQUENCE_DEBUG_EMPTY).enabled);
      setEnabled(Boolean(next));
    };
    window.addEventListener('seq_debug_update', handle);
    return () => window.removeEventListener('seq_debug_update', handle);
  }, []);

  return enabled;
}
