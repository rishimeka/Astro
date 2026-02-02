'use client';

import { useState } from 'react';
import { Pause, Play, X } from 'lucide-react';
import styles from './ConfirmationModal.module.scss';

interface ConfirmationModalProps {
  nodeId: string;
  nodeName?: string;
  prompt: string;
  onConfirm: (additionalContext?: string) => void;
  onCancel: () => void;
  isSubmitting?: boolean;
}

export function ConfirmationModal({
  nodeName,
  prompt,
  onConfirm,
  onCancel,
  isSubmitting = false,
}: ConfirmationModalProps) {
  const [additionalContext, setAdditionalContext] = useState('');

  const handleConfirm = () => {
    onConfirm(additionalContext.trim() || undefined);
  };

  return (
    <div className={styles.overlay}>
      <div className={styles.modal}>
        <div className={styles.header}>
          <div className={styles.iconWrapper}>
            <Pause size={20} />
          </div>
          <div className={styles.headerText}>
            <h2 className={styles.title}>Confirmation Required</h2>
            {nodeName && (
              <p className={styles.nodeName}>Node: {nodeName}</p>
            )}
          </div>
          <button
            className={styles.closeButton}
            onClick={onCancel}
            disabled={isSubmitting}
          >
            <X size={20} />
          </button>
        </div>

        <div className={styles.body}>
          <div className={styles.prompt}>
            {prompt}
          </div>

          <div className={styles.contextSection}>
            <label className={styles.contextLabel}>
              Additional Context (optional)
            </label>
            <textarea
              className={styles.contextInput}
              placeholder="Provide any additional instructions or context..."
              value={additionalContext}
              onChange={(e) => setAdditionalContext(e.target.value)}
              rows={3}
              disabled={isSubmitting}
            />
          </div>
        </div>

        <div className={styles.footer}>
          <button
            className="btn btn-black-and-white btn-outline"
            onClick={onCancel}
            disabled={isSubmitting}
          >
            Cancel Run
          </button>
          <button
            className="btn btn-primary btn-highlight"
            onClick={handleConfirm}
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <>Processing...</>
            ) : (
              <>
                <Play size={16} />
                Continue
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
