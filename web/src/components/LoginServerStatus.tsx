import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

type ServerStatus = 'checking' | 'online' | 'offline';

interface LoginServerStatusProps {
  apiBaseUrl: string;
}

const CACHE_TTL_MS = 60000;

type StatusCache = {
  status: ServerStatus;
  checkedAt: number;
};

export default function LoginServerStatus({ apiBaseUrl }: LoginServerStatusProps) {
  const [status, setStatus] = useState<ServerStatus>('checking');
  const lastCheckedRef = useRef<number>(0);
  const inFlightRef = useRef(false);

  const healthUrl = useMemo(() => {
    if (!apiBaseUrl) {
      return '';
    }
    try {
      return new URL('/_health', apiBaseUrl).toString();
    } catch {
      return '';
    }
  }, [apiBaseUrl]);

  const cacheKey = useMemo(() => {
    if (!healthUrl) {
      return '';
    }
    return `loginHealth:${healthUrl}`;
  }, [healthUrl]);

  const readCache = useCallback((): StatusCache | null => {
    if (!cacheKey) {
      return null;
    }
    try {
      const raw = window.sessionStorage.getItem(cacheKey);
      if (!raw) {
        return null;
      }
      const parsed = JSON.parse(raw) as StatusCache;
      if (!parsed || typeof parsed.checkedAt !== 'number' || typeof parsed.status !== 'string') {
        return null;
      }
      return parsed;
    } catch {
      return null;
    }
  }, [cacheKey]);

  const writeCache = useCallback(
    (nextStatus: ServerStatus, checkedAt: number) => {
      if (!cacheKey) {
        return;
      }
      try {
        window.sessionStorage.setItem(cacheKey, JSON.stringify({ status: nextStatus, checkedAt }));
      } catch {
        // Ignore cache failures in private mode.
      }
    },
    [cacheKey]
  );

  const setStatusIfChanged = useCallback((nextStatus: ServerStatus) => {
    setStatus((prev) => (prev === nextStatus ? prev : nextStatus));
  }, []);

  const checkHealth = useCallback(async (force = false) => {
    if (!healthUrl) {
      setStatusIfChanged('offline');
      return;
    }
    if (inFlightRef.current) {
      return;
    }
    const now = Date.now();
    if (!force && now - lastCheckedRef.current < CACHE_TTL_MS) {
      return;
    }
    inFlightRef.current = true;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 4000);
    try {
      const response = await fetch(healthUrl, {
        method: 'GET',
        cache: 'no-store',
        signal: controller.signal
      });
      const nextStatus: ServerStatus = response.ok ? 'online' : 'offline';
      lastCheckedRef.current = now;
      writeCache(nextStatus, now);
      setStatusIfChanged(nextStatus);
    } catch {
      lastCheckedRef.current = now;
      writeCache('offline', now);
      setStatusIfChanged('offline');
    } finally {
      window.clearTimeout(timeout);
      inFlightRef.current = false;
    }
  }, [healthUrl, setStatusIfChanged, writeCache]);

  useEffect(() => {
    if (!healthUrl) {
      setStatusIfChanged('offline');
      return;
    }
    const cached = readCache();
    if (cached) {
      lastCheckedRef.current = cached.checkedAt;
      setStatusIfChanged(cached.status);
    }
    const now = Date.now();
    if (!cached || now - cached.checkedAt >= CACHE_TTL_MS) {
      void checkHealth(true);
    }
    const interval = window.setInterval(() => {
      if (document.visibilityState === 'visible') {
        void checkHealth();
      }
    }, 30000);
    return () => window.clearInterval(interval);
  }, [checkHealth, healthUrl, readCache, setStatusIfChanged]);

  const statusLabel = useMemo(() => {
    if (status === 'online') {
      return 'Server online';
    }
    if (status === 'offline') {
      return 'Server offline';
    }
    return 'Checking server';
  }, [status]);

  return (
    <div className="auth-status" data-state={status} role="status" aria-live="polite">
      <div className="auth-status__lights" aria-hidden="true">
        <span className="auth-status__light auth-status__light--red" />
        <span className="auth-status__light auth-status__light--yellow" />
        <span className="auth-status__light auth-status__light--green" />
      </div>
      <div className="auth-status__text">
        <span className="auth-status__label">Healthcheck</span>
        <span className="auth-status__value">{statusLabel}</span>
      </div>
    </div>
  );
}
