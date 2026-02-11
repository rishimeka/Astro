'use client';

import { memo, useState, useEffect, useRef } from 'react';
import {
  Play,
  CheckCircle,
  XCircle,
  Loader2,
  Clock,
  Terminal,
  Wrench,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
  MousePointerClick,
  FileOutput,
} from 'lucide-react';
import { Markdown } from '@/components/Markdown';
import styles from './OutputViewer.module.scss';

interface NodeOutput {
  node_id: string;
  star_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  output?: string;
  error?: string;
  tool_calls?: any[];
  started_at?: string;
  completed_at?: string;
}

interface OutputViewerProps {
  status: 'idle' | 'running' | 'completed' | 'failed';
  selectedNodeId: string | null;
  nodeOutputs: Record<string, NodeOutput>;
  progressMessages: string[];
  finalOutput?: string;
  error?: string;
  onNodeSelect?: (nodeId: string) => void;
}

function OutputViewerComponent({
  status,
  selectedNodeId,
  nodeOutputs,
  progressMessages,
  finalOutput,
  error,
  onNodeSelect,
}: OutputViewerProps) {
  const [toolCallsExpanded, setToolCallsExpanded] = useState(false);
  const progressContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll progress messages to bottom when new messages arrive
  useEffect(() => {
    if (progressContainerRef.current) {
      progressContainerRef.current.scrollTop = progressContainerRef.current.scrollHeight;
    }
  }, [progressMessages]);

  const selectedNodeOutput = selectedNodeId ? nodeOutputs[selectedNodeId] : null;

  const getStatusIcon = () => {
    switch (status) {
      case 'running':
        return <Loader2 size={14} />;
      case 'completed':
        return <CheckCircle size={14} />;
      case 'failed':
        return <XCircle size={14} />;
      default:
        return <Clock size={14} />;
    }
  };

  const getStatusLabel = () => {
    switch (status) {
      case 'running':
        return 'Running';
      case 'completed':
        return 'Completed';
      case 'failed':
        return 'Failed';
      default:
        return 'Ready';
    }
  };

  const getNodeStatusIcon = (nodeStatus: string) => {
    switch (nodeStatus) {
      case 'running':
        return <Loader2 size={12} />;
      case 'completed':
        return <CheckCircle size={12} />;
      case 'failed':
        return <XCircle size={12} />;
      default:
        return <Clock size={12} />;
    }
  };

  const formatTimestamp = (index: number) => {
    // Simple timestamp format for progress messages
    const now = new Date();
    const hours = now.getHours().toString().padStart(2, '0');
    const minutes = now.getMinutes().toString().padStart(2, '0');
    const seconds = now.getSeconds().toString().padStart(2, '0');
    return `${hours}:${minutes}:${seconds}`;
  };

  // Pre-execution empty state
  if (status === 'idle' && progressMessages.length === 0 && !selectedNodeId) {
    return (
      <div className={styles.viewer}>
        <div className={styles.header}>
          <div className={styles.headerTitle}>
            <h3 className={styles.title}>Output</h3>
            <span className={`${styles.statusBadge} ${styles.idle}`}>
              {getStatusIcon()}
              {getStatusLabel()}
            </span>
          </div>
        </div>
        <div className={styles.content}>
          <div className={styles.emptyState}>
            <Play size={48} />
            <h4 className={styles.emptyTitle}>Ready to Execute</h4>
            <p className={styles.emptyDescription}>
              Click the Start button to begin running this constellation. Output will appear here as nodes execute.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.viewer}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerTitle}>
          <h3 className={styles.title}>Output</h3>
          <span className={`${styles.statusBadge} ${styles[status]}`}>
            {getStatusIcon()}
            {getStatusLabel()}
          </span>
        </div>
      </div>

      {/* Content */}
      <div className={styles.content}>
        {/* Error display (top priority if failed) */}
        {status === 'failed' && error && (
          <div className={styles.section}>
            <div className={styles.errorHeader}>
              <AlertTriangle size={16} />
              <span>Execution Failed</span>
            </div>
            <pre className={styles.errorContent}>{error}</pre>
          </div>
        )}

        {/* Final output (when completed) */}
        {status === 'completed' && finalOutput && (
          <div className={styles.section}>
            <div className={styles.finalOutput}>
              <div className={styles.finalOutputLabel}>
                <FileOutput size={14} />
                <span>Final Output</span>
              </div>
              <Markdown>{finalOutput}</Markdown>
            </div>
          </div>
        )}

        {/* Selected node output */}
        {selectedNodeId && (
          <div className={styles.section}>
            <div className={styles.nodeOutputHeader}>
              <div className={styles.sectionHeader}>
                <Terminal size={14} />
                <span>Node Output</span>
              </div>
              {selectedNodeOutput && (
                <span className={`${styles.nodeStatus} ${styles[selectedNodeOutput.status]}`}>
                  {getNodeStatusIcon(selectedNodeOutput.status)}
                  {selectedNodeOutput.status}
                </span>
              )}
            </div>
            <span className={styles.nodeName}>{selectedNodeId}</span>

            {selectedNodeOutput ? (
              <>
                {/* Node output content */}
                {selectedNodeOutput.output && (
                  <div className={styles.outputContent}>
                    <Markdown>{selectedNodeOutput.output}</Markdown>
                  </div>
                )}

                {/* Node error */}
                {selectedNodeOutput.error && (
                  <pre className={styles.errorContent}>{selectedNodeOutput.error}</pre>
                )}

                {/* Node tool calls */}
                {selectedNodeOutput.tool_calls && selectedNodeOutput.tool_calls.length > 0 && (
                  <div className={styles.section}>
                    <button
                      className={styles.toolCallsToggle}
                      onClick={() => setToolCallsExpanded(!toolCallsExpanded)}
                      type="button"
                    >
                      {toolCallsExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      <Wrench size={12} />
                      <span>Tool Calls</span>
                      <span className={styles.toolCallsCount}>
                        {selectedNodeOutput.tool_calls.length}
                      </span>
                    </button>

                    {toolCallsExpanded && (
                      <div className={styles.toolCallsList}>
                        {selectedNodeOutput.tool_calls.map((call, idx) => (
                          <div key={idx} className={styles.toolCall}>
                            <div className={styles.toolCallHeader}>
                              <span className={styles.toolCallName}>
                                {call.name || call.function?.name || `Tool ${idx + 1}`}
                              </span>
                            </div>
                            <div className={styles.toolCallBody}>
                              <code>
                                {JSON.stringify(call.arguments || call.input || call, null, 2)}
                              </code>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Empty node output state */}
                {!selectedNodeOutput.output &&
                  !selectedNodeOutput.error &&
                  selectedNodeOutput.status === 'pending' && (
                    <div className={styles.noNodeSelected}>
                      <Clock size={20} />
                      <p>This node hasn&apos;t executed yet.</p>
                    </div>
                  )}
              </>
            ) : (
              <div className={styles.noNodeSelected}>
                <Clock size={20} />
                <p>No output data available for this node.</p>
              </div>
            )}
          </div>
        )}

        {/* No node selected hint */}
        {!selectedNodeId && status !== 'idle' && (
          <div className={styles.noNodeSelected}>
            <MousePointerClick size={24} />
            <p>Click a node on the canvas to view its output.</p>
          </div>
        )}

        {/* Progress messages stream */}
        {progressMessages.length > 0 && (
          <div className={styles.section}>
            <div className={styles.sectionHeader}>
              <Loader2 size={14} className={status === 'running' ? styles.spinning : undefined} />
              <span>Progress</span>
            </div>
            <div className={styles.progressContainer} ref={progressContainerRef}>
              {progressMessages.map((message, index) => (
                <div key={index} className={styles.progressMessage}>
                  <span className={styles.progressTimestamp}>{formatTimestamp(index)}</span>
                  {message}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export const OutputViewer = memo(OutputViewerComponent);
