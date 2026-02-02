'use client';

import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import {
  Cog,
  GitBranch,
  CheckCircle,
  Combine,
  Play,
  FileText,
  Loader2,
  Check,
  X,
  RefreshCw,
} from 'lucide-react';
import type { StarNodeData, StarType } from '../ConstellationBuilder';
import { starTypeColors } from '../ConstellationBuilder/nodes/nodeStyles';
import styles from './ExecutionNodes.module.scss';

interface ExecutionStarNodeData extends StarNodeData {
  executionStatus?: 'pending' | 'running' | 'completed' | 'failed' | 'retrying';
  executionProgress?: string;
  executionError?: string;
  executionOutput?: string;
  isCurrentNode?: boolean;
  isSelected?: boolean;
}

interface ExecutionStarNodeProps extends NodeProps<ExecutionStarNodeData> {
  data: ExecutionStarNodeData;
}

// Icon mapping for star types
const starTypeIcons: Record<StarType, typeof Cog> = {
  worker: Cog,
  planning: GitBranch,
  eval: CheckCircle,
  synthesis: Combine,
  execution: Play,
  docex: FileText,
};

function ExecutionStarNodeComponent({ data }: ExecutionStarNodeProps) {
  const Icon = starTypeIcons[data.starType];
  const iconColor = starTypeColors[data.starType];
  const isEvalStar = data.starType === 'eval';
  const status = data.executionStatus || 'pending';
  const isSelected = data.isSelected || false;

  // Status indicator icon
  const getStatusIcon = () => {
    switch (status) {
      case 'running':
        return <Loader2 size={14} className={styles.spinnerIcon} />;
      case 'completed':
        return <Check size={14} />;
      case 'failed':
        return <X size={14} />;
      case 'retrying':
        return <RefreshCw size={14} className={styles.spinnerIcon} />;
      default:
        return null;
    }
  };

  return (
    <div className={`${styles.starNode} ${styles[status]} ${isSelected ? styles.selected : ''}`}>
      {/* Input Handle - Left side for horizontal flow */}
      <Handle
        type="target"
        position={Position.Left}
        className={styles.handle}
        id="target"
      />

      {/* Header */}
      <div className={styles.starHeader}>
        <div className={styles.headerLeft}>
          <div
            className={styles.iconWrapper}
            style={{ backgroundColor: `${iconColor}20` }}
          >
            <Icon size={14} color={iconColor} />
          </div>
          <span className={styles.starName}>
            {data.displayName || data.starName}
          </span>
        </div>
        <div className={`${styles.statusIndicator} ${styles[status]}`}>
          {getStatusIcon()}
        </div>
      </div>

      {/* Body */}
      <div className={styles.starBody}>
        <div className={styles.directive}>
          {data.directiveName}
        </div>

        {/* Progress message */}
        {status === 'running' && data.executionProgress && (
          <div className={styles.progress}>
            {data.executionProgress}
          </div>
        )}

        {/* Error message */}
        {status === 'failed' && data.executionError && (
          <div className={styles.error}>
            {data.executionError}
          </div>
        )}
      </div>

      {/* Output Handles - Right side for horizontal flow */}
      {isEvalStar ? (
        <>
          <Handle
            type="source"
            position={Position.Right}
            className={styles.handle}
            style={{ top: '30%' }}
            id="loop"
          />
          <Handle
            type="source"
            position={Position.Right}
            className={styles.handle}
            style={{ top: '70%' }}
            id="continue"
          />
        </>
      ) : (
        <Handle
          type="source"
          position={Position.Right}
          className={styles.handle}
          id="source"
        />
      )}
    </div>
  );
}

export const ExecutionStarNode = memo(ExecutionStarNodeComponent);
