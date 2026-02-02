'use client';

import { LayoutGrid, Save, Play, Loader2 } from 'lucide-react';
import { ToolbarProps } from './types';
import styles from './Toolbar.module.scss';

export function Toolbar({
  onAutoLayout,
  onSave,
  onRun,
  isSaving = false,
  hasErrors = false,
  canRun = true,
}: ToolbarProps) {
  return (
    <div className={styles.toolbar}>
      <div className={styles.left}>
        <button
          className={styles.button}
          onClick={onAutoLayout}
          title="Auto Layout"
        >
          <LayoutGrid size={16} />
          <span>Auto Layout</span>
        </button>

      </div>

      <div className={styles.right}>
        <button
          className={`${styles.button} ${styles.primary}`}
          onClick={onSave}
          disabled={isSaving}
          title="Save"
        >
          {isSaving ? (
            <Loader2 size={16} className={styles.spinner} />
          ) : (
            <Save size={16} />
          )}
          <span>{isSaving ? 'Saving...' : 'Save'}</span>
        </button>

        {onRun && (
          <button
            className={`${styles.button} ${styles.primary} ${
              hasErrors ? styles.disabled : ''
            }`}
            onClick={onRun}
            disabled={hasErrors || !canRun}
            title={hasErrors ? 'Fix validation errors before running' : 'Run'}
          >
            <Play size={16} />
            <span>Run</span>
          </button>
        )}
      </div>
    </div>
  );
}
