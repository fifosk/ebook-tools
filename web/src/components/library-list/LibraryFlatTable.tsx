import type { LibraryItem } from '../../api/dtos';
import {
  buildLibraryItemActionState,
  resolveLibraryItemPermissions,
  type LibraryItemActionState,
  type LibraryItemPermissionResolver,
  type LibraryItemPermissions
} from './libraryListActions';
import { LibraryItemActions } from './LibraryItemActions';
import { LibraryBookCell, LibraryJobTypeGlyph, LibrarySubtitleCell, LibraryVideoCell } from './LibraryItemMediaCells';
import { LibraryItemStatusStack } from './LibraryItemStatusStack';
import { LibraryLanguageLabel } from './LibraryLanguageLabel';
import type { LibraryResumeBadge } from './libraryListResume';
import {
  formatLibraryTimestamp,
  resolveAuthor,
  resolveTitle,
  type LibraryFlatLayout
} from './libraryListUtils';
import styles from '../LibraryList.module.css';

type LibraryFlatTableProps = {
  items: LibraryItem[];
  flatLayout: LibraryFlatLayout | null;
  selectedJobId?: string | null;
  mutating?: Record<string, boolean>;
  resumeBadges: Map<string, LibraryResumeBadge>;
  onSelect?: (item: LibraryItem) => void;
  onOpen: (item: LibraryItem) => void;
  onExport?: (item: LibraryItem) => void;
  onRemove: (item: LibraryItem) => void;
  onEditMetadata: (item: LibraryItem) => void;
  resolvePermissions?: LibraryItemPermissionResolver;
};

function resolveItemPermissions(
  item: LibraryItem,
  resolvePermissions?: LibraryItemPermissionResolver,
): LibraryItemPermissions {
  return resolveLibraryItemPermissions(item, resolvePermissions);
}

function resolveItemActionState(
  item: LibraryItem,
  permissions: LibraryItemPermissions,
  mutating: Record<string, boolean>,
): LibraryItemActionState {
  return buildLibraryItemActionState(item, permissions, Boolean(mutating[item.jobId]));
}

function LibraryTableHead({ flatLayout }: { flatLayout: LibraryFlatLayout | null }) {
  if (flatLayout === 'books') {
    return (
      <tr>
        <th>Book</th>
        <th>Language</th>
        <th>Status</th>
        <th>Updated</th>
        <th>Actions</th>
      </tr>
    );
  }
  if (flatLayout === 'subtitles') {
    return (
      <tr>
        <th>Series / Episode</th>
        <th>Language</th>
        <th>Status</th>
        <th>Updated</th>
        <th>Actions</th>
      </tr>
    );
  }
  if (flatLayout === 'videos') {
    return (
      <tr>
        <th>Video</th>
        <th>Language</th>
        <th>Status</th>
        <th>Updated</th>
        <th>Actions</th>
      </tr>
    );
  }
  return (
    <tr>
      <th>Title</th>
      <th>Job</th>
      <th>Author</th>
      <th>Language</th>
      <th>Status</th>
      <th>Updated</th>
      <th>Actions</th>
    </tr>
  );
}

export function LibraryFlatTable({
  items,
  flatLayout,
  selectedJobId,
  mutating = {},
  resumeBadges,
  onSelect,
  onOpen,
  onExport,
  onRemove,
  onEditMetadata,
  resolvePermissions,
}: LibraryFlatTableProps) {
  const tableClassName = [
    styles.table,
    flatLayout === 'books' ? styles.bookTable : '',
    flatLayout === 'subtitles' ? styles.subtitleTable : '',
    flatLayout === 'videos' ? styles.videoTable : '',
  ].filter(Boolean).join(' ');

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

  return (
    <div className={styles.tableWrapper}>
      <table className={tableClassName}>
        <thead>
          <LibraryTableHead flatLayout={flatLayout} />
        </thead>
        <tbody>
          {items.map((item) => {
            const permissions = resolveItemPermissions(item, resolvePermissions);
            const actionState = resolveItemActionState(item, permissions, mutating);
            const handleRowClick = () => {
              if (permissions.canView && onSelect) {
                onSelect(item);
              }
            };
            return (
              <tr
                key={item.jobId}
                className={selectedJobId === item.jobId ? styles.tableRowActive : undefined}
                onClick={handleRowClick}
              >
                {flatLayout === 'books' ? (
                  <>
                    <td className={styles.cellBook}>
                      <LibraryBookCell
                        item={item}
                        onOpen={() => onOpen(item)}
                        disabled={actionState.mediaOpenDisabled}
                      />
                    </td>
                    <td><LibraryLanguageLabel language={item.language} /></td>
                    <td>{renderStatus(item)}</td>
                    <td>{formatLibraryTimestamp(item.updatedAt)}</td>
                    <td>{renderActions(item, actionState)}</td>
                  </>
                ) : flatLayout === 'subtitles' ? (
                  <>
                    <td className={styles.cellSubtitle}>
                      <LibrarySubtitleCell
                        item={item}
                        onOpen={() => onOpen(item)}
                        disabled={actionState.mediaOpenDisabled}
                      />
                    </td>
                    <td><LibraryLanguageLabel language={item.language} /></td>
                    <td>{renderStatus(item)}</td>
                    <td>{formatLibraryTimestamp(item.updatedAt)}</td>
                    <td>{renderActions(item, actionState)}</td>
                  </>
                ) : flatLayout === 'videos' ? (
                  <>
                    <td className={styles.cellVideo}>
                      <LibraryVideoCell
                        item={item}
                        onOpen={() => onOpen(item)}
                        disabled={actionState.mediaOpenDisabled}
                      />
                    </td>
                    <td><LibraryLanguageLabel language={item.language} /></td>
                    <td>{renderStatus(item)}</td>
                    <td>{formatLibraryTimestamp(item.updatedAt)}</td>
                    <td>{renderActions(item, actionState)}</td>
                  </>
                ) : (
                  <>
                    <td className={styles.cellTitle}>{resolveTitle(item)}</td>
                    <td><LibraryJobTypeGlyph item={item} /></td>
                    <td className={styles.cellAuthor}>{resolveAuthor(item)}</td>
                    <td><LibraryLanguageLabel language={item.language} /></td>
                    <td>{renderStatus(item)}</td>
                    <td>{formatLibraryTimestamp(item.updatedAt)}</td>
                    <td>{renderActions(item, actionState)}</td>
                  </>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
