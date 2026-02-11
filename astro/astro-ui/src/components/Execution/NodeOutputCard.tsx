'use client';

import { Clock, CheckCircle, XCircle, ChevronDown, ChevronRight } from 'lucide-react';
import { Markdown } from '@/components/Markdown';
import { Spinner } from '@/components/Loading';
import { formatDateTime } from '@/lib/utils/date';
import type { NodeOutput } from '@/types/astro';
import styles from './NodeOutputCard.module.scss';

export interface NodeOutputCardProps {
  nodeOutput: NodeOutput;
  isExpanded: boolean;
  onToggle: () => void;
  starName?: string;
}

function getNodeStatusIcon(status: NodeOutput['status']) {
  switch (status) {
    case 'completed':
      return <CheckCircle size={16} className={styles.statusCompleted} />;
    case 'failed':
      return <XCircle size={16} className={styles.statusFailed} />;
    case 'running':
      return <Spinner size="sm" />;
    case 'pending':
    default:
      return <Clock size={16} className={styles.statusPending} />;
  }
}

export function NodeOutputCard({
  nodeOutput,
  isExpanded,
  onToggle,
  starName,
}: NodeOutputCardProps) {
  return (
    <div className={`${styles.nodeCard} ${styles[`status-${nodeOutput.status}`]}`}>
      <button className={styles.nodeHeader} onClick={onToggle}>
        <div className={styles.nodeHeaderLeft}>
          {getNodeStatusIcon(nodeOutput.status)}
          <span className={styles.nodeName}>{starName || nodeOutput.star_id}</span>
          <span className={styles.nodeId}>{nodeOutput.node_id}</span>
        </div>
        <div className={styles.nodeHeaderRight}>
          {nodeOutput.started_at && (
            <span className={styles.nodeTime}>
              {formatDateTime(nodeOutput.started_at)}
            </span>
          )}
          {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </div>
      </button>

      {isExpanded && (
        <div className={styles.nodeBody}>
          {nodeOutput.output && (
            <div className={styles.nodeSection}>
              <h4 className={styles.nodeSectionTitle}>Output</h4>
              <div className={styles.outputContent}>
                <Markdown>{nodeOutput.output}</Markdown>
              </div>
            </div>
          )}

          {nodeOutput.error && (
            <div className={styles.nodeSection}>
              <h4 className={styles.nodeSectionTitle}>Error</h4>
              <pre className={styles.errorContent}>{nodeOutput.error}</pre>
            </div>
          )}

          {nodeOutput.tool_calls && nodeOutput.tool_calls.length > 0 && (
            <div className={styles.nodeSection}>
              <h4 className={styles.nodeSectionTitle}>Tool Calls</h4>
              <div className={styles.toolCalls}>
                {nodeOutput.tool_calls.map((call, idx) => (
                  <div key={idx} className={styles.toolCall}>
                    <code>{JSON.stringify(call, null, 2)}</code>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className={styles.nodeMeta}>
            {nodeOutput.started_at && (
              <span>Started: {formatDateTime(nodeOutput.started_at)}</span>
            )}
            {nodeOutput.completed_at && (
              <span>Completed: {formatDateTime(nodeOutput.completed_at)}</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
