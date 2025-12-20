import type { SubtitleTvMetadataPreviewResponse } from '../../api/dtos';
import {
  coerceRecord,
  formatEpisodeCode,
  normalizeTextValue
} from './subtitleToolUtils';
import styles from '../SubtitleToolPage.module.css';

type SubtitleMetadataPanelProps = {
  metadataSourceName: string;
  metadataLookupSourceName: string;
  metadataPreview: SubtitleTvMetadataPreviewResponse | null;
  metadataLoading: boolean;
  metadataError: string | null;
  mediaMetadataDraft: Record<string, unknown> | null;
  onLookupSourceNameChange: (value: string) => void;
  onLookupMetadata: (sourceName: string, force: boolean) => void;
  onClearMetadata: () => void;
  onUpdateMediaMetadataDraft: (updater: (draft: Record<string, unknown>) => void) => void;
  onUpdateMediaMetadataSection: (sectionKey: string, updater: (section: Record<string, unknown>) => void) => void;
};

export default function SubtitleMetadataPanel({
  metadataSourceName,
  metadataLookupSourceName,
  metadataPreview,
  metadataLoading,
  metadataError,
  mediaMetadataDraft,
  onLookupSourceNameChange,
  onLookupMetadata,
  onClearMetadata,
  onUpdateMediaMetadataDraft,
  onUpdateMediaMetadataSection
}: SubtitleMetadataPanelProps) {
  return (
    <section className={styles.card}>
      <div className={styles.cardHeader}>
        <div>
          <h2 className={styles.cardTitle}>Metadata loader</h2>
          <p className={styles.cardHint}>
            Load TV episode metadata from TVMaze (no API key) and edit it before submitting the job.
          </p>
        </div>
      </div>

      {!metadataSourceName ? (
        <p className={styles.status}>Select a subtitle file to load metadata.</p>
      ) : (
        <>
          {metadataError ? <div className="alert" role="alert">{metadataError}</div> : null}
          <div className={styles.controlRow}>
            <label style={{ minWidth: 'min(32rem, 100%)' }}>
              Lookup filename
              <input
                type="text"
                value={metadataLookupSourceName}
                onChange={(event) => onLookupSourceNameChange(event.target.value)}
              />
            </label>
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={() => void onLookupMetadata(metadataLookupSourceName, false)}
              disabled={!metadataLookupSourceName.trim() || metadataLoading}
              aria-busy={metadataLoading}
            >
              {metadataLoading ? 'Looking up…' : 'Lookup'}
            </button>
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={() => void onLookupMetadata(metadataLookupSourceName, true)}
              disabled={!metadataLookupSourceName.trim() || metadataLoading}
              aria-busy={metadataLoading}
            >
              Refresh
            </button>
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={onClearMetadata}
              disabled={metadataLoading}
            >
              Clear
            </button>
          </div>

          {metadataLoading ? <p className={styles.status}>Loading metadata…</p> : null}
          {!metadataLoading && metadataPreview ? (
            (() => {
              const media = coerceRecord(mediaMetadataDraft);
              const show = media ? coerceRecord(media['show']) : null;
              const episode = media ? coerceRecord(media['episode']) : null;
              const errorMessage = normalizeTextValue(media ? media['error'] : null);
              const showName = normalizeTextValue(show ? show['name'] : null);
              const episodeName = normalizeTextValue(episode ? episode['name'] : null);
              const seasonNumber = typeof episode?.season === 'number' ? episode.season : null;
              const episodeNumber = typeof episode?.number === 'number' ? episode.number : null;
              const episodeCode = formatEpisodeCode(seasonNumber, episodeNumber);
              const airdate = normalizeTextValue(episode ? episode['airdate'] : null);
              const networkName = normalizeTextValue(coerceRecord(show ? show['network'] : null)?.name);
              const episodeUrl = normalizeTextValue(episode ? episode['url'] : null);
              const showImage = show ? coerceRecord(show['image']) : null;
              const showImageMedium = normalizeTextValue(showImage ? showImage['medium'] : null);
              const showImageOriginal = normalizeTextValue(showImage ? showImage['original'] : null);
              const showImageUrl = showImageMedium ?? showImageOriginal;
              const showImageLink = showImageOriginal ?? showImageMedium;
              const episodeImage = episode ? coerceRecord(episode['image']) : null;
              const episodeImageMedium = normalizeTextValue(episodeImage ? episodeImage['medium'] : null);
              const episodeImageOriginal = normalizeTextValue(episodeImage ? episodeImage['original'] : null);
              const episodeImageUrl = episodeImageMedium ?? episodeImageOriginal;
              const episodeImageLink = episodeImageOriginal ?? episodeImageMedium;

              const genresValue =
                show && Array.isArray(show['genres'])
                  ? (show['genres'] as unknown[])
                      .filter((entry) => typeof entry === 'string' && entry.trim().length > 0)
                      .join(', ')
                  : '';

              const jobLabel = normalizeTextValue(media ? media['job_label'] : null);

              return (
                <>
                  {showImageUrl || episodeImageUrl ? (
                    <div className="tv-metadata-media" aria-label="TV images">
                      {showImageUrl ? (
                        <a
                          href={showImageLink ?? showImageUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="tv-metadata-media__poster"
                        >
                          <img
                            src={showImageUrl}
                            alt={showName ? `${showName} poster` : 'Show poster'}
                            loading="lazy"
                            decoding="async"
                          />
                        </a>
                      ) : null}
                      {episodeImageUrl ? (
                        <a
                          href={episodeImageLink ?? episodeImageUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="tv-metadata-media__still"
                        >
                          <img
                            src={episodeImageUrl}
                            alt={episodeName ? `${episodeName} still` : 'Episode still'}
                            loading="lazy"
                            decoding="async"
                          />
                        </a>
                      ) : null}
                    </div>
                  ) : null}
                  <dl className="metadata-grid">
                    <div className="metadata-grid__row">
                      <dt>Subtitle</dt>
                      <dd>{metadataPreview.source_name ?? metadataSourceName}</dd>
                    </div>
                    {metadataPreview.parsed ? (
                      <div className="metadata-grid__row">
                        <dt>Parsed</dt>
                        <dd>
                          {metadataPreview.parsed.series}{' '}
                          {formatEpisodeCode(metadataPreview.parsed.season, metadataPreview.parsed.episode) ?? ''}
                        </dd>
                      </div>
                    ) : null}
                    {showName ? (
                      <div className="metadata-grid__row">
                        <dt>Show</dt>
                        <dd>{showName}</dd>
                      </div>
                    ) : null}
                    {episodeCode || episodeName ? (
                      <div className="metadata-grid__row">
                        <dt>Episode</dt>
                        <dd>{episodeCode ? `${episodeCode}${episodeName ? ` — ${episodeName}` : ''}` : episodeName}</dd>
                      </div>
                    ) : null}
                    {airdate ? (
                      <div className="metadata-grid__row">
                        <dt>Airdate</dt>
                        <dd>{airdate}</dd>
                      </div>
                    ) : null}
                    {networkName ? (
                      <div className="metadata-grid__row">
                        <dt>Network</dt>
                        <dd>{networkName}</dd>
                      </div>
                    ) : null}
                    {episodeUrl ? (
                      <div className="metadata-grid__row">
                        <dt>TVMaze</dt>
                        <dd>
                          <a href={episodeUrl} target="_blank" rel="noopener noreferrer">
                            Open episode page
                          </a>
                        </dd>
                      </div>
                    ) : null}
                    {genresValue ? (
                      <div className="metadata-grid__row">
                        <dt>Genres</dt>
                        <dd>{genresValue}</dd>
                      </div>
                    ) : null}
                  </dl>
                  {errorMessage ? <div className="notice notice--warning">{errorMessage}</div> : null}

                  <fieldset>
                    <legend>Edit metadata</legend>
                    <div className="field-grid">
                      <label>
                        Job label
                        <input
                          type="text"
                          value={jobLabel ?? ''}
                          onChange={(event) => {
                            const value = event.target.value;
                            onUpdateMediaMetadataDraft((draft) => {
                              const trimmed = value.trim();
                              if (trimmed) {
                                draft['job_label'] = trimmed;
                              } else {
                                delete draft['job_label'];
                              }
                            });
                          }}
                        />
                      </label>
                      <label>
                        Show title
                        <input
                          type="text"
                          value={showName ?? ''}
                          onChange={(event) => {
                            const value = event.target.value;
                            onUpdateMediaMetadataSection('show', (section) => {
                              const trimmed = value.trim();
                              if (trimmed) {
                                section['name'] = trimmed;
                              } else {
                                delete section['name'];
                              }
                            });
                          }}
                        />
                      </label>
                      <label>
                        Season
                        <input
                          type="number"
                          min={1}
                          value={seasonNumber ?? ''}
                          onChange={(event) => {
                            const raw = event.target.value;
                            onUpdateMediaMetadataSection('episode', (section) => {
                              if (!raw.trim()) {
                                delete section['season'];
                                return;
                              }
                              const parsed = Number(raw);
                              if (!Number.isFinite(parsed) || parsed <= 0) {
                                return;
                              }
                              section['season'] = Math.trunc(parsed);
                            });
                          }}
                        />
                      </label>
                      <label>
                        Episode
                        <input
                          type="number"
                          min={1}
                          value={episodeNumber ?? ''}
                          onChange={(event) => {
                            const raw = event.target.value;
                            onUpdateMediaMetadataSection('episode', (section) => {
                              if (!raw.trim()) {
                                delete section['number'];
                                return;
                              }
                              const parsed = Number(raw);
                              if (!Number.isFinite(parsed) || parsed <= 0) {
                                return;
                              }
                              section['number'] = Math.trunc(parsed);
                            });
                          }}
                        />
                      </label>
                      <label>
                        Episode title
                        <input
                          type="text"
                          value={episodeName ?? ''}
                          onChange={(event) => {
                            const value = event.target.value;
                            onUpdateMediaMetadataSection('episode', (section) => {
                              const trimmed = value.trim();
                              if (trimmed) {
                                section['name'] = trimmed;
                              } else {
                                delete section['name'];
                              }
                            });
                          }}
                        />
                      </label>
                      <label>
                        Airdate
                        <input
                          type="text"
                          value={airdate ?? ''}
                          onChange={(event) => {
                            const value = event.target.value;
                            onUpdateMediaMetadataSection('episode', (section) => {
                              const trimmed = value.trim();
                              if (trimmed) {
                                section['airdate'] = trimmed;
                              } else {
                                delete section['airdate'];
                              }
                            });
                          }}
                          placeholder="YYYY-MM-DD"
                        />
                      </label>
                    </div>
                  </fieldset>

                  {media ? (
                    <details>
                      <summary>Raw payload</summary>
                      <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(media, null, 2)}</pre>
                    </details>
                  ) : null}
                </>
              );
            })()
          ) : null}
          {!metadataLoading && !metadataPreview ? (
            <p className={styles.status}>Metadata is not available yet.</p>
          ) : null}
        </>
      )}
    </section>
  );
}
