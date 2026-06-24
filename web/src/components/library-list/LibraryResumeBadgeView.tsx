import type { LibraryResumeBadge } from './libraryListResume';
import styles from '../LibraryList.module.css';

type LibraryResumeBadgeViewProps = {
  badge: LibraryResumeBadge | null | undefined;
};

export function LibraryResumeBadgeView({ badge }: LibraryResumeBadgeViewProps) {
  if (!badge) {
    return null;
  }
  return (
    <span className={styles.resumeBadge} title={badge.title}>
      <span aria-hidden="true">▶</span>
      <span>{badge.label}</span>
    </span>
  );
}
