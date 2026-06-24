import type { LibraryItem } from '../../api/dtos';
import type { LibraryItemActionState } from './libraryListActions';
import styles from '../LibraryList.module.css';

type LibraryItemActionsProps = {
  item: LibraryItem;
  actionState: LibraryItemActionState;
  onOpen: (item: LibraryItem) => void;
  onEditMetadata: (item: LibraryItem) => void;
  onExport?: (item: LibraryItem) => void;
  onRemove: (item: LibraryItem) => void;
};

export function LibraryItemActions({
  item,
  actionState,
  onOpen,
  onEditMetadata,
  onExport,
  onRemove,
}: LibraryItemActionsProps) {
  return (
    <div className={styles.actions}>
      <button
        type="button"
        className={styles.actionIconButton}
        onClick={(event) => {
          event.stopPropagation();
          if (actionState.canView) {
            onOpen(item);
          }
        }}
        disabled={actionState.mediaOpenDisabled}
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
          if (actionState.canEdit) {
            onEditMetadata(item);
          }
        }}
        disabled={actionState.editDisabled}
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
            if (actionState.isExportReady && actionState.canExport) {
              onExport(item);
            }
          }}
          disabled={actionState.exportDisabled}
          aria-label="Export offline player"
          title={actionState.exportTitle}
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
          if (actionState.canEdit) {
            onRemove(item);
          }
        }}
        disabled={actionState.removeDisabled}
        aria-label="Delete"
        title="Delete"
        data-variant="danger"
      >
        <span aria-hidden="true">🗑</span>
        <span className="visually-hidden">Delete</span>
      </button>
    </div>
  );
}
