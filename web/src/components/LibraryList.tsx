import { useMemo } from 'react';
import type { LibraryItem, LibraryViewMode, ResumePositionEntry } from '../api/dtos';
import { DEFAULT_LANGUAGE_FLAG, resolveLanguageFlag } from '../constants/languageCodes';
import { normalizeLanguageLabel } from '../utils/languages';
import EmojiIcon from './EmojiIcon';
import {
  buildLibraryItemActionState,
  resolveLibraryItemPermissions,
  type LibraryItemActionState,
  type LibraryItemPermissionResolver,
  type LibraryItemPermissions
} from './library-list/libraryListActions';
import { LibraryItemActions } from './library-list/LibraryItemActions';
import { LibraryBookCell, LibraryJobTypeGlyph, LibrarySubtitleCell, LibraryVideoCell } from './library-list/LibraryItemMediaCells';
import { LibraryItemStatusStack } from './library-list/LibraryItemStatusStack';
import { buildLibraryResumeBadgeMap } from './library-list/libraryListResume';
import {
  buildAuthorGroups,
  buildGenreGroups,
  buildLanguageGroups,
  isBookItem,
  isSubtitleItem,
  isVideoItem,
  resolveAuthor,
  resolveTitle
} from './library-list/libraryListUtils';
import styles from './LibraryList.module.css';

type Props = {
  items: LibraryItem[];
  view: LibraryViewMode;
  onSelect?: (item: LibraryItem) => void;
  onOpen: (item: LibraryItem) => void;
  onExport?: (item: LibraryItem) => void;
  onRemove: (item: LibraryItem) => void;
  onEditMetadata: (item: LibraryItem) => void;
  resolvePermissions?: LibraryItemPermissionResolver;
  selectedJobId?: string | null;
  mutating?: Record<string, boolean>;
  variant?: 'card' | 'embedded';
  resumeEntries?: ResumePositionEntry[];
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
  variant = 'card',
  resumeEntries = []
}: Props) {
  const authorGroups = useMemo(() => buildAuthorGroups(items), [items]);
  const genreGroups = useMemo(() => buildGenreGroups(items), [items]);
  const languageGroups = useMemo(() => buildLanguageGroups(items), [items]);
  const isBookLayout = useMemo(() => items.length > 0 && items.every((item) => isBookItem(item)), [items]);
  const isSubtitleLayout = useMemo(() => items.length > 0 && items.every((item) => isSubtitleItem(item)), [items]);
  const isVideoLayout = useMemo(() => items.length > 0 && items.every((item) => isVideoItem(item)), [items]);
  const resumeBadges = useMemo(
    () => buildLibraryResumeBadgeMap(items, resumeEntries),
    [items, resumeEntries],
  );

  const handleSelect = (item: LibraryItem) => {
    if (onSelect) {
      onSelect(item);
    }
  };

  const resolveItemPermissions = (item: LibraryItem): LibraryItemPermissions =>
    resolveLibraryItemPermissions(item, resolvePermissions);

  const resolveItemActionState = (item: LibraryItem, permissions: LibraryItemPermissions): LibraryItemActionState =>
    buildLibraryItemActionState(item, permissions, Boolean(mutating[item.jobId]));

  const renderActions = (item: LibraryItem, actionState: LibraryItemActionState) => (
    <LibraryItemActions
      item={item}
      actionState={actionState}
      onOpen={onOpen}
      onEditMetadata={onEditMetadata}
      onExport={onExport}
      onRemove={onRemove}
    />
  );
  const renderStatus = (item: LibraryItem) => (
    <LibraryItemStatusStack item={item} resumeBadge={resumeBadges.get(item.jobId)} />
  );

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
                const actionState = resolveItemActionState(item, permissions);
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
                          <LibraryBookCell
                            item={item}
                            onOpen={() => onOpen(item)}
                            disabled={actionState.mediaOpenDisabled}
                          />
                        </td>
                        <td>{renderLanguageLabel(item.language)}</td>
                        <td>{renderStatus(item)}</td>
                        <td>{formatTimestamp(item.updatedAt)}</td>
                        <td>{renderActions(item, actionState)}</td>
                      </>
                    ) : isSubtitleLayout ? (
                      <>
                        <td className={styles.cellSubtitle}>
                          <LibrarySubtitleCell
                            item={item}
                            onOpen={() => onOpen(item)}
                            disabled={actionState.mediaOpenDisabled}
                          />
                        </td>
                        <td>{renderLanguageLabel(item.language)}</td>
                        <td>{renderStatus(item)}</td>
                        <td>{formatTimestamp(item.updatedAt)}</td>
                        <td>{renderActions(item, actionState)}</td>
                      </>
                    ) : isVideoLayout ? (
                      <>
                        <td className={styles.cellVideo}>
                          <LibraryVideoCell
                            item={item}
                            onOpen={() => onOpen(item)}
                            disabled={actionState.mediaOpenDisabled}
                          />
                        </td>
                        <td>{renderLanguageLabel(item.language)}</td>
                        <td>{renderStatus(item)}</td>
                        <td>{formatTimestamp(item.updatedAt)}</td>
                        <td>{renderActions(item, actionState)}</td>
                      </>
                    ) : (
                      <>
                        <td className={styles.cellTitle}>{resolveTitle(item)}</td>
                        <td><LibraryJobTypeGlyph item={item} /></td>
                        <td className={styles.cellAuthor}>{resolveAuthor(item)}</td>
                        <td>{renderLanguageLabel(item.language)}</td>
                        <td>{renderStatus(item)}</td>
                        <td>{formatTimestamp(item.updatedAt)}</td>
                        <td>{renderActions(item, actionState)}</td>
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
                        const actionState = resolveItemActionState(item, permissions);
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
                              {renderStatus(item)}
                            </div>
                            <div className={styles.itemMeta}>
                              Updated {formatTimestamp(item.updatedAt)} · Job <LibraryJobTypeGlyph item={item} /> · Library path {item.libraryPath}
                            </div>
                            {renderActions(item, actionState)}
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
                        const actionState = resolveItemActionState(item, permissions);
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
                              {renderStatus(item)}
                            </div>
                            <div className={styles.itemMeta}>
                              Language {renderLanguageLabel(item.language)} · Job <LibraryJobTypeGlyph item={item} /> · Updated {formatTimestamp(item.updatedAt)}
                            </div>
                            {renderActions(item, actionState)}
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
                      const actionState = resolveItemActionState(item, permissions);
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
                            {renderStatus(item)}
                          </div>
                          <div className={styles.itemMeta}>
                            Updated {formatTimestamp(item.updatedAt)} · Job <LibraryJobTypeGlyph item={item} /> · Library path {item.libraryPath}
                          </div>
                          {renderActions(item, actionState)}
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
