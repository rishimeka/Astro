'use client';

import { memo } from 'react';
import {
  EdgeProps,
  getBezierPath,
  EdgeLabelRenderer,
  BaseEdge,
} from 'reactflow';
import styles from './ExecutionEdge.module.scss';

interface ExecutionEdgeData {
  condition?: 'continue' | 'loop';
}

interface ExecutionEdgeProps extends EdgeProps<ExecutionEdgeData> {
  data?: ExecutionEdgeData;
}

// Condition label styles
const continueConditionStyle = {
  fontSize: '10px',
  fontWeight: 500,
  color: '#10B981',
  backgroundColor: 'rgba(16, 185, 129, 0.15)',
  padding: '2px 6px',
  borderRadius: '4px',
  textTransform: 'uppercase' as const,
  letterSpacing: '0.5px',
};

const loopConditionStyle = {
  fontSize: '10px',
  fontWeight: 500,
  color: '#F59E0B',
  backgroundColor: 'rgba(245, 158, 11, 0.15)',
  padding: '2px 6px',
  borderRadius: '4px',
  textTransform: 'uppercase' as const,
  letterSpacing: '0.5px',
};

function ExecutionEdgeComponent({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  style,
  markerEnd,
}: ExecutionEdgeProps) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  // Get condition label style
  const getConditionStyle = () => {
    if (data?.condition === 'continue') return continueConditionStyle;
    if (data?.condition === 'loop') return loopConditionStyle;
    return null;
  };

  const conditionStyle = getConditionStyle();

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={style}
      />

      <EdgeLabelRenderer>
        {/* Condition label only - no delete button */}
        {conditionStyle && (
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY - 15}px)`,
              pointerEvents: 'none',
              ...conditionStyle,
            }}
            className="nodrag nopan"
          >
            {data?.condition}
          </div>
        )}
      </EdgeLabelRenderer>
    </>
  );
}

export const ExecutionEdge = memo(ExecutionEdgeComponent);
