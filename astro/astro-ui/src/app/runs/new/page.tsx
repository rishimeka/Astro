'use client';

import { useState, useEffect, Suspense, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
  Eye,
} from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import { Spinner } from '@/components/Loading';
import { ExecutionCanvas, ConfirmationModal, VariableForm } from '@/components/Execution';
import { ENDPOINTS } from '@/lib/api/endpoints';
import { api } from '@/lib/api/client';
import type { Constellation, RunStatus } from '@/types/astro';
import type { ConstellationNode } from '@/components/ConstellationBuilder';
import type { Edge } from 'reactflow';
import type { ExecutionState } from '@/hooks/useExecutionStream';
import styles from './page.module.scss';

// Convert constellation to React Flow format for visualization
function convertToReactFlowGraph(
  constellation: Constellation
): { nodes: ConstellationNode[]; edges: Edge[] } {
  const nodes: ConstellationNode[] = [];

  nodes.push({
    id: constellation.start.id,
    type: 'start',
    position: constellation.start.position,
    data: { label: 'Start' },
  } as ConstellationNode);

  nodes.push({
    id: constellation.end.id,
    type: 'end',
    position: constellation.end.position,
    data: { label: 'End' },
  } as ConstellationNode);

  constellation.nodes.forEach((node) => {
    nodes.push({
      id: node.id,
      type: 'star',
      position: node.position,
      data: {
        starId: node.star_id,
        starName: node.display_name || node.star_id,
        starType: 'worker',
        directiveId: '',
        directiveName: '',
        displayName: node.display_name || undefined,
        requiresConfirmation: node.requires_confirmation,
        confirmationPrompt: node.confirmation_prompt || undefined,
        hasProbes: false,
        probeCount: 0,
        hasVariables: false,
        variableCount: 0,
      },
    } as ConstellationNode);
  });

  const edges: Edge[] = constellation.edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    type: 'constellation',
    data: edge.condition ? { condition: edge.condition } : undefined,
  }));

  return { nodes, edges };
}

// SSE Event types
type SSEEventType =
  | 'run_started'
  | 'node_started'
  | 'node_progress'
  | 'node_completed'
  | 'node_failed'
  | 'node_retrying'
  | 'awaiting_confirmation'
  | 'run_completed'
  | 'run_failed';

function NewRunContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const constellationId = searchParams.get('constellation');

  const [constellation, setConstellation] = useState<Constellation | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Execution state
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionState, setExecutionState] = useState<ExecutionState | null>(null);
  const [isConfirmSubmitting, setIsConfirmSubmitting] = useState(false);

  // Fetch constellation
  useEffect(() => {
    async function fetchConstellation() {
      if (!constellationId) {
        setError('No constellation specified');
        setIsLoading(false);
        return;
      }

      try {
        const data = await api.get<Constellation>(ENDPOINTS.CONSTELLATION(constellationId));
        setConstellation(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load constellation');
      } finally {
        setIsLoading(false);
      }
    }

    fetchConstellation();
  }, [constellationId]);

  // Handle cancel from VariableForm - navigate back
  const handleVariableCancel = () => {
    router.push('/runs');
  };

  const startExecution = useCallback(async (variables: Record<string, string>) => {
    if (!constellationId) return;

    setIsExecuting(true);
    setExecutionState({
      runId: 'pending',
      status: 'running',
      nodeStates: {},
      currentNodeId: null,
      awaitingConfirmation: null,
      finalOutput: null,
      error: null,
    });

    try {
      // Use fetch directly for SSE stream
      const response = await fetch(ENDPOINTS.CONSTELLATION_RUN(constellationId), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ variables }),
      });

      if (!response.ok) {
        throw new Error(`Failed to start run: ${response.statusText}`);
      }

      // Parse SSE stream
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let eventType: SSEEventType | null = null;

        for (const line of lines) {
          if (line.startsWith('event:')) {
            eventType = line.slice(6).trim() as SSEEventType;
          } else if (line.startsWith('data:') && eventType) {
            try {
              const data = JSON.parse(line.slice(5).trim());
              handleSSEEvent(eventType, data);
            } catch {
              console.error('Failed to parse SSE data:', line);
            }
            eventType = null;
          }
        }
      }
    } catch (err) {
      setExecutionState((prev) =>
        prev
          ? { ...prev, status: 'failed', error: err instanceof Error ? err.message : 'Execution failed' }
          : null
      );
    }
  }, [constellationId]);

  // Handle VariableForm submission - start execution with the provided variables
  const handleVariableSubmit = useCallback((variables: Record<string, string>) => {
    startExecution(variables);
  }, [startExecution]);

  const handleSSEEvent = (eventType: SSEEventType, data: Record<string, unknown>) => {
    setExecutionState((prev) => {
      if (!prev) return prev;

      const newState = { ...prev };

      switch (eventType) {
        case 'run_started':
          newState.status = 'running';
          if (data.run_id) newState.runId = data.run_id as string;
          break;

        case 'node_started':
          newState.currentNodeId = data.node_id as string;
          newState.nodeStates = {
            ...newState.nodeStates,
            [data.node_id as string]: {
              nodeId: data.node_id as string,
              starId: data.star_id as string | undefined,
              status: 'running',
            },
          };
          break;

        case 'node_progress': {
          const existingNode = newState.nodeStates[data.node_id as string];
          newState.nodeStates = {
            ...newState.nodeStates,
            [data.node_id as string]: {
              ...existingNode,
              nodeId: data.node_id as string,
              status: 'running',
              progress: data.message as string,
            },
          };
          break;
        }

        case 'node_completed': {
          const existingCompletedNode = newState.nodeStates[data.node_id as string];
          newState.nodeStates = {
            ...newState.nodeStates,
            [data.node_id as string]: {
              ...existingCompletedNode,
              nodeId: data.node_id as string,
              status: 'completed',
              output: data.output as string,
            },
          };
          if (newState.currentNodeId === data.node_id) {
            newState.currentNodeId = null;
          }
          break;
        }

        case 'node_failed': {
          const existingFailedNode = newState.nodeStates[data.node_id as string];
          newState.nodeStates = {
            ...newState.nodeStates,
            [data.node_id as string]: {
              ...existingFailedNode,
              nodeId: data.node_id as string,
              status: 'failed',
              error: data.error as string,
            },
          };
          if (newState.currentNodeId === data.node_id) {
            newState.currentNodeId = null;
          }
          break;
        }

        case 'node_retrying': {
          const existingRetryNode = newState.nodeStates[data.node_id as string];
          newState.nodeStates = {
            ...newState.nodeStates,
            [data.node_id as string]: {
              ...existingRetryNode,
              nodeId: data.node_id as string,
              status: 'retrying',
            },
          };
          break;
        }

        case 'awaiting_confirmation':
          newState.status = 'awaiting_confirmation';
          newState.runId = data.run_id as string;
          newState.awaitingConfirmation = {
            nodeId: data.node_id as string,
            prompt: data.prompt as string,
          };
          break;

        case 'run_completed':
          newState.status = 'completed';
          newState.runId = data.run_id as string;
          newState.finalOutput = data.final_output as string;
          newState.currentNodeId = null;
          break;

        case 'run_failed':
          newState.status = 'failed';
          if (data.run_id) newState.runId = data.run_id as string;
          newState.error = data.error as string;
          newState.currentNodeId = null;
          break;
      }

      return newState;
    });
  };

  const handleConfirm = async (additionalContext?: string) => {
    if (!executionState?.runId || executionState.runId === 'pending') return;

    setIsConfirmSubmitting(true);
    try {
      await api.post(`${ENDPOINTS.RUN(executionState.runId)}/confirm`, {
        proceed: true,
        additional_context: additionalContext,
      });
      setExecutionState((prev) =>
        prev ? { ...prev, awaitingConfirmation: null, status: 'running' } : null
      );
    } catch (err) {
      console.error('Failed to confirm:', err);
      alert('Failed to send confirmation');
    } finally {
      setIsConfirmSubmitting(false);
    }
  };

  const handleCancelRun = async () => {
    if (!executionState?.runId || executionState.runId === 'pending') return;

    try {
      await api.post(`${ENDPOINTS.RUN(executionState.runId)}/confirm`, {
        proceed: false,
      });
      setExecutionState((prev) =>
        prev ? { ...prev, status: 'cancelled' as RunStatus } : null
      );
    } catch (err) {
      console.error('Failed to cancel run:', err);
      alert('Failed to cancel run');
    }
  };

  const viewRunDetails = () => {
    if (executionState?.runId && executionState.runId !== 'pending') {
      router.push(`/runs/${executionState.runId}`);
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className={styles.loadingContainer}>
        <Spinner size="lg" />
        <p>Loading constellation...</p>
      </div>
    );
  }

  // Error state
  if (error || !constellation) {
    return (
      <div className={styles.errorContainer}>
        <AlertCircle size={48} className={styles.errorIcon} />
        <h2>Unable to Start Run</h2>
        <p>{error || 'Constellation not found'}</p>
        <Link href="/constellations" className="btn btn-primary btn-outline">
          Back to Constellations
        </Link>
      </div>
    );
  }

  const graphData = convertToReactFlowGraph(constellation);
  const isComplete = executionState?.status === 'completed';
  const isFailed = executionState?.status === 'failed';
  const isAwaitingConfirmation = executionState?.status === 'awaiting_confirmation';

  return (
    <div className={styles.page}>
      <PageHeader
        title={isExecuting ? 'Running Constellation' : 'New Run'}
        subtitle={constellation.name}
        backHref="/runs"
        breadcrumbs={[
          { label: 'Runs', href: '/runs' },
          { label: 'New Run' },
        ]}
        actions={
          isExecuting ? (
            <div className={styles.actions}>
              {executionState?.status === 'running' && (
                <span className={styles.liveIndicator}>
                  <span className={styles.liveDot} />
                  Running
                </span>
              )}
              {isComplete && (
                <span className={styles.completeIndicator}>
                  <CheckCircle size={16} />
                  Complete
                </span>
              )}
              {isFailed && (
                <span className={styles.failedIndicator}>
                  <XCircle size={16} />
                  Failed
                </span>
              )}
            </div>
          ) : undefined
        }
      />

      {/* Pre-execution: Split-panel layout with graph preview and variables form */}
      {!isExecuting && (
        <section className={styles.preExecutionLayout}>
          {/* Left Panel: Graph Preview */}
          <div className={styles.graphPreviewPanel}>
            <div className={styles.panelHeader}>
              <Eye size={16} />
              <h3>Constellation Preview</h3>
            </div>
            <div className={styles.graphPreviewContainer}>
              <ExecutionCanvas
                nodes={graphData.nodes}
                edges={graphData.edges}
                nodeStates={{}}
                currentNodeId={null}
              />
            </div>
          </div>

          {/* Right Panel: Variables Form */}
          <div className={styles.variablesPanel}>
            <VariableForm
              constellationId={constellationId!}
              onSubmit={handleVariableSubmit}
              onCancel={handleVariableCancel}
            />
          </div>
        </section>
      )}

      {/* During/After execution: Show graph and status */}
      {isExecuting && executionState && (
        <>
          {/* Status Overview */}
          <section className={styles.statusSection}>
            <div className={styles.statusOverview}>
              <div className={styles.statusMain}>
                <span className={`${styles.statusBadge} ${styles[executionState.status]}`}>
                  {executionState.status === 'running' && <Loader2 size={14} className={styles.spinning} />}
                  {executionState.status === 'completed' && <CheckCircle size={14} />}
                  {executionState.status === 'failed' && <XCircle size={14} />}
                  {executionState.status === 'awaiting_confirmation' && <AlertCircle size={14} />}
                  {executionState.status.replace('_', ' ')}
                </span>
                <span className={styles.constellationName}>{constellation.name}</span>
              </div>
              {isComplete && executionState.runId !== 'pending' && (
                <button className="btn btn-primary btn-outline" onClick={viewRunDetails}>
                  View Run Details
                </button>
              )}
            </div>
          </section>

          {/* Graph Visualization */}
          <div className={styles.graphContainer}>
            <ExecutionCanvas
              nodes={graphData.nodes}
              edges={graphData.edges}
              nodeStates={executionState.nodeStates}
              currentNodeId={executionState.currentNodeId}
            />
          </div>

          {/* Final Output */}
          {isComplete && executionState.finalOutput && (
            <section className={styles.outputSection}>
              <h3 className={styles.sectionTitle}>Output</h3>
              <pre className={styles.outputContent}>{executionState.finalOutput}</pre>
            </section>
          )}

          {/* Error */}
          {isFailed && executionState.error && (
            <section className={styles.errorSection}>
              <div className={styles.errorHeader}>
                <AlertCircle size={18} />
                <h3>Error</h3>
              </div>
              <pre className={styles.errorContent}>{executionState.error}</pre>
            </section>
          )}
        </>
      )}

      {/* Confirmation Modal */}
      {isAwaitingConfirmation && executionState?.awaitingConfirmation && (
        <ConfirmationModal
          nodeId={executionState.awaitingConfirmation.nodeId}
          prompt={executionState.awaitingConfirmation.prompt}
          onConfirm={handleConfirm}
          onCancel={handleCancelRun}
          isSubmitting={isConfirmSubmitting}
        />
      )}
    </div>
  );
}

export default function NewRunPage() {
  return (
    <Suspense
      fallback={
        <div className={styles.loadingContainer}>
          <Spinner size="lg" />
          <p>Loading...</p>
        </div>
      }
    >
      <NewRunContent />
    </Suspense>
  );
}
