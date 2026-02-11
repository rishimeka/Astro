import { Loader2, Sparkles, Wrench } from 'lucide-react';
import styles from './ZeroShotProgress.module.scss';

interface ZeroShotProgressProps {
  thinkingMessage?: string;
  selectedDirectives?: string[];
  directiveReasoning?: string;
  boundTools?: string[];
}

export default function ZeroShotProgress({
  thinkingMessage,
  selectedDirectives,
  directiveReasoning,
  boundTools,
}: ZeroShotProgressProps) {
  const hasProgress = thinkingMessage || selectedDirectives?.length || boundTools?.length;

  if (!hasProgress) return null;

  return (
    <div className={styles.progressContainer}>
      {thinkingMessage && (
        <div className={styles.thinkingRow}>
          <Loader2 size={16} className={styles.spinner} />
          <span className={styles.thinkingText}>{thinkingMessage}</span>
        </div>
      )}

      {selectedDirectives && selectedDirectives.length > 0 && (
        <div className={styles.directivesRow}>
          <div className={styles.directivesHeader}>
            <Sparkles size={16} className={styles.directiveIcon} />
            <span className={styles.directiveLabel}>Selected Directives:</span>
            <span className={styles.directiveIds}>
              {selectedDirectives.join(', ')}
            </span>
          </div>
          {directiveReasoning && (
            <p className={styles.directiveReasoning}>{directiveReasoning}</p>
          )}
        </div>
      )}

      {boundTools && boundTools.length > 0 && (
        <div className={styles.toolsRow}>
          <Wrench size={16} className={styles.toolIcon} />
          <span className={styles.toolLabel}>Tools:</span>
          <div className={styles.toolsList}>
            {boundTools.map((tool) => (
              <span key={tool} className={styles.toolBadge}>
                {tool}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
