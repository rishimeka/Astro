'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';
import rehypeRaw from 'rehype-raw';
import styles from './Markdown.module.scss';

interface MarkdownProps {
  children: string;
  className?: string;
}

export function Markdown({ children, className }: MarkdownProps) {
  return (
    <div className={`${styles.markdown} ${className || ''}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize, rehypeRaw]}>
        {children}
      </ReactMarkdown>
    </div>
  );
}
