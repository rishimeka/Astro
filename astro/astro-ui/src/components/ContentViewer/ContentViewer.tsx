'use client';

import { useMemo } from 'react';
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

  return (
    <pre className={`${styles.content} ${className}`}>
      {segments.map((segment, index) => {
        if (segment.type === 'text') {
          return <span key={index}>{segment.value}</span>;
        }

        return (
          <span
            key={index}
            className={`${styles.reference} ${styles[segment.type]}`}
            title={`${segment.type}: ${segment.reference}`}
          >
            {segment.value}
          </span>
        );
      })}
    </pre>
  );
}
