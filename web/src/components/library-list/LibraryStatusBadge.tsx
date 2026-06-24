import type { LibraryItem } from '../../api/dtos';
import { getStatusGlyph } from '../../utils/status';
import styles from '../LibraryList.module.css';

type StatusVariant = 'ready' | 'missing';

type StatusDescription = {
  label: string;
  variant?: StatusVariant;
  glyphKey: string;
};

function describeStatus(item: LibraryItem): StatusDescription {
  if (!item.mediaCompleted) {
    return { label: 'Media removed', variant: 'missing', glyphKey: 'cancelled' };
  }
  if (item.status === 'paused') {
    return { label: 'Paused', variant: 'ready', glyphKey: 'paused' };
  }
  return { label: 'Finished', variant: 'ready', glyphKey: 'completed' };
}

type LibraryStatusBadgeProps = {
  item: LibraryItem;
};

export function LibraryStatusBadge({ item }: LibraryStatusBadgeProps) {
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
