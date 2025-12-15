import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ReadingBedEntry, ReadingBedListResponse } from '../../api/dtos';
import { deleteReadingBed, fetchReadingBeds, updateReadingBed, uploadReadingBed, withBase } from '../../api/client';
import styles from './ReadingBedsPanel.module.css';

type PanelState = {
  catalog: ReadingBedListResponse | null;
  isLoading: boolean;
  error: string | null;
};

function ReadingBedsPanel() {
  const [state, setState] = useState<PanelState>({ catalog: null, isLoading: true, error: null });
  const [uploadLabel, setUploadLabel] = useState('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [mutatingIds, setMutatingIds] = useState<Record<string, boolean>>({});
  const [labelDrafts, setLabelDrafts] = useState<Record<string, string>>({});
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const refresh = useCallback(async () => {
    setState((previous) => ({ ...previous, isLoading: true, error: null }));
    try {
      const catalog = await fetchReadingBeds();
      setState({ catalog, isLoading: false, error: null });
      setLabelDrafts((previous) => {
        const next: Record<string, string> = { ...previous };
        for (const bed of catalog.beds) {
          if (typeof next[bed.id] !== 'string') {
            next[bed.id] = bed.label;
          }
        }
        return next;
      });
    } catch (error) {
      setState({
        catalog: null,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Unable to load reading beds.'
      });
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const defaultId = state.catalog?.default_id ?? null;
  const beds = state.catalog?.beds ?? [];

  const sortedBeds = useMemo(() => {
    return [...beds].sort((a, b) => a.label.localeCompare(b.label));
  }, [beds]);

  const handleUpload = useCallback(async () => {
    if (!uploadFile) {
      return;
    }
    setIsUploading(true);
    try {
      await uploadReadingBed(uploadFile, uploadLabel);
      setUploadFile(null);
      setUploadLabel('');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      await refresh();
    } catch (error) {
      setState((previous) => ({
        ...previous,
        error: error instanceof Error ? error.message : 'Unable to upload reading bed.'
      }));
    } finally {
      setIsUploading(false);
    }
  }, [refresh, uploadFile, uploadLabel]);

  const markMutating = useCallback((bedId: string, value: boolean) => {
    setMutatingIds((previous) => ({ ...previous, [bedId]: value }));
  }, []);

  const handleSetDefault = useCallback(
    async (bed: ReadingBedEntry) => {
      markMutating(bed.id, true);
      try {
        await updateReadingBed(bed.id, { set_default: true });
        await refresh();
      } catch (error) {
        setState((previous) => ({
          ...previous,
          error: error instanceof Error ? error.message : 'Unable to update default.'
        }));
      } finally {
        markMutating(bed.id, false);
      }
    },
    [markMutating, refresh]
  );

  const handleSaveLabel = useCallback(
    async (bed: ReadingBedEntry) => {
      const draft = (labelDrafts[bed.id] ?? '').trim();
      markMutating(bed.id, true);
      try {
        await updateReadingBed(bed.id, { label: draft || bed.id });
        await refresh();
      } catch (error) {
        setState((previous) => ({
          ...previous,
          error: error instanceof Error ? error.message : 'Unable to update label.'
        }));
      } finally {
        markMutating(bed.id, false);
      }
    },
    [labelDrafts, markMutating, refresh]
  );

  const handleDelete = useCallback(
    async (bed: ReadingBedEntry) => {
      const confirmed = window.confirm(`Delete reading bed "${bed.label}"?`);
      if (!confirmed) {
        return;
      }
      markMutating(bed.id, true);
      try {
        await deleteReadingBed(bed.id);
        await refresh();
      } catch (error) {
        setState((previous) => ({
          ...previous,
          error: error instanceof Error ? error.message : 'Unable to delete reading bed.'
        }));
      } finally {
        markMutating(bed.id, false);
      }
    },
    [markMutating, refresh]
  );

  return (
    <div>
      <section className="account-panel">
        <h2>Reading music beds</h2>
        <p>Upload, rename, delete, and set the default background music track for the interactive player.</p>
        {state.error ? (
          <div className="error-message" role="alert">
            {state.error}
          </div>
        ) : null}
        <div className="account-panel__row">
          <div className="account-panel__field">
            <label className="account-panel__label" htmlFor="reading-bed-upload">
              Upload MP3
            </label>
            <input
              id="reading-bed-upload"
              ref={fileInputRef}
              type="file"
              accept="audio/mpeg,audio/mp3,.mp3"
              disabled={isUploading}
              onChange={(event) => {
                const file = event.target.files?.[0] ?? null;
                setUploadFile(file);
              }}
            />
          </div>
          <div className="account-panel__field">
            <label className="account-panel__label" htmlFor="reading-bed-upload-label">
              Display name (optional)
            </label>
            <input
              id="reading-bed-upload-label"
              type="text"
              value={uploadLabel}
              disabled={isUploading}
              onChange={(event) => setUploadLabel(event.target.value)}
              placeholder="e.g. Calm piano loop"
            />
          </div>
          <div className="account-panel__field">
            <span className="account-panel__label" aria-hidden="true">
              &nbsp;
            </span>
            <button
              type="button"
              className="session-info__button"
              disabled={!uploadFile || isUploading}
              onClick={() => {
                void handleUpload();
              }}
            >
              {isUploading ? 'Uploading…' : 'Upload'}
            </button>
          </div>
        </div>
      </section>

      <section className="account-panel">
        <div className="account-panel__row" style={{ alignItems: 'center' }}>
          <h2 style={{ margin: 0 }}>Available beds</h2>
          <button
            type="button"
            className="session-info__button"
            disabled={state.isLoading}
            onClick={() => {
              void refresh();
            }}
          >
            Reload
          </button>
        </div>
        {state.isLoading ? <p>Loading…</p> : null}
        {!state.isLoading && sortedBeds.length === 0 ? <p>No reading beds found.</p> : null}
        {sortedBeds.length > 0 ? (
          <div className="user-management__table-wrapper">
            <table className="user-management__table" style={{ minWidth: 720 }}>
              <thead>
                <tr>
                  <th scope="col" style={{ width: 80 }}>
                    Default
                  </th>
                  <th scope="col">Name</th>
                  <th scope="col" style={{ width: 120 }}>
                    Type
                  </th>
                  <th scope="col" style={{ width: 80 }}>
                    Link
                  </th>
                  <th scope="col" style={{ width: 180 }}>
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {sortedBeds.map((bed) => {
                  const draft = labelDrafts[bed.id] ?? bed.label;
                  const isDefault = Boolean(defaultId && bed.id === defaultId);
                  const isMutating = Boolean(mutatingIds[bed.id]);
                  const canSave = draft.trim() !== bed.label.trim();
                  const openUrl = bed.url.startsWith('/api/') ? withBase(bed.url) : bed.url;
                  return (
                    <tr key={bed.id}>
                      <td>
                        {isDefault ? (
                          <span className={styles.defaultBadge} title="Default bed" aria-label="Default bed">
                            ★
                          </span>
                        ) : (
                          <span style={{ opacity: 0.4 }}>—</span>
                        )}
                      </td>
                      <td>
                        <div className={styles.bedNameCell}>
                          <input
                            type="text"
                            value={draft}
                            disabled={isMutating}
                            onChange={(event) => {
                              const value = event.target.value;
                              setLabelDrafts((previous) => ({ ...previous, [bed.id]: value }));
                            }}
                          />
                          <div className={styles.bedIdLine}>
                            <code>{bed.id}</code>
                          </div>
                        </div>
                      </td>
                      <td style={{ fontSize: '0.95rem', opacity: 0.85 }}>{bed.kind}</td>
                      <td>
                        <a
                          href={openUrl}
                          target="_blank"
                          rel="noreferrer"
                          title="Open audio URL"
                          aria-label="Open audio URL"
                        >
                          Open
                        </a>
                      </td>
                      <td>
                        <div className={styles.actions}>
                          <button
                            type="button"
                            className={styles.actionIconButton}
                            disabled={isMutating || isDefault}
                            onClick={() => {
                              void handleSetDefault(bed);
                            }}
                            title="Set as default"
                            aria-label="Set as default"
                          >
                            <span aria-hidden="true">{isDefault ? '★' : '☆'}</span>
                            <span className="visually-hidden">Set as default</span>
                          </button>
                          <button
                            type="button"
                            className={styles.actionIconButton}
                            disabled={isMutating || !canSave}
                            onClick={() => {
                              void handleSaveLabel(bed);
                            }}
                            title="Save name"
                            aria-label="Save name"
                          >
                            <span aria-hidden="true">{isMutating ? '…' : '💾'}</span>
                            <span className="visually-hidden">Save name</span>
                          </button>
                          <button
                            type="button"
                            className={styles.actionIconButton}
                            disabled={isMutating}
                            onClick={() => {
                              void handleDelete(bed);
                            }}
                            title="Delete"
                            aria-label="Delete"
                            data-variant="danger"
                          >
                            <span aria-hidden="true">{isMutating ? '…' : '🗑'}</span>
                            <span className="visually-hidden">Delete</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </div>
  );
}

export default ReadingBedsPanel;
