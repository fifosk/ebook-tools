import { useEffect, useState } from 'react';
import {
  fetchSubtitleTvMetadata,
  fetchYoutubeVideoMetadata,
  lookupSubtitleTvMetadata,
  lookupYoutubeVideoMetadata,
} from '../../api/client';
import type { SubtitleTvMetadataResponse, YoutubeVideoMetadataResponse } from '../../api/dtos';
import { coerceRecord, formatEpisodeCode, normalizeTextValue } from './jobProgressUtils';

type JobProgressMediaMetadataProps = {
  jobId: string;
  supportsTvMetadata: boolean;
  supportsYoutubeMetadata: boolean;
  showMetadata: boolean;
  canManage: boolean;
  onReload: () => void;
};

export function JobProgressMediaMetadata({
  jobId,
  supportsTvMetadata,
  supportsYoutubeMetadata,
  showMetadata,
  canManage,
  onReload,
}: JobProgressMediaMetadataProps) {
  const [tvMetadata, setTvMetadata] = useState<SubtitleTvMetadataResponse | null>(null);
  const [tvMetadataLoading, setTvMetadataLoading] = useState(false);
  const [tvMetadataMutating, setTvMetadataMutating] = useState(false);
  const [tvMetadataError, setTvMetadataError] = useState<string | null>(null);
  const [youtubeMetadata, setYoutubeMetadata] = useState<YoutubeVideoMetadataResponse | null>(null);
  const [youtubeMetadataLoading, setYoutubeMetadataLoading] = useState(false);
  const [youtubeMetadataMutating, setYoutubeMetadataMutating] = useState(false);
  const [youtubeMetadataError, setYoutubeMetadataError] = useState<string | null>(null);

  useEffect(() => {
    if (!supportsTvMetadata || !showMetadata) {
      return;
    }
    let cancelled = false;
    setTvMetadataLoading(true);
    setTvMetadataError(null);
    fetchSubtitleTvMetadata(jobId)
      .then((payload) => {
        if (!cancelled) {
          setTvMetadata(payload);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : 'Unable to load TV metadata.';
          setTvMetadataError(message);
          setTvMetadata(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setTvMetadataLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [supportsTvMetadata, jobId, showMetadata]);

  useEffect(() => {
    if (!supportsYoutubeMetadata || !showMetadata) {
      return;
    }
    let cancelled = false;
    setYoutubeMetadataLoading(true);
    setYoutubeMetadataError(null);
    fetchYoutubeVideoMetadata(jobId)
      .then((payload) => {
        if (!cancelled) {
          setYoutubeMetadata(payload);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : 'Unable to load YouTube metadata.';
          setYoutubeMetadataError(message);
          setYoutubeMetadata(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setYoutubeMetadataLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [supportsYoutubeMetadata, jobId, showMetadata]);

  if (!supportsTvMetadata || !showMetadata) {
    return null;
  }

  return (
    <>
      <div className="job-card__section">
        <h4>TV metadata</h4>
        {tvMetadataError ? <div className="alert">{tvMetadataError}</div> : null}
        {tvMetadataLoading ? <p>Loading metadata…</p> : null}
        {!tvMetadataLoading && tvMetadata ? (
          (() => {
            const mediaMetadata = tvMetadata.media_metadata ?? null;
            const media = coerceRecord(mediaMetadata);
            const show = media ? coerceRecord(media['show']) : null;
            const episode = media ? coerceRecord(media['episode']) : null;
            const errorMessage = normalizeTextValue(media ? media['error'] : null);
            const showName = normalizeTextValue(show ? show['name'] : null);
            const episodeName = normalizeTextValue(episode ? episode['name'] : null);
            const seasonNumber = typeof episode?.season === 'number' ? episode.season : null;
            const episodeNumber = typeof episode?.number === 'number' ? episode.number : null;
            const code = formatEpisodeCode(seasonNumber, episodeNumber);
            const airdate = normalizeTextValue(episode ? episode['airdate'] : null);
            const network = show ? coerceRecord(show['network']) : null;
            const networkName = normalizeTextValue(network ? network['name'] : null);
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

            const canLookup = canManage && !tvMetadataMutating;
            const hasLookupResult = Boolean(media && (showName || errorMessage));

            const handleLookup = async (force: boolean) => {
              setTvMetadataMutating(true);
              setTvMetadataError(null);
              try {
                const payload = await lookupSubtitleTvMetadata(jobId, { force });
                setTvMetadata(payload);
                onReload();
              } catch (error) {
                const message = error instanceof Error ? error.message : 'Unable to lookup TV metadata.';
                setTvMetadataError(message);
              } finally {
                setTvMetadataMutating(false);
              }
            };

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
                  {tvMetadata.source_name ? (
                    <div className="metadata-grid__row">
                      <dt>Source</dt>
                      <dd>{tvMetadata.source_name}</dd>
                    </div>
                  ) : null}
                  {tvMetadata.parsed ? (
                    <div className="metadata-grid__row">
                      <dt>Parsed</dt>
                      <dd>
                        {tvMetadata.parsed.series}{' '}
                        {formatEpisodeCode(tvMetadata.parsed.season, tvMetadata.parsed.episode) ?? ''}
                      </dd>
                    </div>
                  ) : null}
                  {showName ? (
                    <div className="metadata-grid__row">
                      <dt>Show</dt>
                      <dd>{showName}</dd>
                    </div>
                  ) : null}
                  {code ? (
                    <div className="metadata-grid__row">
                      <dt>Episode</dt>
                      <dd>
                        {code}
                        {episodeName ? ` — ${episodeName}` : ''}
                      </dd>
                    </div>
                  ) : episodeName ? (
                    <div className="metadata-grid__row">
                      <dt>Episode</dt>
                      <dd>{episodeName}</dd>
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
                </dl>
                {errorMessage ? <div className="notice notice--warning">{errorMessage}</div> : null}
                <div className="job-card__tab-actions">
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => handleLookup(false)}
                    disabled={!canLookup}
                    aria-busy={tvMetadataMutating}
                  >
                    {tvMetadataMutating ? 'Looking up…' : hasLookupResult ? 'Lookup (cached)' : 'Lookup on TVMaze'}
                  </button>
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => handleLookup(true)}
                    disabled={!canLookup}
                    aria-busy={tvMetadataMutating}
                  >
                    Refresh
                  </button>
                </div>
                {media ? (
                  <details className="job-card__details">
                    <summary>Raw payload</summary>
                    <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(media, null, 2)}</pre>
                  </details>
                ) : null}
              </>
            );
          })()
        ) : null}
        {!tvMetadataLoading && !tvMetadata ? <p>Metadata is not available yet.</p> : null}

        {supportsYoutubeMetadata ? (
          <div style={{ marginTop: '1.5rem' }}>
            <h4>YouTube metadata</h4>
            {youtubeMetadataError ? <div className="alert">{youtubeMetadataError}</div> : null}
            {youtubeMetadataLoading ? <p>Loading metadata…</p> : null}
            {!youtubeMetadataLoading && youtubeMetadata ? (
              (() => {
                const youtube = coerceRecord(youtubeMetadata.youtube_metadata ?? null);
                const title = normalizeTextValue(youtube ? youtube['title'] : null);
                const channel =
                  normalizeTextValue(youtube ? youtube['channel'] : null) ??
                  normalizeTextValue(youtube ? youtube['uploader'] : null);
                const webpageUrl = normalizeTextValue(youtube ? youtube['webpage_url'] : null);
                const thumbnailUrl = normalizeTextValue(youtube ? youtube['thumbnail'] : null);
                const summary = normalizeTextValue(youtube ? youtube['summary'] : null);
                const errorMessage = normalizeTextValue(youtube ? youtube['error'] : null);
                const rawPayload = youtube ? youtube['raw_payload'] : null;

                const canLookup = canManage && !youtubeMetadataMutating;

                const handleLookup = async (force: boolean) => {
                  setYoutubeMetadataMutating(true);
                  setYoutubeMetadataError(null);
                  try {
                    const payload = await lookupYoutubeVideoMetadata(jobId, { force });
                    setYoutubeMetadata(payload);
                    onReload();
                  } catch (error) {
                    const message = error instanceof Error ? error.message : 'Unable to lookup YouTube metadata.';
                    setYoutubeMetadataError(message);
                  } finally {
                    setYoutubeMetadataMutating(false);
                  }
                };

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
                      {youtubeMetadata.source_name ? (
                        <div className="metadata-grid__row">
                          <dt>Source</dt>
                          <dd>{youtubeMetadata.source_name}</dd>
                        </div>
                      ) : null}
                      {youtubeMetadata.parsed ? (
                        <div className="metadata-grid__row">
                          <dt>Video id</dt>
                          <dd>{youtubeMetadata.parsed.video_id}</dd>
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
                    </dl>
                    {summary ? <p>{summary}</p> : null}
                    {errorMessage ? <div className="notice notice--warning">{errorMessage}</div> : null}
                    <div className="job-card__tab-actions">
                      <button
                        type="button"
                        className="link-button"
                        onClick={() => handleLookup(false)}
                        disabled={!canLookup}
                        aria-busy={youtubeMetadataMutating}
                      >
                        {youtubeMetadataMutating ? 'Looking up…' : youtube ? 'Lookup (cached)' : 'Lookup via yt-dlp'}
                      </button>
                      <button
                        type="button"
                        className="link-button"
                        onClick={() => handleLookup(true)}
                        disabled={!canLookup}
                        aria-busy={youtubeMetadataMutating}
                      >
                        Refresh
                      </button>
                    </div>
                    {rawPayload ? (
                      <details className="job-card__details">
                        <summary>Raw payload</summary>
                        <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(rawPayload, null, 2)}</pre>
                      </details>
                    ) : null}
                  </>
                );
              })()
            ) : null}
            {!youtubeMetadataLoading && !youtubeMetadata ? <p>Metadata is not available yet.</p> : null}
          </div>
        ) : null}
      </div>
    </>
  );
}
