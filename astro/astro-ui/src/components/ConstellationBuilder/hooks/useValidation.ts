'use client';

import { useMemo, useCallback } from 'react';
import { Node, Edge } from 'reactflow';
import { ValidationError, StarNodeData } from '../types';

interface UseValidationOptions {
  nodes: Node[];
  edges: Edge[];
}

export interface UseValidationReturn {
  errors: ValidationError[];
  validate: () => ValidationError[];
  isValid: boolean;
}

export function useValidation({
  nodes,
  edges,
}: UseValidationOptions): UseValidationReturn {
  // Validation function
  const validate = useCallback((): ValidationError[] => {
    const errors: ValidationError[] = [];

    // 1. Exactly one StartNode
    const startNodes = nodes.filter((n) => n.type === 'start');
    if (startNodes.length === 0) {
      errors.push({
        message: 'Missing Start node',
        severity: 'error',
      });
    } else if (startNodes.length > 1) {
      errors.push({
        message: 'Multiple Start nodes found (only one allowed)',
        severity: 'error',
      });
    }

    // 2. Exactly one EndNode
    const endNodes = nodes.filter((n) => n.type === 'end');
    if (endNodes.length === 0) {
      errors.push({
        message: 'Missing End node',
        severity: 'error',
      });
    } else if (endNodes.length > 1) {
      errors.push({
        message: 'Multiple End nodes found (only one allowed)',
        severity: 'error',
      });
    }

    // 3. All StarNodes must have at least one incoming edge (except those connected to Start)
    const starNodes = nodes.filter((n) => n.type === 'star');
    const nodesWithIncoming = new Set(edges.map((e) => e.target));

    starNodes.forEach((node) => {
      if (!nodesWithIncoming.has(node.id)) {
        const data = node.data as StarNodeData | undefined;
        errors.push({
          nodeId: node.id,
          message: `Node "${data?.starName || node.id}" has no incoming edges`,
          severity: 'error',
        });
      }
    });

    // 4. All StarNodes must have at least one outgoing edge
    const nodesWithOutgoing = new Set(edges.map((e) => e.source));

    starNodes.forEach((node) => {
      if (!nodesWithOutgoing.has(node.id)) {
        const data = node.data as StarNodeData | undefined;
        errors.push({
          nodeId: node.id,
          message: `Node "${data?.starName || node.id}" has no outgoing edges`,
          severity: 'error',
        });
      }
    });

    // 5. EndNode must be reachable from StartNode
    if (startNodes.length === 1 && endNodes.length === 1) {
      const startId = startNodes[0].id;
      const endId = endNodes[0].id;

      // BFS to check reachability
      const visited = new Set<string>();
      const queue = [startId];

      while (queue.length > 0) {
        const currentId = queue.shift()!;
        if (visited.has(currentId)) continue;
        visited.add(currentId);

        const outgoingEdges = edges.filter((e) => e.source === currentId);
        outgoingEdges.forEach((e) => {
          if (!visited.has(e.target)) {
            queue.push(e.target);
          }
        });
      }

      if (!visited.has(endId)) {
        errors.push({
          message: 'End node is not reachable from Start',
          severity: 'error',
        });
      }
    }

    // 6. Check for cycles (except explicit EvalStar loops)
    // For now, we allow cycles through EvalStar loop handles
    // A more sophisticated check would distinguish between valid loops and invalid cycles

    // 7. EvalStar must have exactly 2 outgoing edges with conditions "continue" and "loop"
    const evalNodes = nodes.filter((n) => {
      if (n.type !== 'star') return false;
      const data = n.data as StarNodeData | undefined;
      return data?.starType === 'eval';
    });

    evalNodes.forEach((node) => {
      const data = node.data as StarNodeData | undefined;
      const outgoingEdges = edges.filter((e) => e.source === node.id);

      if (outgoingEdges.length !== 2) {
        errors.push({
          nodeId: node.id,
          message: `Eval node "${data?.starName || node.id}" must have exactly 2 outgoing edges (continue and loop)`,
          severity: 'error',
        });
      } else {
        const hasLoop = outgoingEdges.some((e) => e.data?.condition === 'loop');
        const hasContinue = outgoingEdges.some(
          (e) => e.data?.condition === 'continue'
        );

        if (!hasLoop) {
          errors.push({
            nodeId: node.id,
            message: `Eval node "${data?.starName || node.id}" missing "loop" edge`,
            severity: 'error',
          });
        }
        if (!hasContinue) {
          errors.push({
            nodeId: node.id,
            message: `Eval node "${data?.starName || node.id}" missing "continue" edge`,
            severity: 'error',
          });
        }
      }
    });

    // 8. Confirmation nodes cannot have multiple incoming edges
    const confirmationNodes = nodes.filter((n) => {
      if (n.type !== 'star') return false;
      const data = n.data as StarNodeData | undefined;
      return data?.requiresConfirmation;
    });

    confirmationNodes.forEach((node) => {
      const data = node.data as StarNodeData | undefined;
      const incomingEdges = edges.filter((e) => e.target === node.id);
      if (incomingEdges.length > 1) {
        errors.push({
          nodeId: node.id,
          message: `Confirmation node "${data?.starName || node.id}" cannot have multiple incoming edges`,
          severity: 'warning',
        });
      }
    });

    // Check Start node has no incoming edges
    if (startNodes.length === 1) {
      const startIncoming = edges.filter((e) => e.target === startNodes[0].id);
      if (startIncoming.length > 0) {
        errors.push({
          nodeId: startNodes[0].id,
          message: 'Start node cannot have incoming edges',
          severity: 'error',
        });
      }
    }

    // Check End node has no outgoing edges
    if (endNodes.length === 1) {
      const endOutgoing = edges.filter((e) => e.source === endNodes[0].id);
      if (endOutgoing.length > 0) {
        errors.push({
          nodeId: endNodes[0].id,
          message: 'End node cannot have outgoing edges',
          severity: 'error',
        });
      }
    }

    return errors;
  }, [nodes, edges]);

  // Memoized validation results
  const errors = useMemo(() => validate(), [validate]);
  const isValid = errors.filter((e) => e.severity === 'error').length === 0;

  return {
    errors,
    validate,
    isValid,
  };
}
