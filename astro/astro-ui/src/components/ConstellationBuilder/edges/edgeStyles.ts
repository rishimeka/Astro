import { CSSProperties } from 'react';

// Default edge style
export const defaultEdgeStyle: CSSProperties = {
  stroke: 'rgba(255, 255, 255, 0.3)',
  strokeWidth: 2,
};

// Selected edge style
export const selectedEdgeStyle: CSSProperties = {
  stroke: 'var(--accent-primary)',
  strokeWidth: 2,
};

// Animated (running) edge style - CSS animation applied separately
export const animatedEdgeStyle: CSSProperties = {
  stroke: 'var(--accent-primary)',
  strokeWidth: 2,
  strokeDasharray: 5,
};

// Condition label styles
export const conditionLabelBaseStyle: CSSProperties = {
  padding: '2px 8px',
  borderRadius: 10,
  fontSize: 10,
  fontFamily: 'var(--font-mono)',
  fontWeight: 600,
  textTransform: 'uppercase' as const,
  letterSpacing: '0.5px',
};

export const continueConditionStyle: CSSProperties = {
  ...conditionLabelBaseStyle,
  backgroundColor: '#10B981',
  color: 'white',
};

export const loopConditionStyle: CSSProperties = {
  ...conditionLabelBaseStyle,
  backgroundColor: '#F59E0B',
  color: 'white',
};

// Delete button style
export const deleteButtonStyle: CSSProperties = {
  width: 20,
  height: 20,
  borderRadius: '50%',
  backgroundColor: 'var(--accent-danger)',
  border: 'none',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'pointer',
  opacity: 0,
  transition: 'opacity 0.2s ease',
};

export const deleteButtonVisibleStyle: CSSProperties = {
  ...deleteButtonStyle,
  opacity: 1,
};
