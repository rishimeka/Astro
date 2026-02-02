'use client';

import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Square, Check, X } from 'lucide-react';
import type { EndNodeData } from '../ConstellationBuilder';
import styles from './ExecutionNodes.module.scss';

interface ExecutionEndNodeData extends EndNodeData {
  executionStatus?: 'pending' | 'running' | 'completed' | 'failed';
}

interface ExecutionEndNodeProps extends NodeProps<ExecutionEndNodeData> {
  data: ExecutionEndNodeData;
}

function ExecutionEndNodeComponent({ data }: ExecutionEndNodeProps) {
  const status = data.executionStatus || 'pending';

  const getIcon = () => {
    switch (status) {
      case 'completed':
        return <Check size={20} color="white" />;
      case 'failed':
        return <X size={20} color="white" />;
      default:
        return <Square size={20} color="white" fill="white" />;
    }
  };

  return (
    <div className={`${styles.circularNode} ${styles.endNode} ${styles[status]}`}>
      {/* Input handle on left for horizontal flow */}
      <Handle
        type="target"
        position={Position.Left}
        className={styles.handle}
        id="target"
      />

      {getIcon()}

      <div className={styles.nodeLabel}>{data.label}</div>
    </div>
  );
}

export const ExecutionEndNode = memo(ExecutionEndNodeComponent);
