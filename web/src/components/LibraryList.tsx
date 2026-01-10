import { useMemo } from 'react';
import type { LibraryItem, LibraryViewMode } from '../api/dtos';
import { appendAccessToken, resolveLibraryMediaUrl } from '../api/client';
import { DEFAULT_LANGUAGE_FLAG, resolveLanguageFlag } from '../constants/languageCodes';
import { extractJobType, getJobTypeGlyph } from '../utils/jobGlyphs';
import { normalizeLanguageLabel } from '../utils/languages';
import { extractLibraryBookMetadata, resolveLibraryCoverUrl } from '../utils/libraryMetadata';
import { getStatusGlyph } from '../utils/status';
import EmojiIcon from './EmojiIcon';
import styles from './LibraryList.module.css';

type Props = {
  items: LibraryItem[];
  view: LibraryViewMode;
  onSelect?: (item: LibraryItem) => void;
  onOpen: (item: LibraryItem) => void;
  onExport?: (item: LibraryItem) => void;
  onRemove: (item: LibraryItem) => void;
  onEditMetadata: (item: LibraryItem) => void;
  resolvePermissions?: (item: LibraryItem) => LibraryItemPermissions;
  selectedJobId?: string | null;
  mutating?: Record<string, boolean>;
  variant?: 'card' | 'embedded';
};

type LibraryItemPermissions = {
  canView: boolean;
  canEdit: boolean;
  canExport: boolean;
};

type AuthorGroup = {
  author: string;
  books: Array<{
    bookTitle: string;
    languages: Array<{ language: string; items: LibraryItem[] }>;
  }>;
};

type GenreGroup = {
  genre: string;
  authors: Array<{
    author: string;
    books: Array<{ bookTitle: string; items: LibraryItem[] }>;
  }>;
};

type LanguageGroup = {
  language: string;
  authors: Array<{
    author: string;
    books: Array<{ bookTitle: string; items: LibraryItem[] }>;
  }>;
};

const UNKNOWN_AUTHOR = 'Unknown Author';
const UNKNOWN_CREATOR = 'Unknown Creator';

function renderLanguageLabel(language: string | null | undefined) {
  const label = normalizeLanguageLabel(language) || 'Unknown';
  const flag = resolveLanguageFlag(language ?? label) ?? DEFAULT_LANGUAGE_FLAG;
  return (
    <span className={styles.languageLabel}>
      <EmojiIcon emoji={flag} className={styles.languageFlag} />
      <span>{label}</span>
    </span>
  );
}
const UNTITLED_BOOK = 'Untitled Book';
const UNTITLED_VIDEO = 'Untitled Video';
const UNTITLED_SUBTITLE = 'Untitled Subtitle';
const UNKNOWN_GENRE = 'Unknown Genre';
const SUBTITLE_AUTHOR = 'Subtitles';

type StatusVariant = 'ready' | 'missing';

function normalizeItemType(item: LibraryItem): 'book' | 'video' | 'narrated_subtitle' {
  return (item.itemType ?? 'book') as 'book' | 'video' | 'narrated_subtitle';
}

function isBookItem(item: LibraryItem): boolean {
  return normalizeItemType(item) === 'book';
}

function isSubtitleItem(item: LibraryItem): boolean {
  return normalizeItemType(item) === 'narrated_subtitle';
}

function isVideoItem(item: LibraryItem): boolean {
  return normalizeItemType(item) === 'video';
}

function resolveJobType(item: LibraryItem): string {
  return extractJobType(item.metadata) ?? 'pipeline';
}

function renderJobTypeGlyph(item: LibraryItem) {
  const jobType = resolveJobType(item);
  const glyph = getJobTypeGlyph(jobType);
  return (
    <span className={styles.jobGlyph} title={glyph.label} aria-label={glyph.label}>
      {glyph.icon}
    </span>
  );
}

