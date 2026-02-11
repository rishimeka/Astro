'use client';

import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Play, Check } from 'lucide-react';
import type { StartNodeData } from '../ConstellationBuilder';
import styles from './ExecutionNodes.module.scss';

interface ExecutionStartNodeData extends StartNodeData {
  executionStatus?: 'pending' | 'running' | 'completed' | 'failed';
}

interface ExecutionStartNodeProps extends NodeProps<ExecutionStartNodeData> {
  data: ExecutionStartNodeData;
}

function ExecutionStartNodeComponent({ data }: ExecutionStartNodeProps) {
  const status = data.executionStatus || 'completed'; // Start node is always complete

  return (
    <div className={`${styles.circularNode} ${styles.startNode} ${styles[status]}`}>
      {status === 'completed' ? (
        <Check size={24} color="white" />
      ) : (
        <Play size={24} color="white" fill="white" style={{ marginLeft: 2 }} />
      )}

      {/* Output handle on right for horizontal flow */}
      <Handle
        type="source"
        position={Position.Right}
        className={styles.handle}
        id="source"
      />

      <div className={styles.nodeLabel}>{data.label}</div>
    </div>
  );
}

export const ExecutionStartNode = memo(ExecutionStartNodeComponent);
