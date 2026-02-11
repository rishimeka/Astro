'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  ChevronDown,
  ChevronUp,
  Play,
  Check,
  Loader2,
  AlertCircle,
  Wrench,
  Brain,
  Clock,
  CheckCircle,
  XCircle,
} from 'lucide-react';
import type { NodeStatus, ToolCall, ExecutionProgressState } from '@/hooks/useChat';
import styles from './Chat.module.scss';

interface ExecutionProgressProps {
  runId: string;
  constellationName: string;
  currentNode?: string;
  nodes?: NodeStatus[];
  toolCalls?: ToolCall[];
  thoughts?: string;
  totalNodes?: number;
  durationMs?: number;
  isRunning?: boolean;
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const minutes = Math.floor(ms / 60000);
  const seconds = Math.floor((ms % 60000) / 1000);
  return `${minutes}m ${seconds}s`;
}

function NodeItem({ node }: { node: NodeStatus }) {
  const getNodeIcon = (status: NodeStatus['status']) => {
    switch (status) {
      case 'completed':
        return <Check size={14} />;
      case 'running':
        return <Loader2 size={14} className={styles.spinning} />;
      case 'failed':
        return <AlertCircle size={14} />;
      default:
        return <div className={styles.pendingDot} />;
    }
  };

  return (
    <div className={`${styles.executionProgressNode} ${styles[node.status]}`}>
      <span className={styles.executionProgressNodeIcon}>
        {getNodeIcon(node.status)}
      </span>
      <span className={styles.executionProgressNodeName}>
        {node.name}
      </span>
      {node.starType && (
        <span className={styles.nodeStarType}>
          {node.starType}
        </span>
      )}
      {node.durationMs !== undefined && node.status !== 'running' && (
        <span className={styles.nodeDuration}>
          {formatDuration(node.durationMs)}
        </span>
      )}
      {node.error && (
        <span className={styles.nodeError} title={node.error}>
          {node.error.length > 30 ? `${node.error.slice(0, 30)}...` : node.error}
        </span>
      )}
    </div>
  );
}

function ToolCallItem({ tool }: { tool: ToolCall }) {
  const getToolIcon = () => {
    switch (tool.status) {
      case 'completed':
        return <CheckCircle size={12} className={styles.toolSuccess} />;
      case 'failed':
        return <XCircle size={12} className={styles.toolError} />;
      default:
        return <Loader2 size={12} className={styles.spinning} />;
    }
  };

  return (
    <div className={`${styles.toolCallItem} ${styles[tool.status]}`}>
      <Wrench size={12} className={styles.toolIcon} />
      <span className={styles.toolName}>{tool.toolName}</span>
      {getToolIcon()}
      {tool.durationMs !== undefined && tool.status !== 'running' && (
        <span className={styles.toolDuration}>{formatDuration(tool.durationMs)}</span>
      )}
    </div>
  );
}

export default function ExecutionProgress({
  runId,
  constellationName,
  currentNode,
  nodes = [],
  toolCalls = [],
  thoughts = '',
  totalNodes = 0,
  durationMs,
  isRunning = true,
}: ExecutionProgressProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [showThoughts, setShowThoughts] = useState(false);

  const completedCount = nodes.filter((n) => n.status === 'completed').length;
  const failedCount = nodes.filter((n) => n.status === 'failed').length;
  const effectiveTotal = totalNodes || nodes.length;
  const progress = effectiveTotal > 0 ? (completedCount / effectiveTotal) * 100 : 0;

  const activeToolCalls = toolCalls.filter(t => t.status === 'running');
  const hasThoughts = thoughts.length > 0;

  return (
    <div className={styles.executionProgress}>
      <div className={styles.executionProgressHeader}>
        <div className={styles.executionProgressInfo}>
          <div className={`${styles.executionProgressIcon} ${!isRunning ? styles.completed : ''}`}>
            {isRunning ? (
              <Loader2 size={14} className={styles.spinning} />
            ) : failedCount > 0 ? (
              <AlertCircle size={14} />
            ) : (
              <Check size={14} />
            )}
          </div>
          <div className={styles.executionProgressText}>
            <span className={styles.executionProgressLabel}>
              {isRunning ? 'Running' : failedCount > 0 ? 'Failed' : 'Completed'}: {constellationName}
            </span>
            <span className={styles.executionProgressCurrentNode}>
              {isRunning && currentNode ? (
                <>
                  <Loader2 size={10} className={styles.spinning} style={{ marginRight: 4 }} />
                  {currentNode}
                </>
              ) : (
                `${completedCount}/${effectiveTotal} nodes`
              )}
            </span>
          </div>
        </div>
        <div className={styles.executionProgressActions}>
          {durationMs !== undefined && (
            <span className={styles.executionDuration}>
              <Clock size={12} />
              {formatDuration(durationMs)}
            </span>
          )}
          <Link
            href={`/runs/${runId}`}
            className={styles.executionProgressViewLink}
          >
            View run
          </Link>
          <button
            type="button"
            className={styles.executionProgressExpandButton}
            onClick={() => setIsExpanded(!isExpanded)}
            aria-label={isExpanded ? 'Collapse details' : 'Expand details'}
          >
            {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>
      </div>

      {/* Progress bar */}
      <div className={styles.executionProgressBar}>
        <div
          className={`${styles.executionProgressBarFill} ${failedCount > 0 ? styles.hasError : ''}`}
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Active tool calls indicator */}
      {activeToolCalls.length > 0 && (
        <div className={styles.activeToolCalls}>
          <Wrench size={12} />
          <span>
            {activeToolCalls.length} tool{activeToolCalls.length > 1 ? 's' : ''} running
          </span>
        </div>
      )}

      {/* Thoughts indicator */}
      {hasThoughts && (
        <button
          type="button"
          className={styles.thoughtsToggle}
          onClick={() => setShowThoughts(!showThoughts)}
        >
          <Brain size={12} />
          <span>{showThoughts ? 'Hide' : 'Show'} reasoning</span>
          {showThoughts ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </button>
      )}

      {/* Thoughts content */}
      {showThoughts && hasThoughts && (
        <div className={styles.thoughtsContent}>
          {thoughts}
          {isRunning && <span className={styles.thoughtsCursor}>|</span>}
        </div>
      )}

      {/* Expanded node list */}
      {isExpanded && nodes.length > 0 && (
        <div className={styles.executionProgressNodes}>
          {nodes.map((node) => (
            <NodeItem key={node.id} node={node} />
          ))}
        </div>
      )}

      {/* Tool calls list */}
      {isExpanded && toolCalls.length > 0 && (
        <div className={styles.toolCallsList}>
          <div className={styles.toolCallsHeader}>
            <Wrench size={12} />
            <span>Tool calls ({toolCalls.length})</span>
          </div>
          {toolCalls.slice(-5).map((tool) => (
            <ToolCallItem key={tool.callId} tool={tool} />
          ))}
          {toolCalls.length > 5 && (
            <div className={styles.toolCallsMore}>
              +{toolCalls.length - 5} more
            </div>
          )}
        </div>
      )}
    </div>
  );
}
