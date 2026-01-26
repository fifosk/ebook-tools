import type { SubtitleTvMetadataPreviewResponse, YoutubeVideoMetadataPreviewResponse } from '../../api/dtos';
import type { VideoMetadataSection } from './videoDubbingTypes';
import {
  coerceRecord,
  formatCount,
  formatDurationSeconds,
  formatEpisodeCode,
  normalizeTextValue
} from './videoDubbingUtils';
import styles from '../VideoDubbingPage.module.css';

type VideoMetadataPanelProps = {
  metadataSourceName: string;
  metadataSection: VideoMetadataSection;
  metadataLookupSourceName: string;
  metadataPreview: SubtitleTvMetadataPreviewResponse | null;
  metadataLoading: boolean;
  metadataError: string | null;
  youtubeLookupSourceName: string;
  youtubeMetadataPreview: YoutubeVideoMetadataPreviewResponse | null;
  youtubeMetadataLoading: boolean;
  youtubeMetadataError: string | null;
  mediaMetadataDraft: Record<string, unknown> | null;
  onMetadataSectionChange: (section: VideoMetadataSection) => void;
  onMetadataLookupSourceNameChange: (value: string) => void;
  onYoutubeLookupSourceNameChange: (value: string) => void;
  onLookupMetadata: (sourceName: string, force: boolean) => void;
  onLookupYoutubeMetadata: (sourceName: string, force: boolean) => void;
  onClearTvMetadata: () => void;
  onClearYoutubeMetadata: () => void;
  onUpdateMediaMetadataDraft: (updater: (draft: Record<string, unknown>) => void) => void;
  onUpdateMediaMetadataSection: (sectionKey: string, updater: (section: Record<string, unknown>) => void) => void;
};

