import type { SubtitleTvMetadataPreviewResponse } from '../../api/dtos';
import { MetadataGrid } from '../../components/metadata/MetadataGrid';
import { RawPayloadDetails } from '../../components/metadata/RawPayloadDetails';
import {
  coerceRecord,
  formatEpisodeCode,
  normalizeTextValue
} from './videoDubbingUtils';

type VideoTvMetadataPreviewProps = {
  metadataSourceName: string;
  metadataPreview: SubtitleTvMetadataPreviewResponse;
  mediaMetadataDraft: Record<string, unknown> | null;
  onUpdateMediaMetadataDraft: (updater: (draft: Record<string, unknown>) => void) => void;
  onUpdateMediaMetadataSection: (sectionKey: string, updater: (section: Record<string, unknown>) => void) => void;
};

export default function VideoTvMetadataPreview({
  metadataSourceName,
  metadataPreview,
  mediaMetadataDraft,
  onUpdateMediaMetadataDraft,
  onUpdateMediaMetadataSection
}: VideoTvMetadataPreviewProps) {
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

  const tmdbId =
    typeof show?.tmdb_id === 'number'
      ? show.tmdb_id
      : typeof media?.tmdb_id === 'number'
        ? media.tmdb_id
        : null;
  const imdbId = normalizeTextValue(show ? show['imdb_id'] : null)
    ?? normalizeTextValue(media ? media['imdb_id'] : null);

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
}
