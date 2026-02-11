'use client';

import styles from './ExecutionModeToggle.module.scss';

export type ExecutionMode = 'simple' | 'detailed';

export interface ExecutionModeToggleProps {
  mode: ExecutionMode;
  onChange: (mode: ExecutionMode) => void;
}

export function ExecutionModeToggle({ mode, onChange }: ExecutionModeToggleProps) {
  return (
    <div className={styles.modeToggle} role="group" aria-label="Execution mode">
      <button
        type="button"
        className={`${styles.toggleButton} ${mode === 'simple' ? styles.active : ''}`}
        onClick={() => onChange('simple')}
        aria-pressed={mode === 'simple'}
      >
        Simple
      </button>
      <button
        type="button"
        className={`${styles.toggleButton} ${mode === 'detailed' ? styles.active : ''}`}
        onClick={() => onChange('detailed')}
        aria-pressed={mode === 'detailed'}
      >
        Detailed
      </button>
    </div>
  );
}
