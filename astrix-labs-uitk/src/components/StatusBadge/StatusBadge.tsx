import styles from './StatusBadge.module.scss';

export type Status = 'running' | 'completed' | 'failed' | 'pending' | 'awaiting_confirmation' | 'cancelled';

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

export function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
  const config = statusConfig[status] || { label: status, className: styles.pending };

  return (
    <span className={`${styles.badge} ${config.className} ${styles[size]}`}>
      <span className={styles.dot} />
      {config.label}
    </span>
  );
}
