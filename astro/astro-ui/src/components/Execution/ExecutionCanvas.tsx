'use client';

import { useMemo, useCallback, useEffect, useRef } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
  ReactFlowProvider,
  useReactFlow,
  Node,
  Edge,
  NodeMouseHandler,
} from 'reactflow';
import 'reactflow/dist/style.css';

import { ExecutionStartNode } from './ExecutionStartNode';
import { ExecutionEndNode } from './ExecutionEndNode';
import { ExecutionStarNode } from './ExecutionStarNode';
import { ExecutionEdge } from './ExecutionEdge';
import type { NodeExecutionState } from '@/hooks/useExecutionStream';
import type { ConstellationNode } from '../ConstellationBuilder';
import styles from './ExecutionCanvas.module.scss';

// Register custom node types
const nodeTypes = {
  start: ExecutionStartNode,
  end: ExecutionEndNode,
  star: ExecutionStarNode,
};

// Register custom edge types
const edgeTypes = {
  constellation: ExecutionEdge,
};

// Default edge options
const defaultEdgeOptions = {
  type: 'constellation',
  animated: false,
  style: { stroke: 'rgba(255, 255, 255, 0.3)', strokeWidth: 2 },
};

// Hide React Flow attribution
const proOptions = { hideAttribution: true };

interface ExecutionCanvasProps {
  nodes: ConstellationNode[];
  edges: Edge[];
  nodeStates: Record<string, NodeExecutionState>;
  currentNodeId: string | null;
  selectedNodeId?: string | null;
  onNodeSelect?: (nodeId: string | null) => void;
}

function ExecutionCanvasInner({
  nodes: initialNodes,
  edges,
  nodeStates,
  currentNodeId,
  selectedNodeId,
  onNodeSelect,
}: ExecutionCanvasProps) {
  const { fitView } = useReactFlow();
  const isPanelOpen = selectedNodeId !== null;
  const prevPanelOpenRef = useRef(isPanelOpen);

  // Re-fit view when panel opens/closes (after CSS transition)
  useEffect(() => {
    if (prevPanelOpenRef.current !== isPanelOpen) {
      prevPanelOpenRef.current = isPanelOpen;
      // Wait for CSS transition to complete (300ms in the SCSS)
      const timer = setTimeout(() => {
        fitView({ padding: 0.2, duration: 200 });
      }, 320);
      return () => clearTimeout(timer);
    }
  }, [isPanelOpen, fitView]);

  // Handle node click
  const handleNodeClick: NodeMouseHandler = useCallback(
    (_, node) => {
      // Only allow selecting star nodes (not start/end)
      if (node.type === 'star') {
        onNodeSelect?.(node.id);
      }
    },
    [onNodeSelect]
  );

  // Handle pane click to deselect
  const handlePaneClick = useCallback(() => {
    onNodeSelect?.(null);
  }, [onNodeSelect]);

  // Enhance nodes with execution state
  const nodesWithState = useMemo(() => {
    return initialNodes.map((node) => {
      const executionState = nodeStates[node.id];
      const isCurrentNode = currentNodeId === node.id;
      const isSelected = selectedNodeId === node.id;

      return {
        ...node,
        data: {
          ...node.data,
          executionStatus: executionState?.status || 'pending',
          executionProgress: executionState?.progress,
          executionError: executionState?.error,
          executionOutput: executionState?.output,
          isCurrentNode,
          isSelected,
        },
      };
    });
  }, [initialNodes, nodeStates, currentNodeId, selectedNodeId]);

  // Enhance edges to animate when their source node is running or completed
  const edgesWithState = useMemo(() => {
    return edges.map((edge) => {
      const sourceState = nodeStates[edge.source];
      const isAnimated =
        sourceState?.status === 'running' || sourceState?.status === 'completed';

      return {
        ...edge,
        animated: isAnimated,
        style: {
          ...edge.style,
          stroke:
            sourceState?.status === 'completed'
              ? '#10B981'
              : sourceState?.status === 'running'
                ? 'var(--accent-primary)'
                : sourceState?.status === 'failed'
                  ? 'var(--accent-danger)'
                  : 'rgba(255, 255, 255, 0.3)',
          strokeWidth: isAnimated ? 3 : 2,
        },
      };
    });
  }, [edges, nodeStates]);

  // Get node color for minimap
  const nodeColor = (node: Node) => {
    const executionState = nodeStates[node.id];
    if (executionState?.status === 'completed') return '#10B981';
    if (executionState?.status === 'running') return '#4A9DEA';
    if (executionState?.status === 'failed') return '#EF4444';
    if (node.type === 'start') return '#4A9DEA';
    if (node.type === 'end') return 'rgba(255, 255, 255, 0.3)';
    return 'rgba(74, 157, 234, 0.3)';
  };

  return (
    <div className={styles.canvasContainer}>
      <ReactFlow
        nodes={nodesWithState}
        edges={edgesWithState}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
        fitView
        proOptions={proOptions}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={true}
        onNodeClick={handleNodeClick}
        onPaneClick={handlePaneClick}
        panOnScroll
        zoomOnScroll
        minZoom={0.25}
        maxZoom={2}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color="rgba(255, 255, 255, 0.05)"
        />
        <Controls className={styles.controls} showInteractive={false} />
        <MiniMap
          className={styles.minimap}
          nodeColor={nodeColor}
          maskColor="rgba(13, 17, 23, 0.8)"
          pannable
          zoomable
        />
      </ReactFlow>
    </div>
  );
}

// Wrapper component that provides ReactFlow context
export function ExecutionCanvas(props: ExecutionCanvasProps) {
  return (
    <ReactFlowProvider>
      <ExecutionCanvasInner {...props} />
    </ReactFlowProvider>
  );
}
