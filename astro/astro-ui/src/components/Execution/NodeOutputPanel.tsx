'use client';

import { memo } from 'react';
import Link from 'next/link';
import {
  X,
  Clock,
  CheckCircle,
  XCircle,
  RefreshCw,
  Loader2,
  Wrench,
  FileText,
  AlertTriangle,
} from 'lucide-react';
import { Markdown } from '@/components/Markdown';
import type { NodeOutput } from '@/types/astro';
import type { NodeExecutionState } from '@/hooks/useExecutionStream';
import { formatDateTime } from '@/lib/utils/date';
import styles from './NodeOutputPanel.module.scss';

interface NodeOutputPanelProps {
  nodeId: string;
  nodeName?: string;
  starType?: string;
  directiveId?: string;
  directiveName?: string;
  // Can receive either live execution state or persisted node output
  executionState?: NodeExecutionState;
  persistedOutput?: NodeOutput;
  onClose: () => void;
}

function NodeOutputPanelComponent({
  nodeId,
  nodeName,
  starType,
  directiveId,
  directiveName,
  executionState,
  persistedOutput,
  onClose,
}: NodeOutputPanelProps) {
  // Merge live execution state with persisted output
  const status = executionState?.status || persistedOutput?.status || 'pending';
  const output = executionState?.output || persistedOutput?.output;
  const error = executionState?.error || persistedOutput?.error;
  const progress = executionState?.progress;
  const toolCalls = persistedOutput?.tool_calls || [];
  const startedAt = persistedOutput?.started_at;
  const completedAt = persistedOutput?.completed_at;

  const getStatusIcon = () => {
    switch (status) {
      case 'completed':
        return <CheckCircle size={16} className={styles.statusCompleted} />;
      case 'failed':
        return <XCircle size={16} className={styles.statusFailed} />;
      case 'running':
        return <Loader2 size={16} className={styles.statusRunning} />;
      case 'retrying':
        return <RefreshCw size={16} className={styles.statusRetrying} />;
      default:
        return <Clock size={16} className={styles.statusPending} />;
    }
  };

  const getStatusLabel = () => {
    switch (status) {
      case 'completed':
        return 'Completed';
      case 'failed':
        return 'Failed';
      case 'running':
        return 'Running';
      case 'retrying':
        return 'Retrying';
      default:
        return 'Pending';
    }
  };

  return (
    <div className={styles.panel}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerInfo}>
          <h3 className={styles.nodeName}>{nodeName || nodeId}</h3>
          <div className={styles.headerMeta}>
            {starType && (
              <span className={styles.starType}>{starType}</span>
            )}
            <span className={`${styles.statusBadge} ${styles[status]}`}>
              {getStatusIcon()}
              {getStatusLabel()}
            </span>
          </div>
        </div>
        <button className={styles.closeButton} onClick={onClose} aria-label="Close panel">
          <X size={18} />
        </button>
      </div>

      {/* Content */}
      <div className={styles.content}>
        {/* Directive Info */}
        {directiveName && (
          <div className={styles.section}>
            <div className={styles.sectionHeader}>
              <FileText size={14} />
              <span>Directive</span>
            </div>
            {directiveId ? (
              <Link
                href={`/directives/${directiveId}`}
                target="_blank"
                className={styles.directiveLink}
              >
                {directiveName}
              </Link>
            ) : (
              <div className={styles.directiveName}>{directiveName}</div>
            )}
          </div>
        )}

        {/* Progress (live) */}
        {status === 'running' && progress && (
          <div className={styles.section}>
            <div className={styles.sectionHeader}>
              <Loader2 size={14} className={styles.spinnerIcon} />
              <span>Progress</span>
            </div>
            <div className={styles.progressMessage}>{progress}</div>
          </div>
        )}

        {/* Output */}
        {output && (
          <div className={styles.section}>
            <div className={styles.sectionHeader}>
              <CheckCircle size={14} />
              <span>Output</span>
            </div>
            <div className={styles.outputContent}>
              <Markdown>{output}</Markdown>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className={styles.section}>
            <div className={styles.sectionHeader}>
              <AlertTriangle size={14} />
              <span>Error</span>
            </div>
            <pre className={styles.errorContent}>{error}</pre>
          </div>
        )}

        {/* Tool Calls */}
        {toolCalls.length > 0 && (
          <div className={styles.section}>
            <div className={styles.sectionHeader}>
              <Wrench size={14} />
              <span>Tool Calls ({toolCalls.length})</span>
            </div>
            <div className={styles.toolCalls}>
              {toolCalls.map((call, idx) => (
                <div key={idx} className={styles.toolCall}>
                  <code>{JSON.stringify(call, null, 2)}</code>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Timing */}
        {(startedAt || completedAt) && (
          <div className={styles.section}>
            <div className={styles.sectionHeader}>
              <Clock size={14} />
              <span>Timing</span>
            </div>
            <div className={styles.timing}>
              {startedAt && (
                <div className={styles.timingRow}>
                  <span className={styles.timingLabel}>Started:</span>
                  <span className={styles.timingValue}>{formatDateTime(startedAt)}</span>
                </div>
              )}
              {completedAt && (
                <div className={styles.timingRow}>
                  <span className={styles.timingLabel}>Completed:</span>
                  <span className={styles.timingValue}>{formatDateTime(completedAt)}</span>
                </div>
              )}
              {startedAt && completedAt && (
                <div className={styles.timingRow}>
                  <span className={styles.timingLabel}>Duration:</span>
                  <span className={styles.timingValue}>
                    {Math.round(
                      (new Date(completedAt).getTime() - new Date(startedAt).getTime()) / 1000
                    )}s
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Empty state */}
        {!output && !error && !progress && status === 'pending' && (
          <div className={styles.emptyState}>
            <Clock size={24} />
            <p>This node hasn&apos;t executed yet.</p>
          </div>
        )}
      </div>
    </div>
  );
}

export const NodeOutputPanel = memo(NodeOutputPanelComponent);
