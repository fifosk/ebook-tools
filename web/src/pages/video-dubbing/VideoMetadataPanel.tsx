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
import { MetadataGrid } from '../../components/metadata/MetadataGrid';
import { MetadataLookupRow } from '../../components/metadata/MetadataLookupRow';
import { RawPayloadDetails } from '../../components/metadata/RawPayloadDetails';

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
              <MetadataLookupRow
                query={metadataLookupSourceName}
                onQueryChange={onMetadataLookupSourceNameChange}
                onLookup={(force) => void onLookupMetadata(metadataLookupSourceName, force)}
                onClear={onClearTvMetadata}
                isLoading={metadataLoading}
                placeholder="Filename containing series/episode info"
                inputLabel="Lookup filename"
                hasResult={!!metadataPreview}
                disabled={!metadataLookupSourceName.trim()}
              />

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

                      <MetadataGrid
                        rows={[
                          { label: 'Source', value: metadataPreview.source_name ?? metadataSourceName },
                          {
                            label: 'Parsed',
                            value: metadataPreview.parsed
                              ? `${metadataPreview.parsed.series} ${formatEpisodeCode(metadataPreview.parsed.season, metadataPreview.parsed.episode) ?? ''}`
                              : undefined,
                          },
                          { label: 'Show', value: showName },
                          {
                            label: 'Episode',
                            value: episodeCode
                              ? `${episodeCode}${episodeName ? ` — ${episodeName}` : ''}`
                              : episodeName,
                          },
                          { label: 'Airdate', value: airdate },
                          { label: 'TVMaze', value: episodeUrl ? 'Open episode page' : undefined, href: episodeUrl ?? undefined },
                          { label: 'Status', value: errorMessage },
                        ]}
                      />

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

                      <RawPayloadDetails payload={media} />
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
              <MetadataLookupRow
                query={youtubeLookupSourceName}
                onQueryChange={onYoutubeLookupSourceNameChange}
                onLookup={(force) => void onLookupYoutubeMetadata(youtubeLookupSourceName, force)}
                onClear={onClearYoutubeMetadata}
                isLoading={youtubeMetadataLoading}
                placeholder="Example: Title [dQw4w9WgXcQ].mp4"
                inputLabel="Lookup video id / filename"
                hasResult={!!youtubeMetadataPreview}
                disabled={!youtubeLookupSourceName.trim()}
              />

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

                      <MetadataGrid
                        rows={[
                          { label: 'Source', value: youtubeMetadataPreview.source_name ?? youtubeLookupSourceName },
                          { label: 'Video id', value: youtubeMetadataPreview.parsed?.video_id },
                          { label: 'Title', value: title },
                          { label: 'Channel', value: channel },
                          { label: 'Duration', value: duration },
                          { label: 'Uploaded', value: uploaded },
                          { label: 'Views', value: views ? `${views}${likes ? ` · 👍 ${likes}` : ''}` : undefined },
                          { label: 'Link', value: webpageUrl ? 'Open on YouTube' : undefined, href: webpageUrl ?? undefined },
                          { label: 'Status', value: errorMessage },
                        ]}
                      />

                      {summary ? <p className={styles.status}>{summary}</p> : null}
                      {description ? (
                        <details>
                          <summary>Description</summary>
                          <pre style={{ whiteSpace: 'pre-wrap' }}>{description}</pre>
                        </details>
                      ) : null}
                      <RawPayloadDetails payload={rawPayload} />
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
