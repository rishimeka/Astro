import type { RunStatus } from '@/types/astro';
import styles from './StatusBadge.module.scss';

export type Status = RunStatus | 'pending';

export interface StatusBadgeProps {
  status: Status;
  size?: 'sm' | 'md';
}

const statusConfig: Record<Status, { label: string; className: string }> = {
  running: { label: 'Running', className: styles.running },
  completed: { label: 'Completed', className: styles.completed },
  failed: { label: 'Failed', className: styles.failed },
  pending: { label: 'Pending', className: styles.pending },
  awaiting_confirmation: { label: 'Awaiting', className: styles.awaiting },
  cancelled: { label: 'Cancelled', className: styles.cancelled },
};

export default function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
  const config = statusConfig[status] || { label: status, className: styles.pending };

  return (
    <span className={`${styles.badge} ${config.className} ${styles[size]}`}>
      <span className={styles.dot} />
      {config.label}
    </span>
  );
}
