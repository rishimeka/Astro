'use client';

import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Play } from 'lucide-react';
import { StartNodeData } from '../types';
import { startNodeStyle, handleStyle, nodeLabelStyle } from './nodeStyles';

interface StartNodeProps extends NodeProps<StartNodeData> {
  selected: boolean;
}

function StartNodeComponent({ data, selected }: StartNodeProps) {
  const nodeStyle = {
    ...startNodeStyle,
    ...(selected && {
      boxShadow: '0 0 0 3px rgba(74, 157, 234, 0.4), 0 4px 12px rgba(74, 157, 234, 0.3)',
    }),
  };

  return (
    <div style={nodeStyle}>
      <Play size={24} color="white" fill="white" style={{ marginLeft: 2 }} />

      <Handle
        type="source"
        position={Position.Right}
        style={handleStyle}
        id="source"
      />

      <div style={nodeLabelStyle}>{data.label}</div>
    </div>
  );
}

export const StartNode = memo(StartNodeComponent);
