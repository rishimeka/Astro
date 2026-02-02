'use client';

import { useCallback, useEffect, forwardRef, useImperativeHandle } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
  ReactFlowProvider,
  SelectionMode,
  Node,
  OnSelectionChangeFunc,
} from 'reactflow';
import 'reactflow/dist/style.css';

import { StartNode, EndNode, StarNode } from './nodes';
import { ConstellationEdge } from './edges';
import { useConstellationState, useDragAndDrop, useValidation } from './hooks';
import { CanvasProps, CanvasRef, StarNodeData } from './types';
import styles from './Canvas.module.scss';

// Register custom node types
const nodeTypes = {
  start: StartNode,
  end: EndNode,
  star: StarNode,
};

// Register custom edge types
const edgeTypes = {
  constellation: ConstellationEdge,
};

// Default edge options
const defaultEdgeOptions = {
  type: 'constellation',
  animated: false,
  style: { stroke: 'rgba(255, 255, 255, 0.3)', strokeWidth: 2 },
};

// Connection line style when dragging
const connectionLineStyle = {
  stroke: '#6C72FF',
  strokeWidth: 2,
};

// Hide React Flow attribution
const proOptions = { hideAttribution: true };

const CanvasInner = forwardRef<CanvasRef, CanvasProps>(function CanvasInner({
  initialNodes,
  initialEdges,
  onChange,
  onValidationChange,
  onNodeSelect,
  readOnly = false,
}, ref) {
  const {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    addNode,
    removeNode,
    updateNodeData,
    autoLayout,
  } = useConstellationState({
    initialNodes,
    initialEdges,
    onChange,
  });

  const { errors } = useValidation({ nodes, edges });

  const { onDragOver, onDrop } = useDragAndDrop({ addNode });

  // Handle selection changes
  const handleSelectionChange: OnSelectionChangeFunc = useCallback(({ nodes: selectedNodes }) => {
    if (!onNodeSelect) return;

    if (selectedNodes.length === 1) {
      const node = selectedNodes[0];
      onNodeSelect({
        id: node.id,
        type: node.type as 'start' | 'end' | 'star',
        data: node.data,
      });
    } else {
      onNodeSelect(null);
    }
  }, [onNodeSelect]);

  // Expose methods to parent via ref
  useImperativeHandle(ref, () => ({
    autoLayout,
    updateNode: (nodeId: string, updates: Partial<StarNodeData>) => {
      updateNodeData(nodeId, updates);
    },
  }), [autoLayout, updateNodeData]);

  // Notify parent of validation changes
  useEffect(() => {
    if (onValidationChange) {
      onValidationChange(errors);
    }
  }, [errors, onValidationChange]);

  // Auto-layout on initial load
  useEffect(() => {
    if (nodes.length > 2) {
      autoLayout();
    }
    // Only run once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Handle keyboard shortcuts
  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (readOnly) return;

      // Delete selected nodes
      if (event.key === 'Delete' || event.key === 'Backspace') {
        const selectedNodes = nodes.filter((n: Node) => n.selected);
        selectedNodes.forEach((node: Node) => {
          if (node.id !== 'start' && node.id !== 'end') {
            removeNode(node.id);
          }
        });
      }
    },
    [nodes, removeNode, readOnly]
  );

  // Handle delete edge events from custom edge component
  useEffect(() => {
    const handleDeleteEdge = (event: CustomEvent<{ id: string }>) => {
      if (readOnly) return;
      onEdgesChange([{ type: 'remove', id: event.detail.id }]);
    };

    window.addEventListener('deleteEdge', handleDeleteEdge as EventListener);
    return () => {
      window.removeEventListener('deleteEdge', handleDeleteEdge as EventListener);
    };
  }, [onEdgesChange, readOnly]);

  // Handle delete node events from StarNode menu
  useEffect(() => {
    const handleDeleteNode = (event: CustomEvent<{ id: string }>) => {
      if (readOnly) return;
      const nodeId = event.detail.id;
      // Don't allow deleting start/end nodes
      if (nodeId !== 'start' && nodeId !== 'end') {
        removeNode(nodeId);
      }
    };

    window.addEventListener('deleteNode', handleDeleteNode as EventListener);
    return () => {
      window.removeEventListener('deleteNode', handleDeleteNode as EventListener);
    };
  }, [removeNode, readOnly]);

  // Handle select node events from StarNode menu (for Edit)
  useEffect(() => {
    const handleSelectNode = (event: CustomEvent<{ id: string }>) => {
      const nodeId = event.detail.id;
      const node = nodes.find((n: Node) => n.id === nodeId);
      if (node && onNodeSelect) {
        onNodeSelect({
          id: node.id,
          type: node.type as 'start' | 'end' | 'star',
          data: node.data,
        });
      }
    };

    window.addEventListener('selectNode', handleSelectNode as EventListener);
    return () => {
      window.removeEventListener('selectNode', handleSelectNode as EventListener);
    };
  }, [nodes, onNodeSelect]);

  // Get node color for minimap
  const nodeColor = (node: Node) => {
    if (node.type === 'start') return '#6C72FF';
    if (node.type === 'end') return 'rgba(255, 255, 255, 0.3)';
    return 'rgba(108, 114, 255, 0.5)';
  };

  return (
    <div
      className={styles.canvasContainer}
      onKeyDown={handleKeyDown}
      tabIndex={0}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={readOnly ? undefined : onNodesChange}
        onEdgesChange={readOnly ? undefined : onEdgesChange}
        onConnect={readOnly ? undefined : onConnect}
        onDragOver={readOnly ? undefined : onDragOver}
        onDrop={readOnly ? undefined : onDrop}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
        connectionLineStyle={connectionLineStyle}
        fitView
        snapToGrid
        snapGrid={[20, 20]}
        proOptions={proOptions}
        nodesDraggable={!readOnly}
        nodesConnectable={!readOnly}
        elementsSelectable={!readOnly}
        selectionMode={SelectionMode.Partial}
        multiSelectionKeyCode="Shift"
        deleteKeyCode={null} // We handle delete manually
        onSelectionChange={handleSelectionChange}
        panOnScroll
        zoomOnScroll
        minZoom={0.25}
        maxZoom={2}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color="rgba(255, 255, 255, 0.25)"
        />
        <Controls
          className={styles.controls}
          showInteractive={false}
        />
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
});

// Wrapper component that provides ReactFlow context
export const Canvas = forwardRef<CanvasRef, CanvasProps>(function Canvas(props, ref) {
  return (
    <ReactFlowProvider>
      <CanvasInner ref={ref} {...props} />
    </ReactFlowProvider>
  );
});
