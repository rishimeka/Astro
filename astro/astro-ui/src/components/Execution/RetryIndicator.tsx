'use client';

import { memo } from 'react';
import { RefreshCw, Clock } from 'lucide-react';
import styles from './RetryIndicator.module.scss';

interface RetryIndicatorProps {
  nodeId: string;
  attempt: number;
  maxAttempts: number;
  lastError: string;
  nextRetryIn?: number; // seconds until next retry (parent should update this value)
  compact?: boolean;
}

/**
 * RetryIndicator - Shows when a node is being retried during execution
 *
 * Displays:
 * - Current attempt / max attempts
 * - Last error message (truncated)
 * - Optional countdown to next retry
 *
 * Note: For the countdown to work, the parent component should update
 * the `nextRetryIn` prop each second.
 */
function RetryIndicatorComponent({
  nodeId,
  attempt,
  maxAttempts,
  lastError,
  nextRetryIn,
  compact = false,
}: RetryIndicatorProps) {
  // Truncate error message for display
  const truncatedError = lastError.length > 100
    ? `${lastError.substring(0, 100)}...`
    : lastError;

  const showCountdown = nextRetryIn !== undefined && nextRetryIn > 0;

  return (
    <div
      className={`${styles.container} ${compact ? styles.compact : ''}`}
      data-node-id={nodeId}
      role="status"
      aria-live="polite"
    >
      {/* Header with retry icon and badge */}
      <div className={styles.header}>
        <div className={styles.iconWrapper}>
          <RefreshCw size={compact ? 12 : 14} className={styles.spinnerIcon} />
        </div>
        <span className={styles.retryBadge}>
          <span className={styles.attemptText}>
            Retry {attempt}/{maxAttempts}
          </span>
        </span>
      </div>

      {/* Error message */}
      {lastError && (
        <div className={styles.errorContainer}>
          <span className={styles.errorLabel}>Last error</span>
          <span className={styles.errorText} title={lastError}>
            {truncatedError}
          </span>
        </div>
      )}

      {/* Countdown to next retry */}
      {showCountdown && (
        <div className={`${styles.countdown} ${styles.countdownPulse}`}>
          <Clock size={compact ? 10 : 12} className={styles.countdownIcon} />
          <span>Next retry in</span>
          <span className={styles.countdownValue}>{nextRetryIn}s</span>
        </div>
      )}
    </div>
  );
}

export const RetryIndicator = memo(RetryIndicatorComponent);
