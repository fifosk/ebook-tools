import { useCallback, useEffect, useState } from 'react';
import {
  type ConfigGroup,
  type SnapshotMetadata,
  type ValidationError,
  createSnapshot,
  deleteSnapshot,
  exportSnapshot,
  fetchGroupedConfig,
  importConfig,
  listSnapshots,
  restoreSnapshot,
  updateConfigGroup,
  validateConfig
} from '../../api/client';
import ConfigGroupEditor from './ConfigGroupEditor';

interface SettingsPanelProps {
  currentUser: string;
}

type RefreshMode = 'initial' | 'subsequent';

export default function SettingsPanel({ currentUser }: SettingsPanelProps) {
  // Configuration state
  const [groups, setGroups] = useState<ConfigGroup[]>([]);
  const [activeGroup, setActiveGroup] = useState<string | null>(null);
  const [pendingChanges, setPendingChanges] = useState<Record<string, unknown>>({});
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);
  const [validationWarnings, setValidationWarnings] = useState<ValidationError[]>([]);

  // Snapshots state
  const [snapshots, setSnapshots] = useState<SnapshotMetadata[]>([]);
  const [showSnapshots, setShowSnapshots] = useState(false);

  // Loading and UI state
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [showSecrets, setShowSecrets] = useState(false);

  const refreshConfig = useCallback(async (mode: RefreshMode = 'subsequent', secrets = showSecrets) => {
    if (mode === 'initial') {
      setIsLoading(true);
    } else {
      setIsRefreshing(true);
    }
    setError(null);

    try {
      const response = await fetchGroupedConfig({ showSecrets: secrets });
      setGroups(response.groups);

      // Set first group as active if none selected
      if (!activeGroup && response.groups.length > 0) {
        setActiveGroup(response.groups[0].group);
      }
    } catch (requestError) {
      const message =
        requestError instanceof Error
          ? requestError.message
          : 'Unable to load configuration. Please try again.';
      setError(message);
    } finally {
      if (mode === 'initial') {
        setIsLoading(false);
      } else {
        setIsRefreshing(false);
      }
    }
  }, [activeGroup]);

  const refreshSnapshots = useCallback(async () => {
    try {
      const response = await listSnapshots(20, 0);
      setSnapshots(response.snapshots);
    } catch (requestError) {
      console.error('Failed to load snapshots:', requestError);
    }
  }, []);

  useEffect(() => {
    void refreshConfig('initial');
    void refreshSnapshots();
  }, [refreshConfig, refreshSnapshots]);

  const handleValueChange = useCallback((key: string, value: unknown) => {
    setPendingChanges(prev => ({ ...prev, [key]: value }));
    // Clear validation for this key
    setValidationErrors(prev => prev.filter(e => e.key !== key));
    setValidationWarnings(prev => prev.filter(e => e.key !== key));
  }, []);

  const handleValidate = useCallback(async () => {
    if (Object.keys(pendingChanges).length === 0) return;

    setIsValidating(true);
    try {
      const result = await validateConfig(pendingChanges, activeGroup ?? undefined);
      setValidationErrors(result.errors);
      setValidationWarnings(result.warnings);
      return result.isValid;
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Validation failed');
      return false;
    } finally {
      setIsValidating(false);
    }
  }, [pendingChanges, activeGroup]);

  const handleApply = useCallback(async () => {
    if (!activeGroup || Object.keys(pendingChanges).length === 0) return;

    // Validate first
    const isValid = await handleValidate();
    if (!isValid) {
      setError('Please fix validation errors before applying changes.');
      return;
    }

    setIsSaving(true);
    setError(null);
    setFeedback(null);

    try {
      const result = await updateConfigGroup(activeGroup, {
        values: pendingChanges,
        createBackup: true
      });

      setPendingChanges({});
      setValidationErrors([]);
      setValidationWarnings([]);

      if (result.requiresRestart) {
        setFeedback(
          `Updated ${result.updatedKeys.length} setting(s). A restart is required for changes to take effect.`
        );
      } else {
        setFeedback(`Updated ${result.updatedKeys.length} setting(s) successfully.`);
      }

      await refreshConfig();
      await refreshSnapshots();
    } catch (requestError) {
      const message =
        requestError instanceof Error ? requestError.message : 'Failed to apply changes.';
      setError(message);
    } finally {
      setIsSaving(false);
    }
  }, [activeGroup, pendingChanges, handleValidate, refreshConfig, refreshSnapshots]);

  const handleDiscard = useCallback(() => {
    setPendingChanges({});
    setValidationErrors([]);
    setValidationWarnings([]);
    setFeedback(null);
  }, []);

  const handleCreateBackup = useCallback(async () => {
    const label = window.prompt('Enter a label for this backup (optional):');
    if (label === null) return; // Cancelled

    try {
      await createSnapshot({ label: label || undefined });
      setFeedback('Backup created successfully.');
      await refreshSnapshots();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Failed to create backup.');
    }
  }, [refreshSnapshots]);

  const handleRestore = useCallback(async (snapshot: SnapshotMetadata) => {
    const confirmed = window.confirm(
      `Restore configuration from "${snapshot.label || snapshot.snapshotId}"? This will replace current settings.`
    );
    if (!confirmed) return;

    try {
      const result = await restoreSnapshot(snapshot.snapshotId);

      if (result.requiresRestart) {
        setFeedback(
          `Configuration restored. A restart is required for ${result.restartKeys.length} setting(s) to take effect.`
        );
      } else {
        setFeedback('Configuration restored successfully.');
      }

      await refreshConfig();
      await refreshSnapshots();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Failed to restore backup.');
    }
  }, [refreshConfig, refreshSnapshots]);

  const handleDeleteSnapshot = useCallback(async (snapshot: SnapshotMetadata) => {
    if (snapshot.isActive) {
      setError('Cannot delete the active snapshot.');
      return;
    }

    const confirmed = window.confirm(
      `Delete backup "${snapshot.label || snapshot.snapshotId}"? This cannot be undone.`
    );
    if (!confirmed) return;

    try {
      await deleteSnapshot(snapshot.snapshotId);
      setFeedback('Backup deleted.');
      await refreshSnapshots();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Failed to delete backup.');
    }
  }, [refreshSnapshots]);

  const handleExport = useCallback(async (snapshot: SnapshotMetadata) => {
    try {
      const data = await exportSnapshot(snapshot.snapshotId, true);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `config-${snapshot.snapshotId}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Failed to export backup.');
    }
  }, []);

  const handleImport = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const label = window.prompt('Enter a label for the imported configuration (optional):');

    try {
      const result = await importConfig(file, label ?? undefined, false);
      setFeedback(`Imported configuration with ${result.keyCount} keys.`);
      await refreshSnapshots();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Failed to import configuration.');
    }

    // Reset input
    event.target.value = '';
  }, [refreshSnapshots]);

  const hasPendingChanges = Object.keys(pendingChanges).length > 0;
  const hasErrors = validationErrors.length > 0;
  const isBusy = isSaving || isValidating || isRefreshing;
  const activeGroupData = groups.find(g => g.group === activeGroup);

  return (
    <div className="settings-panel">
      <header className="settings-panel__header">
        <div>
          <h2>System Settings</h2>
          <p className="settings-panel__description">
            Configure system settings, manage backups, and control server behavior.
          </p>
        </div>
        <div className="settings-panel__header-actions">
          {activeGroup === 'api_keys' && (
            <label className="settings-panel__toggle-secrets">
              <input
                type="checkbox"
                checked={showSecrets}
                onChange={e => {
                  setShowSecrets(e.target.checked);
                  void refreshConfig('subsequent', e.target.checked);
                }}
              />
              <span>Show API Key Values</span>
            </label>
          )}
          <button
            type="button"
            className="settings-panel__secondary"
            onClick={() => void refreshConfig()}
            disabled={isRefreshing}
          >
            {isRefreshing ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </header>

      {error && (
        <div className="settings-panel__alert" role="alert">
          {error}
        </div>
      )}
      {feedback && (
        <div className="settings-panel__notice" role="status">
          {feedback}
        </div>
      )}

      {isLoading ? (
        <div className="settings-panel__loading">Loading configuration...</div>
      ) : (
        <div className="settings-panel__content">
          {/* Group Navigation */}
          <nav className="settings-panel__nav">
            <h3>Configuration Groups</h3>
            <ul>
              {groups.map(group => (
                <li key={group.group}>
                  <button
                    type="button"
                    className={`settings-panel__nav-item ${
                      activeGroup === group.group ? 'settings-panel__nav-item--active' : ''
                    }`}
                    onClick={() => setActiveGroup(group.group)}
                  >
                    <span className="settings-panel__nav-label">
                      {group.metadata.displayName}
                    </span>
                    <span className="settings-panel__nav-count">{group.metadata.keyCount}</span>
                  </button>
                </li>
              ))}
            </ul>
          </nav>

          {/* Configuration Editor */}
          <section className="settings-panel__editor">
            {activeGroupData && (
              <ConfigGroupEditor
                group={activeGroupData}
                pendingChanges={pendingChanges}
                onChangeValue={handleValueChange}
                validationErrors={validationErrors}
                validationWarnings={validationWarnings}
              />
            )}

            {hasPendingChanges && (
              <div className="settings-panel__actions">
                <span className="settings-panel__changes-indicator">
                  {Object.keys(pendingChanges).length} unsaved change(s)
                </span>
                <button
                  type="button"
                  className="settings-panel__secondary"
                  onClick={handleDiscard}
                  disabled={isBusy}
                >
                  Discard
                </button>
                <button
                  type="button"
                  className="settings-panel__secondary"
                  onClick={() => void handleValidate()}
                  disabled={isBusy}
                >
                  {isValidating ? 'Validating...' : 'Validate'}
                </button>
                <button
                  type="button"
                  className="settings-panel__primary"
                  onClick={() => void handleApply()}
                  disabled={isBusy || hasErrors}
                >
                  {isSaving ? 'Applying...' : 'Apply Changes'}
                </button>
              </div>
            )}
          </section>
        </div>
      )}

      {/* Backup/Restore Section */}
      <section className="settings-panel__backups">
        <div className="settings-panel__backups-header">
          <h3>Configuration Backups</h3>
          <div className="settings-panel__backups-actions">
            <button
              type="button"
              className="settings-panel__secondary"
              onClick={() => setShowSnapshots(!showSnapshots)}
            >
              {showSnapshots ? 'Hide Backups' : 'Show Backups'}
            </button>
            <button
              type="button"
              className="settings-panel__primary"
              onClick={() => void handleCreateBackup()}
            >
              Create Backup
            </button>
            <label className="settings-panel__import-label">
              <input
                type="file"
                accept=".json"
                onChange={event => void handleImport(event)}
                className="settings-panel__import-input"
              />
              <span className="settings-panel__secondary">Import</span>
            </label>
          </div>
        </div>

        {showSnapshots && (
          <div className="settings-panel__snapshots">
            {snapshots.length === 0 ? (
              <p className="settings-panel__empty">No backups available.</p>
            ) : (
              <table className="settings-panel__table">
                <thead>
                  <tr>
                    <th>Label</th>
                    <th>Created</th>
                    <th>Source</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {snapshots.map(snapshot => (
                    <tr key={snapshot.snapshotId}>
                      <td>{snapshot.label || snapshot.snapshotId}</td>
                      <td>{new Date(snapshot.createdAt).toLocaleString()}</td>
                      <td>{snapshot.source}</td>
                      <td>
                        {snapshot.isActive ? (
                          <span className="settings-panel__badge settings-panel__badge--active">
                            Active
                          </span>
                        ) : null}
                      </td>
                      <td>
                        <div className="settings-panel__row-actions">
                          <button
                            type="button"
                            className="settings-panel__link"
                            onClick={() => void handleRestore(snapshot)}
                            disabled={snapshot.isActive}
                          >
                            Restore
                          </button>
                          <button
                            type="button"
                            className="settings-panel__link"
                            onClick={() => void handleExport(snapshot)}
                          >
                            Export
                          </button>
                          <button
                            type="button"
                            className="settings-panel__link settings-panel__link--danger"
                            onClick={() => void handleDeleteSnapshot(snapshot)}
                            disabled={snapshot.isActive}
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
