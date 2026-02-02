'use client';

import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Square } from 'lucide-react';
import { EndNodeData } from '../types';
import { endNodeStyle, handleStyle, nodeLabelStyle } from './nodeStyles';

interface EndNodeProps extends NodeProps<EndNodeData> {
  selected: boolean;
}

function EndNodeComponent({ data, selected }: EndNodeProps) {
  const nodeStyle = {
    ...endNodeStyle,
    ...(selected && {
      borderColor: 'var(--accent-primary)',
      boxShadow: '0 0 0 3px rgba(108, 114, 255, 0.4)',
    }),
  };

  return (
    <div style={nodeStyle}>
      <Handle
        type="target"
        position={Position.Left}
        style={handleStyle}
        id="target"
      />

      <Square size={20} color="white" fill="white" />

      <div style={nodeLabelStyle}>{data.label}</div>
    </div>
  );
}

export const EndNode = memo(EndNodeComponent);
