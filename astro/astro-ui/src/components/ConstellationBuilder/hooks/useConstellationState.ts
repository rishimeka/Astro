'use client';

import { useCallback } from 'react';
import {
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  OnNodesChange,
  OnEdgesChange,
  XYPosition,
  Node,
  Edge,
} from 'reactflow';
import dagre from 'dagre';
import {
  ConstellationNode,
  ConstellationEdge,
  ConstellationGraph,
  PaletteItem,
  StarNodeData,
  StartNodeData,
  EndNodeData,
} from '../types';
import { NODE_DIMENSIONS } from '../nodes/nodeStyles';

// Default start and end nodes (horizontal layout: left to right)
const defaultStartNode: Node = {
  id: 'start',
  type: 'start',
  position: { x: 0, y: 200 },
  data: { label: 'Start' } as StartNodeData,
  deletable: false,
};

const defaultEndNode: Node = {
  id: 'end',
  type: 'end',
  position: { x: 600, y: 200 },
  data: { label: 'End' } as EndNodeData,
  deletable: false,
};

interface UseConstellationStateOptions {
  initialNodes?: ConstellationNode[];
  initialEdges?: ConstellationEdge[];
  onChange?: (graph: ConstellationGraph) => void;
}

export interface UseConstellationStateReturn {
  nodes: Node[];
  edges: Edge[];
  setNodes: React.Dispatch<React.SetStateAction<Node[]>>;
  setEdges: React.Dispatch<React.SetStateAction<Edge[]>>;
  onNodesChange: OnNodesChange;
  onEdgesChange: OnEdgesChange;
  onConnect: (connection: Connection) => void;
  addNode: (item: PaletteItem, position: XYPosition) => void;
  removeNode: (nodeId: string) => void;
  updateNodeData: (nodeId: string, data: Partial<StarNodeData>) => void;
  getGraph: () => ConstellationGraph;
  loadGraph: (graph: ConstellationGraph) => void;
  autoLayout: () => void;
}

export function useConstellationState(
  options: UseConstellationStateOptions = {}
): UseConstellationStateReturn {
  const {
    initialNodes,
    initialEdges = [],
    onChange,
  } = options;

  const startingNodes: Node[] = initialNodes
    ? (initialNodes as Node[])
    : [defaultStartNode, defaultEndNode];

  const [nodes, setNodes, onNodesChange] = useNodesState(startingNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges as Edge[]);

  // Handle new connections
  const onConnect = useCallback(
    (connection: Connection) => {
      // Determine edge data based on source handle
      const edgeData =
        connection.sourceHandle === 'loop'
          ? { condition: 'loop' as const }
          : connection.sourceHandle === 'continue'
            ? { condition: 'continue' as const }
            : undefined;

      const newEdge: Edge = {
        ...connection,
        id: `${connection.source}-${connection.target}-${Date.now()}`,
        type: 'constellation',
        data: edgeData,
        source: connection.source || '',
        target: connection.target || '',
      };

      setEdges((eds) => addEdge(newEdge, eds));

      if (onChange) {
        onChange({
          nodes: nodes as ConstellationNode[],
          edges: [...edges, newEdge] as ConstellationEdge[]
        });
      }
    },
    [setEdges, onChange, nodes, edges]
  );

  // Add a new node from the palette
  const addNode = useCallback(
    (item: PaletteItem, position: XYPosition) => {
      const newNode: Node = {
        id: `star-${Date.now()}`,
        type: 'star',
        position,
        data: {
          starId: item.starId,
          starName: item.starName,
          starType: item.starType,
          directiveId: item.directiveId,
          directiveName: item.directiveName,
          requiresConfirmation: false,
          hasProbes: false,
          probeCount: 0,
          hasVariables: false,
          variableCount: 0,
        } as StarNodeData,
      };

      setNodes((nds) => [...nds, newNode]);

      if (onChange) {
        onChange({
          nodes: [...nodes, newNode] as ConstellationNode[],
          edges: edges as ConstellationEdge[]
        });
      }
    },
    [setNodes, onChange, nodes, edges]
  );

  // Remove a node (cannot remove start/end)
  const removeNode = useCallback(
    (nodeId: string) => {
      if (nodeId === 'start' || nodeId === 'end') {
        console.warn('Cannot delete Start or End nodes');
        return;
      }

      setNodes((nds) => nds.filter((n) => n.id !== nodeId));
      setEdges((eds) =>
        eds.filter((e) => e.source !== nodeId && e.target !== nodeId)
      );

      if (onChange) {
        const updatedNodes = nodes.filter((n) => n.id !== nodeId);
        const updatedEdges = edges.filter(
          (e) => e.source !== nodeId && e.target !== nodeId
        );
        onChange({
          nodes: updatedNodes as ConstellationNode[],
          edges: updatedEdges as ConstellationEdge[]
        });
      }
    },
    [setNodes, setEdges, onChange, nodes, edges]
  );

  // Update node data
  const updateNodeData = useCallback(
    (nodeId: string, data: Partial<StarNodeData>) => {
      setNodes((nds) =>
        nds.map((node) => {
          if (node.id === nodeId && node.type === 'star') {
            return {
              ...node,
              data: { ...node.data, ...data },
            };
          }
          return node;
        })
      );
    },
    [setNodes]
  );

  // Get current graph state
  const getGraph = useCallback((): ConstellationGraph => {
    return {
      nodes: nodes as ConstellationNode[],
      edges: edges as ConstellationEdge[]
    };
  }, [nodes, edges]);

  // Load a graph
  const loadGraph = useCallback(
    (graph: ConstellationGraph) => {
      setNodes(graph.nodes as Node[]);
      setEdges(graph.edges as Edge[]);
    },
    [setNodes, setEdges]
  );

  // Auto-layout using dagre
  const autoLayout = useCallback(() => {
    const dagreGraph = new dagre.graphlib.Graph();
    dagreGraph.setDefaultEdgeLabel(() => ({}));
    dagreGraph.setGraph({ rankdir: 'LR', nodesep: 80, ranksep: 120 });

    // Add nodes to dagre
    nodes.forEach((node) => {
      const dimensions =
        node.type === 'star' ? NODE_DIMENSIONS.star : NODE_DIMENSIONS.start;
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
      const dimensions =
        node.type === 'star' ? NODE_DIMENSIONS.star : NODE_DIMENSIONS.start;

      return {
        ...node,
        position: {
          x: nodeWithPosition.x - dimensions.width / 2,
          y: nodeWithPosition.y - dimensions.height / 2,
        },
      };
    });

    setNodes(layoutedNodes);

    if (onChange) {
      onChange({
        nodes: layoutedNodes as ConstellationNode[],
        edges: edges as ConstellationEdge[]
      });
    }
  }, [nodes, edges, setNodes, onChange]);

  return {
    nodes,
    edges,
    setNodes,
    setEdges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    addNode,
    removeNode,
    updateNodeData,
    getGraph,
    loadGraph,
    autoLayout,
  };
}
