'use client';

import type { CSSProperties, ReactNode } from 'react';

export type TagTone = 'default' | 'accent' | 'seal' | 'live' | 'ochre' | 'danger';

export interface TagProps {
  children: ReactNode;
  tone?: TagTone;
  style?: CSSProperties;
  className?: string;
}

const TONE_STYLES: Record<TagTone, CSSProperties> = {
  default: {
    color: 'var(--ink-3)',
    borderColor: 'var(--rule-1)',
    background: 'var(--paper-2)',
  },
  accent: {
    color: 'var(--accent)',
    borderColor: 'var(--accent-wash)',
    background: 'var(--accent-wash)',
  },
  seal: {
    color: 'var(--seal-ink)',
    borderColor: 'var(--seal-wash)',
    background: 'var(--seal-wash)',
  },
  live: {
    color: 'var(--live)',
    borderColor: 'oklch(0.45 0.10 145 / 0.15)',
    background: 'oklch(0.45 0.10 145 / 0.08)',
  },
  ochre: {
    color: 'var(--ochre)',
    borderColor: 'oklch(0.50 0.08 80 / 0.15)',
    background: 'oklch(0.50 0.08 80 / 0.08)',
  },
  danger: {
    color: 'var(--danger)',
    borderColor: 'var(--danger-wash)',
    background: 'var(--danger-wash)',
  },
};

export function Tag({ children, tone = 'default', style, className }: TagProps) {
  return (
    <span
      className={className}
      style={{
        font: 'var(--t-label)',
        textTransform: 'uppercase',
        letterSpacing: 'var(--trk-label)',
        border: '1px solid',
        borderRadius: 'var(--r-sm)',
        padding: '3px 6px',
        whiteSpace: 'nowrap',
        ...TONE_STYLES[tone],
        ...style,
      }}
    >
      {children}
    </span>
  );
}
