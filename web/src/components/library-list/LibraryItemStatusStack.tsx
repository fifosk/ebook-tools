import type { LibraryItem } from '../../api/dtos';
import { LibraryResumeBadgeView } from './LibraryResumeBadgeView';
import { LibraryStatusBadge } from './LibraryStatusBadge';
import type { LibraryResumeBadge } from './libraryListResume';
import styles from '../LibraryList.module.css';

type LibraryItemStatusStackProps = {
  item: LibraryItem;
  resumeBadge?: LibraryResumeBadge | null;
};

export function LibraryItemStatusStack({ item, resumeBadge }: LibraryItemStatusStackProps) {
  return (
    <div className={styles.statusStack}>
      <LibraryStatusBadge item={item} />
      <LibraryResumeBadgeView badge={resumeBadge} />
    </div>
  );
}
