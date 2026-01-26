import { useCallback, useEffect, useState } from 'react';
import {
  type AuditLogEntry,
  type SystemStatusResponse,
  cancelRestart,
  fetchAuditLog,
  fetchSystemStatus,
  reloadConfig,
  requestRestart
} from '../../api/client';

interface SystemPanelProps {
  currentUser: string;
}

function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  const parts: string[] = [];
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0) parts.push(`${minutes}m`);
  if (secs > 0 || parts.length === 0) parts.push(`${secs}s`);

  return parts.join(' ');
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return 'N/A';
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

export default function SystemPanel({ currentUser }: SystemPanelProps) {
  // System status state
  const [status, setStatus] = useState<SystemStatusResponse | null>(null);
  const [isLoadingStatus, setIsLoadingStatus] = useState(true);

  // Restart state
  const [isRestarting, setIsRestarting] = useState(false);
  const [restartCountdown, setRestartCountdown] = useState<number | null>(null);
  const [isReloading, setIsReloading] = useState(false);

  // Audit log state
  const [auditEntries, setAuditEntries] = useState<AuditLogEntry[]>([]);
  const [isLoadingAudit, setIsLoadingAudit] = useState(true);

  // UI state
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const refreshStatus = useCallback(async () => {
    try {
      const data = await fetchSystemStatus();
      setStatus(data);
    } catch (requestError) {
      console.error('Failed to fetch system status:', requestError);
    } finally {
      setIsLoadingStatus(false);
    }
  }, []);

  const refreshAuditLog = useCallback(async () => {
    try {
      const data = await fetchAuditLog({ limit: 20 });
      setAuditEntries(data.entries);
    } catch (requestError) {
      console.error('Failed to fetch audit log:', requestError);
    } finally {
      setIsLoadingAudit(false);
    }
  }, []);

  useEffect(() => {
    void refreshStatus();
    void refreshAuditLog();

    // Refresh status periodically
    const interval = setInterval(() => {
      void refreshStatus();
    }, 30000);

    return () => clearInterval(interval);
  }, [refreshStatus, refreshAuditLog]);

  // Handle restart countdown
  useEffect(() => {
    if (restartCountdown === null || restartCountdown <= 0) return;

    const timer = setTimeout(() => {
      setRestartCountdown(prev => (prev !== null ? prev - 1 : null));
    }, 1000);

    return () => clearTimeout(timer);
  }, [restartCountdown]);

  const handleReloadConfig = useCallback(async () => {
    setIsReloading(true);
    setError(null);
    setFeedback(null);

    try {
      const result = await reloadConfig();
      if (result.success) {
        if (result.changedKeys.length > 0) {
          setFeedback(`Configuration reloaded. ${result.changedKeys.length} setting(s) changed.`);
        } else {
          setFeedback('Configuration reloaded. No changes detected.');
        }
        await refreshStatus();
        await refreshAuditLog();
      } else {
        setError(result.error || 'Failed to reload configuration.');
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Failed to reload configuration.');
    } finally {
      setIsReloading(false);
    }
  }, [refreshStatus, refreshAuditLog]);

  const handleRestartRequest = useCallback(async () => {
    const reason = window.prompt('Enter a reason for the restart (optional):');
    if (reason === null) return; // Cancelled

    const confirmed = window.confirm(
      'This will restart the API server. Active requests will complete before shutdown. Continue?'
    );
    if (!confirmed) return;

    setIsRestarting(true);
    setError(null);
    setFeedback(null);

    try {
      const result = await requestRestart({
        reason: reason || undefined,
        delaySeconds: 5
      });

      if (result.scheduled) {
        setRestartCountdown(result.delaySeconds);
        setFeedback(`Restart scheduled. Server will restart in ${result.delaySeconds} seconds.`);

        if (result.runningJobs > 0) {
          setFeedback(prev =>
            `${prev} Note: ${result.runningJobs} job(s) are currently running.`
          );
        }
      }
    } catch (requestError) {
      setIsRestarting(false);
      setError(requestError instanceof Error ? requestError.message : 'Failed to request restart.');
    }
  }, []);

  const handleCancelRestart = useCallback(async () => {
    try {
      const result = await cancelRestart();
      if (result.cancelled) {
        setIsRestarting(false);
        setRestartCountdown(null);
        setFeedback('Restart cancelled.');
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Failed to cancel restart.');
    }
  }, []);

  return (
    <div className="system-panel">
      <header className="system-panel__header">
        <h2>System Control</h2>
        <p className="system-panel__description">
          Monitor system status, reload configuration, and manage server restarts.
        </p>
      </header>

      {error && (
        <div className="system-panel__alert" role="alert">
          {error}
        </div>
      )}
      {feedback && (
        <div className="system-panel__notice" role="status">
          {feedback}
        </div>
      )}

      {/* System Status */}
      <section className="system-panel__section">
        <h3>System Status</h3>
        {isLoadingStatus ? (
          <div className="system-panel__loading">Loading status...</div>
        ) : status ? (
          <div className="system-panel__status-grid">
            <dl>
              <dt>Uptime</dt>
              <dd>{formatDuration(status.uptimeSeconds)}</dd>

              <dt>Configuration Loaded</dt>
              <dd>{formatTimestamp(status.configLoadedAt)}</dd>

              <dt>Database Config</dt>
              <dd>{status.dbEnabled ? 'Enabled' : 'Disabled'}</dd>

              <dt>Active Snapshot</dt>
              <dd>{status.activeSnapshotId || 'None'}</dd>
            </dl>

            {status.restartRequired && (
              <div className="system-panel__warning">
                <strong>Restart Required</strong>
                <p>
                  The following settings require a restart to take effect:
                  {status.restartKeys.length > 0
                    ? ` ${status.restartKeys.join(', ')}`
                    : ' (pending changes)'}
                </p>
              </div>
            )}
          </div>
        ) : (
          <div className="system-panel__error">Unable to load system status.</div>
        )}
      </section>

      {/* System Actions */}
      <section className="system-panel__section">
        <h3>System Actions</h3>
        <div className="system-panel__actions">
          <div className="system-panel__action">
            <button
              type="button"
              className="system-panel__button"
              onClick={() => void handleReloadConfig()}
              disabled={isReloading || isRestarting}
            >
              {isReloading ? 'Reloading...' : 'Reload Configuration'}
            </button>
            <p className="system-panel__action-description">
              Hot-reload configuration from files and database. Settings that require restart will be queued.
            </p>
          </div>

          <div className="system-panel__action">
            {isRestarting ? (
              <div className="system-panel__restart-pending">
                <div className="system-panel__countdown">
                  {restartCountdown !== null && restartCountdown > 0
                    ? `Restarting in ${restartCountdown}s...`
                    : 'Restarting...'}
                </div>
                <button
                  type="button"
                  className="system-panel__button system-panel__button--secondary"
                  onClick={() => void handleCancelRestart()}
                  disabled={restartCountdown !== null && restartCountdown <= 0}
                >
                  Cancel Restart
                </button>
              </div>
            ) : (
              <button
                type="button"
                className="system-panel__button system-panel__button--danger"
                onClick={() => void handleRestartRequest()}
                disabled={isReloading}
              >
                Restart API Server
              </button>
            )}
            <p className="system-panel__action-description">
              Gracefully restart the server. Active requests will complete before shutdown.
            </p>
          </div>
        </div>
      </section>

      {/* Recent Audit Log */}
      <section className="system-panel__section">
        <h3>Recent Configuration Changes</h3>
        {isLoadingAudit ? (
          <div className="system-panel__loading">Loading audit log...</div>
        ) : auditEntries.length === 0 ? (
          <p className="system-panel__empty">No recent changes recorded.</p>
        ) : (
          <div className="system-panel__table-wrapper">
            <table className="system-panel__table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>User</th>
                  <th>Action</th>
                  <th>Details</th>
                  <th>Changes</th>
                </tr>
              </thead>
              <tbody>
                {auditEntries.map(entry => (
                  <tr key={entry.id}>
                    <td>{formatTimestamp(entry.timestamp)}</td>
                    <td>{entry.username || 'System'}</td>
                    <td>
                      <span className={`system-panel__action-badge system-panel__action-badge--${entry.action}`}>
                        {entry.action}
                      </span>
                    </td>
                    <td>
                      {entry.groupName && entry.keyName
                        ? `${entry.groupName}.${entry.keyName}`
                        : entry.snapshotId
                          ? `Snapshot: ${entry.snapshotId}`
                          : entry.metadata
                            ? JSON.stringify(entry.metadata).slice(0, 50)
                            : '-'}
                    </td>
                    <td className="system-panel__changes-cell">
                      {entry.oldValue || entry.newValue ? (
                        <div className="system-panel__changes">
                          {entry.oldValue && (
                            <span className="system-panel__change-old" title={entry.oldValue}>
                              {entry.oldValue.length > 30 ? `${entry.oldValue.slice(0, 30)}…` : entry.oldValue}
                            </span>
                          )}
                          {entry.oldValue && entry.newValue && (
                            <span className="system-panel__change-arrow">→</span>
                          )}
                          {entry.newValue && (
                            <span className="system-panel__change-new" title={entry.newValue}>
                              {entry.newValue.length > 30 ? `${entry.newValue.slice(0, 30)}…` : entry.newValue}
                            </span>
                          )}
                        </div>
                      ) : (
                        '-'
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
