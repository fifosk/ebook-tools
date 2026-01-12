import { useCallback, useEffect, useMemo, useState } from 'react';

type ServerStatus = 'checking' | 'online' | 'offline';

interface LoginServerStatusProps {
  apiBaseUrl: string;
}

export default function LoginServerStatus({ apiBaseUrl }: LoginServerStatusProps) {
  const [status, setStatus] = useState<ServerStatus>('checking');

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

  const checkHealth = useCallback(async () => {
    if (!healthUrl) {
      setStatus('offline');
      return;
    }
    setStatus('checking');
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 4000);
    try {
      const response = await fetch(healthUrl, {
        method: 'GET',
        cache: 'no-store',
        signal: controller.signal
      });
      setStatus(response.ok ? 'online' : 'offline');
    } catch {
      setStatus('offline');
    } finally {
      window.clearTimeout(timeout);
    }
  }, [healthUrl]);

  useEffect(() => {
    void checkHealth();
    const interval = window.setInterval(() => {
      void checkHealth();
    }, 15000);
    return () => window.clearInterval(interval);
  }, [checkHealth]);

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
