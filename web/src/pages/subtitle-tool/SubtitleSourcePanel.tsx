import type { ChangeEvent } from 'react';
import type { SubtitleSourceEntry } from '../../api/dtos';
import EmojiIcon from '../../components/EmojiIcon';
import {
  resolveSubtitleFlag,
  resolveSubtitleLanguageCandidate,
  subtitleFormatFromPath,
  subtitleLanguageDetail
} from '../../utils/subtitles';
import type { SubtitleSourceMode } from './subtitleToolTypes';
import styles from '../SubtitleToolPage.module.css';

type SubtitleSourcePanelProps = {
  sourceMode: SubtitleSourceMode;
  sourceDirectory: string;
  sourceCount: number;
  sortedSources: SubtitleSourceEntry[];
  selectedSource: string;
  isLoadingSources: boolean;
  sourceError: string | null;
  sourceMessage: string | null;
  deletingSourcePath: string | null;
  isAssSelection: boolean;
  onSourceModeChange: (mode: SubtitleSourceMode) => void;
  onSelectSource: (path: string) => void;
  onRefreshSources: () => void;
  onDeleteSource: (entry: SubtitleSourceEntry) => void;
  onUploadFileChange: (file: File | null) => void;
};

export default function SubtitleSourcePanel({
  sourceMode,
  sourceDirectory,
  sourceCount,
  sortedSources,
  selectedSource,
  isLoadingSources,
  sourceError,
  sourceMessage,
  deletingSourcePath,
  isAssSelection,
  onSourceModeChange,
  onSelectSource,
  onRefreshSources,
  onDeleteSource,
  onUploadFileChange
}: SubtitleSourcePanelProps) {
  const handleSourceModeChange = (event: ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value === 'upload' ? 'upload' : 'existing';
    onSourceModeChange(value);
  };

  return (
    <section className={styles.card}>
      <div className={styles.cardHeader}>
        <div>
          <h2 className={styles.cardTitle}>Subtitle selection</h2>
          <p className={styles.cardHint}>Pick an existing NAS subtitle file or upload a new one to translate.</p>
        </div>
      </div>
      <fieldset>
        <legend>Subtitle source</legend>
        <div className="field">
          <label>
            <input
              type="radio"
              name="subtitle_source_mode"
              value="existing"
              checked={sourceMode === 'existing'}
              onChange={handleSourceModeChange}
            />
            Use existing file
          </label>
          <label>
            <input
              type="radio"
              name="subtitle_source_mode"
              value="upload"
              checked={sourceMode === 'upload'}
              onChange={handleSourceModeChange}
            />
            Upload new file
          </label>
        </div>
        {sourceMode === 'existing' ? (
          <div className="field">
            <div className={styles.cardHeader}>
              <div>
                <div className="field-label">Subtitle directory</div>
                <p className={styles.cardHint}>
                  Using the default NAS Subtitles folder; scans for .srt/.vtt files plus generated .ass outputs and mirrors deletions alongside HTML transcripts.
                </p>
                <p className={styles.sourcePath}>{sourceDirectory}</p>
              </div>
              <div className={styles.controlRow}>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={() => void onRefreshSources()}
                  disabled={isLoadingSources || Boolean(deletingSourcePath)}
                >
                  {isLoadingSources ? 'Refreshing…' : 'Refresh list'}
                </button>
              </div>
            </div>
            {sourceError ? <div className="alert" role="alert">{sourceError}</div> : null}
            {sourceMessage && !sourceError ? <p className={styles.status}>{sourceMessage}</p> : null}
            <div className={styles.sourceList}>
              {isLoadingSources && sourceCount === 0 ? (
                <p className={styles.status}>Scanning directory…</p>
              ) : null}
              {!isLoadingSources && sourceCount === 0 ? (
                <p className={styles.status}>No subtitles found in {sourceDirectory}.</p>
              ) : null}
              {isAssSelection ? (
                <p className={styles.status}>
                  Generated ASS files are read-only—pick the original SRT/VTT or upload a new subtitle to process.
                </p>
              ) : null}
              {sortedSources.map((entry) => {
                const isActive = selectedSource === entry.path;
                const isDeleting = deletingSourcePath === entry.path;
                const language = resolveSubtitleLanguageCandidate(entry.language, entry.path, entry.name);
                const languageLabel = subtitleLanguageDetail(language, entry.path, entry.name);
                const languageFlag = resolveSubtitleFlag(language, entry.path, entry.name);
                const format = (entry.format || subtitleFormatFromPath(entry.path) || 'srt').toUpperCase();
                const isAssFormat = format.toLowerCase() === 'ass';
                return (
                  <div
                    key={entry.path}
                    className={`${styles.sourceCard} ${isActive ? styles.sourceCardActive : ''}`}
                  >
                    <label className={styles.sourceChoice}>
                      <input
                        type="radio"
                        name="subtitle_source"
                        value={entry.path}
                        checked={isActive}
                        disabled={Boolean(deletingSourcePath)}
                        onChange={() => onSelectSource(entry.path)}
                      />
                      <div className={styles.sourceBody}>
                        <div className={styles.sourceHeaderRow}>
                          <div className={styles.sourceName}>{entry.name}</div>
                          <div className={styles.sourceBadges} aria-label="Subtitle details">
                            <span
                              className={`${styles.pill} ${isAssFormat ? styles.pillAss : styles.pillFormat}`}
                            >
                              {format}
                            </span>
                            <span
                              className={`${styles.pill} ${styles.pillMuted} ${styles.pillFlag}`}
                              title={languageLabel}
                              aria-label={languageLabel}
                            >
                              <EmojiIcon emoji={languageFlag} />
                            </span>
                          </div>
                        </div>
                      </div>
                    </label>
                    <div className={styles.sourceActions}>
                      <button
                        type="button"
                        className={styles.dangerButton}
                        onClick={() => void onDeleteSource(entry)}
                        disabled={Boolean(deletingSourcePath) || isLoadingSources}
                        title={`Delete ${entry.name}`}
                        aria-label={`Delete ${entry.name}`}
                      >
                        {isDeleting ? '…' : '🗑'}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <div className="field">
            <label className="field-label" htmlFor="subtitle-upload-input">
              Upload subtitle file
            </label>
            <input
              id="subtitle-upload-input"
              type="file"
              accept=".srt,.vtt"
              onChange={(event) => {
                const file = event.target.files && event.target.files.length > 0 ? event.target.files[0] : null;
                onUploadFileChange(file);
              }}
            />
          </div>
        )}
      </fieldset>
    </section>
  );
}
