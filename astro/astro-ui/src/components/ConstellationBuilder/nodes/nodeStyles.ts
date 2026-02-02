import { CSSProperties } from 'react';
import { StarType } from '../types';

// Shared node styling constants
export const NODE_DIMENSIONS = {
  start: { width: 60, height: 60 },
  end: { width: 60, height: 60 },
  star: { width: 280, height: 120 },
} as const;

// Circular node base style (Start and End)
export const circularNodeStyle: CSSProperties = {
  width: 60,
  height: 60,
  borderRadius: '50%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'pointer',
};

// Start node specific style
export const startNodeStyle: CSSProperties = {
  ...circularNodeStyle,
  backgroundColor: 'var(--accent-primary)',
  border: 'none',
  boxShadow: '0 4px 12px rgba(108, 114, 255, 0.3)',
};

// End node specific style
export const endNodeStyle: CSSProperties = {
  ...circularNodeStyle,
  backgroundColor: 'var(--bg-elevated)',
  border: '2px solid var(--border-strong)',
};

// Star node base style
export const starNodeStyle: CSSProperties = {
  width: NODE_DIMENSIONS.star.width,
  minHeight: 100,
  backgroundColor: 'var(--bg-elevated)',
  borderRadius: 'var(--radius-sm)',
  borderWidth: 1,
  borderStyle: 'solid',
  borderColor: 'var(--border-default)',
  overflow: 'hidden',
  cursor: 'pointer',
  transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
};

// Star node states
export const starNodeHoverStyle: CSSProperties = {
  borderColor: 'var(--border-strong)',
};

export const starNodeSelectedStyle: CSSProperties = {
  borderColor: 'var(--accent-primary)',
  boxShadow: '0 0 0 2px rgba(108, 114, 255, 0.2)',
};

export const starNodeErrorStyle: CSSProperties = {
  borderColor: 'var(--accent-danger)',
  boxShadow: '0 0 0 2px rgba(255, 92, 92, 0.2)',
};

export const starNodeRunningStyle: CSSProperties = {
  borderColor: 'var(--accent-primary)',
  animation: 'pulse 2s infinite',
};

// Handle styles
export const handleStyle: CSSProperties = {
  width: 10,
  height: 10,
  backgroundColor: 'var(--accent-primary)',
  border: '2px solid var(--bg-primary)',
  borderRadius: '50%',
};

// Label style for Start/End nodes
export const nodeLabelStyle: CSSProperties = {
  position: 'absolute',
  top: '100%',
  left: '50%',
  transform: 'translateX(-50%)',
  marginTop: 8,
  fontFamily: 'var(--font-body)',
  fontSize: 12,
  color: 'var(--text-secondary)',
  whiteSpace: 'nowrap',
};

// Icon color mapping for star types
export const starTypeColors: Record<StarType, string> = {
  worker: 'var(--accent-primary)',
  planning: 'var(--color-success)',
  eval: 'var(--color-warning)',
  synthesis: 'var(--color-info)',
  execution: 'var(--accent-primary)',
  docex: '#8B5CF6', // purple
};

// Star type display names
export const starTypeLabels: Record<StarType, string> = {
  worker: 'Worker',
  planning: 'Planning',
  eval: 'Eval',
  synthesis: 'Synthesis',
  execution: 'Execution',
  docex: 'DocEx',
};
