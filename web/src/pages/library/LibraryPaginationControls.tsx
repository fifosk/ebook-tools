import styles from '../LibraryPage.module.css';

type LibraryPaginationControlsProps = {
  page: number;
  totalPages: number;
  rangeLabel: string;
  onPageChange: (page: number) => void;
};

export default function LibraryPaginationControls({
  page,
  totalPages,
  rangeLabel,
  onPageChange,
}: LibraryPaginationControlsProps) {
  const previousPage = Math.max(1, page - 1);
  const nextPage = Math.min(totalPages, page + 1);

  return (
    <nav className={styles.pagination} aria-label="Library pagination">
      <button type="button" onClick={() => onPageChange(previousPage)} disabled={page <= 1}>
        Previous
      </button>
      <span>{rangeLabel}</span>
      <button type="button" onClick={() => onPageChange(nextPage)} disabled={page >= totalPages}>
        Next
      </button>
    </nav>
  );
}
