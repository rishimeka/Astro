'use client';

import type { CSSProperties, ReactNode } from 'react';

export interface MonoProps {
  children: ReactNode;
  color?: string;
  size?: 'sm' | 'md' | 'lg';
  weight?: number;
  style?: CSSProperties;
  className?: string;
}

const SIZE_MAP = {
  sm: 'var(--t-mono-sm)',
  md: 'var(--t-mono)',
  lg: 'var(--t-mono-big)',
} as const;

export function Mono({ children, color, size = 'md', weight, style, className }: MonoProps) {
  return (
    <span
      className={className}
      style={{
        font: SIZE_MAP[size],
        letterSpacing: 'var(--trk-mono)',
        color: color ?? 'var(--ink-3)',
        fontWeight: weight,
        ...style,
      }}
    >
      {children}
    </span>
  );
}
