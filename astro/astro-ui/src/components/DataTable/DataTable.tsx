'use client';

import { SkeletonLoader } from '@/components/Loading';
import styles from './DataTable.module.scss';

export interface Column<T> {
  key: keyof T | string;
  header: string;
  width?: string;
  align?: 'left' | 'center' | 'right';
  sortable?: boolean;
  render?: (value: unknown, row: T) => React.ReactNode;
}

export interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  onRowClick?: (row: T) => void;
  loading?: boolean;
  emptyMessage?: string;
  sortColumn?: string;
  sortDirection?: 'asc' | 'desc';
  onSort?: (column: string, direction: 'asc' | 'desc') => void;
  keyExtractor?: (row: T) => string;
}

function getNestedValue<T>(obj: T, path: string): unknown {
  return path.split('.').reduce((acc: unknown, part) => {
    if (acc && typeof acc === 'object' && part in acc) {
      return (acc as Record<string, unknown>)[part];
    }
    return undefined;
  }, obj);
}

export default function DataTable<T>({
  data,
  columns,
  onRowClick,
  loading = false,
  emptyMessage = 'No data available',
  sortColumn,
  sortDirection = 'asc',
  onSort,
  keyExtractor,
}: DataTableProps<T>) {
  const handleHeaderClick = (column: Column<T>) => {
    if (!column.sortable || !onSort) return;

    const columnKey = String(column.key);
    const newDirection =
      sortColumn === columnKey && sortDirection === 'asc' ? 'desc' : 'asc';
    onSort(columnKey, newDirection);
  };

  const renderSortIcon = (column: Column<T>) => {
    if (!column.sortable) return null;

    const columnKey = String(column.key);
    const isActive = sortColumn === columnKey;

    return (
      <span className={`${styles.sortIcon} ${isActive ? styles.active : ''}`}>
        {isActive && sortDirection === 'desc' ? (
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M6 9l6 6 6-6" />
          </svg>
        ) : (
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 15l-6-6-6 6" />
          </svg>
        )}
      </span>
    );
  };

  const renderSkeletonRows = () => {
    return Array.from({ length: 5 }).map((_, rowIndex) => (
      <tr key={`skeleton-${rowIndex}`} className={styles.row}>
        {columns.map((column, colIndex) => (
          <td
            key={`skeleton-${rowIndex}-${colIndex}`}
            className={styles.cell}
            style={{ width: column.width, textAlign: column.align }}
          >
            <SkeletonLoader height="20px" width="80%" />
          </td>
        ))}
      </tr>
    ));
  };

  const renderCell = (row: T, column: Column<T>) => {
    const value = getNestedValue(row, String(column.key));

    if (column.render) {
      return column.render(value, row);
    }

    if (value === null || value === undefined) {
      return <span className={styles.nullValue}>—</span>;
    }

    return String(value);
  };

  const getRowKey = (row: T, index: number): string => {
    if (keyExtractor) {
      return keyExtractor(row);
    }
    if (typeof row === 'object' && row !== null && 'id' in row) {
      return String((row as { id: unknown }).id);
    }
    return String(index);
  };

  return (
    <div className={styles.tableContainer}>
      <table className={styles.table}>
        <thead className={styles.header}>
          <tr>
            {columns.map((column, index) => (
              <th
                key={index}
                className={`${styles.headerCell} ${column.sortable ? styles.sortable : ''}`}
                style={{ width: column.width, textAlign: column.align }}
                onClick={() => handleHeaderClick(column)}
              >
                <span className={styles.headerContent}>
                  {column.header}
                  {renderSortIcon(column)}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className={styles.body}>
          {loading ? (
            renderSkeletonRows()
          ) : data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className={styles.emptyCell}>
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, rowIndex) => (
              <tr
                key={getRowKey(row, rowIndex)}
                className={`${styles.row} ${onRowClick ? styles.clickable : ''}`}
                onClick={() => onRowClick?.(row)}
              >
                {columns.map((column, colIndex) => (
                  <td
                    key={colIndex}
                    className={styles.cell}
                    style={{ width: column.width, textAlign: column.align }}
                  >
                    {renderCell(row, column)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
