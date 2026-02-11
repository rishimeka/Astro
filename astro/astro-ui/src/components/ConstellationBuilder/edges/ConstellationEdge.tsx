'use client';

import { memo, useState } from 'react';
import {
  EdgeProps,
  getBezierPath,
  EdgeLabelRenderer,
  BaseEdge,
} from 'reactflow';
import { X } from 'lucide-react';
import { ConstellationEdgeData } from '../types';
import {
  continueConditionStyle,
  loopConditionStyle,
} from './edgeStyles';
import styles from './ConstellationEdge.module.scss';

interface ConstellationEdgeProps extends EdgeProps<ConstellationEdgeData> {
  data?: ConstellationEdgeData;
}

function ConstellationEdgeComponent({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  selected,
  markerEnd,
}: ConstellationEdgeProps) {
  const [isHovered, setIsHovered] = useState(false);

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const edgeColor = selected
    ? 'var(--accent-primary)'
    : 'rgba(255, 255, 255, 0.3)';

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    // Edge deletion is handled by React Flow's onEdgesChange
    const event = new CustomEvent('deleteEdge', { detail: { id } });
    window.dispatchEvent(event);
  };

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
        style={{ stroke: edgeColor, strokeWidth: 2 }}
        interactionWidth={20}
      />

      {/* Invisible wider path for hover detection */}
      <path
        d={edgePath}
        fill="none"
        strokeWidth={20}
        stroke="transparent"
        className={styles.hoverPath}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      />

      <EdgeLabelRenderer>
        {/* Condition label */}
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

        {/* Delete button on hover */}
        {isHovered && (
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              pointerEvents: 'all',
            }}
            className="nodrag nopan"
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
          >
            <button
              className={styles.deleteButton}
              onClick={handleDelete}
              title="Delete edge"
            >
              <X size={12} color="white" />
            </button>
          </div>
        )}
      </EdgeLabelRenderer>
    </>
  );
}

export const ConstellationEdge = memo(ConstellationEdgeComponent);
