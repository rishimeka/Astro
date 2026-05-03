'use client';

import type { CSSProperties } from 'react';

export interface IconProps {
  name: string;
  size?: number;
  color?: string;
  fill?: boolean;
  style?: CSSProperties;
  className?: string;
}

export function Icon({ name, size = 20, color, fill = false, style, className }: IconProps) {
  return (
    <span
      className={`material-symbols-outlined ${className ?? ''}`}
      style={{
        fontSize: size,
        color,
        fontVariationSettings: `'FILL' ${fill ? 1 : 0}, 'wght' 400, 'GRAD' 0, 'opsz' ${size}`,
        lineHeight: 1,
        verticalAlign: 'middle',
        userSelect: 'none',
        ...style,
      }}
    >
      {name}
    </span>
  );
}