function resolveTitle(item: LibraryItem): string {
  const base = (item.bookTitle ?? '').trim();
  if (base) {
    return base;
  }
  switch (normalizeItemType(item)) {
    case 'video':
      return UNTITLED_VIDEO;
    case 'narrated_subtitle':
      return UNTITLED_SUBTITLE;
    default:
      return UNTITLED_BOOK;
  }
}

function resolveAuthor(item: LibraryItem): string {
  const base = (item.author ?? '').trim();
  if (base) {
    return base;
  }
  switch (normalizeItemType(item)) {
    case 'video':
      return UNKNOWN_CREATOR;
    case 'narrated_subtitle':
      return SUBTITLE_AUTHOR;
    default:
      return UNKNOWN_AUTHOR;
  }
}

function resolveGenre(item: LibraryItem): string {
  const base = (item.genre ?? '').toString().trim();
  if (base) {
    return base;
  }
  switch (normalizeItemType(item)) {
    case 'video':
      return 'Video';
    case 'narrated_subtitle':
      return 'Subtitles';
    default:
      return UNKNOWN_GENRE;
  }
}

function resolveBookSummary(item: LibraryItem): string | null {
  const bookMetadata = extractLibraryBookMetadata(item);
  if (!bookMetadata) {
    return null;
  }
  const candidate = bookMetadata['book_summary'] ?? bookMetadata['summary'] ?? bookMetadata['description'];
  if (typeof candidate !== 'string') {
    return null;
  }
  const trimmed = candidate.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function renderBookCell(item: LibraryItem, options: { onOpen: () => void; disabled: boolean }) {
  const title = resolveTitle(item);
  const author = resolveAuthor(item);
  const genre = resolveGenre(item);
  const summary = resolveBookSummary(item);
  const bookMetadata = extractLibraryBookMetadata(item);
  const coverUrl = resolveLibraryCoverUrl(item, bookMetadata);
  return (
    <div className={styles.bookCell}>
      <button
        type="button"
        className={styles.mediaOpenButton}
        onClick={(event) => {
          event.stopPropagation();
          options.onOpen();
        }}
        disabled={options.disabled}
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

function readNestedValue(source: unknown, path: string[]): unknown {
  let current: unknown = source;
  for (const key of path) {
    if (!current || typeof current !== 'object') {
      return null;
    }
    current = (current as Record<string, unknown>)[key];
  }
  return current;
}

function resolveLibraryAssetUrl(jobId: string, value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  if (/^[a-z]+:\/\//i.test(trimmed)) {
    return trimmed;
  }
  if (trimmed.startsWith('/api/')) {
    return appendAccessToken(trimmed);
  }
  if (trimmed.startsWith('/')) {
    return trimmed;
  }
  return resolveLibraryMediaUrl(jobId, trimmed);
}

function extractTvMediaMetadata(item: LibraryItem): Record<string, unknown> | null {
  const payload = item.metadata ?? null;
  if (!payload || typeof payload !== 'object') {
    return null;
  }
  const candidate =
    readNestedValue(payload, ['result', 'youtube_dub', 'media_metadata']) ??
    readNestedValue(payload, ['result', 'subtitle', 'metadata', 'media_metadata']) ??
    readNestedValue(payload, ['request', 'media_metadata']) ??
    readNestedValue(payload, ['media_metadata']) ??
    null;
  return candidate && typeof candidate === 'object' ? (candidate as Record<string, unknown>) : null;
}

function resolveVideoSourcePill(item: LibraryItem): string | null {
  const payload = item.metadata ?? null;
  if (!payload || typeof payload !== 'object') {
    return null;
  }
  const raw =
    readNestedValue(payload, ['request', 'source_kind']) ??
    readNestedValue(payload, ['result', 'youtube_dub', 'source_kind']) ??
    readNestedValue(payload, ['source_kind']) ??
    null;
  if (typeof raw !== 'string') {
    return null;
  }
  const normalized = raw.trim().toLowerCase();
  if (!normalized) {
    return null;
  }
  if (normalized === 'youtube') {
    return 'YouTube';
  }
  if (normalized === 'nas_video') {
    return 'NAS';
  }
  return raw.trim();
}

function videoSourceBadgeFromLabel(label: string): { icon: string; label: string; title: string } {
  const normalized = label.trim().toLowerCase();
  if (normalized === 'youtube') {
    return { icon: '📺', label: 'YT', title: 'YouTube download' };
  }
  if (normalized === 'nas') {
    return { icon: '🗃', label: 'NAS', title: 'NAS video' };
  }
  return { icon: '📦', label, title: label };
}

function resolveSubtitleShowName(item: LibraryItem, tvMetadata: Record<string, unknown> | null): string {
  const metadata = item.metadata ?? null;
  if (metadata && typeof metadata === 'object') {
    const seriesTitle = (metadata as Record<string, unknown>)['series_title'];
    if (typeof seriesTitle === 'string' && seriesTitle.trim()) {
      return seriesTitle.trim();
    }
  }
  const show = tvMetadata?.['show'];
  if (show && typeof show === 'object') {
    const name = (show as Record<string, unknown>)['name'];
    if (typeof name === 'string' && name.trim()) {
      return name.trim();
    }
  }
  const author = resolveAuthor(item);
  return author === SUBTITLE_AUTHOR ? UNTITLED_SUBTITLE : author;
}

function resolveSubtitleEpisodeParts(
  item: LibraryItem,
  tvMetadata: Record<string, unknown> | null,
): { code: string | null; title: string | null; airdate: string | null } {
  const metadata = item.metadata ?? null;
  const record = metadata && typeof metadata === 'object' ? (metadata as Record<string, unknown>) : null;
  const explicitCode = record && typeof record['episode_code'] === 'string' ? (record['episode_code'] as string).trim() : '';
  const explicitTitle = record && typeof record['episode_title'] === 'string' ? (record['episode_title'] as string).trim() : '';
  const explicitAirdate = record && typeof record['airdate'] === 'string' ? (record['airdate'] as string).trim() : '';

  const episode = tvMetadata?.['episode'];
  const episodeRecord = episode && typeof episode === 'object' ? (episode as Record<string, unknown>) : null;
  const season = episodeRecord?.['season'];
  const number = episodeRecord?.['number'];
  const computedCode =
    typeof season === 'number' && typeof number === 'number' && season > 0 && number > 0
      ? `S${season.toString().padStart(2, '0')}E${number.toString().padStart(2, '0')}`
      : null;
  const tvTitle = typeof episodeRecord?.['name'] === 'string' ? (episodeRecord['name'] as string).trim() : '';
  const tvAirdate = typeof episodeRecord?.['airdate'] === 'string' ? (episodeRecord['airdate'] as string).trim() : '';

  const code = explicitCode || computedCode || null;
  const title = explicitTitle || tvTitle || null;
  const airdate = explicitAirdate || tvAirdate || null;

  return { code, title, airdate };
}

function resolveSubtitleSummary(tvMetadata: Record<string, unknown> | null): string | null {
  const episode = tvMetadata?.['episode'];
  if (episode && typeof episode === 'object') {
    const summary = (episode as Record<string, unknown>)['summary'];
    if (typeof summary === 'string' && summary.trim()) {
      return summary.trim();
    }
  }
  const show = tvMetadata?.['show'];
  if (show && typeof show === 'object') {
    const summary = (show as Record<string, unknown>)['summary'];
    if (typeof summary === 'string' && summary.trim()) {
      return summary.trim();
    }
  }
  return null;
}

function resolveSubtitleGenres(item: LibraryItem, tvMetadata: Record<string, unknown> | null): string[] {
  const metadata = item.metadata ?? null;
  const record = metadata && typeof metadata === 'object' ? (metadata as Record<string, unknown>) : null;
  const fromMetadata = record?.['series_genres'];
  if (Array.isArray(fromMetadata)) {
    const filtered = fromMetadata.filter((entry) => typeof entry === 'string' && entry.trim()).map((entry) => entry.trim());
    if (filtered.length > 0) {
      return filtered.slice(0, 3);
    }
  }
  const show = tvMetadata?.['show'];
  if (show && typeof show === 'object') {
    const genres = (show as Record<string, unknown>)['genres'];
    if (Array.isArray(genres)) {
      const filtered = genres.filter((entry) => typeof entry === 'string' && entry.trim()).map((entry) => entry.trim());
      return filtered.slice(0, 3);
    }
  }
  return [];
}

function resolveTvImage(
  jobId: string,
  tvMetadata: Record<string, unknown> | null,
  path: 'show' | 'episode',
): string | null {
  const section = tvMetadata?.[path];
  if (!section || typeof section !== 'object') {
    return null;
  }
  const image = (section as Record<string, unknown>)['image'];
  if (!image) {
    return null;
  }
  if (typeof image === 'string') {
    return resolveLibraryAssetUrl(jobId, image);
  }
  if (typeof image === 'object') {
    const record = image as Record<string, unknown>;
    return (
      resolveLibraryAssetUrl(jobId, record['medium']) ??
      resolveLibraryAssetUrl(jobId, record['original']) ??
      null
    );
  }
  return null;
}

function extractYoutubeVideoMetadata(tvMetadata: Record<string, unknown> | null): Record<string, unknown> | null {
  const youtube = tvMetadata?.['youtube'];
  return youtube && typeof youtube === 'object' && !Array.isArray(youtube) ? (youtube as Record<string, unknown>) : null;
}

function resolveYoutubeThumbnail(jobId: string, youtubeMetadata: Record<string, unknown> | null): string | null {
  if (!youtubeMetadata) {
    return null;
  }
  return resolveLibraryAssetUrl(jobId, youtubeMetadata['thumbnail']);
}

function resolveYoutubeTitle(youtubeMetadata: Record<string, unknown> | null): string | null {
  if (!youtubeMetadata) {
    return null;
  }
  const title = youtubeMetadata['title'];
  return typeof title === 'string' && title.trim() ? title.trim() : null;
}

function resolveYoutubeChannel(youtubeMetadata: Record<string, unknown> | null): string | null {
  if (!youtubeMetadata) {
    return null;
  }
  const channel = youtubeMetadata['channel'];
  if (typeof channel === 'string' && channel.trim()) {
    return channel.trim();
  }
  const uploader = youtubeMetadata['uploader'];
  return typeof uploader === 'string' && uploader.trim() ? uploader.trim() : null;
}

function resolveYoutubeSummary(youtubeMetadata: Record<string, unknown> | null): string | null {
  if (!youtubeMetadata) {
    return null;
  }
  const summary = youtubeMetadata['summary'];
  if (typeof summary === 'string' && summary.trim()) {
    return summary.trim();
  }
  const description = youtubeMetadata['description'];
  return typeof description === 'string' && description.trim() ? description.trim() : null;
}

function renderSubtitleCell(item: LibraryItem, options: { onOpen: () => void; disabled: boolean }) {
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
        onClick={(event) => {
          event.stopPropagation();
          options.onOpen();
        }}
        disabled={options.disabled}
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

function renderVideoCell(item: LibraryItem, options: { onOpen: () => void; disabled: boolean }) {
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
        onClick={(event) => {
          event.stopPropagation();
          options.onOpen();
        }}
        disabled={options.disabled}
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

function describeStatus(item: LibraryItem): { label: string; variant?: StatusVariant; glyphKey: string } {
  if (!item.mediaCompleted) {
    return { label: 'Media removed', variant: 'missing', glyphKey: 'cancelled' };
  }
  if (item.status === 'paused') {
    return { label: 'Paused', variant: 'ready', glyphKey: 'paused' };
  }
  return { label: 'Finished', variant: 'ready', glyphKey: 'completed' };
}

function renderStatusBadge(item: LibraryItem) {
  const { label, variant, glyphKey } = describeStatus(item);
  const glyph = getStatusGlyph(glyphKey);
  return (
    <span className={styles.statusBadge} data-variant={variant} title={glyph.label}>
      <span className={styles.statusIcon} aria-hidden="true">
        {glyph.icon}
      </span>
      <span>{label}</span>
    </span>
  );
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return '—';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function buildAuthorGroups(items: LibraryItem[]): AuthorGroup[] {
  const authorMap = new Map<string, Map<string, Map<string, LibraryItem[]>>>();
  items.forEach((item) => {
    const authorKey = resolveAuthor(item);
    const bookKey = resolveTitle(item);
    const languageKey = item.language || 'unknown';

    if (!authorMap.has(authorKey)) {
      authorMap.set(authorKey, new Map());
    }
    const booksMap = authorMap.get(authorKey)!;
    if (!booksMap.has(bookKey)) {
      booksMap.set(bookKey, new Map());
    }
    const languageMap = booksMap.get(bookKey)!;
    if (!languageMap.has(languageKey)) {
      languageMap.set(languageKey, []);
    }
    languageMap.get(languageKey)!.push(item);
  });

  return Array.from(authorMap.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([author, booksMap]) => ({
      author,
      books: Array.from(booksMap.entries())
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([bookTitle, languageMap]) => ({
          bookTitle,
          languages: Array.from(languageMap.entries())
            .sort((a, b) => a[0].localeCompare(b[0]))
            .map(([language, entries]) => ({
              language,
              items: [...entries].sort((left, right) => right.updatedAt.localeCompare(left.updatedAt))
            }))
        }))
    }));
}

function buildGenreGroups(items: LibraryItem[]): GenreGroup[] {
  const genreMap = new Map<string, Map<string, Map<string, LibraryItem[]>>>();
  items.forEach((item) => {
    const genreKey = resolveGenre(item);
    const authorKey = resolveAuthor(item);
    const bookKey = resolveTitle(item);

    if (!genreMap.has(genreKey)) {
      genreMap.set(genreKey, new Map());
    }
    const authorMap = genreMap.get(genreKey)!;
    if (!authorMap.has(authorKey)) {
      authorMap.set(authorKey, new Map());
    }
    const bookMap = authorMap.get(authorKey)!;
    if (!bookMap.has(bookKey)) {
      bookMap.set(bookKey, []);
    }
    bookMap.get(bookKey)!.push(item);
  });

  return Array.from(genreMap.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([genre, authorMap]) => ({
      genre,
      authors: Array.from(authorMap.entries())
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([author, bookMap]) => ({
          author,
          books: Array.from(bookMap.entries())
            .sort((a, b) => a[0].localeCompare(b[0]))
            .map(([bookTitle, entries]) => ({
              bookTitle,
              items: [...entries].sort((left, right) => right.updatedAt.localeCompare(left.updatedAt))
            }))
        }))
    }));
}

function buildLanguageGroups(items: LibraryItem[]): LanguageGroup[] {
  const languageMap = new Map<string, Map<string, Map<string, LibraryItem[]>>>();
  items.forEach((item) => {
    const languageKey = item.language || 'unknown';
    const authorKey = resolveAuthor(item);
    const bookKey = resolveTitle(item);

    if (!languageMap.has(languageKey)) {
      languageMap.set(languageKey, new Map());
    }
    const authorMap = languageMap.get(languageKey)!;
    if (!authorMap.has(authorKey)) {
      authorMap.set(authorKey, new Map());
    }
    const bookMap = authorMap.get(authorKey)!;
    if (!bookMap.has(bookKey)) {
      bookMap.set(bookKey, []);
    }
    bookMap.get(bookKey)!.push(item);
  });

  return Array.from(languageMap.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([language, authorMap]) => ({
      language,
      authors: Array.from(authorMap.entries())
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([author, bookMap]) => ({
          author,
          books: Array.from(bookMap.entries())
            .sort((a, b) => a[0].localeCompare(b[0]))
            .map(([bookTitle, entries]) => ({
              bookTitle,
              items: [...entries].sort((left, right) => right.updatedAt.localeCompare(left.updatedAt))
            }))
        }))
    }));
}

function LibraryList({
  items,
  view,
  onSelect,
  onOpen,
  onExport,
  onRemove,
  onEditMetadata,
  resolvePermissions,
  selectedJobId,
  mutating = {},
  variant = 'card'
}: Props) {
  const authorGroups = useMemo(() => buildAuthorGroups(items), [items]);
  const genreGroups = useMemo(() => buildGenreGroups(items), [items]);
  const languageGroups = useMemo(() => buildLanguageGroups(items), [items]);
  const isBookLayout = useMemo(() => items.length > 0 && items.every((item) => isBookItem(item)), [items]);
  const isSubtitleLayout = useMemo(() => items.length > 0 && items.every((item) => isSubtitleItem(item)), [items]);
  const isVideoLayout = useMemo(() => items.length > 0 && items.every((item) => isVideoItem(item)), [items]);

  const handleSelect = (item: LibraryItem) => {
    if (onSelect) {
      onSelect(item);
    }
  };

  const resolveItemPermissions = (item: LibraryItem): LibraryItemPermissions => {
    if (!resolvePermissions) {
      return { canView: true, canEdit: true, canExport: true };
    }
    const resolved = resolvePermissions(item);
    return {
      canView: resolved.canView,
      canEdit: resolved.canEdit,
      canExport: resolved.canExport
    };
  };

  const renderActions = (item: LibraryItem, permissions: LibraryItemPermissions) => {
    const isExportReady = item.mediaCompleted;
    const exportTitle = isExportReady ? 'Export offline player' : 'Export available after media completes';
    const isMutating = Boolean(mutating[item.jobId]);
    const canView = permissions.canView;
    const canEdit = permissions.canEdit;
    const canExport = permissions.canExport && canView;
    return (
      <div className={styles.actions}>
        <button
          type="button"
          className={styles.actionIconButton}
          onClick={(event) => {
            event.stopPropagation();
            if (canView) {
              onOpen(item);
            }
          }}
          disabled={isMutating || !canView}
          aria-label="Play"
          title="Play"
        >
          <span aria-hidden="true">▶</span>
          <span className="visually-hidden">Play</span>
        </button>
        <button
          type="button"
          className={styles.actionIconButton}
          onClick={(event) => {
            event.stopPropagation();
            if (canEdit) {
              onEditMetadata(item);
            }
          }}
          disabled={isMutating || !canEdit}
          aria-label="Edit"
          title="Edit"
        >
          <span aria-hidden="true">✎</span>
          <span className="visually-hidden">Edit</span>
        </button>
        {onExport ? (
          <button
            type="button"
            className={styles.actionIconButton}
            onClick={(event) => {
              event.stopPropagation();
              if (isExportReady && canExport) {
                onExport(item);
              }
            }}
            disabled={isMutating || !isExportReady || !canExport}
            aria-label="Export offline player"
            title={exportTitle}
          >
            <span aria-hidden="true">📦</span>
            <span className="visually-hidden">Export offline player</span>
          </button>
        ) : null}
        <button
          type="button"
          className={styles.actionIconButton}
          onClick={(event) => {
            event.stopPropagation();
            if (canEdit) {
              onRemove(item);
            }
          }}
          disabled={isMutating || !canEdit}
          aria-label="Delete"
          title="Delete"
          data-variant="danger"
        >
          <span aria-hidden="true">🗑</span>
          <span className="visually-hidden">Delete</span>
        </button>
      </div>
    );
  };

  if (items.length === 0) {
    return (
      <div
        className={`${styles.listContainer} ${variant === 'embedded' ? styles.listContainerEmbedded : ''}`}
      >
        <p className={styles.emptyState}>No library entries match the current filters.</p>
      </div>
    );
  }

  if (view === 'flat') {
    return (
      <div
        className={`${styles.listContainer} ${variant === 'embedded' ? styles.listContainerEmbedded : ''}`}
        data-layout={isBookLayout ? 'books' : isSubtitleLayout ? 'subtitles' : isVideoLayout ? 'videos' : undefined}
      >
        <div className={styles.tableWrapper}>
          <table
            className={`${styles.table} ${isBookLayout ? styles.bookTable : isSubtitleLayout ? styles.subtitleTable : isVideoLayout ? styles.videoTable : ''}`}
          >
            <thead>
              <tr>
                {isBookLayout ? (
                  <>
                    <th>Book</th>
                    <th>Language</th>
                    <th>Status</th>
                    <th>Updated</th>
                    <th>Actions</th>
                  </>
                ) : isSubtitleLayout ? (
                  <>
                    <th>Series / Episode</th>
                    <th>Language</th>
                    <th>Status</th>
                    <th>Updated</th>
                    <th>Actions</th>
                  </>
                ) : isVideoLayout ? (
                  <>
                    <th>Video</th>
                    <th>Language</th>
                    <th>Status</th>
                    <th>Updated</th>
                    <th>Actions</th>
                  </>
                ) : (
                  <>
                    <th>Title</th>
                    <th>Job</th>
                    <th>Author</th>
                    <th>Language</th>
                    <th>Status</th>
                    <th>Updated</th>
                    <th>Actions</th>
                  </>
                )}
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const permissions = resolveItemPermissions(item);
                const isBusy = Boolean(mutating[item.jobId]);
                const isDisabled = isBusy || !permissions.canView;
                return (
                  <tr
                    key={item.jobId}
                    className={selectedJobId === item.jobId ? styles.tableRowActive : undefined}
                    onClick={() => {
                      if (permissions.canView) {
                        handleSelect(item);
                      }
                    }}
                  >
                    {isBookLayout ? (
                      <>
                        <td className={styles.cellBook}>
                          {renderBookCell(item, {
                            onOpen: () => onOpen(item),
                            disabled: isDisabled,
                          })}
                        </td>
                        <td>{renderLanguageLabel(item.language)}</td>
                        <td>{renderStatusBadge(item)}</td>
                        <td>{formatTimestamp(item.updatedAt)}</td>
                        <td>{renderActions(item, permissions)}</td>
                      </>
                    ) : isSubtitleLayout ? (
                      <>
                        <td className={styles.cellSubtitle}>
                          {renderSubtitleCell(item, {
                            onOpen: () => onOpen(item),
                            disabled: isDisabled,
                          })}
                        </td>
                        <td>{renderLanguageLabel(item.language)}</td>
                        <td>{renderStatusBadge(item)}</td>
                        <td>{formatTimestamp(item.updatedAt)}</td>
                        <td>{renderActions(item, permissions)}</td>
                      </>
                    ) : isVideoLayout ? (
                      <>
                        <td className={styles.cellVideo}>
                          {renderVideoCell(item, {
                            onOpen: () => onOpen(item),
                            disabled: isDisabled,
                          })}
                        </td>
                        <td>{renderLanguageLabel(item.language)}</td>
                        <td>{renderStatusBadge(item)}</td>
                        <td>{formatTimestamp(item.updatedAt)}</td>
                        <td>{renderActions(item, permissions)}</td>
                      </>
                    ) : (
                      <>
                        <td className={styles.cellTitle}>{resolveTitle(item)}</td>
                        <td>{renderJobTypeGlyph(item)}</td>
                        <td className={styles.cellAuthor}>{resolveAuthor(item)}</td>
                        <td>{renderLanguageLabel(item.language)}</td>
                        <td>{renderStatusBadge(item)}</td>
                        <td>{formatTimestamp(item.updatedAt)}</td>
                        <td>{renderActions(item, permissions)}</td>
                      </>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  if (view === 'by_author') {
    return (
      <div className={`${styles.listContainer} ${variant === 'embedded' ? styles.listContainerEmbedded : ''}`}>
        {authorGroups.map((group) => (
          <details key={group.author} className={styles.group} open>
            <summary>{group.author}</summary>
            {group.books.map((book) => (
              <details key={book.bookTitle} className={styles.subGroup} open>
                <summary>{book.bookTitle}</summary>
                {book.languages.map((entry) => (
                  <div key={entry.language}>
                    <h4 className={styles.languageHeader}>{renderLanguageLabel(entry.language)}</h4>
                    <ul className={styles.itemList}>
                      {entry.items.map((item) => {
                        const permissions = resolveItemPermissions(item);
                        return (
                          <li
                            key={item.jobId}
                            className={styles.itemCard}
                            onClick={() => {
                              if (permissions.canView) {
                                handleSelect(item);
                              }
                            }}
                          >
                            <div className={styles.itemHeader}>
                              <span>Job {item.jobId}</span>
                              {renderStatusBadge(item)}
                            </div>
                            <div className={styles.itemMeta}>
                              Updated {formatTimestamp(item.updatedAt)} · Job {renderJobTypeGlyph(item)} · Library path {item.libraryPath}
                            </div>
                            {renderActions(item, permissions)}
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                ))}
              </details>
            ))}
          </details>
        ))}
      </div>
    );
  }

  if (view === 'by_genre') {
    return (
      <div className={`${styles.listContainer} ${variant === 'embedded' ? styles.listContainerEmbedded : ''}`}>
        {genreGroups.map((group) => (
          <details key={group.genre} className={styles.group} open>
            <summary>{group.genre}</summary>
            {group.authors.map((author) => (
              <details key={author.author} className={styles.subGroup} open>
                <summary>{author.author}</summary>
                {author.books.map((book) => (
                  <div key={book.bookTitle}>
                    <h4 className={styles.languageHeader}>{book.bookTitle}</h4>
                    <ul className={styles.itemList}>
                      {book.items.map((item) => {
                        const permissions = resolveItemPermissions(item);
                        return (
                          <li
                            key={item.jobId}
                            className={styles.itemCard}
                            onClick={() => {
                              if (permissions.canView) {
                                handleSelect(item);
                              }
                            }}
                          >
                            <div className={styles.itemHeader}>
                              <span>Job {item.jobId}</span>
                              {renderStatusBadge(item)}
                            </div>
                            <div className={styles.itemMeta}>
                              Language {renderLanguageLabel(item.language)} · Job {renderJobTypeGlyph(item)} · Updated {formatTimestamp(item.updatedAt)}
                            </div>
                            {renderActions(item, permissions)}
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                ))}
              </details>
            ))}
          </details>
        ))}
      </div>
    );
  }

  return (
    <div className={`${styles.listContainer} ${variant === 'embedded' ? styles.listContainerEmbedded : ''}`}>
      {languageGroups.map((group) => (
        <details key={group.language} className={styles.group} open>
          <summary>{renderLanguageLabel(group.language)}</summary>
          {group.authors.map((author) => (
            <details key={author.author} className={styles.subGroup} open>
              <summary>{author.author}</summary>
              {author.books.map((book) => (
                <div key={book.bookTitle}>
                  <h4 className={styles.languageHeader}>{book.bookTitle}</h4>
                  <ul className={styles.itemList}>
                    {book.items.map((item) => {
                      const permissions = resolveItemPermissions(item);
                      return (
                        <li
                          key={item.jobId}
                          className={styles.itemCard}
                          onClick={() => {
                            if (permissions.canView) {
                              handleSelect(item);
                            }
                          }}
                        >
                          <div className={styles.itemHeader}>
                            <span>Job {item.jobId}</span>
                            {renderStatusBadge(item)}
                          </div>
                          <div className={styles.itemMeta}>
                            Updated {formatTimestamp(item.updatedAt)} · Job {renderJobTypeGlyph(item)} · Library path {item.libraryPath}
                          </div>
                          {renderActions(item, permissions)}
                        </li>
                      );
                    })}
                  </ul>
                </div>
              ))}
            </details>
          ))}
        </details>
      ))}
    </div>
  );
}

export default LibraryList;
