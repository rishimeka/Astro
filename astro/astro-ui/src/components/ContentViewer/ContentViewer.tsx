'use client';

import { useMemo, useState } from 'react';
import { useProbes } from '@/hooks/useProbes';
import { useDirectives } from '@/hooks/useDirectives';
import styles from './ContentViewer.module.scss';

export interface ContentViewerProps {
  content: string;
  className?: string;
}

interface ParsedSegment {
  type: 'text' | 'probe' | 'directive' | 'variable';
  value: string;
  reference?: string;
}

interface TooltipData {
  name: string;
  description: string;
  type: 'probe' | 'directive' | 'variable';
}

function parseContent(content: string): ParsedSegment[] {
  const segments: ParsedSegment[] = [];
  const regex = /@(probe|directive|variable):([a-zA-Z0-9_-]+)/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(content)) !== null) {
    // Add text before match
    if (match.index > lastIndex) {
      segments.push({
        type: 'text',
        value: content.slice(lastIndex, match.index),
      });
    }

    // Add the reference
    const [fullMatch, refType, refName] = match;
    segments.push({
      type: refType as 'probe' | 'directive' | 'variable',
      value: fullMatch,
      reference: refName,
    });

    lastIndex = match.index + fullMatch.length;
  }

  // Add remaining text
  if (lastIndex < content.length) {
    segments.push({
      type: 'text',
      value: content.slice(lastIndex),
    });
  }

  return segments;
}

export default function ContentViewer({ content, className = '' }: ContentViewerProps) {
  const segments = useMemo(() => parseContent(content), [content]);
  const { probes } = useProbes();
  const { directives } = useDirectives();

  const [tooltip, setTooltip] = useState<{
    data: TooltipData;
    position: { x: number; y: number };
  } | null>(null);

  // Create lookup maps
  const probeMap = useMemo(() => {
    const map = new Map<string, { name: string; description: string }>();
    probes.forEach(p => map.set(p.name, { name: p.name, description: p.description }));
    return map;
  }, [probes]);

  const directiveMap = useMemo(() => {
    const map = new Map<string, { name: string; description: string }>();
    directives.forEach(d => map.set(d.id, { name: d.name, description: d.description }));
    return map;
  }, [directives]);

  const handleMouseEnter = (
    e: React.MouseEvent,
    segment: ParsedSegment
  ) => {
    if (segment.type === 'text' || !segment.reference) return;

    let data: TooltipData | null = null;

    if (segment.type === 'probe') {
      const probe = probeMap.get(segment.reference);
      if (probe) {
        data = { ...probe, type: 'probe' };
      } else {
        data = { name: segment.reference, description: 'Probe not found', type: 'probe' };
      }
    } else if (segment.type === 'directive') {
      const directive = directiveMap.get(segment.reference);
      if (directive) {
        data = { ...directive, type: 'directive' };
      } else {
        data = { name: segment.reference, description: 'Directive not found', type: 'directive' };
      }
    } else if (segment.type === 'variable') {
      data = { name: segment.reference, description: 'Runtime variable', type: 'variable' };
    }

    if (data) {
      const rect = (e.target as HTMLElement).getBoundingClientRect();
      setTooltip({
        data,
        position: { x: rect.left, y: rect.bottom + 4 },
      });
    }
  };

  const handleMouseLeave = () => {
    setTooltip(null);
  };

  return (
    <div className={styles.wrapper}>
      <pre className={`${styles.content} ${className}`}>
        {segments.map((segment, index) => {
          if (segment.type === 'text') {
            return <span key={index}>{segment.value}</span>;
          }

          return (
            <span
              key={index}
              className={`${styles.reference} ${styles[segment.type]}`}
              onMouseEnter={(e) => handleMouseEnter(e, segment)}
              onMouseLeave={handleMouseLeave}
            >
              {segment.value}
            </span>
          );
        })}
      </pre>

      {tooltip && (
        <div
          className={`${styles.tooltip} ${styles[`tooltip${tooltip.data.type.charAt(0).toUpperCase() + tooltip.data.type.slice(1)}`]}`}
          style={{
            left: `${tooltip.position.x}px`,
            top: `${tooltip.position.y}px`,
          }}
        >
          <div className={styles.tooltipHeader}>
            <span className={styles.tooltipType}>{tooltip.data.type}</span>
            <span className={styles.tooltipName}>{tooltip.data.name}</span>
          </div>
          <div className={styles.tooltipDescription}>{tooltip.data.description}</div>
        </div>
      )}
    </div>
  );
}
