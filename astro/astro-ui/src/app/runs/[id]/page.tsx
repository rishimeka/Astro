'use client';

import { use, useState, useEffect, useCallback, useMemo } from 'react';
import Link from 'next/link';
import {
  Clock,
  CheckCircle,
  AlertCircle,
  LayoutGrid,
  List,
} from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import { StatusBadge } from '@/components/StatusBadge';
import { Spinner } from '@/components/Loading';
import { Markdown } from '@/components/Markdown';
import { ExecutionCanvas, ConfirmationModal, NodeOutputPanel, NodeOutputCard } from '@/components/Execution';
import { useExecutionStream, type NodeExecutionState } from '@/hooks/useExecutionStream';
import { useStars } from '@/hooks/useStars';
import { useDirectives } from '@/hooks/useDirectives';
import { formatDateTime } from '@/lib/utils/date';
import { ENDPOINTS } from '@/lib/api/endpoints';
import { api } from '@/lib/api/client';
import type { NodeOutput, RunStatus, Run, Constellation, StarNode, Edge as AstroEdge, StarSummary, DirectiveSummary } from '@/types/astro';
import type { ConstellationNode } from '@/components/ConstellationBuilder';
import type { Edge as ReactFlowEdge } from 'reactflow';
import dagre from 'dagre';
import { NodeType } from '@/types/astro';
import styles from './page.module.scss';

// Node dimensions for dagre layout
const NODE_DIMENSIONS = {
  start: { width: 60, height: 60 },
  end: { width: 60, height: 60 },
  star: { width: 280, height: 120 },
} as const;

interface RunDetailProps {
  params: Promise<{ id: string }>;
}

