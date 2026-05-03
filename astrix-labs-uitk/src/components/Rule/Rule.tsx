'use client';

import type { CSSProperties, ReactNode } from 'react';

export interface RuleProps {
  children?: ReactNode;
  style?: CSSProperties;
  className?: string;
}

export function Rule({ children, style, className }: RuleProps) {
  if (!children) {
    return (
      <hr
        className={className}
        style={{
          border: 'none',
          borderTop: '1px solid var(--rule-1)',
          margin: '16px 0',
          ...style,
        }}
      />
    );
  }

  return (
    <div
      className={className}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        font: 'var(--t-label)',
        textTransform: 'uppercase',
        letterSpacing: 'var(--trk-label)',
        color: 'var(--ink-3)',
        ...style,
      }}
    >
      <span style={{ flex: 1, height: 1, background: 'var(--rule-1)' }} />
      {children}
      <span style={{ flex: 1, height: 1, background: 'var(--rule-1)' }} />
    </div>
  );
}
