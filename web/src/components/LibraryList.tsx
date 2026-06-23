import { useMemo } from 'react';
import type { LibraryItem, LibraryViewMode } from '../api/dtos';
import { DEFAULT_LANGUAGE_FLAG, resolveLanguageFlag } from '../constants/languageCodes';
import { extractJobType, getJobTypeGlyph, isTvSeriesMetadata } from '../utils/jobGlyphs';
import JobTypeGlyphBadge from './JobTypeGlyphBadge';
import { normalizeLanguageLabel } from '../utils/languages';
import { extractLibraryBookMetadata, resolveLibraryCoverUrl } from '../utils/libraryMetadata';
import { getStatusGlyph } from '../utils/status';
import EmojiIcon from './EmojiIcon';
import {
  buildAuthorGroups,
  buildGenreGroups,
  buildLanguageGroups,
  isBookItem,
  isSubtitleItem,
  isVideoItem,
  resolveAuthor,
  resolveGenre,
  resolveTitle
} from './library-list/libraryListUtils';
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
} from './library-list/libraryListMediaUtils';
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

type StatusVariant = 'ready' | 'missing';

function resolveJobType(item: LibraryItem): string {
  return extractJobType(item.metadata) ?? 'pipeline';
}

function renderJobTypeGlyph(item: LibraryItem) {
  const jobType = resolveJobType(item);
  const tvMetadata = extractTvMediaMetadata(item);
  const glyph = getJobTypeGlyph(jobType, { isTvSeries: isTvSeriesMetadata(tvMetadata) });
  return (
    <JobTypeGlyphBadge glyph={glyph} className={styles.jobGlyph} />
  );
}

function renderBookCell(item: LibraryItem, options: { onOpen: () => void; disabled: boolean }) {
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