// Convert constellation to React Flow format with auto-layout
function convertToReactFlowGraph(
  constellation: Constellation,
  stars: StarSummary[],
  directives: DirectiveSummary[]
): { nodes: ConstellationNode[]; edges: ReactFlowEdge[] } {
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
    const star = stars.find((s) => s.id === node.star_id);
    const directive = directives.find((d) => d.id === star?.directive_id);

    nodes.push({
      id: node.id,
      type: 'star',
      position: node.position,
      data: {
        starId: node.star_id,
        starName: star?.name || node.display_name || 'Unknown Star',
        starType: star?.type || 'worker',
        directiveId: star?.directive_id || '',
        directiveName: directive?.name || 'Unknown Directive',
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

  const edges: ReactFlowEdge[] = constellation.edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    type: 'constellation',
    data: edge.condition ? { condition: edge.condition } : undefined,
  }));

  // Apply dagre auto-layout for proper horizontal positioning
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: 'LR', nodesep: 80, ranksep: 120 });

  // Add nodes to dagre
  nodes.forEach((node) => {
    const dimensions = node.type === 'star'
      ? NODE_DIMENSIONS.star
      : NODE_DIMENSIONS.start;
    dagreGraph.setNode(node.id, {
      width: dimensions.width,
      height: dimensions.height,
    });
  });

  // Add edges to dagre
  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  // Run layout
  dagre.layout(dagreGraph);

  // Apply positions to nodes
  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    const dimensions = node.type === 'star'
      ? NODE_DIMENSIONS.star
      : NODE_DIMENSIONS.start;

    return {
      ...node,
      position: {
        x: nodeWithPosition.x - dimensions.width / 2,
        y: nodeWithPosition.y - dimensions.height / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
}

export default function RunDetailPage({ params }: RunDetailProps) {
  const { id } = use(params);
  const [run, setRun] = useState<Run | null>(null);
  const [constellation, setConstellation] = useState<Constellation | null>(null);
  const [isLoadingRun, setIsLoadingRun] = useState(true);
  const [viewMode, setViewMode] = useState<'graph' | 'list'>('graph');
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const [isConfirmSubmitting, setIsConfirmSubmitting] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Fetch stars and directives for node labels
  const { stars, isLoading: isLoadingStars } = useStars();
  const { directives, isLoading: isLoadingDirectives } = useDirectives();

  const isLoading = isLoadingRun || isLoadingStars || isLoadingDirectives;

  // SSE Stream for live updates - only connect if run is actively running
  const isRunning = run?.status === 'running' || run?.status === 'awaiting_confirmation';

  const {
    state: executionState,
    isConnected,
    clearAwaitingConfirmation,
  } = useExecutionStream({
    runId: id,
    enabled: isRunning, // Don't connect for completed/failed runs
    initialStatus: run?.status, // Pass initial status to prevent reconnection for terminal runs
    onComplete: (output) => {
      setRun((prev) =>
        prev ? { ...prev, status: 'completed', final_output: output } : null
      );
    },
    onError: (error) => {
      setRun((prev) =>
        prev ? { ...prev, status: 'failed', error } : null
      );
    },
  });

  // Build a minimal constellation from run's node_outputs when API fails
  function buildConstellationFromRun(runData: Run): Constellation {
    // Extract unique node IDs from node_outputs and build star nodes
    const nodeOutputs = Object.values(runData.node_outputs);
    const starNodes: StarNode[] = nodeOutputs.map((nodeOutput, index) => ({
      type: NodeType.STAR,
      id: nodeOutput.node_id,
      star_id: nodeOutput.star_id,
      display_name: null,
      variable_bindings: {},
      requires_confirmation: false,
      confirmation_prompt: null,
      position: {
        x: 250,
        y: 100 + (index * 150) // Stack nodes vertically
      },
    }));

    // Create edges: start -> first node, each node -> next, last node -> end
    const edges: AstroEdge[] = [];
    if (starNodes.length > 0) {
      // Start to first node
      edges.push({
        id: 'edge-start-0',
        source: 'start',
        target: starNodes[0].id,
        condition: null,
      });

      // Chain nodes
      for (let i = 0; i < starNodes.length - 1; i++) {
        edges.push({
          id: `edge-${i}-${i + 1}`,
          source: starNodes[i].id,
          target: starNodes[i + 1].id,
          condition: null,
        });
      }

      // Last node to end
      edges.push({
        id: 'edge-last-end',
        source: starNodes[starNodes.length - 1].id,
        target: 'end',
        condition: null,
      });
    } else {
      // No nodes - connect start directly to end
      edges.push({
        id: 'edge-start-end',
        source: 'start',
        target: 'end',
        condition: null,
      });
    }

    const endY = starNodes.length > 0
      ? 100 + (starNodes.length * 150)
      : 200;

    return {
      id: runData.constellation_id,
      name: runData.constellation_name,
      description: '',
      start: {
        id: 'start',
        type: NodeType.START,
        position: { x: 250, y: 0 },
        original_query: null,
        constellation_purpose: null,
      },
      end: {
        id: 'end',
        type: NodeType.END,
        position: { x: 250, y: endY },
      },
      nodes: starNodes,
      edges: edges,
      max_loop_iterations: 5,
      max_retry_attempts: 3,
      retry_delay_base: 1,
      metadata: {},
    };
  }

  // Fetch run data
  useEffect(() => {
    async function fetchData() {
      setIsLoadingRun(true);
      let runData: Run | null = null;

      try {
        // Fetch run from API
        runData = await api.get<Run>(ENDPOINTS.RUN(id));
        setRun(runData);
      } catch (err) {
        console.error('Failed to fetch run:', err);
      }

      // Now try to fetch constellation
      if (runData) {
        try {
          const constData = await api.get<Constellation>(
            ENDPOINTS.CONSTELLATION(runData.constellation_id)
          );
          setConstellation(constData);
        } catch {
          // Constellation API failed - build from run data
          const fallbackConstellation = buildConstellationFromRun(runData);
          setConstellation(fallbackConstellation);
        }
      }

      setIsLoadingRun(false);
    }

    fetchData();
  }, [id]);

  const handleConfirm = useCallback(
    async (additionalContext?: string) => {
      setIsConfirmSubmitting(true);
      try {
        await api.post(`${ENDPOINTS.RUN(id)}/confirm`, {
          proceed: true,
          additional_context: additionalContext,
        });
        clearAwaitingConfirmation();
      } catch (error) {
        console.error('Failed to confirm:', error);
        alert('Failed to send confirmation');
      } finally {
        setIsConfirmSubmitting(false);
      }
    },
    [id, clearAwaitingConfirmation]
  );

  const handleCancelRun = useCallback(async () => {
    try {
      await api.post(`${ENDPOINTS.RUN(id)}/confirm`, {
        proceed: false,
      });
      setRun((prev) => (prev ? { ...prev, status: 'cancelled' } : null));
    } catch (error) {
      console.error('Failed to cancel run:', error);
      alert('Failed to cancel run');
    }
  }, [id]);

  const toggleNode = (nodeId: string) => {
    setExpandedNodes((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  };

  const expandAll = () => {
    if (run) {
      setExpandedNodes(new Set(Object.keys(run.node_outputs)));
    }
  };

  const collapseAll = () => {
    setExpandedNodes(new Set());
  };

  const handleNodeSelect = useCallback((nodeId: string | null) => {
    setSelectedNodeId(nodeId);
  }, []);

  // Build nodeStates from run's node_outputs (for completed/historical runs)
  // Then overlay any live SSE updates on top
  // Note: This must be called before early returns to maintain hook order
  const mergedNodeStates = useMemo(() => {
    // Start with node states from the run's persisted data
    const baseStates: Record<string, NodeExecutionState> = {};

    if (run) {
      for (const [nodeId, nodeOutput] of Object.entries(run.node_outputs)) {
        baseStates[nodeId] = {
          nodeId,
          starId: nodeOutput.star_id,
          status: nodeOutput.status as NodeExecutionState['status'],
          output: nodeOutput.output || undefined,
          error: nodeOutput.error || undefined,
        };
      }
    }

    // Overlay SSE state for live updates
    return { ...baseStates, ...executionState.nodeStates };
  }, [run, executionState.nodeStates]);

  // Get graph data (also before early returns for consistent hook order)
  const graphData = useMemo(() => {
    return constellation ? convertToReactFlowGraph(constellation, stars, directives) : null;
  }, [constellation, stars, directives]);

  // Get selected node info for the output panel (must be before early returns)
  const selectedNodeInfo = useMemo(() => {
    if (!selectedNodeId || !constellation || !run) return null;

    const node = constellation.nodes.find((n) => n.id === selectedNodeId);
    if (!node) return null;

    const star = stars.find((s) => s.id === node.star_id);
    const directive = directives.find((d) => d.id === star?.directive_id);
    const nodeExecutionState = mergedNodeStates[selectedNodeId];
    const persistedOutput = run.node_outputs[selectedNodeId];

    return {
      nodeId: selectedNodeId,
      nodeName: node.display_name || star?.name || 'Unknown',
      starType: star?.type,
      directiveId: directive?.id,
      directiveName: directive?.name,
      executionState: nodeExecutionState,
      persistedOutput,
    };
  }, [selectedNodeId, constellation, stars, directives, mergedNodeStates, run]);

  if (isLoading) {
    return (
      <div className={styles.loadingContainer}>
        <Spinner size="lg" />
        <p>Loading run details...</p>
      </div>
    );
  }

  if (!run) {
    return (
      <div className={styles.errorContainer}>
        <h2>Run Not Found</h2>
        <p>The run with ID &quot;{id}&quot; does not exist.</p>
        <Link href="/runs" className="btn btn-primary btn-outline">
          Back to Runs
        </Link>
      </div>
    );
  }

  const sortedNodeOutputs = Object.values(run.node_outputs).sort((a, b) => {
    if (!a.started_at) return 1;
    if (!b.started_at) return -1;
    return new Date(a.started_at).getTime() - new Date(b.started_at).getTime();
  });

  const duration =
    run.started_at && run.completed_at
      ? Math.round(
          (new Date(run.completed_at).getTime() - new Date(run.started_at).getTime()) / 1000
        )
      : null;

  // Determine current node name for confirmation modal
  const awaitingNodeName = executionState.awaitingConfirmation
    ? stars.find(
        (s) =>
          constellation?.nodes.find(
            (n) => n.id === executionState.awaitingConfirmation?.nodeId
          )?.star_id === s.id
      )?.name
    : undefined;

  return (
    <div className={styles.page}>
      <PageHeader
        title={`Run ${run.id}`}
        titleBadge={<StatusBadge status={run.status as RunStatus} />}
        subtitle={
          <Link href={`/constellations/${run.constellation_id}`}>
            {run.constellation_name}
          </Link>
        }
        meta={
          <div className={styles.metaTags}>
            <span className={styles.metaTag}>
              <Clock size={14} />
              Started: {formatDateTime(run.started_at)}
            </span>
            {run.completed_at && (
              <span className={styles.metaTag}>
                <CheckCircle size={14} />
                Completed: {formatDateTime(run.completed_at)}
              </span>
            )}
            {duration !== null && (
              <span className={styles.metaTag}>
                Duration: {duration}s
              </span>
            )}
          </div>
        }
        backHref="/runs"
        breadcrumbs={[
          { label: 'Runs', href: '/runs' },
          { label: run.id },
        ]}
        actions={
          <div className={styles.actions}>
            {isRunning && isConnected && (
              <span className={styles.liveIndicator}>
                <span className={styles.liveDot} />
                Live
              </span>
            )}
            <div className={styles.viewToggle}>
              <button
                className={`${styles.viewButton} ${viewMode === 'graph' ? styles.active : ''}`}
                onClick={() => setViewMode('graph')}
                title="Graph View"
              >
                <LayoutGrid size={16} />
              </button>
              <button
                className={`${styles.viewButton} ${viewMode === 'list' ? styles.active : ''}`}
                onClick={() => setViewMode('list')}
                title="List View"
              >
                <List size={16} />
              </button>
            </div>
          </div>
        }
      />

      <div className={styles.mainContent}>
        {/* Graph View */}
        {viewMode === 'graph' && graphData && (
          <div className={`${styles.graphContainer} ${selectedNodeId ? styles.withPanel : ''}`}>
            <div className={styles.canvasWrapper}>
              <ExecutionCanvas
                nodes={graphData.nodes}
                edges={graphData.edges}
                nodeStates={mergedNodeStates}
                currentNodeId={executionState.currentNodeId}
                selectedNodeId={selectedNodeId}
                onNodeSelect={handleNodeSelect}
              />
            </div>
            {selectedNodeInfo && (
              <div className={styles.outputPanel}>
                <NodeOutputPanel
                  nodeId={selectedNodeInfo.nodeId}
                  nodeName={selectedNodeInfo.nodeName}
                  starType={selectedNodeInfo.starType}
                  directiveId={selectedNodeInfo.directiveId}
                  directiveName={selectedNodeInfo.directiveName}
                  executionState={selectedNodeInfo.executionState}
                  persistedOutput={selectedNodeInfo.persistedOutput}
                  onClose={() => setSelectedNodeId(null)}
                />
              </div>
            )}
          </div>
        )}

        {/* List View */}
        {viewMode === 'list' && (
          <div className={styles.listContainer}>
            {/* Variables */}
            {Object.keys(run.variables).length > 0 && (
              <section className={styles.section}>
                <h3 className={styles.sectionTitle}>Variables</h3>
                <div className={styles.variables}>
                  {Object.entries(run.variables).map(([key, value]) => (
                    <div key={key} className={styles.variable}>
                      <code className={styles.variableKey}>{key}</code>
                      <span className={styles.variableValue}>{String(value)}</span>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Node Outputs */}
            <section className={styles.section}>
              <div className={styles.nodeOutputsHeader}>
                <h3 className={styles.sectionTitle}>Node Outputs</h3>
                <div className={styles.nodeOutputsActions}>
                  <button className={styles.expandButton} onClick={expandAll}>
                    Expand All
                  </button>
                  <button className={styles.expandButton} onClick={collapseAll}>
                    Collapse All
                  </button>
                </div>
              </div>

              {sortedNodeOutputs.length === 0 ? (
                <p className={styles.emptyText}>No node outputs yet.</p>
              ) : (
                <div className={styles.nodeList}>
                  {sortedNodeOutputs.map((nodeOutput) => {
                    const star = stars.find(s => s.id === nodeOutput.star_id);
                    return (
                      <NodeOutputCard
                        key={nodeOutput.node_id}
                        nodeOutput={nodeOutput}
                        isExpanded={expandedNodes.has(nodeOutput.node_id)}
                        onToggle={() => toggleNode(nodeOutput.node_id)}
                        starName={star?.name}
                      />
                    );
                  })}
                </div>
              )}
            </section>

            {/* Final Output */}
            {run.final_output && (
              <section className={styles.section}>
                <h3 className={styles.sectionTitle}>Final Output</h3>
                <div className={styles.finalOutput}>
                  <Markdown>{run.final_output}</Markdown>
                </div>
              </section>
            )}

            {/* Error */}
            {run.error && (
              <section className={styles.errorSection}>
                <div className={styles.errorHeader}>
                  <AlertCircle size={18} />
                  <h3>Error</h3>
                </div>
                <pre className={styles.errorContent}>{run.error}</pre>
              </section>
            )}
          </div>
        )}
      </div>

      {/* Confirmation Modal */}
      {executionState.awaitingConfirmation && (
        <ConfirmationModal
          nodeId={executionState.awaitingConfirmation.nodeId}
          nodeName={awaitingNodeName}
          prompt={executionState.awaitingConfirmation.prompt}
          onConfirm={handleConfirm}
          onCancel={handleCancelRun}
          isSubmitting={isConfirmSubmitting}
        />
      )}
    </div>
  );
}
