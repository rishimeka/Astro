'use client';

import styles from './Pagination.module.scss';

export interface PaginationProps {
  currentPage: number;
  totalPages: number;
  pageSize: number;
  totalItems: number;
  onPageChange: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  pageSizeOptions?: number[];
}

export function Pagination({
  currentPage,
  totalPages,
  pageSize,
  totalItems,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [10, 25, 50, 100],
}: PaginationProps) {
  const startItem = totalItems === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const endItem = Math.min(currentPage * pageSize, totalItems);

  const handlePrevious = () => {
    if (currentPage > 1) {
      onPageChange(currentPage - 1);
    }
  };

  const handleNext = () => {
    if (currentPage < totalPages) {
      onPageChange(currentPage + 1);
    }
  };

  const handlePageSizeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newSize = parseInt(e.target.value, 10);
    onPageSizeChange?.(newSize);
  };

  return (
    <div className={styles.container}>
      <div className={styles.info}>
        <span className={styles.count}>
          Showing {startItem}-{endItem} of {totalItems}
        </span>
        {onPageSizeChange && (
          <div className={styles.pageSizeSelector}>
            <label htmlFor="pageSize" className={styles.pageSizeLabel}>
              per page:
            </label>
            <select
              id="pageSize"
              className={styles.pageSizeSelect}
              value={pageSize}
              onChange={handlePageSizeChange}
            >
              {pageSizeOptions.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      <div className={styles.navigation}>
        <button
          type="button"
          className={styles.navButton}
          onClick={handlePrevious}
          disabled={currentPage <= 1}
          aria-label="Previous page"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
          <span className={styles.navText}>Previous</span>
        </button>

        <span className={styles.pageIndicator}>
          Page {currentPage} of {totalPages || 1}
        </span>

        <button
          type="button"
          className={styles.navButton}
          onClick={handleNext}
          disabled={currentPage >= totalPages}
          aria-label="Next page"
        >
          <span className={styles.navText}>Next</span>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="9 18 15 12 9 6" />
          </svg>
        </button>
      </div>
    </div>
  );
}