export default function VideoMetadataPanel({
  metadataSourceName,
  metadataSection,
  metadataLookupSourceName,
  metadataPreview,
  metadataLoading,
  metadataError,
  youtubeLookupSourceName,
  youtubeMetadataPreview,
  youtubeMetadataLoading,
  youtubeMetadataError,
  mediaMetadataDraft,
  onMetadataSectionChange,
  onMetadataLookupSourceNameChange,
  onYoutubeLookupSourceNameChange,
  onLookupMetadata,
  onLookupYoutubeMetadata,
  onClearTvMetadata,
  onClearYoutubeMetadata,
  onUpdateMediaMetadataDraft,
  onUpdateMediaMetadataSection
}: VideoMetadataPanelProps) {
  return (
    <section className={styles.card}>
      <div className={styles.cardHeader}>
        <div>
          <h2 className={styles.cardTitle}>Metadata loader</h2>
          <p className={styles.cardHint}>
            {metadataSection === 'tv'
              ? 'Load TV episode metadata from TVMaze (no API key) and edit it before submitting the job.'
              : 'Load YouTube video metadata via yt-dlp (no API key) using the video id in brackets.'}
          </p>
        </div>
        <div className={styles.tabs} role="tablist" aria-label="Metadata sections">
          <button
            type="button"
            role="tab"
            className={`${styles.tabButton} ${metadataSection === 'tv' ? styles.tabButtonActive : ''}`}
            aria-selected={metadataSection === 'tv'}
            onClick={() => onMetadataSectionChange('tv')}
          >
            TVMaze
          </button>
          <button
            type="button"
            role="tab"
            className={`${styles.tabButton} ${metadataSection === 'youtube' ? styles.tabButtonActive : ''}`}
            aria-selected={metadataSection === 'youtube'}
            onClick={() => onMetadataSectionChange('youtube')}
          >
            YouTube
          </button>
        </div>
      </div>

      {!metadataSourceName ? (
        <p className={styles.status}>Select a video/subtitle to load metadata.</p>
      ) : (
        <>
          {metadataSection === 'tv' ? (
            <>
              {metadataError ? <div className="alert" role="alert">{metadataError}</div> : null}
              <div className={styles.controlRow}>
                <label style={{ minWidth: 'min(32rem, 100%)' }}>
                  Lookup filename
                  <input
                    type="text"
                    className={styles.input}
                    value={metadataLookupSourceName}
                    onChange={(event) => onMetadataLookupSourceNameChange(event.target.value)}
                  />
                </label>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={(e) => void onLookupMetadata(metadataLookupSourceName, e.shiftKey)}
                  disabled={!metadataLookupSourceName.trim() || metadataLoading}
                  aria-busy={metadataLoading}
                  title="Lookup TV metadata from TMDB/OMDb/TVMaze. Hold Shift to force refresh."
                >
                  {metadataLoading ? 'Looking up…' : 'Lookup'}
                </button>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={onClearTvMetadata}
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
                  const episodeUrl = normalizeTextValue(episode ? episode['url'] : null);
                  const jobLabel = normalizeTextValue(media ? media['job_label'] : null);

                  // External IDs for direct lookup
                  const tmdbId = typeof show?.tmdb_id === 'number' ? show.tmdb_id : typeof media?.tmdb_id === 'number' ? media.tmdb_id : null;
                  const imdbId = normalizeTextValue(show ? show['imdb_id'] : null) ?? normalizeTextValue(media ? media['imdb_id'] : null);

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
                          <dt>Source</dt>
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
                            <dd>
                              {episodeCode ? `${episodeCode}${episodeName ? ` — ${episodeName}` : ''}` : episodeName}
                            </dd>
                          </div>
                        ) : null}
                        {airdate ? (
                          <div className="metadata-grid__row">
                            <dt>Airdate</dt>
                            <dd>{airdate}</dd>
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
                        {errorMessage ? (
                          <div className="metadata-grid__row">
                            <dt>Status</dt>
                            <dd>{errorMessage}</dd>
                          </div>
                        ) : null}
                      </dl>

                      <fieldset className="metadata-fieldset">
                        <legend>Edit metadata</legend>
                        <div className="metadata-fieldset__fields">
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
                            Show
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
                          <label>
                            TMDB ID
                            <input
                              type="number"
                              min={1}
                              value={tmdbId ?? ''}
                              onChange={(event) => {
                                const raw = event.target.value;
                                onUpdateMediaMetadataSection('show', (section) => {
                                  if (!raw.trim()) {
                                    delete section['tmdb_id'];
                                    return;
                                  }
                                  const parsed = Number(raw);
                                  if (!Number.isFinite(parsed) || parsed <= 0) {
                                    return;
                                  }
                                  section['tmdb_id'] = Math.trunc(parsed);
                                });
                              }}
                              placeholder="e.g. 1396 for Breaking Bad"
                            />
                          </label>
                          <label>
                            IMDb ID
                            <input
                              type="text"
                              value={imdbId ?? ''}
                              onChange={(event) => {
                                const value = event.target.value;
                                onUpdateMediaMetadataSection('show', (section) => {
                                  const trimmed = value.trim();
                                  if (trimmed) {
                                    section['imdb_id'] = trimmed;
                                  } else {
                                    delete section['imdb_id'];
                                  }
                                });
                              }}
                              placeholder="e.g. tt0903747 for Breaking Bad"
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

              {!metadataLoading && !metadataPreview ? <p className={styles.status}>Metadata is not available yet.</p> : null}
            </>
          ) : null}

          {metadataSection === 'youtube' ? (
            <>
              {youtubeMetadataError ? <div className="alert" role="alert">{youtubeMetadataError}</div> : null}
              <div className={styles.controlRow}>
                <label style={{ minWidth: 'min(32rem, 100%)' }}>
                  Lookup video id / filename
                  <input
                    type="text"
                    className={styles.input}
                    value={youtubeLookupSourceName}
                    onChange={(event) => onYoutubeLookupSourceNameChange(event.target.value)}
                    placeholder="Example: Title [dQw4w9WgXcQ].mp4"
                  />
                </label>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={(e) => void onLookupYoutubeMetadata(youtubeLookupSourceName, e.shiftKey)}
                  disabled={!youtubeLookupSourceName.trim() || youtubeMetadataLoading}
                  aria-busy={youtubeMetadataLoading}
                  title="Lookup YouTube metadata via yt-dlp. Hold Shift to force refresh."
                >
                  {youtubeMetadataLoading ? 'Looking up…' : 'Lookup'}
                </button>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={onClearYoutubeMetadata}
                  disabled={youtubeMetadataLoading}
                >
                  Clear
                </button>
              </div>

              {youtubeMetadataLoading ? <p className={styles.status}>Loading metadata…</p> : null}
              {!youtubeMetadataLoading && youtubeMetadataPreview ? (
                (() => {
                  const youtube = mediaMetadataDraft ? coerceRecord(mediaMetadataDraft['youtube']) : null;
                  const title = normalizeTextValue(youtube ? youtube['title'] : null);
                  const channel =
                    normalizeTextValue(youtube ? youtube['channel'] : null) ??
                    normalizeTextValue(youtube ? youtube['uploader'] : null);
                  const webpageUrl = normalizeTextValue(youtube ? youtube['webpage_url'] : null);
                  const thumbnailUrl = normalizeTextValue(youtube ? youtube['thumbnail'] : null);
                  const summary = normalizeTextValue(youtube ? youtube['summary'] : null);
                  const description = normalizeTextValue(youtube ? youtube['description'] : null);
                  const views = formatCount(youtube ? youtube['view_count'] : null);
                  const likes = formatCount(youtube ? youtube['like_count'] : null);
                  const uploaded = normalizeTextValue(youtube ? youtube['upload_date'] : null);
                  const duration = formatDurationSeconds(youtube ? youtube['duration_seconds'] : null);
                  const rawErrorMessage = normalizeTextValue(youtube ? youtube['error'] : null);
                  // Don't show the "no video ID" error - it's expected for TV content without YouTube IDs
                  const isExpectedNoIdError = rawErrorMessage?.includes('Unable to locate a YouTube video id');
                  const errorMessage = isExpectedNoIdError ? null : rawErrorMessage;
                  const rawPayload = youtube ? youtube['raw_payload'] : null;

                  return (
                    <>
                      {thumbnailUrl ? (
                        <div className="tv-metadata-media" aria-label="YouTube thumbnail">
                          <a
                            href={webpageUrl ?? thumbnailUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="tv-metadata-media__still"
                          >
                            <img
                              src={thumbnailUrl}
                              alt={title ? `${title} thumbnail` : 'YouTube thumbnail'}
                              loading="lazy"
                              decoding="async"
                            />
                          </a>
                        </div>
                      ) : null}

                      <dl className="metadata-grid">
                        <div className="metadata-grid__row">
                          <dt>Source</dt>
                          <dd>{youtubeMetadataPreview.source_name ?? youtubeLookupSourceName}</dd>
                        </div>
                        {youtubeMetadataPreview.parsed ? (
                          <div className="metadata-grid__row">
                            <dt>Video id</dt>
                            <dd>{youtubeMetadataPreview.parsed.video_id}</dd>
                          </div>
                        ) : null}
                        {title ? (
                          <div className="metadata-grid__row">
                            <dt>Title</dt>
                            <dd>{title}</dd>
                          </div>
                        ) : null}
                        {channel ? (
                          <div className="metadata-grid__row">
                            <dt>Channel</dt>
                            <dd>{channel}</dd>
                          </div>
                        ) : null}
                        {duration ? (
                          <div className="metadata-grid__row">
                            <dt>Duration</dt>
                            <dd>{duration}</dd>
                          </div>
                        ) : null}
                        {uploaded ? (
                          <div className="metadata-grid__row">
                            <dt>Uploaded</dt>
                            <dd>{uploaded}</dd>
                          </div>
                        ) : null}
                        {views ? (
                          <div className="metadata-grid__row">
                            <dt>Views</dt>
                            <dd>{views}{likes ? ` · 👍 ${likes}` : ''}</dd>
                          </div>
                        ) : null}
                        {webpageUrl ? (
                          <div className="metadata-grid__row">
                            <dt>Link</dt>
                            <dd>
                              <a href={webpageUrl} target="_blank" rel="noopener noreferrer">
                                Open on YouTube
                              </a>
                            </dd>
                          </div>
                        ) : null}
                        {errorMessage ? (
                          <div className="metadata-grid__row">
                            <dt>Status</dt>
                            <dd>{errorMessage}</dd>
                          </div>
                        ) : null}
                      </dl>

                      {summary ? <p className={styles.status}>{summary}</p> : null}
                      {description ? (
                        <details>
                          <summary>Description</summary>
                          <pre style={{ whiteSpace: 'pre-wrap' }}>{description}</pre>
                        </details>
                      ) : null}
                      {rawPayload ? (
                        <details>
                          <summary>Raw payload</summary>
                          <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(rawPayload, null, 2)}</pre>
                        </details>
                      ) : null}
                    </>
                  );
                })()
              ) : null}

              {!youtubeMetadataLoading && !youtubeMetadataPreview ? (
                <p className={styles.status}>Metadata is not available yet.</p>
              ) : null}
            </>
          ) : null}
        </>
      )}
    </section>
  );
}
