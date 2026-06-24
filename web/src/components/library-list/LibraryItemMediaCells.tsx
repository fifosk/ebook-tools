import type { MouseEvent } from 'react';
import type { LibraryItem } from '../../api/dtos';
import JobTypeGlyphBadge from '../JobTypeGlyphBadge';
import { extractLibraryBookMetadata, resolveLibraryCoverUrl } from '../../utils/libraryMetadata';
import { extractJobType, getJobTypeGlyph, isTvSeriesMetadata } from '../../utils/jobGlyphs';
import {
  extractTvMediaMetadata,
  extractYoutubeVideoMetadata,
  resolveBookSummary,
  resolveSubtitleEpisodeParts,
  resolveSubtitleGenres,
  resolveSubtitleShowName,
  resolveSubtitleSummary,
  resolveTvImage,
  resolveVideoSourcePill,
  resolveYoutubeChannel,
  resolveYoutubeSummary,
  resolveYoutubeThumbnail,
  resolveYoutubeTitle,
  videoSourceBadgeFromLabel
} from './libraryListMediaUtils';
import { resolveAuthor, resolveGenre, resolveTitle } from './libraryListUtils';
import styles from '../LibraryList.module.css';

type LibraryItemMediaCellProps = {
  item: LibraryItem;
  onOpen: () => void;
  disabled: boolean;
};

function handleMediaOpenClick(event: MouseEvent<HTMLButtonElement>, onOpen: () => void) {
  event.stopPropagation();
  onOpen();
}

function resolveJobType(item: LibraryItem): string {
  return extractJobType(item.metadata) ?? 'pipeline';
}

export function LibraryJobTypeGlyph({ item }: { item: LibraryItem }) {
  const jobType = resolveJobType(item);
  const tvMetadata = extractTvMediaMetadata(item);
  const glyph = getJobTypeGlyph(jobType, { isTvSeries: isTvSeriesMetadata(tvMetadata) });
  return (
    <JobTypeGlyphBadge glyph={glyph} className={styles.jobGlyph} />
  );
}

export function LibraryBookCell({ item, onOpen, disabled }: LibraryItemMediaCellProps) {
  const title = resolveTitle(item);
  const author = resolveAuthor(item);
  const genre = resolveGenre(item);
  const summary = resolveBookSummary(item);
  const mediaMetadata = extractLibraryBookMetadata(item);
  const coverUrl = resolveLibraryCoverUrl(item, mediaMetadata);
  return (
    <div className={styles.bookCell}>
      <button
        type="button"
        className={styles.mediaOpenButton}
        onClick={(event) => handleMediaOpenClick(event, onOpen)}
        disabled={disabled}
        aria-label={`Play ${title}`}
        title="Play"
      >
        {coverUrl ? (
          <img
            src={coverUrl}
            alt={`Cover for ${title}`}
            className={styles.bookCover}
            loading="lazy"
          />
        ) : (
          <div className={styles.bookCoverPlaceholder} aria-hidden="true" />
        )}
      </button>
      <div className={styles.bookText}>
        <div className={styles.bookTitleRow}>{title}</div>
        <div className={styles.bookMetaRow}>
          <span className={styles.bookAuthor}>{author}</span>
          <span className={styles.genrePill}>{genre}</span>
        </div>
        {summary ? <div className={styles.bookSummary}>{summary}</div> : null}
      </div>
    </div>
  );
}

export function LibrarySubtitleCell({ item, onOpen, disabled }: LibraryItemMediaCellProps) {
  const tvMetadata = extractTvMediaMetadata(item);
  const showName = resolveSubtitleShowName(item, tvMetadata);
  const { code, title, airdate } = resolveSubtitleEpisodeParts(item, tvMetadata);
  const summary = resolveSubtitleSummary(tvMetadata);
  const genres = resolveSubtitleGenres(item, tvMetadata);
  const episodeImageUrl = resolveTvImage(item.jobId, tvMetadata, 'episode');
  const showImageUrl = resolveTvImage(item.jobId, tvMetadata, 'show');

  return (
    <div className={styles.subtitleCell}>
      <button
        type="button"
        className={styles.mediaOpenButton}
        onClick={(event) => handleMediaOpenClick(event, onOpen)}
        disabled={disabled}
        aria-label={`Play ${showName}`}
        title="Play"
      >
        <div className={styles.subtitleArt}>
          {episodeImageUrl ? (
            <img
              src={episodeImageUrl}
              alt={`Episode image for ${showName}`}
              className={styles.subtitleEpisodeImage}
              loading="lazy"
            />
          ) : (
            <div className={styles.subtitleEpisodePlaceholder} aria-hidden="true" />
          )}
          {showImageUrl ? (
            <img
              src={showImageUrl}
              alt={`Show cover for ${showName}`}
              className={styles.subtitleShowImage}
              loading="lazy"
            />
          ) : null}
        </div>
      </button>
      <div className={styles.subtitleText}>
        <div className={styles.subtitleShowRow}>{showName}</div>
        <div className={styles.subtitleEpisodeRow}>
          {code ? <span className={styles.subtitleEpisodeCode}>{code}</span> : null}
          {title ? <span className={styles.subtitleEpisodeTitle}>{title}</span> : null}
          {airdate ? <span className={styles.subtitleAirdate}>{airdate}</span> : null}
        </div>
        {genres.length > 0 ? (
          <div className={styles.subtitleGenres}>
            {genres.map((genre) => (
              <span key={genre} className={styles.genrePill}>
                {genre}
              </span>
            ))}
          </div>
        ) : null}
        {summary ? <div className={styles.subtitleSummary}>{summary}</div> : null}
      </div>
    </div>
  );
}

