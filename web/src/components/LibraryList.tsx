import { useMemo } from 'react';
import type { LibraryItem, LibraryViewMode, ResumePositionEntry } from '../api/dtos';
import {
  buildLibraryItemActionState,
  resolveLibraryItemPermissions,
  type LibraryItemActionState,
  type LibraryItemPermissionResolver,
  type LibraryItemPermissions
} from './library-list/libraryListActions';
import { LibraryItemActions } from './library-list/LibraryItemActions';
import { LibraryFlatTable } from './library-list/LibraryFlatTable';
import { LibraryJobTypeGlyph } from './library-list/LibraryItemMediaCells';
import { LibraryItemStatusStack } from './library-list/LibraryItemStatusStack';
import { LibraryLanguageLabel } from './library-list/LibraryLanguageLabel';
import { buildLibraryResumeBadgeMap } from './library-list/libraryListResume';
import {
  buildAuthorGroups,
  buildGenreGroups,
  buildLanguageGroups,
  formatLibraryTimestamp,
  resolveLibraryFlatLayout,
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
  const flatLayout = useMemo(() => resolveLibraryFlatLayout(items), [items]);
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
        data-layout={flatLayout ?? undefined}
      >
        <LibraryFlatTable
          items={items}
          flatLayout={flatLayout}
          selectedJobId={selectedJobId}
          mutating={mutating}
          resumeBadges={resumeBadges}
          onSelect={onSelect}
          onOpen={onOpen}
          onExport={onExport}
          onRemove={onRemove}
          onEditMetadata={onEditMetadata}
          resolvePermissions={resolvePermissions}
        />
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
                    <h4 className={styles.languageHeader}><LibraryLanguageLabel language={entry.language} /></h4>
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
                              Updated {formatLibraryTimestamp(item.updatedAt)} · Job <LibraryJobTypeGlyph item={item} /> · Library path {item.libraryPath}
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
                              Language <LibraryLanguageLabel language={item.language} /> · Job <LibraryJobTypeGlyph item={item} /> · Updated {formatLibraryTimestamp(item.updatedAt)}
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
          <summary><LibraryLanguageLabel language={group.language} /></summary>
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
                            Updated {formatLibraryTimestamp(item.updatedAt)} · Job <LibraryJobTypeGlyph item={item} /> · Library path {item.libraryPath}
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
