'use client';

import type { CSSProperties } from 'react';

export interface TickBarProps {
  value: number;
  total?: number;
  color?: string;
  width?: number;
  style?: CSSProperties;
  className?: string;
}

export function TickBar({
  value,
  total = 20,
  color = 'var(--accent)',
  width = 80,
  style,
  className,
}: TickBarProps) {
  const filled = Math.round(Math.min(1, Math.max(0, value)) * total);

  return (
    <svg
      className={className}
      width={width}
      height={8}
      viewBox={`0 0 ${total * 4} 8`}
      style={style}
    >
      {Array.from({ length: total }, (_, i) => (
        <rect
          key={i}
          x={i * 4}
          y={1}
          width={2}
          height={6}
          rx={0.5}
          fill={i < filled ? color : 'var(--rule-1)'}
        />
      ))}
    </svg>
  );
}
