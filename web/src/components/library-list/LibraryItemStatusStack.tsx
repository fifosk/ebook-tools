import type { LibraryItem } from '../../api/dtos';
import { LibraryResumeBadgeView } from './LibraryResumeBadgeView';
import { LibraryStatusBadge } from './LibraryStatusBadge';
import { resolveLibraryAttentionBadge } from './libraryListAttention';
import type { LibraryResumeBadge } from './libraryListResume';
import styles from '../LibraryList.module.css';

type LibraryItemStatusStackProps = {
  item: LibraryItem;
  resumeBadge?: LibraryResumeBadge | null;
};

export function LibraryItemStatusStack({ item, resumeBadge }: LibraryItemStatusStackProps) {
  const attentionBadge = resolveLibraryAttentionBadge(item, resumeBadge);
  return (
    <div className={styles.statusStack}>
      <LibraryStatusBadge item={item} />
      <LibraryResumeBadgeView badge={resumeBadge} />
      {attentionBadge ? (
        <span
          className={styles.attentionBadge}
          data-variant={attentionBadge.variant}
          title={attentionBadge.title}
        >
          {attentionBadge.label}
        </span>
      ) : null}
    </div>
  );
}
