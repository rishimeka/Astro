'use client';

import { AlertTriangle, X, ArrowRight } from 'lucide-react';
import { ValidationPanelProps } from './types';
import styles from './ValidationPanel.module.scss';

export function ValidationPanel({ errors, onErrorClick }: ValidationPanelProps) {
  if (errors.length === 0) {
    return null;
  }

  const errorCount = errors.filter((e) => e.severity === 'error').length;
  const warningCount = errors.filter((e) => e.severity === 'warning').length;

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <AlertTriangle size={16} className={styles.icon} />
        <span className={styles.title}>
          {errorCount > 0 && `${errorCount} Error${errorCount !== 1 ? 's' : ''}`}
          {errorCount > 0 && warningCount > 0 && ', '}
          {warningCount > 0 &&
            `${warningCount} Warning${warningCount !== 1 ? 's' : ''}`}
        </span>
      </div>

      <div className={styles.content}>
        {errors.map((error, index) => (
          <div
            key={`${error.nodeId || error.edgeId || index}-${error.message}`}
            className={`${styles.errorRow} ${
              error.severity === 'error' ? styles.error : styles.warning
            }`}
          >
            <span className={styles.errorIcon}>
              {error.severity === 'error' ? (
                <X size={14} />
              ) : (
                <AlertTriangle size={14} />
              )}
            </span>
            <span className={styles.errorMessage}>{error.message}</span>
            {(error.nodeId || error.edgeId) && onErrorClick && (
              <button
                className={styles.focusButton}
                onClick={() => onErrorClick(error)}
                title="Focus on element"
              >
                <ArrowRight size={14} />
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
