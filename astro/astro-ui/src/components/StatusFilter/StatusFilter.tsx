'use client';

import type { RunStatus } from '@/types/astro';
import styles from './StatusFilter.module.scss';

export type FilterableStatus = RunStatus | 'all';

export interface StatusFilterProps {
  value: FilterableStatus;
  onChange: (status: FilterableStatus) => void;
}

const statusConfig: Record<FilterableStatus, { label: string; color: string }> = {
  all: { label: 'All', color: 'var(--text-secondary)' },
  running: { label: 'Running', color: 'var(--color-info)' },
  completed: { label: 'Completed', color: 'var(--color-success)' },
  failed: { label: 'Failed', color: 'var(--accent-danger)' },
  awaiting_confirmation: { label: 'Awaiting', color: 'var(--color-warning)' },
  cancelled: { label: 'Cancelled', color: 'var(--text-muted)' },
};

const statusOrder: FilterableStatus[] = [
  'all',
  'running',
  'awaiting_confirmation',
  'completed',
  'failed',
  'cancelled',
];

export default function StatusFilter({ value, onChange }: StatusFilterProps) {
  return (
    <div className={styles.container}>
      {statusOrder.map((status) => {
        const config = statusConfig[status];
        const isSelected = value === status;
        return (
          <button
            key={status}
            type="button"
            className={`${styles.chip} ${isSelected ? styles.selected : ''}`}
            style={isSelected ? { backgroundColor: `${config.color}20`, color: config.color, borderColor: config.color } : undefined}
            onClick={() => onChange(status)}
          >
            {status !== 'all' && <span className={styles.dot} style={{ backgroundColor: config.color }} />}
            {config.label}
          </button>
        );
      })}
    </div>
  );
}
