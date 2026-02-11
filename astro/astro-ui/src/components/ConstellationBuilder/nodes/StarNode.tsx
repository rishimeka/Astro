'use client';

import { memo, useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Handle, Position, NodeProps } from 'reactflow';
import {
  Cog,
  GitBranch,
  CheckCircle,
  Combine,
  Play,
  FileText,
  MoreHorizontal,
  Zap,
  PenLine,
  Pause,
} from 'lucide-react';
import { StarNodeData, StarType } from '../types';
import {
  starNodeStyle,
  starNodeSelectedStyle,
  starNodeErrorStyle,
  handleStyle,
  starTypeColors,
} from './nodeStyles';
import styles from './StarNode.module.scss';

interface StarNodeProps extends NodeProps<StarNodeData> {
  selected: boolean;
  isValidationError?: boolean;
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

function StarNodeComponent({ id, data, selected, isValidationError }: StarNodeProps) {
  const [showMenu, setShowMenu] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const [menuPosition, setMenuPosition] = useState({ top: 0, left: 0 });
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const Icon = starTypeIcons[data.starType];
  const iconColor = starTypeColors[data.starType];
  const isEvalStar = data.starType === 'eval';

  // Handle delete node
  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowMenu(false);
    // Dispatch custom event for Canvas to handle
    window.dispatchEvent(new CustomEvent('deleteNode', { detail: { id } }));
  };

  // Handle edit node (select it to show in properties panel)
  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowMenu(false);
    // Dispatch custom event to select this node for editing
    window.dispatchEvent(new CustomEvent('selectNode', { detail: { id } }));
  };

  // Calculate menu position when opening
  const handleMenuToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!showMenu && menuButtonRef.current) {
      const rect = menuButtonRef.current.getBoundingClientRect();
      setMenuPosition({
        top: rect.bottom + 4,
        left: rect.right - 120, // Menu width is ~120px, align right edge
      });
    }
    setShowMenu(!showMenu);
  };

  // Close menu when clicking outside
  useEffect(() => {
    if (!showMenu) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (
        menuRef.current &&
        !menuRef.current.contains(e.target as Node) &&
        menuButtonRef.current &&
        !menuButtonRef.current.contains(e.target as Node)
      ) {
        setShowMenu(false);
      }
    };

    // Use capture phase to catch events before ReactFlow handles them
    document.addEventListener('mousedown', handleClickOutside, true);
    return () => document.removeEventListener('mousedown', handleClickOutside, true);
  }, [showMenu]);

  // Compute node style based on state
  const computedStyle = {
    ...starNodeStyle,
    ...(isHovered && { borderColor: 'var(--border-strong)' }),
    ...(selected && starNodeSelectedStyle),
    ...(isValidationError && starNodeErrorStyle),
  };

  return (
    <div
      className={styles.starNode}
      style={computedStyle}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Left}
        style={handleStyle}
        id="target"
      />

      {/* Header */}
      <div className={styles.header}>
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
        <button
          ref={menuButtonRef}
          className={styles.menuButton}
          onClick={handleMenuToggle}
        >
          <MoreHorizontal size={16} color="var(--text-secondary)" />
        </button>

        {showMenu && createPortal(
          <div
            ref={menuRef}
            className={styles.menu}
            style={{
              position: 'fixed',
              top: menuPosition.top,
              left: menuPosition.left,
            }}
          >
            <button className={styles.menuItem} onClick={handleEdit}>Edit</button>
            <button className={styles.menuItem} onClick={() => setShowMenu(false)}>Duplicate</button>
            <button
              className={styles.menuItem}
              style={{ color: 'var(--accent-danger)' }}
              onClick={handleDelete}
            >
              Delete
            </button>
          </div>,
          document.body
        )}
      </div>

      {/* Body */}
      <div className={styles.body}>
        <div className={styles.directive}>
          Directive: <span className={styles.directiveName}>{data.directiveName}</span>
        </div>

        {/* Badges */}
        {(data.hasProbes || data.hasVariables) && (
          <div className={styles.badges}>
            {data.hasProbes && data.probeCount > 0 && (
              <div className={styles.probeBadge}>
                <Zap size={12} />
                <span>{data.probeCount}</span>
              </div>
            )}
            {data.hasVariables && data.variableCount > 0 && (
              <div className={styles.variableBadge}>
                <PenLine size={12} />
                <span>{data.variableCount}</span>
              </div>
            )}
          </div>
        )}

        {/* Confirmation indicator */}
        {data.requiresConfirmation && (
          <div className={styles.confirmation}>
            <Pause size={12} />
            <span>Requires confirmation</span>
          </div>
        )}
      </div>

      {/* Output Handles */}
      {isEvalStar ? (
        <>
          <Handle
            type="source"
            position={Position.Right}
            style={{ ...handleStyle, top: '35%' }}
            id="loop"
          />
          <Handle
            type="source"
            position={Position.Right}
            style={{ ...handleStyle, top: '65%' }}
            id="continue"
          />
          <div className={styles.handleLabelsHorizontal}>
            <span className={styles.loopLabel}>loop</span>
            <span className={styles.continueLabel}>continue</span>
          </div>
        </>
      ) : (
        <Handle
          type="source"
          position={Position.Right}
          style={handleStyle}
          id="source"
        />
      )}
    </div>
  );
}

export const StarNode = memo(StarNodeComponent);
