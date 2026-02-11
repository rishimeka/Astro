'use client';

import { useState } from 'react';
import { Sparkles, Check, X, Loader2 } from 'lucide-react';
import styles from './DirectiveGenerationCard.module.scss';

export interface DirectiveGenerationCardProps {
  offered?: boolean;
  previewContent?: string;
  directiveName?: string;
  selectedProbes?: string[];
  onApprove?: () => void;
  onReject?: () => void;
  isApproving?: boolean;
}

export default function DirectiveGenerationCard({
  offered,
  previewContent,
  directiveName,
  selectedProbes = [],
  onApprove,
  onReject,
  isApproving = false,
}: DirectiveGenerationCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Offered state - waiting for generation or showing found directive
  if (offered && !previewContent) {
    const isComplete = !isApproving && directiveName;

    return (
      <div className={styles.card}>
        <div className={styles.header}>
          <Sparkles size={20} className={styles.icon} />
          <span className={styles.title}>
            {isComplete ? 'Found Existing Directive' : 'Creating New Directive'}
          </span>
        </div>
        <p className={styles.message}>
          {isComplete
            ? 'Found a similar workflow from a previous query. Using it for this task.'
            : "I don't have a specialized workflow for this yet. Let me create one for you."}
        </p>
        {!isComplete && (
          <div className={styles.loading}>
            <Loader2 size={16} className={styles.spinner} />
            <span>Analyzing task and selecting tools...</span>
          </div>
        )}
        {isComplete && selectedProbes.length > 0 && (
          <div className={styles.probes}>
            <span className={styles.probesLabel}>Tools:</span>
            <div className={styles.probesList}>
              {selectedProbes.map((probe) => (
                <span key={probe} className={styles.probeBadge}>
                  {probe}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // Preview state - show directive for approval
  if (previewContent) {
    return (
      <div className={styles.card}>
        <div className={styles.header}>
          <Sparkles size={20} className={styles.icon} />
          <span className={styles.title}>New Directive Created</span>
        </div>

        {directiveName && (
          <div className={styles.directiveName}>
            <strong>{directiveName}</strong>
          </div>
        )}

        {selectedProbes.length > 0 && (
          <div className={styles.probes}>
            <span className={styles.probesLabel}>Tools:</span>
            <div className={styles.probesList}>
              {selectedProbes.map((probe) => (
                <span key={probe} className={styles.probeBadge}>
                  {probe}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className={styles.preview}>
          <button
            className={styles.expandButton}
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? 'Hide' : 'Show'} Directive Content
          </button>

          {isExpanded && (
            <div className={styles.previewContent}>
              <pre>{previewContent}</pre>
            </div>
          )}
        </div>

        <div className={styles.actions}>
          <button
            className={`${styles.button} ${styles.approve}`}
            onClick={onApprove}
            disabled={isApproving}
          >
            {isApproving ? (
              <>
                <Loader2 size={16} className={styles.spinner} />
                Saving...
              </>
            ) : (
              <>
                <Check size={16} />
                Approve & Use
              </>
            )}
          </button>

          <button
            className={`${styles.button} ${styles.reject}`}
            onClick={onReject}
            disabled={isApproving}
          >
            <X size={16} />
            Reject
          </button>
        </div>

        <p className={styles.note}>
          Approving will save this directive for future use on similar queries.
        </p>
      </div>
    );
  }

  return null;
}
