import { useEffect, useState } from 'react';
import {
  clearTvMetadataCache,
  clearYoutubeMetadataCache,
  fetchSubtitleTvMetadata,
  fetchYoutubeVideoMetadata,
  lookupSubtitleTvMetadata,
  lookupYoutubeVideoMetadata,
} from '../../api/client';
import type { SubtitleTvMetadataResponse, YoutubeVideoMetadataResponse } from '../../api/dtos';
import { coerceRecord, formatEpisodeCode, formatGenreList, normalizeTextValue } from './jobProgressUtils';
import { MetadataGrid, type MetadataRow } from '../metadata/MetadataGrid';
import { MetadataActionButtons } from '../metadata/MetadataActionButtons';
import { RawPayloadDetails } from '../metadata/RawPayloadDetails';

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

  // Determine actual content kind from loaded metadata
  const tvMedia = tvMetadata?.media_metadata ? coerceRecord(tvMetadata.media_metadata) : null;
  const tvKind = normalizeTextValue(tvMedia ? tvMedia['kind'] : null);
  const hasTvShowData = Boolean(tvMedia && coerceRecord(tvMedia['show']));
  const isTvContent = tvKind === 'tv_episode' || tvKind === 'tv_series' || hasTvShowData;

  const youtubeData = youtubeMetadata?.youtube_metadata ? coerceRecord(youtubeMetadata.youtube_metadata) : null;
  const hasYoutubeTitle = Boolean(normalizeTextValue(youtubeData ? youtubeData['title'] : null));
  const hasYoutubeVideoId = Boolean(youtubeMetadata?.parsed?.video_id);
  const isYoutubeContent = hasYoutubeTitle || hasYoutubeVideoId;

  // Only show YouTube section if it's actually YouTube content (not TV with failed YouTube lookup)
  const shouldShowYoutubeSection = supportsYoutubeMetadata && !isTvContent && (isYoutubeContent || youtubeMetadataLoading);

  return (
    <>
      <div className="job-card__section">
        <h4>{isTvContent ? 'TV metadata' : 'Media metadata'}</h4>
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
            const showGenres = formatGenreList(show ? show['genres'] : null);

            const canLookup = canManage && !tvMetadataMutating;
            const hasLookupResult = Boolean(media && (showName || errorMessage));

            const handleClear = async () => {
              setTvMetadataMutating(true);
              setTvMetadataError(null);
              try {
                // Clear frontend state
                setTvMetadata(null);
                // Clear backend cache using source_name as query
                const query = tvMetadata.source_name;
                if (query) {
                  await clearTvMetadataCache(query);
                }
              } catch {
                // Ignore cache clear failures - frontend state is already cleared
              } finally {
                setTvMetadataMutating(false);
              }
            };

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
                <MetadataGrid
                  rows={[
                    { label: 'Source', value: tvMetadata.source_name },
                    {
                      label: 'Parsed',
                      value: tvMetadata.parsed
                        ? `${tvMetadata.parsed.series} ${formatEpisodeCode(tvMetadata.parsed.season, tvMetadata.parsed.episode) ?? ''}`
                        : undefined,
                    },
                    { label: 'Show', value: showName },
                    {
                      label: 'Episode',
                      value: code
                        ? `${code}${episodeName ? ` — ${episodeName}` : ''}`
                        : episodeName,
                    },
                    { label: 'Airdate', value: airdate },
                    { label: 'Network', value: networkName },
                    { label: 'Genres', value: showGenres },
                    { label: 'TVMaze', value: episodeUrl ? 'Open episode page' : undefined, href: episodeUrl ?? undefined },
                  ]}
                />
                {errorMessage ? <div className="notice notice--warning">{errorMessage}</div> : null}
                <MetadataActionButtons
                  onLookup={handleLookup}
                  onClear={handleClear}
                  isLoading={tvMetadataMutating}
                  hasResult={hasLookupResult}
                  disabled={!canManage}
                />
                <RawPayloadDetails payload={media} />
              </>
            );
          })()
        ) : null}
        {!tvMetadataLoading && !tvMetadata ? <p>Metadata is not available yet.</p> : null}

        {shouldShowYoutubeSection ? (
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
                const categories = formatGenreList(youtube ? youtube['categories'] : null);
                const summary = normalizeTextValue(youtube ? youtube['summary'] : null);
                const rawErrorMessage = normalizeTextValue(youtube ? youtube['error'] : null);
                // Don't show the "no video ID" error - it's expected for TV content without YouTube IDs
                const isExpectedNoIdError = rawErrorMessage?.includes('Unable to locate a YouTube video id');
                const errorMessage = isExpectedNoIdError ? null : rawErrorMessage;
                const rawPayload = youtube ? youtube['raw_payload'] : null;

                const canLookup = canManage && !youtubeMetadataMutating;
                const hasYoutubeLookupResult = Boolean(youtube && (title || errorMessage));

                const handleClear = async () => {
                  setYoutubeMetadataMutating(true);
                  setYoutubeMetadataError(null);
                  try {
                    // Clear frontend state
                    setYoutubeMetadata(null);
                    // Clear backend cache using source_name as query
                    const query = youtubeMetadata.source_name;
                    if (query) {
                      await clearYoutubeMetadataCache(query);
                    }
                  } catch {
                    // Ignore cache clear failures - frontend state is already cleared
                  } finally {
                    setYoutubeMetadataMutating(false);
                  }
                };

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
                    <MetadataGrid
                      rows={[
                        { label: 'Source', value: youtubeMetadata.source_name },
                        { label: 'Video id', value: youtubeMetadata.parsed?.video_id },
                        { label: 'Title', value: title },
                        { label: 'Channel', value: channel },
                        { label: 'Categories', value: categories },
                        { label: 'Link', value: webpageUrl ? 'Open on YouTube' : undefined, href: webpageUrl ?? undefined },
                      ]}
                    />
                    {summary ? <p>{summary}</p> : null}
                    {errorMessage ? <div className="notice notice--warning">{errorMessage}</div> : null}
                    <MetadataActionButtons
                      onLookup={handleLookup}
                      onClear={handleClear}
                      isLoading={youtubeMetadataMutating}
                      hasResult={hasYoutubeLookupResult}
                      disabled={!canManage}
                    />
                    <RawPayloadDetails payload={rawPayload} />
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