export function LibraryVideoCell({ item, onOpen, disabled }: LibraryItemMediaCellProps) {
  const tvMetadata = extractTvMediaMetadata(item);
  const youtubeMetadata = extractYoutubeVideoMetadata(tvMetadata);
  const showName = resolveSubtitleShowName(item, tvMetadata);
  const youtubeTitle = resolveYoutubeTitle(youtubeMetadata);
  const youtubeChannel = resolveYoutubeChannel(youtubeMetadata);
  const primaryTitle = youtubeTitle ?? showName;
  const { code, title, airdate } = resolveSubtitleEpisodeParts(item, tvMetadata);
  const summary = resolveSubtitleSummary(tvMetadata) ?? resolveYoutubeSummary(youtubeMetadata);
  const genres = resolveSubtitleGenres(item, tvMetadata);
  const episodeImageUrl = resolveTvImage(item.jobId, tvMetadata, 'episode');
  const showImageUrl = resolveTvImage(item.jobId, tvMetadata, 'show');
  const youtubeThumbnail = resolveYoutubeThumbnail(item.jobId, youtubeMetadata);
  const thumbnailUrl = episodeImageUrl ?? showImageUrl ?? youtubeThumbnail;
  const sourcePill = resolveVideoSourcePill(item);
  const secondaryTitle = title ?? youtubeChannel;
  const sourceBadge = sourcePill ? videoSourceBadgeFromLabel(sourcePill) : null;

  return (
    <div className={styles.videoCell}>
      <button
        type="button"
        className={styles.mediaOpenButton}
        onClick={(event) => handleMediaOpenClick(event, onOpen)}
        disabled={disabled}
        aria-label={`Play ${primaryTitle}`}
        title="Play"
      >
        <div className={styles.videoArt}>
          {thumbnailUrl ? (
            <img
              src={thumbnailUrl}
              alt={`Video thumbnail for ${primaryTitle}`}
              className={styles.videoThumbnail}
              loading="lazy"
            />
          ) : (
            <div className={styles.videoThumbnailPlaceholder} aria-hidden="true">
              🎬
            </div>
          )}
          {showImageUrl && thumbnailUrl !== showImageUrl ? (
            <img
              src={showImageUrl}
              alt={`Show cover for ${showName}`}
              className={styles.videoShowImage}
              loading="lazy"
            />
          ) : null}
        </div>
      </button>
      <div className={styles.videoText}>
        <div className={styles.videoTitleRow}>
          <span className={styles.videoTitleText}>{primaryTitle}</span>
          <span className={styles.videoTitleMeta}>
            {sourceBadge ? (
              <span
                className={`${styles.pill} ${styles.pillMeta} ${styles.pillSource}`}
                title={sourceBadge.title}
              >
                <span aria-hidden="true">{sourceBadge.icon}</span>
                <span>{sourceBadge.label}</span>
              </span>
            ) : null}
            <span className={`${styles.pill} ${styles.pillMeta} ${styles.pillDub}`} title="Dubbed video">
              <span aria-hidden="true">🎙️</span>
              <span>Dub</span>
            </span>
          </span>
        </div>
        <div className={styles.videoMetaRow}>
          {code ? <span className={styles.videoEpisodeCode}>{code}</span> : null}
          {secondaryTitle ? <span className={styles.videoEpisodeTitle}>{secondaryTitle}</span> : null}
          {airdate ? <span className={styles.videoAirdate}>{airdate}</span> : null}
        </div>
        {genres.length > 0 ? (
          <div className={styles.videoGenres}>
            {genres.map((genre) => (
              <span key={genre} className={styles.genrePill}>
                {genre}
              </span>
            ))}
          </div>
        ) : null}
        {summary ? <div className={styles.videoSummary}>{summary}</div> : null}
      </div>
    </div>
  );
}
